"""
self_critique.py — Self-Critique Engine for Autonomous Data Intelligence Platform (ADIP).

The AI critiques its own analysis BEFORE users see it.
This builds trust: users see we already identified the limitations.

Philosophy: "A senior analyst always qualifies their conclusions."
"""

import numpy as np
import pandas as pd
from datetime import datetime


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def generate_self_critique(df: pd.DataFrame, schema: dict, results: dict) -> dict:
    """Generate a comprehensive self-critique of the analysis.

    Returns
    -------
    dict
        {overall_reliability, trust_score, warnings, strengths,
         data_quality_issues, analysis_limitations}
    """
    warnings   = []
    strengths  = []
    dq_issues  = []
    limitations = []

    warnings.extend(check_sample_size(df))
    dq_issues.extend(check_data_quality(df, schema))
    limitations.extend(check_forecast_reliability(df, schema, results))
    limitations.extend(check_statistical_power(df, schema, results))

    # Strengths
    n = len(df)
    if n >= 200:
        strengths.append({"category": "sample_size",
                          "message": f"Large dataset ({n:,} rows) enables reliable statistical analysis."})
    elif n >= 30:
        strengths.append({"category": "sample_size",
                          "message": f"Adequate sample size ({n:,} rows) for core statistical analyses."})

    completeness = _compute_completeness(df)
    if completeness >= 95:
        strengths.append({"category": "data_quality",
                          "message": f"Excellent data completeness: {completeness:.1f}%."})
    elif completeness >= 80:
        strengths.append({"category": "data_quality",
                          "message": f"Good data completeness: {completeness:.1f}%."})

    date_col = schema.get("date_col")
    if date_col and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(dates) >= 2:
            months = (dates.max() - dates.min()).days / 30
            if months >= 6:
                strengths.append({"category": "temporal_coverage",
                                  "message": f"Strong temporal coverage: {months:.1f} months of data."})

    cat_col = schema.get("category_col")
    if cat_col and cat_col in df.columns:
        n_cats = df[cat_col].nunique()
        if n_cats >= 5:
            strengths.append({"category": "diversity",
                              "message": f"Good category diversity: {n_cats} distinct expense categories."})

    all_warnings = warnings + dq_issues + limitations
    trust_score  = compute_trust_score(df, all_warnings)

    if trust_score >= 80:
        reliability = "high"
    elif trust_score >= 55:
        reliability = "medium"
    else:
        reliability = "low"

    return {
        "available": True,
        "overall_reliability": reliability,
        "trust_score": round(trust_score, 1),
        "warnings": all_warnings,
        "strengths": strengths,
        "data_quality_issues": dq_issues,
        "analysis_limitations": limitations,
        "total_warnings": len(all_warnings),
        "total_strengths": len(strengths),
        "critique_summary": _build_summary(reliability, trust_score, all_warnings, strengths),
    }


# ---------------------------------------------------------------------------
# Individual Check Functions
# ---------------------------------------------------------------------------

def check_sample_size(df: pd.DataFrame) -> list:
    """Generate warnings for small sample sizes."""
    warnings = []
    n = len(df)
    if n < 10:
        warnings.append(_warn(
            "CRITICAL", "sample_size",
            f"Critical: Only {n} rows detected. Results are unreliable.",
            "Collect at least 30 data points for meaningful analysis.",
        ))
    elif n < 30:
        warnings.append(_warn(
            "WARNING", "sample_size",
            f"Small dataset ({n} rows). Statistical power is low.",
            "Aim for 100+ rows for reliable pattern detection.",
        ))
    elif n < 100:
        warnings.append(_warn(
            "INFO", "sample_size",
            f"Moderate dataset ({n} rows). Some patterns may not be detectable.",
            "More data will improve forecast accuracy and anomaly detection.",
        ))
    return warnings


def check_data_quality(df: pd.DataFrame, schema: dict) -> list:
    """Check for data quality issues."""
    issues = []

    # Missing values per column
    for col in df.columns[:10]:  # Check first 10 columns
        miss_rate = float(df[col].isna().mean())
        if miss_rate > 0.3:
            issues.append(_warn(
                "WARNING", "data_quality",
                f"Column '{col}' has {miss_rate*100:.1f}% missing values.",
                f"Fill or impute missing values in '{col}' for better analysis.",
            ))
        elif miss_rate > 0.05:
            issues.append(_warn(
                "INFO", "data_quality",
                f"Column '{col}' has {miss_rate*100:.1f}% missing values.",
                "Minor missing data — results may be slightly affected.",
            ))

    # Duplicate rows
    dup_rate = float(df.duplicated().mean())
    if dup_rate > 0.1:
        issues.append(_warn(
            "WARNING", "data_quality",
            f"{dup_rate*100:.1f}% duplicate rows detected. This may inflate totals.",
            "Remove duplicates or verify intentional repetitions.",
        ))

    # Negatives in amount column
    amount_col = schema.get("amount_col")
    if amount_col and amount_col in df.columns:
        amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
        neg_pct = float((amounts < 0).mean())
        if neg_pct > 0.05:
            issues.append(_warn(
                "WARNING", "data_quality",
                f"{neg_pct*100:.1f}% of amounts are negative. May affect sum/average calculations.",
                "Verify if negatives represent refunds/credits or data errors.",
            ))

        # Check for potential outliers (amount > 10x mean)
        if len(amounts) >= 10:
            mean_val = float(amounts.mean())
            extreme  = (amounts > mean_val * 10).sum()
            if extreme > 0:
                issues.append(_warn(
                    "INFO", "data_quality",
                    f"{extreme} transaction(s) are >10x the mean (₹{mean_val:,.0f}). May affect averages.",
                    "Consider excluding extreme outliers when interpreting mean values.",
                ))

    # Date gaps
    date_col = schema.get("date_col")
    if date_col and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna().sort_values()
        if len(dates) >= 2:
            gaps = dates.diff().dt.days.dropna()
            max_gap = float(gaps.max())
            if max_gap > 30:
                issues.append(_warn(
                    "WARNING", "data_quality",
                    f"Data gap of {max_gap:.0f} days detected. Trend analysis may be discontinuous.",
                    "Check if missing period is intentional (e.g., vacation) or a data issue.",
                ))

    return issues


