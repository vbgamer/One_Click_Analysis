"""
explainability.py — Explainability layer for Expense Intelligence System.

Functions
---------
explain_anomaly         : Detailed explanation for a flagged transaction.
explain_recommendation  : Feature attribution for a recommendation.
generate_model_card     : Model card summarising the full AI analysis.
compute_confidence_score : Overall confidence in the AI results.
"""

import json

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional: shap
# ---------------------------------------------------------------------------
try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_col(df: pd.DataFrame, schema: dict, key: str) -> str | None:
    col = schema.get(key)
    return col if col and col in df.columns else None


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_anomaly(
    row: pd.Series,
    df: pd.DataFrame,
    schema: dict,
    anomaly_score: float,
) -> dict:
    """Generate a detailed explanation for why a transaction was flagged.

    Parameters
    ----------
    row : pd.Series
        The flagged transaction row.
    df : pd.DataFrame
        Full dataframe (used for population statistics).
    schema : dict
        Output of ``etl.infer_schema(df)``.
    anomaly_score : float
        Normalised anomaly score (0-1).

    Returns
    -------
    dict
        Keys: ``summary``, ``factors`` (list), ``visualization_data``.
    """
    try:
        amount_col = _get_col(df, schema, "amount_col")
        date_col = _get_col(df, schema, "date_col")
        payer_col = _get_col(df, schema, "payer_col")
        category_col = _get_col(df, schema, "category_col")

        factors: list = []
        amount = _safe_float(row.get(amount_col)) if amount_col else 0.0
        all_amounts = (
            pd.to_numeric(df[amount_col], errors="coerce").dropna().values
            if amount_col
            else np.array([])
        )
        global_mean = float(np.mean(all_amounts)) if len(all_amounts) > 0 else 0.0
        global_std = float(np.std(all_amounts)) if len(all_amounts) > 0 else 0.0

        # Factor 1: Amount vs global average
        if global_mean > 0:
            ratio = amount / global_mean
            z = (amount - global_mean) / (global_std + 1e-9)
            weight = min(abs(z) / 5.0, 1.0)
            factors.append(
                {
                    "feature": "Transaction Amount",
                    "value": round(amount, 2),
                    "population_avg": round(global_mean, 2),
                    "z_score": round(z, 2),
                    "weight": round(weight, 3),
                    "direction": "high" if amount > global_mean else "low",
                    "description": (
                        f"₹{amount:,.0f} is {abs(ratio - 1)*100:.0f}% "
                        f"{'above' if amount > global_mean else 'below'} average"
                    ),
                }
            )

        # Factor 2: Payer-specific anomaly
        if payer_col and payer_col in row.index:
            payer = str(row[payer_col])
            payer_amounts = pd.to_numeric(
                df[df[payer_col] == payer][amount_col], errors="coerce"
            ).dropna().values if amount_col else np.array([])
            if len(payer_amounts) > 1:
                payer_mean = float(np.mean(payer_amounts))
                payer_std = float(np.std(payer_amounts))
                payer_z = (amount - payer_mean) / (payer_std + 1e-9)
                if abs(payer_z) > 1.5:
                    factors.append(
                        {
                            "feature": f"Payer ({payer}) Behaviour",
                            "value": round(amount, 2),
                            "population_avg": round(payer_mean, 2),
                            "z_score": round(payer_z, 2),
                            "weight": round(min(abs(payer_z) / 5.0, 1.0), 3),
                            "direction": "high" if amount > payer_mean else "low",
                            "description": (
                                f"{payer}'s usual average is ₹{payer_mean:,.0f}; "
                                f"this is {abs(payer_z):.1f}σ away"
                            ),
                        }
                    )

        # Factor 3: Temporal anomaly
        if date_col and date_col in row.index:
            txn_date = pd.to_datetime(row[date_col], errors="coerce")
            if pd.notna(txn_date):
                dow = txn_date.day_name()
                df_dates = pd.to_datetime(df[date_col], errors="coerce")
                dow_mask = df_dates.dt.day_name() == dow
                dow_amounts = (
                    pd.to_numeric(df[dow_mask][amount_col], errors="coerce").dropna()
                    if amount_col
                    else pd.Series([], dtype=float)
                )
                if len(dow_amounts) > 2:
                    dow_mean = float(dow_amounts.mean())
                    if dow_mean > 0 and amount > 2.5 * dow_mean:
                        factors.append(
                            {
                                "feature": f"Day of Week ({dow})",
                                "value": round(amount, 2),
                                "population_avg": round(dow_mean, 2),
                                "z_score": None,
                                "weight": 0.5,
                                "direction": "high",
                                "description": (
                                    f"On {dow}s, average spend is ₹{dow_mean:,.0f}; "
                                    f"this is {amount/dow_mean:.1f}× higher"
                                ),
                            }
                        )

        # Sort by weight
        factors.sort(key=lambda f: f["weight"], reverse=True)

        # Build summary
        top_reason = factors[0]["description"] if factors else "Statistical outlier detected"
        summary = (
            f"Anomaly score {anomaly_score:.2f}/1.0 — {top_reason}."
        )

        # Visualization data (bar chart of factor weights)
        viz_data = {
            "type": "bar",
            "labels": [f["feature"] for f in factors],
            "values": [f["weight"] for f in factors],
            "directions": [f["direction"] for f in factors],
        }

        return {
            "summary": summary,
            "anomaly_score": round(anomaly_score, 3),
            "factors": factors,
            "visualization_data": viz_data,
        }

    except Exception as e:
        return {
            "summary": "Could not generate explanation",
            "factors": [],
            "visualization_data": {},
            "error": str(e),
        }


