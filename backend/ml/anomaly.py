"""
anomaly.py — Anomaly detection engine for Expense Intelligence System.

Functions
---------
detect_anomalies            : IsolationForest + z-score on transactions.
detect_behavioral_anomalies : Payer-level and temporal spike detection.
generate_anomaly_reasons    : Human-readable explanation for flagged rows.
"""

from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional: scikit-learn
# ---------------------------------------------------------------------------
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

# Optional: scipy
try:
    from scipy import stats as scipy_stats
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_amount_col(df: pd.DataFrame, schema: dict) -> str | None:
    col = schema.get("amount_col")
    if col and col in df.columns:
        return col
    return None


def _get_date_col(df: pd.DataFrame, schema: dict) -> str | None:
    col = schema.get("date_col")
    if col and col in df.columns:
        return col
    return None


def _severity(score: float) -> str:
    if score >= 0.7:
        return "high"
    elif score >= 0.4:
        return "medium"
    return "low"


def _build_feature_matrix(df: pd.DataFrame, amount_col: str, date_col: str | None) -> np.ndarray:
    """Build feature matrix for anomaly detection."""
    features = []

    amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0).values
    features.append(amounts.reshape(-1, 1))

    if date_col and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        day_of_week = dates.dt.dayofweek.fillna(3).values  # default Wed
        month = dates.dt.month.fillna(1).values
        features.append(day_of_week.reshape(-1, 1))
        features.append(month.reshape(-1, 1))

    return np.hstack(features).astype(float)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_anomalies(df: pd.DataFrame, schema: dict) -> dict:
    """Detect transaction-level anomalies using IsolationForest and z-score.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``anomalies`` (list), ``anomaly_count``, ``anomaly_rate_pct``,
        ``total_anomalous_amount``, ``plotly_heatmap_data``, ``available``.
    """
    amount_col = _get_amount_col(df, schema)
    if not amount_col:
        return {"available": False, "reason": "amount_col not found in schema/dataframe"}

    if len(df) < 5:
        return {"available": False, "reason": "Fewer than 5 rows — insufficient for anomaly detection"}

    date_col = _get_date_col(df, schema)

    try:
        df_work = df.copy().reset_index(drop=True)
        df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)

        X = _build_feature_matrix(df_work, amount_col, date_col)

        # --- Z-score anomaly flags ---
        amounts = df_work[amount_col].values
        mean_a = np.mean(amounts)
        std_a = np.std(amounts)
        z_scores = np.abs((amounts - mean_a) / (std_a + 1e-9))
        z_flag = z_scores > 2.5  # flag if |z| > 2.5σ

        # --- IsolationForest ---
        if _SKLEARN_AVAILABLE and len(df_work) >= 10:
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            contamination = min(0.15, max(0.01, 10 / len(df_work)))
            iso = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                random_state=42,
            )
            iso_labels = iso.fit_predict(X_scaled)  # -1 = anomaly
            iso_scores_raw = iso.score_samples(X_scaled)
            # Normalise to [0, 1] where 1 = most anomalous
            iso_scores_norm = 1 - (iso_scores_raw - iso_scores_raw.min()) / (
                iso_scores_raw.max() - iso_scores_raw.min() + 1e-9
            )
            iso_flag = iso_labels == -1
        else:
            iso_flag = np.zeros(len(df_work), dtype=bool)
            iso_scores_norm = np.zeros(len(df_work))

        # Combine flags
        combined_flag = iso_flag | z_flag

        anomalies = []
        for idx in np.where(combined_flag)[0]:
            row = df_work.iloc[idx]
            amount = float(row[amount_col])

            # Determine reason
            reasons = []
            if z_scores[idx] > 2.5:
                reasons.append(
                    f"Amount {amount:,.2f} is {z_scores[idx]:.1f}σ above average"
                )
            if iso_flag[idx]:
                reasons.append("Flagged as outlier by Isolation Forest")
            reason_str = "; ".join(reasons) if reasons else "Statistical outlier"

            # Compute a normalised anomaly score
            z_score_norm = min(float(z_scores[idx]) / 5.0, 1.0)
            iso_s = float(iso_scores_norm[idx]) if _SKLEARN_AVAILABLE else 0.0
            anomaly_score = round((z_score_norm * 0.4 + iso_s * 0.6), 3)

            row_dict = {
                "row_index": int(idx),
                "amount": amount,
                "reason": generate_anomaly_reasons(row, df_work, schema, anomaly_score),
                "anomaly_score": anomaly_score,
                "severity": _severity(anomaly_score),
            }
            if date_col and date_col in row.index:
                row_dict["date"] = str(row[date_col])
            payer_col = schema.get("payer_col")
            if payer_col and payer_col in row.index:
                row_dict["payer"] = str(row[payer_col])
            merchant_col = schema.get("merchant_col")
            if merchant_col and merchant_col in row.index:
                row_dict["merchant"] = str(row[merchant_col])

            anomalies.append(row_dict)

        # Sort by anomaly score descending
        anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)

        total_anomalous = sum(a["amount"] for a in anomalies)
        anomaly_rate = round(len(anomalies) / len(df_work) * 100, 2)

        # Plotly heatmap data (date vs anomaly score)
        heatmap_data: dict = {"x": [], "y": [], "text": []}
        if date_col and date_col in df_work.columns:
            dates_col = pd.to_datetime(df_work[date_col], errors="coerce")
            for a in anomalies:
                idx = a["row_index"]
                if idx < len(df_work) and not pd.isna(dates_col.iloc[idx]):
                    heatmap_data["x"].append(str(dates_col.iloc[idx].date()))
                    heatmap_data["y"].append(a["anomaly_score"])
                    heatmap_data["text"].append(a["reason"])

        return {
            "available": True,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "anomaly_rate_pct": anomaly_rate,
            "total_anomalous_amount": round(total_anomalous, 2),
            "plotly_heatmap_data": heatmap_data,
        }

    except Exception as e:
        return {"available": False, "reason": f"Anomaly detection error: {e}"}