def check_forecast_reliability(df: pd.DataFrame, schema: dict, results: dict) -> list:
    """Check if we have enough data for reliable forecasting."""
    limitations = []
    date_col    = schema.get("date_col")
    amount_col  = schema.get("amount_col")

    if not date_col or date_col not in df.columns:
        limitations.append(_warn(
            "WARNING", "forecast",
            "No date column detected. Forecasting and trend analysis are unavailable.",
            "Add a date column to enable time-series forecasting.",
        ))
        return limitations

    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if len(dates) < 2:
        return limitations

    months = (dates.max() - dates.min()).days / 30

    if months < 3:
        limitations.append(_warn(
            "WARNING", "forecast",
            f"Only {months:.1f} month(s) of data. Forecasts will have very low reliability.",
            "Collect 6+ months of data for meaningful forecasting.",
        ))
    elif months < 12:
        limitations.append(_warn(
            "INFO", "forecast",
            f"{months:.1f} months of history available. Seasonal patterns may not be detectable.",
            "12+ months of data enables seasonal decomposition.",
        ))

    return limitations


def check_statistical_power(df: pd.DataFrame, schema: dict, results: dict) -> list:
    """Check statistical power of key analyses."""
    limitations = []
    n = len(df)

    # Anomaly detection power
    if n < 20:
        limitations.append(_warn(
            "WARNING", "statistical_power",
            f"Anomaly detection with {n} rows has low statistical power.",
            "IsolationForest is most reliable with 50+ data points.",
        ))

    # Category analysis
    cat_col = schema.get("category_col")
    if cat_col and cat_col in df.columns:
        n_cats = df[cat_col].nunique()
        if n_cats < 3:
            limitations.append(_warn(
                "INFO", "statistical_power",
                f"Only {n_cats} unique categories. Category analysis is limited.",
                "Richer categorization enables better spending pattern analysis.",
            ))

    # Payer analysis
    payer_col = schema.get("payer_col")
    if payer_col and payer_col in df.columns:
        n_payers = df[payer_col].nunique()
        if n_payers < 2:
            limitations.append(_warn(
                "INFO", "statistical_power",
                "Only one payer detected. Settlement analysis is trivial.",
                "Multi-payer data enables fairness and settlement optimization.",
            ))

    # Schema ambiguity
    if not schema.get("amount_col"):
        limitations.append(_warn(
            "CRITICAL", "schema",
            "No amount/value column detected. Most financial KPIs are unavailable.",
            "Ensure your dataset has a column with numeric transaction amounts.",
        ))

    return limitations


def compute_trust_score(df: pd.DataFrame, warnings: list) -> float:
    """Compute 0-100 trust score. Deduct for each warning by severity."""
    score = 100.0
    deductions = {"CRITICAL": -20, "WARNING": -8, "INFO": -2}
    for w in warnings:
        score += deductions.get(w.get("severity", "INFO"), -2)
    return max(10.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _warn(severity: str, category: str, message: str, recommendation: str) -> dict:
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "recommendation": recommendation,
    }


def _compute_completeness(df: pd.DataFrame) -> float:
    total  = len(df) * len(df.columns)
    missing = int(df.isna().sum().sum())
    return round(100 * (1 - missing / max(total, 1)), 2)


def _build_summary(reliability: str, trust_score: float, warnings: list, strengths: list) -> str:
    criticals = sum(1 for w in warnings if w.get("severity") == "CRITICAL")
    w_count   = sum(1 for w in warnings if w.get("severity") == "WARNING")
    if reliability == "high":
        return (f"High reliability analysis (trust score: {trust_score:.0f}/100). "
                f"{len(strengths)} strength(s) identified. "
                f"{'No critical issues.' if criticals == 0 else f'{criticals} critical issue(s) found.'}")
    elif reliability == "medium":
        return (f"Medium reliability (trust score: {trust_score:.0f}/100). "
                f"{w_count} warning(s), {criticals} critical issue(s). "
                f"Results are directionally useful but verify key findings.")
    else:
        return (f"Low reliability (trust score: {trust_score:.0f}/100). "
                f"{criticals} critical issue(s) detected. "
                f"Treat all results as indicative only.")