def explain_recommendation(rec: dict, df: pd.DataFrame, schema: dict) -> dict:
    """Generate SHAP-style feature attribution for a recommendation.

    Parameters
    ----------
    rec : dict
        A recommendation dict from ``recommendations.generate_recommendations``.
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``key_drivers`` (list of {feature, contribution, direction}),
        ``recommendation_type``, ``confidence``.
    """
    try:
        supporting = rec.get("supporting_data", {})
        rec_type = rec.get("type", "unknown")
        confidence = rec.get("confidence", 0.5)

        key_drivers: list = []

        # Extract drivers from supporting data
        for key, val in supporting.items():
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                direction = "positive" if val > 0 else "negative"
                # Contribution heuristic: normalise value to [-1, 1]
                contribution = round(min(abs(float(val)) / 1000, 1.0), 3)
                key_drivers.append(
                    {
                        "feature": key.replace("_", " ").title(),
                        "contribution": contribution,
                        "direction": direction,
                        "raw_value": round(float(val), 2),
                    }
                )
            elif isinstance(val, str):
                key_drivers.append(
                    {
                        "feature": key.replace("_", " ").title(),
                        "contribution": 0.5,
                        "direction": "neutral",
                        "raw_value": val,
                    }
                )

        # Sort by contribution magnitude
        key_drivers.sort(key=lambda d: abs(d["contribution"]), reverse=True)

        return {
            "recommendation_type": rec_type,
            "confidence": confidence,
            "key_drivers": key_drivers[:6],  # Top 6 drivers
        }

    except Exception as e:
        return {
            "recommendation_type": rec.get("type", "unknown"),
            "confidence": 0.0,
            "key_drivers": [],
            "error": str(e),
        }


