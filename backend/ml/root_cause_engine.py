"""
root_cause_engine.py — Root Cause Analysis Engine for ADIP.

Answers "WHY did this happen?" not just "WHAT happened?".

For any detected metric change, decomposes which dimensions contributed
to that change using waterfall decomposition — like a senior analyst would.

Example output:
  "Spending decreased 20.3% MoM.
   Root Causes: Food (65% of decline), Travel (22%), Utilities (13%)."
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def analyze_root_causes(df: pd.DataFrame, schema: dict, results: dict) -> dict:
    """Run all root cause analyses and return structured results.

    Returns
    -------
    dict
        {available, analyses: list, primary_finding: str}
    """
    if df is None or len(df) == 0:
        return {"available": False, "reason": "Empty dataset", "analyses": []}

    analyses = []

    # 1. MoM spending change decomposition
    mom = decompose_spending_change(df, schema)
    if mom.get("available"):
        analyses.append(mom)

    # 2. Spend drivers
    drivers = detect_spend_drivers(df, schema)
    if drivers.get("available"):
        analyses.append(drivers)

    # 3. Dimension impact (category, payer separately)
    date_col = schema.get("date_col")
    amount_col = schema.get("amount_col")
    category_col = schema.get("category_col")
    payer_col = schema.get("payer_col")

    if date_col and amount_col and category_col:
        try:
            cat_impact = compute_dimension_impact(df, category_col, amount_col, date_col)
            if cat_impact.get("available"):
                analyses.append({**cat_impact, "type": "category_impact"})
        except Exception:
            pass

    if date_col and amount_col and payer_col and payer_col != category_col:
        try:
            payer_impact = compute_dimension_impact(df, payer_col, amount_col, date_col)
            if payer_impact.get("available"):
                analyses.append({**payer_impact, "type": "payer_impact"})
        except Exception:
            pass

    primary_finding = ""
    if analyses:
        first = analyses[0]
        primary_finding = first.get("explanation", first.get("summary", ""))

    return {
        "available": len(analyses) > 0,
        "analyses": analyses,
        "primary_finding": primary_finding,
        "total_analyses": len(analyses),
    }


# ---------------------------------------------------------------------------
# Core Analysis Functions
# ---------------------------------------------------------------------------

def decompose_spending_change(df: pd.DataFrame, schema: dict) -> dict:
    """Decompose MoM spending change by dimension (category, payer, etc.)."""
    date_col   = schema.get("date_col")
    amount_col = schema.get("amount_col")
    cat_col    = schema.get("category_col")

    if not date_col or not amount_col:
        return {"available": False, "reason": "Missing date or amount column"}
    if date_col not in df.columns or amount_col not in df.columns:
        return {"available": False, "reason": "Date or amount column not in dataframe"}

    try:
        work = df[[date_col, amount_col] + ([cat_col] if cat_col and cat_col in df.columns else [])].copy()
        work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
        work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
        work = work.dropna(subset=[date_col])

        if len(work) < 2:
            return {"available": False, "reason": "Insufficient rows after parsing dates"}

        work["_month"] = work[date_col].dt.to_period("M")
        monthly = work.groupby("_month")[amount_col].sum().sort_index()

        if len(monthly) < 2:
            return {"available": False, "reason": "Need at least 2 months of data for MoM comparison"}

        current_period  = monthly.index[-1]
        previous_period = monthly.index[-2]
        current_val  = float(monthly.iloc[-1])
        previous_val = float(monthly.iloc[-2])

        change_abs = current_val - previous_val
        change_pct = (change_abs / previous_val * 100) if previous_val != 0 else 0.0
        direction  = "increased" if change_abs >= 0 else "decreased"

        root_causes = []
        if cat_col and cat_col in work.columns:
            current_by_cat  = work[work["_month"] == current_period].groupby(cat_col)[amount_col].sum()
            previous_by_cat = work[work["_month"] == previous_period].groupby(cat_col)[amount_col].sum()
            all_cats = set(current_by_cat.index) | set(previous_by_cat.index)

            for cat in all_cats:
                cur = float(current_by_cat.get(cat, 0))
                prev = float(previous_by_cat.get(cat, 0))
                contribution = cur - prev
                contribution_pct = (contribution / abs(change_abs) * 100) if change_abs != 0 else 0
                root_causes.append({
                    "factor": str(cat),
                    "dimension": cat_col,
                    "contribution_abs": round(contribution, 2),
                    "contribution_pct": round(contribution_pct, 1),
                    "current_value": round(cur, 2),
                    "previous_value": round(prev, 2),
                    "confidence": 90 if len(work) >= 30 else 65,
                })

            # Sort by absolute contribution (largest first)
            root_causes.sort(key=lambda x: abs(x["contribution_abs"]), reverse=True)
            root_causes = root_causes[:8]  # Top 8

        # Build human-readable explanation
        explanation = _build_mom_explanation(
            direction, change_pct, change_abs, current_val, previous_val,
            str(previous_period), str(current_period), root_causes
        )

        return {
            "available": True,
            "type": "mom_decomposition",
            "title": f"Month-over-Month Spending {direction.title()} Decomposition",
            "period_current":  str(current_period),
            "period_previous": str(previous_period),
            "current_value":   round(current_val, 2),
            "previous_value":  round(previous_val, 2),
            "change_abs":   round(change_abs, 2),
            "change_pct":   round(change_pct, 1),
            "direction":    direction,
            "root_causes":  root_causes,
            "explanation":  explanation,
            "rows_analyzed": len(work),
        }

    except Exception as e:
        return {"available": False, "reason": f"Error in MoM decomposition: {e}"}


def find_top_contributors(
    df: pd.DataFrame,
    schema: dict,
    metric_col: str,
    group_col: str,
    top_n: int = 5,
) -> list:
    """Find which values of group_col contribute most to metric_col total."""
    if group_col not in df.columns or metric_col not in df.columns:
        return []
    try:
        amounts = pd.to_numeric(df[metric_col], errors="coerce").fillna(0)
        grouped = amounts.groupby(df[group_col].astype(str)).sum().sort_values(ascending=False)
        total = grouped.sum() or 1
        result = []
        for rank, (val_name, total_val) in enumerate(grouped.head(top_n).items(), 1):
            result.append({
                "rank": rank,
                "value": str(val_name),
                "total": round(float(total_val), 2),
                "share_pct": round(float(total_val) / float(total) * 100, 1),
            })
        return result
    except Exception:
        return []


def detect_spend_drivers(df: pd.DataFrame, schema: dict) -> dict:
    """Identify key drivers of total spending."""
    amount_col   = schema.get("amount_col")
    date_col     = schema.get("date_col")
    category_col = schema.get("category_col")
    payer_col    = schema.get("payer_col")

    if not amount_col or amount_col not in df.columns:
        return {"available": False, "reason": "No amount column"}

    try:
        amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
        total   = float(amounts.sum())
        if total == 0:
            return {"available": False, "reason": "Total spend is zero"}

        drivers = []

        # Category concentration
        if category_col and category_col in df.columns:
            cat_shares = amounts.groupby(df[category_col].astype(str)).sum().sort_values(ascending=False)
            top_cat_share = float(cat_shares.iloc[0]) / total * 100 if len(cat_shares) > 0 else 0
            top_cat_name  = str(cat_shares.index[0]) if len(cat_shares) > 0 else "Unknown"
            drivers.append({
                "driver_type": "category_concentration",
                "description": f"'{top_cat_name}' accounts for {top_cat_share:.1f}% of total spending",
                "impact_pct": round(top_cat_share, 1),
                "confidence": 92,
                "evidence": {
                    "top_category": top_cat_name,
                    "share_pct": round(top_cat_share, 1),
                    "source_columns": [category_col, amount_col],
                },
            })

        # Payer concentration
        if payer_col and payer_col in df.columns and payer_col != category_col:
            payer_shares = amounts.groupby(df[payer_col].astype(str)).sum().sort_values(ascending=False)
            top_payer_share = float(payer_shares.iloc[0]) / total * 100 if len(payer_shares) > 0 else 0
            top_payer_name  = str(payer_shares.index[0]) if len(payer_shares) > 0 else "Unknown"
            drivers.append({
                "driver_type": "payer_concentration",
                "description": f"'{top_payer_name}' paid {top_payer_share:.1f}% of total expenses",
                "impact_pct": round(top_payer_share, 1),
                "confidence": 95,
                "evidence": {
                    "top_payer": top_payer_name,
                    "share_pct": round(top_payer_share, 1),
                    "source_columns": [payer_col, amount_col],
                },
            })

        # Weekend vs weekday
        if date_col and date_col in df.columns:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            valid_mask = dates.notna()
            if valid_mask.sum() > 10:
                weekend_mask = dates[valid_mask].dt.dayofweek >= 5
                weekend_spend   = float(amounts[valid_mask][weekend_mask].sum())
                weekday_spend   = float(amounts[valid_mask][~weekend_mask].sum())
                weekend_n       = weekend_mask.sum()
                weekday_n       = (~weekend_mask).sum()
                weekend_avg     = weekend_spend / max(weekend_n, 1)
                weekday_avg     = weekday_spend / max(weekday_n, 1)
                if weekday_avg > 0 and weekend_avg / weekday_avg > 1.5:
                    drivers.append({
                        "driver_type": "weekend_spike",
                        "description": f"Weekend avg spend (₹{weekend_avg:,.0f}) is {weekend_avg/weekday_avg:.1f}x weekday avg (₹{weekday_avg:,.0f})",
                        "impact_pct": round(weekend_spend / total * 100, 1),
                        "confidence": 88,
                        "evidence": {
                            "weekend_avg": round(weekend_avg, 2),
                            "weekday_avg": round(weekday_avg, 2),
                            "ratio": round(weekend_avg / weekday_avg, 2),
                            "source_columns": [date_col, amount_col],
                        },
                    })

        return {
            "available": len(drivers) > 0,
            "type": "spend_drivers",
            "title": "Key Spending Drivers",
            "drivers": drivers,
            "summary": f"Identified {len(drivers)} key spending driver(s).",
        }

    except Exception as e:
        return {"available": False, "reason": f"Error detecting spend drivers: {e}"}


def compute_dimension_impact(
    df: pd.DataFrame,
    group_col: str,
    amount_col: str,
    date_col: str,
) -> dict:
    """Compute MoM change per group and rank by absolute impact."""
    if not all(c in df.columns for c in [group_col, amount_col, date_col]):
        return {"available": False, "reason": "Required columns missing"}
    try:
        work = df[[group_col, amount_col, date_col]].copy()
        work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
        work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
        work = work.dropna(subset=[date_col])
        work["_month"] = work[date_col].dt.to_period("M")
        months = sorted(work["_month"].unique())
        if len(months) < 2:
            return {"available": False, "reason": "Need 2+ months"}

        cur  = months[-1]
        prev = months[-2]
        current_by  = work[work["_month"] == cur].groupby(group_col)[amount_col].sum()
        previous_by = work[work["_month"] == prev].groupby(group_col)[amount_col].sum()
        all_groups  = set(current_by.index) | set(previous_by.index)

        total_change = sum(float(current_by.get(g, 0)) - float(previous_by.get(g, 0)) for g in all_groups)
        impacts = []
        for g in all_groups:
            cur_v  = float(current_by.get(g, 0))
            prev_v = float(previous_by.get(g, 0))
            chg    = cur_v - prev_v
            impacts.append({
                "value": str(g),
                "current":  round(cur_v, 2),
                "previous": round(prev_v, 2),
                "change":   round(chg, 2),
                "change_pct": round(chg / prev_v * 100, 1) if prev_v != 0 else None,
                "share_of_total_change": round(chg / total_change * 100, 1) if total_change != 0 else 0,
            })
        impacts.sort(key=lambda x: abs(x["change"]), reverse=True)

        return {
            "available": True,
            "dimension": group_col,
            "period_current":  str(cur),
            "period_previous": str(prev),
            "total_change": round(total_change, 2),
            "impacts": impacts[:8],
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mom_explanation(
    direction: str,
    change_pct: float,
    change_abs: float,
    current: float,
    previous: float,
    prev_period: str,
    cur_period: str,
    root_causes: list,
) -> str:
    sign = "+" if change_abs >= 0 else ""
    base = (
        f"Spending {direction} {abs(change_pct):.1f}% MoM "
        f"(₹{previous:,.0f} → ₹{current:,.0f}, {sign}₹{change_abs:,.0f}) "
        f"from {prev_period} to {cur_period}."
    )
    if not root_causes:
        return base
    top = root_causes[:3]
    contributors = ", ".join(
        f"{r['factor']} ({abs(r['contribution_pct']):.0f}% of change)" for r in top
    )
    return f"{base} Top contributors: {contributors}."
