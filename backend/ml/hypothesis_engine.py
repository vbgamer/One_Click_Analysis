"""
hypothesis_engine.py — Hypothesis Generation & Testing Engine for ADIP.

Acts like a senior analyst: not just reporting findings but generating and
TESTING hypotheses against actual data.

Every hypothesis is either:
  - verified:     strong statistical signal found
  - rejected:     clearly not true based on data
  - inconclusive: data too sparse or signal too weak
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def generate_and_test_hypotheses(df: pd.DataFrame, schema: dict) -> dict:
    """Generate and test all relevant hypotheses for this dataset.

    Returns
    -------
    dict
        {total, verified, rejected, inconclusive, hypotheses: list}
    """
    all_hypotheses = []

    tests = [
        test_weekend_spending_hypothesis,
        test_payer_concentration_hypothesis,
        test_spending_trend_hypothesis,
        test_category_concentration_hypothesis,
        test_month_end_spike_hypothesis,
        test_repeat_pattern_hypothesis,
    ]

    for test_fn in tests:
        try:
            result = test_fn(df, schema)
            if result and result.get("status") != "skipped":
                all_hypotheses.append(result)
        except Exception:
            pass

    verified     = [h for h in all_hypotheses if h.get("status") == "verified"]
    rejected     = [h for h in all_hypotheses if h.get("status") == "rejected"]
    inconclusive = [h for h in all_hypotheses if h.get("status") == "inconclusive"]

    return {
        "available": len(all_hypotheses) > 0,
        "total": len(all_hypotheses),
        "verified": len(verified),
        "rejected": len(rejected),
        "inconclusive": len(inconclusive),
        "hypotheses": all_hypotheses,
    }


# ---------------------------------------------------------------------------
# Individual Hypothesis Tests
# ---------------------------------------------------------------------------

def test_weekend_spending_hypothesis(df: pd.DataFrame, schema: dict) -> dict:
    """H: Weekend spending is significantly higher than weekday spending."""
    date_col   = schema.get("date_col")
    amount_col = schema.get("amount_col")
    if not date_col or not amount_col:
        return _skip("weekend_spending", "No date/amount column")
    if date_col not in df.columns or amount_col not in df.columns:
        return _skip("weekend_spending", "Columns not in dataframe")

    work = df[[date_col, amount_col]].copy()
    work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
    work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
    work = work.dropna(subset=[date_col])

    if len(work) < 14:
        return _inconclusive("weekend_spending", "Weekend spending vs weekday",
                             "Not enough data (< 14 rows).", {})

    weekend_mask = work[date_col].dt.dayofweek >= 5
    weekend_data = work[weekend_mask][amount_col]
    weekday_data = work[~weekend_mask][amount_col]

    if len(weekend_data) < 3 or len(weekday_data) < 3:
        return _inconclusive("weekend_spending", "Weekend spending vs weekday",
                             "Insufficient weekend or weekday data.", {})

    weekend_avg = float(weekend_data.mean())
    weekday_avg = float(weekday_data.mean())
    ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 1.0

    evidence = {
        "weekday_avg": round(weekday_avg, 2),
        "weekend_avg": round(weekend_avg, 2),
        "ratio": round(ratio, 2),
        "weekday_rows": int(len(weekday_data)),
        "weekend_rows": int(len(weekend_data)),
        "calculation": "AVG(weekend_amounts) / AVG(weekday_amounts)",
        "source_columns": [date_col, amount_col],
    }

    conf = min(95, 50 + len(work) * 0.3)
    if ratio > 1.5:
        return _hypothesis(
            "weekend_spending",
            "Weekend spending is significantly higher than weekday spending",
            "verified",
            round(conf, 1),
            f"Weekend spending is {ratio:.2f}x higher (₹{weekend_avg:,.0f} vs ₹{weekday_avg:,.0f} avg)",
            evidence,
            "Consider reviewing weekend-specific expense categories",
        )
    elif ratio < 0.9:
        return _hypothesis(
            "weekend_spending",
            "Weekend spending is significantly higher than weekday spending",
            "rejected",
            round(conf, 1),
            f"Weekend avg (₹{weekend_avg:,.0f}) is lower than weekday avg (₹{weekday_avg:,.0f}). Hypothesis rejected.",
            evidence,
            "Weekday expenses dominate — review recurring weekday costs",
        )
    return _inconclusive("weekend_spending", "Weekend spending is significantly higher than weekday spending",
                         f"Ratio {ratio:.2f} — no strong difference detected.", evidence)


def test_payer_concentration_hypothesis(df: pd.DataFrame, schema: dict) -> dict:
    """H: One payer contributes disproportionately (>40% of total)."""
    payer_col  = schema.get("payer_col")
    amount_col = schema.get("amount_col")
    if not payer_col or not amount_col:
        return _skip("payer_concentration", "No payer/amount column")
    if payer_col not in df.columns or amount_col not in df.columns:
        return _skip("payer_concentration", "Columns not in dataframe")

    amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
    payer_totals = amounts.groupby(df[payer_col].astype(str)).sum().sort_values(ascending=False)
    total = float(payer_totals.sum())

    if total == 0 or len(payer_totals) < 2:
        return _inconclusive("payer_concentration", "One payer dominates group spending",
                             "Only one payer or zero total spend.", {})

    top_payer = str(payer_totals.index[0])
    top_share = float(payer_totals.iloc[0]) / total * 100

    evidence = {
        "payer_shares": {str(k): round(float(v) / total * 100, 1) for k, v in payer_totals.items()},
        "top_payer": top_payer,
        "top_payer_share_pct": round(top_share, 1),
        "calculation": "MAX(payer_total) / SUM(all_totals) × 100",
        "source_columns": [payer_col, amount_col],
    }

    conf = min(97, 70 + len(amounts) * 0.1)
    if top_share > 40:
        return _hypothesis(
            "payer_concentration",
            "One payer contributes disproportionately (>40% of total)",
            "verified",
            round(conf, 1),
            f"'{top_payer}' paid {top_share:.1f}% of total group expenses",
            evidence,
            f"Consider redistributing expenses so '{top_payer}' does not bear disproportionate burden",
        )
    return _hypothesis(
        "payer_concentration",
        "One payer contributes disproportionately (>40% of total)",
        "rejected",
        round(conf, 1),
        f"Top payer '{top_payer}' holds {top_share:.1f}% — no dominant concentration detected",
        evidence,
        "Payments are relatively distributed among group members",
    )


def test_spending_trend_hypothesis(df: pd.DataFrame, schema: dict) -> dict:
    """H: Spending has a significant upward or downward trend."""
    date_col   = schema.get("date_col")
    amount_col = schema.get("amount_col")
    if not date_col or not amount_col:
        return _skip("spending_trend", "No date/amount column")
    if date_col not in df.columns or amount_col not in df.columns:
        return _skip("spending_trend", "Columns not in dataframe")

    work = df[[date_col, amount_col]].copy()
    work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
    work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
    work = work.dropna(subset=[date_col])
    work["_month"] = work[date_col].dt.to_period("M")
    monthly = work.groupby("_month")[amount_col].sum().sort_index()

    if len(monthly) < 3:
        return _inconclusive("spending_trend", "Spending has a significant trend",
                             "Need at least 3 months of data.", {})

    x = np.arange(len(monthly))
    y = monthly.values.astype(float)
    # Simple linear regression
    x_mean = x.mean(); y_mean = y.mean()
    slope = float(np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    y_pred = slope * x + (y_mean - slope * x_mean)
    ss_res = float(np.sum((y - y_pred) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    direction = "upward" if slope > 0 else "downward"
    monthly_change_pct = (slope / y_mean * 100) if y_mean != 0 else 0

    evidence = {
        "monthly_values": {str(p): round(float(v), 2) for p, v in monthly.items()},
        "slope_per_month": round(slope, 2),
        "direction": direction,
        "r_squared": round(r_squared, 3),
        "monthly_change_pct": round(monthly_change_pct, 1),
        "calculation": "Linear regression on monthly totals (OLS)",
        "source_columns": [date_col, amount_col],
    }

    conf = min(93, 40 + r_squared * 60 + len(monthly) * 2)
    if r_squared > 0.3:
        return _hypothesis(
            "spending_trend",
            "Spending has a significant upward or downward trend",
            "verified",
            round(conf, 1),
            f"Spending has a {direction} trend of {abs(monthly_change_pct):.1f}%/month (R²={r_squared:.2f})",
            evidence,
            f"{'Budget review recommended' if direction == 'upward' else 'Positive spending discipline trend'}",
        )
    return _inconclusive(
        "spending_trend",
        "Spending has a significant trend",
        f"No clear trend detected (R²={r_squared:.2f} — weak signal).",
        evidence,
    )


def test_category_concentration_hypothesis(df: pd.DataFrame, schema: dict) -> dict:
    """H: One category dominates spending (>50% of total)."""
    cat_col    = schema.get("category_col")
    amount_col = schema.get("amount_col")
    if not cat_col or not amount_col:
        return _skip("category_concentration", "No category/amount column")
    if cat_col not in df.columns or amount_col not in df.columns:
        return _skip("category_concentration", "Columns not in dataframe")

    amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
    cat_totals = amounts.groupby(df[cat_col].astype(str)).sum().sort_values(ascending=False)
    total = float(cat_totals.sum())

    if total == 0:
        return _skip("category_concentration", "Zero total spend")

    top_cat   = str(cat_totals.index[0])
    top_share = float(cat_totals.iloc[0]) / total * 100

    evidence = {
        "category_shares": {str(k): round(float(v) / total * 100, 1) for k, v in cat_totals.head(10).items()},
        "top_category": top_cat,
        "top_category_share_pct": round(top_share, 1),
        "calculation": "MAX(category_total) / SUM(all_totals) × 100",
        "source_columns": [cat_col, amount_col],
    }

    conf = min(97, 70 + len(amounts) * 0.1)
    if top_share > 50:
        return _hypothesis(
            "category_concentration",
            "One expense category dominates total spending (>50%)",
            "verified",
            round(conf, 1),
            f"'{top_cat}' accounts for {top_share:.1f}% of all spending",
            evidence,
            f"High concentration in '{top_cat}' — review if this is expected",
        )
    return _hypothesis(
        "category_concentration",
        "One expense category dominates total spending (>50%)",
        "rejected",
        round(conf, 1),
        f"Top category '{top_cat}' holds {top_share:.1f}% — spending is distributed",
        evidence,
        "Expense categories are well-diversified",
    )


def test_month_end_spike_hypothesis(df: pd.DataFrame, schema: dict) -> dict:
    """H: Spending spikes at month end (last 5 days)."""
    date_col   = schema.get("date_col")
    amount_col = schema.get("amount_col")
    if not date_col or not amount_col:
        return _skip("month_end_spike", "No date/amount column")
    if date_col not in df.columns or amount_col not in df.columns:
        return _skip("month_end_spike", "Columns not in dataframe")

    work = df[[date_col, amount_col]].copy()
    work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
    work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
    work = work.dropna(subset=[date_col])

    if len(work) < 20:
        return _inconclusive("month_end_spike", "Spending spikes at month end",
                             "Not enough data.", {})

    days_in_month = work[date_col].dt.days_in_month
    day_of_month  = work[date_col].dt.day
    month_end_mask = (days_in_month - day_of_month) <= 4  # last 5 days

    me_data  = work[month_end_mask][amount_col]
    rest     = work[~month_end_mask][amount_col]

    if len(me_data) < 3 or len(rest) < 3:
        return _inconclusive("month_end_spike", "Spending spikes at month end", "Not enough month-end data.", {})

    me_avg   = float(me_data.mean())
    rest_avg = float(rest.mean())
    ratio    = me_avg / rest_avg if rest_avg > 0 else 1.0

    evidence = {
        "month_end_avg": round(me_avg, 2),
        "non_month_end_avg": round(rest_avg, 2),
        "ratio": round(ratio, 2),
        "month_end_rows": int(len(me_data)),
        "source_columns": [date_col, amount_col],
        "calculation": "AVG(last_5_days) / AVG(other_days)",
    }

    conf = min(88, 55 + len(work) * 0.2)
    if ratio > 1.3:
        return _hypothesis(
            "month_end_spike",
            "Spending spikes significantly at month end",
            "verified",
            round(conf, 1),
            f"Month-end avg (₹{me_avg:,.0f}) is {ratio:.2f}x non-month-end avg (₹{rest_avg:,.0f})",
            evidence,
            "Plan budget buffer for month-end periods",
        )
    return _inconclusive("month_end_spike", "Spending spikes at month end",
                         f"Ratio {ratio:.2f} — no significant spike detected.", evidence)


def test_repeat_pattern_hypothesis(df: pd.DataFrame, schema: dict) -> dict:
    """H: There are recurring expense patterns (same amount, similar timing)."""
    amount_col   = schema.get("amount_col")
    category_col = schema.get("category_col")
    if not amount_col or amount_col not in df.columns:
        return _skip("repeat_pattern", "No amount column")

    amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
    rounded = amounts.round(0)
    vc = rounded.value_counts()
    recurring = vc[vc >= 3]

    evidence = {
        "recurring_amounts": {str(int(k)): int(v) for k, v in recurring.head(5).items()},
        "total_recurring_transactions": int(recurring.sum()),
        "unique_recurring_amounts": int(len(recurring)),
        "calculation": "COUNT(*) WHERE ROUND(Amount,0) appears >= 3 times",
        "source_columns": [amount_col],
    }

    if len(recurring) >= 2:
        top_recurring = int(vc.index[0])
        count = int(vc.iloc[0])
        return _hypothesis(
            "repeat_pattern",
            "Recurring expense patterns exist (same amount appearing 3+ times)",
            "verified",
            82.0,
            f"{len(recurring)} recurring amount(s) found; ₹{top_recurring:,} appears {count} times",
            evidence,
            "Recurring expenses may be subscriptions or fixed costs — verify intentionality",
        )
    return _hypothesis(
        "repeat_pattern",
        "Recurring expense patterns exist",
        "rejected",
        75.0,
        "No significant recurring amount patterns found.",
        evidence,
        "Expenses appear to be one-off transactions",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hypothesis(id_, statement, status, confidence, key_finding, evidence, implication) -> dict:
    return {
        "id": id_,
        "statement": statement,
        "status": status,
        "confidence": confidence,
        "key_finding": key_finding,
        "evidence": evidence,
        "business_implication": implication,
    }


def _inconclusive(id_, statement, reason, evidence) -> dict:
    return _hypothesis(id_, statement, "inconclusive", 40.0, reason, evidence, "Collect more data to draw conclusions.")


def _skip(id_, reason) -> dict:
    return {"id": id_, "status": "skipped", "reason": reason}