def generate_model_card(
    df: pd.DataFrame,
    schema: dict,
    ml_results: dict,
) -> dict:
    """Generate a model card explaining the full AI analysis.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    ml_results : dict
        Aggregated results from the pipeline.

    Returns
    -------
    dict
        Full model card with metadata, data quality, and limitations.
    """
    try:
        n_rows, n_cols = df.shape
        missing_pct = round(df.isnull().sum().sum() / (n_rows * n_cols) * 100, 2) if n_rows > 0 else 0

        detected_cols = {k: v for k, v in schema.items() if v is not None}

        limitations = []
        if n_rows < 30:
            limitations.append("Very small dataset (<30 rows) — results may be unreliable")
        if missing_pct > 20:
            limitations.append(f"High missing data rate ({missing_pct}%) — imputed values may skew results")
        if len(detected_cols) < 3:
            limitations.append("Few expense-specific columns detected — analysis may be incomplete")
        if not schema.get("date_col"):
            limitations.append("No date column detected — time-series forecasting is disabled")
        if not schema.get("payer_col"):
            limitations.append("No payer column detected — settlement optimisation is disabled")

        quality_score = ml_results.get("quality_score", {})
        leakage_warnings = ml_results.get("leakage", [])

        confidence = compute_confidence_score(df, schema, ml_results)

        return {
            "model_name": "Expense Intelligence AI v1.0",
            "model_version": "1.0.0",
            "created_at": str(pd.Timestamp.now().isoformat()),
            "dataset_info": {
                "n_rows": n_rows,
                "n_cols": n_cols,
                "missing_pct": missing_pct,
                "duplicate_pct": round(df.duplicated().sum() / max(n_rows, 1) * 100, 2),
            },
            "schema_detected": schema,
            "columns_detected": len(detected_cols),
            "data_quality_score": quality_score,
            "leakage_warnings": leakage_warnings,
            "limitations": limitations,
            "overall_confidence": confidence.get("score", 0),
            "confidence_breakdown": confidence.get("breakdown", {}),
            "modules_used": [
                "etl",
                "anomaly",
                "forecasting",
                "nlp",
                "settlement",
                "recommendations",
                "explainability",
            ],
        }

    except Exception as e:
        return {"error": str(e)}


def compute_confidence_score(
    df: pd.DataFrame,
    schema: dict,
    results: dict,
) -> dict:
    """Compute overall confidence in the AI analysis (0-100).

    Confidence is based on: data quality, sample size, leakage detection,
    and column detection coverage.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    results : dict
        Aggregated pipeline results.

    Returns
    -------
    dict
        Keys: ``score`` (float 0-100), ``breakdown`` (dict).
    """
    try:
        breakdown: dict = {}

        # 1. Sample size score (more data = more confident)
        n = len(df)
        if n >= 500:
            sample_score = 100.0
        elif n >= 100:
            sample_score = 70.0 + (n - 100) / 400 * 30
        elif n >= 20:
            sample_score = 40.0 + (n - 20) / 80 * 30
        else:
            sample_score = max(10.0, n * 2.0)
        breakdown["sample_size"] = round(sample_score, 1)

        # 2. Schema coverage (how many key columns were detected)
        all_schema_keys = ["date_col", "amount_col", "payer_col", "category_col", "merchant_col"]
        detected = sum(1 for k in all_schema_keys if schema.get(k))
        schema_score = round(detected / len(all_schema_keys) * 100, 1)
        breakdown["schema_coverage"] = schema_score

        # 3. Data quality score
        if isinstance(results.get("quality_score"), dict):
            quality = float(results["quality_score"].get("score", 70))
        else:
            missing_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1] + 1) * 100
            quality = max(0, 100 - missing_pct * 2)
        breakdown["data_quality"] = round(quality, 1)

        # 4. Leakage penalty
        leakage = results.get("leakage", [])
        leakage_penalty = min(len(leakage) * 15, 40)
        breakdown["leakage_penalty"] = -leakage_penalty

        # Overall (weighted)
        score = round(
            0.30 * sample_score
            + 0.25 * schema_score
            + 0.30 * quality
            + 0.15 * max(0, 100 - leakage_penalty),
            1,
        )
        score = max(0.0, min(100.0, score))

        return {"score": score, "breakdown": breakdown}

    except Exception as e:
        return {"score": 50.0, "breakdown": {"error": str(e)}}
