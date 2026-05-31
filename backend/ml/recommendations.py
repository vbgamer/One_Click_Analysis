"""
recommendations.py — Recommendation engine for Expense Intelligence System.

Functions
---------
generate_recommendations  : Data-backed spending recommendations.
compute_optimization_score : 0-100 financial optimisation score.
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_amount_col(df: pd.DataFrame, schema: dict) -> str | None:
    col = schema.get("amount_col")
    return col if col and col in df.columns else None


def _get_date_col(df: pd.DataFrame, schema: dict) -> str | None:
    col = schema.get("date_col")
    return col if col and col in df.columns else None


def _get_payer_col(df: pd.DataFrame, schema: dict) -> str | None:
    col = schema.get("payer_col")
    return col if col and col in df.columns else None


def _get_category_col(df: pd.DataFrame, schema: dict) -> str | None:
    col = schema.get("category_col")
    return col if col and col in df.columns else None


def _month_label(period: pd.Period) -> str:
    """Return 'Jan 2024' style label."""
    return period.strftime("%b %Y")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_recommendations(
    df: pd.DataFrame,
    schema: dict,
    anomalies: dict,
    forecasts: dict,
) -> list:
    """Analyse spending patterns and generate 5-10 specific recommendations.

    Each recommendation is a dict with keys:
    ``type``, ``title``, ``description``, ``impact``, ``confidence``,
    ``supporting_data``, ``priority``.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    anomalies : dict
        Output of ``anomaly.detect_anomalies(df, schema)``.
    forecasts : dict
        Output of ``forecasting.forecast_expenses(df, schema)``.

    Returns
    -------
    list of dict
        Recommendations sorted by priority (high > medium > low).
    """
    recommendations: list = []

    amount_col = _get_amount_col(df, schema)
    date_col = _get_date_col(df, schema)
    payer_col = _get_payer_col(df, schema)
    category_col = _get_category_col(df, schema)

    if amount_col is None:
        return [
            {
                "type": "alert",
                "title": "Insufficient Data",
                "description": "Amount column not detected — recommendations unavailable.",
                "impact": "N/A",
                "confidence": 0.0,
                "supporting_data": {},
                "priority": "low",
            }
        ]

    df_work = df.copy()
    df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)

    # -----------------------------------------------------------------------
    # 1. Anomaly-based alert
    # -----------------------------------------------------------------------
    if anomalies and anomalies.get("available") and anomalies.get("anomaly_count", 0) > 0:
        count = anomalies["anomaly_count"]
        total = anomalies.get("total_anomalous_amount", 0)
        rate = anomalies.get("anomaly_rate_pct", 0)
        priority = "high" if rate > 10 else "medium"
        recommendations.append(
            {
                "type": "alert",
                "title": f"⚠ {count} Suspicious Transactions Detected",
                "description": (
                    f"{count} transactions (₹{total:,.0f} total) appear statistically unusual. "
                    f"They represent {rate:.1f}% of all expenses. Review these for errors or fraud."
                ),
                "impact": f"Potential ₹{total:,.0f} in irregular spending",
                "confidence": 0.82,
                "supporting_data": {
                    "anomaly_count": count,
                    "total_anomalous_amount": total,
                    "anomaly_rate_pct": rate,
                },
                "priority": priority,
            }
        )

    # -----------------------------------------------------------------------
    # 2. Forecast trend alert
    # -----------------------------------------------------------------------
    if forecasts and forecasts.get("available"):
        trend = forecasts.get("trend_direction", "stable")
        next_month = forecasts.get("next_month_prediction", 0)
        monthly_avg = forecasts.get("monthly_avg", 0)
        if trend == "increasing" and monthly_avg > 0:
            pct_increase = round((next_month - monthly_avg) / monthly_avg * 100, 1)
            recommendations.append(
                {
                    "type": "budget",
                    "title": "📈 Spending Trend is Increasing",
                    "description": (
                        f"Projected spending for next month is ₹{next_month:,.0f}, "
                        f"{pct_increase:.1f}% above the current average of ₹{monthly_avg:,.0f}. "
                        "Consider setting a monthly budget cap."
                    ),
                    "impact": f"Potential overspend of ₹{next_month - monthly_avg:,.0f}",
                    "confidence": 0.74,
                    "supporting_data": {
                        "trend_direction": trend,
                        "monthly_avg": monthly_avg,
                        "next_month_prediction": next_month,
                        "pct_increase": pct_increase,
                    },
                    "priority": "high",
                }
            )
        elif trend == "decreasing":
            recommendations.append(
                {
                    "type": "saving",
                    "title": "📉 Spending Trend is Decreasing — Good Progress!",
                    "description": (
                        f"Spending is on a downward trend. Projected next month: ₹{next_month:,.0f} "
                        f"vs average ₹{monthly_avg:,.0f}. Keep this up!"
                    ),
                    "impact": f"Potential savings of ₹{monthly_avg - next_month:,.0f}",
                    "confidence": 0.70,
                    "supporting_data": {
                        "trend_direction": trend,
                        "monthly_avg": monthly_avg,
                        "next_month_prediction": next_month,
                    },
                    "priority": "low",
                }
            )

    # -----------------------------------------------------------------------
    # 3. Category spending analysis
    # -----------------------------------------------------------------------
    if category_col:
        cat_totals = df_work.groupby(category_col)[amount_col].sum()
        grand_total = cat_totals.sum()
        if grand_total > 0:
            top_cat = cat_totals.idxmax()
            top_pct = round(cat_totals.max() / grand_total * 100, 1)
            if top_pct > 40:
                recommendations.append(
                    {
                        "type": "budget",
                        "title": f"🏷 {top_cat} Dominates Spending at {top_pct}%",
                        "description": (
                            f"{top_cat} accounts for {top_pct}% of total expenditure "
                            f"(₹{cat_totals.max():,.0f}). This is a concentration risk. "
                            "Consider diversifying or setting a category cap."
                        ),
                        "impact": f"₹{cat_totals.max():,.0f} in a single category",
                        "confidence": 0.88,
                        "supporting_data": {
                            "category": str(top_cat),
                            "amount": round(float(cat_totals.max()), 2),
                            "percentage": top_pct,
                        },
                        "priority": "medium",
                    }
                )

        # Month-over-month category comparison
        if date_col and date_col in df_work.columns:
            df_work["_month_period"] = pd.to_datetime(
                df_work[date_col], errors="coerce"
            ).dt.to_period("M")
            df_valid = df_work.dropna(subset=["_month_period"])
            if len(df_valid["_month_period"].unique()) >= 2:
                months_sorted = sorted(df_valid["_month_period"].unique())
                curr_month = months_sorted[-1]
                prev_month = months_sorted[-2]
                for cat in cat_totals.index[:3]:  # Top 3 categories
                    curr_val = float(
                        df_valid[
                            (df_valid[category_col] == cat)
                            & (df_valid["_month_period"] == curr_month)
                        ][amount_col].sum()
                    )
                    prev_val = float(
                        df_valid[
                            (df_valid[category_col] == cat)
                            & (df_valid["_month_period"] == prev_month)
                        ][amount_col].sum()
                    )
                    if prev_val > 0:
                        change_pct = (curr_val - prev_val) / prev_val * 100
                        if change_pct > 40:
                            recommendations.append(
                                {
                                    "type": "budget",
                                    "title": f"📊 {cat} spending up {change_pct:.0f}% vs last month",
                                    "description": (
                                        f"{cat} spending rose from ₹{prev_val:,.0f} "
                                        f"({_month_label(prev_month)}) to ₹{curr_val:,.0f} "
                                        f"({_month_label(curr_month)}), a {change_pct:.0f}% jump. "
                                        "Review for unnecessary expenses."
                                    ),
                                    "impact": f"₹{curr_val - prev_val:,.0f} more than last month",
                                    "confidence": 0.85,
                                    "supporting_data": {
                                        "category": str(cat),
                                        "prev_month": str(prev_month),
                                        "curr_month": str(curr_month),
                                        "prev_amount": round(prev_val, 2),
                                        "curr_amount": round(curr_val, 2),
                                        "change_pct": round(change_pct, 1),
                                    },
                                    "priority": "medium",
                                }
                            )

    # -----------------------------------------------------------------------
    # 4. Payer contribution fairness
    # -----------------------------------------------------------------------
    if payer_col and payer_col in df_work.columns:
        payer_totals = df_work.groupby(payer_col)[amount_col].sum()
        total = payer_totals.sum()
        if total > 0 and len(payer_totals) >= 2:
            fair_share = 100 / len(payer_totals)
            for payer, amt in payer_totals.items():
                payer_pct = round(amt / total * 100, 1)
                if payer_pct > fair_share + 15:
                    recommendations.append(
                        {
                            "type": "behavior",
                            "title": f"⚖ {payer} is over-contributing",
                            "description": (
                                f"{payer} pays {payer_pct:.1f}% of total expenses "
                                f"(₹{amt:,.0f}), significantly above the fair share of "
                                f"{fair_share:.1f}%. Consider rebalancing contributions."
                            ),
                            "impact": f"₹{amt - total * fair_share/100:,.0f} above fair share",
                            "confidence": 0.90,
                            "supporting_data": {
                                "payer": str(payer),
                                "paid_amount": round(float(amt), 2),
                                "paid_percentage": payer_pct,
                                "fair_share_pct": round(fair_share, 1),
                                "n_payers": len(payer_totals),
                            },
                            "priority": "medium",
                        }
                    )

    # -----------------------------------------------------------------------
    # 5. Weekend vs weekday spending
    # -----------------------------------------------------------------------
    if date_col and date_col in df_work.columns:
        dates_parsed = pd.to_datetime(df_work[date_col], errors="coerce")
        df_work["_is_weekend"] = dates_parsed.dt.dayofweek >= 5
        weekend_mean = float(df_work[df_work["_is_weekend"]][amount_col].mean()) if df_work["_is_weekend"].any() else 0
        weekday_mean = float(df_work[~df_work["_is_weekend"]][amount_col].mean()) if (~df_work["_is_weekend"]).any() else 0

        if weekday_mean > 0 and weekend_mean > 3 * weekday_mean:
            recommendations.append(
                {
                    "type": "saving",
                    "title": "🗓 Weekend Spending is 3× Higher Than Weekdays",
                    "description": (
                        f"Weekend average transaction is ₹{weekend_mean:,.0f} vs "
                        f"₹{weekday_mean:,.0f} on weekdays — {weekend_mean/weekday_mean:.1f}× higher. "
                        "Consider setting a weekend spending budget."
                    ),
                    "impact": f"₹{(weekend_mean - weekday_mean)*8:,.0f} potential monthly savings",
                    "confidence": 0.78,
                    "supporting_data": {
                        "weekend_avg": round(weekend_mean, 2),
                        "weekday_avg": round(weekday_mean, 2),
                        "ratio": round(weekend_mean / weekday_mean, 2),
                    },
                    "priority": "medium",
                }
            )

    # -----------------------------------------------------------------------
    # 6. High average transaction size
    # -----------------------------------------------------------------------
    avg_txn = float(df_work[amount_col].mean())
    p90_txn = float(df_work[amount_col].quantile(0.90))
    if p90_txn > 3 * avg_txn:
        recommendations.append(
            {
                "type": "budget",
                "title": f"💸 Top 10% Transactions Are Very Large",
                "description": (
                    f"The 90th percentile transaction is ₹{p90_txn:,.0f}, "
                    f"vs an average of ₹{avg_txn:,.0f}. A few large purchases are "
                    "driving up total spend significantly."
                ),
                "impact": f"₹{p90_txn - avg_txn:,.0f} above average per large transaction",
                "confidence": 0.80,
                "supporting_data": {
                    "avg_transaction": round(avg_txn, 2),
                    "p90_transaction": round(p90_txn, 2),
                    "ratio": round(p90_txn / avg_txn, 2),
                },
                "priority": "low",
            }
        )

    # Sort: high → medium → low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 2))

    return recommendations[:10]  # Return at most 10


def compute_optimization_score(df: pd.DataFrame, schema: dict) -> dict:
    """Compute a 0-100 financial optimisation score with sub-score breakdown.

    Sub-scores:
    * ``budget_adherence`` — consistency of spending levels.
    * ``spending_consistency`` — low CV means consistent spending.
    * ``category_balance`` — even category distribution.
    * ``anomaly_rate`` — fewer anomalies = better.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``score``, ``budget_adherence``, ``spending_consistency``,
        ``category_balance``, ``anomaly_rate_score``, ``available``.
    """
    amount_col = _get_amount_col(df, schema)
    if not amount_col:
        return {"available": False, "reason": "amount_col not found"}

    try:
        df_work = df.copy()
        df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
        amounts = df_work[amount_col].values

        # --- Budget adherence: penalise month-over-month variance ---
        date_col = _get_date_col(df_work, schema)
        budget_adherence = 70.0  # default
        if date_col:
            df_work["_month"] = pd.to_datetime(
                df_work[date_col], errors="coerce"
            ).dt.to_period("M")
            monthly = df_work.groupby("_month")[amount_col].sum().values
            if len(monthly) >= 2:
                cv = np.std(monthly) / (np.mean(monthly) + 1e-9) * 100
                budget_adherence = max(0, 100 - min(cv, 100))

        # --- Spending consistency: lower CV is better ---
        cv_txn = np.std(amounts) / (np.mean(amounts) + 1e-9) * 100 if len(amounts) > 1 else 0
        spending_consistency = max(0, 100 - min(cv_txn, 100))

        # --- Category balance: entropy-based ---
        category_col = _get_category_col(df_work, schema)
        category_balance = 60.0  # default if no categories
        if category_col and category_col in df_work.columns:
            cat_counts = df_work[category_col].value_counts(normalize=True).values
            n_cats = len(cat_counts)
            if n_cats > 1:
                entropy = -np.sum(cat_counts * np.log(cat_counts + 1e-9))
                max_entropy = np.log(n_cats)
                category_balance = round(entropy / (max_entropy + 1e-9) * 100, 1)

        # --- Anomaly rate score ---
        # We compute a lightweight z-score anomaly rate
        if len(amounts) > 5:
            z_scores = np.abs((amounts - np.mean(amounts)) / (np.std(amounts) + 1e-9))
            anomaly_rate = (z_scores > 2.5).mean() * 100
            anomaly_rate_score = max(0.0, 100.0 - anomaly_rate * 5)
        else:
            anomaly_rate_score = 100.0

        # Overall (weighted)
        score = round(
            0.30 * budget_adherence
            + 0.25 * spending_consistency
            + 0.25 * category_balance
            + 0.20 * anomaly_rate_score,
            1,
        )

        return {
            "available": True,
            "score": score,
            "budget_adherence": round(budget_adherence, 1),
            "spending_consistency": round(spending_consistency, 1),
            "category_balance": round(category_balance, 1),
            "anomaly_rate_score": round(anomaly_rate_score, 1),
        }

    except Exception as e:
        return {"available": False, "reason": f"Optimisation score error: {e}"}