def detect_behavioral_anomalies(df: pd.DataFrame, schema: dict) -> dict:
    """Detect unusual payer behaviour and temporal spending spikes.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``payer_anomalies``, ``temporal_anomalies``, ``available``.
    """
    amount_col = _get_amount_col(df, schema)
    if not amount_col:
        return {"available": False, "reason": "amount_col not found in schema/dataframe"}

    date_col = _get_date_col(df, schema)
    payer_col = schema.get("payer_col")

    try:
        df_work = df.copy().reset_index(drop=True)
        df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)

        payer_anomalies: list = []
        temporal_anomalies: list = []

        # --- Payer behavioural anomalies ---
        if payer_col and payer_col in df_work.columns:
            payer_stats = df_work.groupby(payer_col)[amount_col].agg(
                ["mean", "std", "count", "sum"]
            )
            global_mean = float(df_work[amount_col].mean())

            for payer, row in payer_stats.iterrows():
                payer_mean = float(row["mean"])
                payer_count = int(row["count"])

                if payer_count < 3:
                    continue  # Not enough data

                # Individual transactions vs their own average
                payer_txns = df_work[df_work[payer_col] == payer][amount_col]
                max_txn = float(payer_txns.max())
                payer_std = float(row["std"]) if not np.isnan(float(row["std"])) else 0

                if payer_mean > 0 and max_txn > 3 * payer_mean:
                    payer_anomalies.append(
                        {
                            "payer": str(payer),
                            "type": "sudden_spike",
                            "avg_spend": round(payer_mean, 2),
                            "max_transaction": round(max_txn, 2),
                            "ratio": round(max_txn / payer_mean, 2),
                            "description": (
                                f"{payer} has a transaction of ₹{max_txn:,.2f} which is "
                                f"{max_txn/payer_mean:.1f}× their average of ₹{payer_mean:,.2f}"
                            ),
                        }
                    )

                # Check if payer spends much more than global average
                if global_mean > 0 and payer_mean > 2.5 * global_mean:
                    payer_anomalies.append(
                        {
                            "payer": str(payer),
                            "type": "high_spender",
                            "avg_spend": round(payer_mean, 2),
                            "global_avg": round(global_mean, 2),
                            "ratio": round(payer_mean / global_mean, 2),
                            "description": (
                                f"{payer}'s average spend of ₹{payer_mean:,.2f} is "
                                f"{payer_mean/global_mean:.1f}× the global average"
                            ),
                        }
                    )

        # --- Temporal anomalies ---
        if date_col and date_col in df_work.columns:
            dates_parsed = pd.to_datetime(df_work[date_col], errors="coerce")
            df_work["_dow"] = dates_parsed.dt.day_name()
            df_work["_month"] = dates_parsed.dt.month_name()

            # Day-of-week spikes
            dow_mean = df_work.groupby("_dow")[amount_col].mean()
            global_mean = float(df_work[amount_col].mean())
            for dow, mean_val in dow_mean.items():
                if global_mean > 0 and float(mean_val) > 2.5 * global_mean:
                    temporal_anomalies.append(
                        {
                            "period": str(dow),
                            "type": "day_of_week_spike",
                            "mean_spend": round(float(mean_val), 2),
                            "global_avg": round(global_mean, 2),
                            "ratio": round(float(mean_val) / global_mean, 2),
                            "description": (
                                f"Spending on {dow}s is {float(mean_val)/global_mean:.1f}× "
                                f"higher than average (₹{float(mean_val):,.2f} vs ₹{global_mean:,.2f})"
                            ),
                        }
                    )

            # Monthly spikes
            month_mean = df_work.groupby("_month")[amount_col].mean()
            for month, mean_val in month_mean.items():
                if global_mean > 0 and float(mean_val) > 2.0 * global_mean:
                    temporal_anomalies.append(
                        {
                            "period": str(month),
                            "type": "month_spike",
                            "mean_spend": round(float(mean_val), 2),
                            "global_avg": round(global_mean, 2),
                            "ratio": round(float(mean_val) / global_mean, 2),
                            "description": (
                                f"{month} average spending of ₹{float(mean_val):,.2f} is "
                                f"{float(mean_val)/global_mean:.1f}× higher than the overall average"
                            ),
                        }
                    )

        return {
            "available": True,
            "payer_anomalies": payer_anomalies,
            "temporal_anomalies": temporal_anomalies,
        }

    except Exception as e:
        return {"available": False, "reason": f"Behavioral anomaly detection error: {e}"}


def generate_anomaly_reasons(
    row: pd.Series, df: pd.DataFrame, schema: dict, anomaly_score: float
) -> str:
    """Generate a human-readable explanation for a flagged transaction.

    Parameters
    ----------
    row : pd.Series
        The transaction row.
    df : pd.DataFrame
        Full dataframe (used to compute population stats).
    schema : dict
        Output of ``etl.infer_schema(df)``.
    anomaly_score : float
        Normalised anomaly score (0-1).

    Returns
    -------
    str
        One-sentence human-readable explanation.
    """
    try:
        amount_col = schema.get("amount_col")
        payer_col = schema.get("payer_col")

        if not amount_col or amount_col not in df.columns:
            return "Transaction flagged as anomalous"

        amount = float(row[amount_col]) if pd.notna(row.get(amount_col)) else 0.0
        all_amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
        global_avg = float(all_amounts.mean())
        ratio = amount / global_avg if global_avg > 0 else 1.0

        payer_str = ""
        if payer_col and payer_col in row.index and pd.notna(row.get(payer_col)):
            payer = str(row[payer_col])
            payer_amounts = pd.to_numeric(
                df[df[payer_col] == payer][amount_col], errors="coerce"
            ).dropna()
            payer_avg = float(payer_amounts.mean()) if len(payer_amounts) > 0 else global_avg
            payer_ratio = amount / payer_avg if payer_avg > 0 else ratio
            payer_str = (
                f" {payer}'s average spend of ₹{payer_avg:,.0f}"
                if payer_avg != global_avg
                else f" the group average of ₹{global_avg:,.0f}"
            )
            effective_ratio = payer_ratio
        else:
            payer_str = f" the average of ₹{global_avg:,.0f}"
            effective_ratio = ratio

        if effective_ratio >= 2.0:
            return (
                f"This ₹{amount:,.0f} transaction is {effective_ratio:.1f}×"
                f" above{payer_str}"
            )
        elif amount < 1:
            return f"Unusually small transaction: ₹{amount:,.2f}"
        else:
            return (
                f"Transaction of ₹{amount:,.0f} is statistically unusual "
                f"(anomaly score: {anomaly_score:.2f})"
            )

    except Exception:
        return "Transaction flagged as statistically anomalous"
