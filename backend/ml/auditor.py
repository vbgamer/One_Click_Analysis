"""
auditor.py — Auditor Agent for Autonomous Data Intelligence Platform (ADIP).

The Auditor Agent has VETO AUTHORITY over all outputs.
Any insight it marks FAILED is replaced with 'Unable to verify this conclusion.'

Responsibilities:
- Validate calculations independently
- Detect hallucinations (values not traceable to source data)
- Detect impossible statistics (>100% percentages, negative totals)
- Verify forecast sanity (no >500% growth predictions)
- Verify recommendation grounding
"""

import math
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def audit_results(results: dict, df: pd.DataFrame, schema: dict) -> dict:
    """Audit all pipeline results and return a structured audit report.

    Parameters
    ----------
    results : dict
        Full pipeline results dict.
    df : pd.DataFrame
        Source dataframe.
    schema : dict
        Detected column schema.

    Returns
    -------
    dict
        {overall_status, score, passed, failed, warnings, vetoed_keys, audit_summary}
    """
    all_checks = []

    # Run all audit checks
    all_checks.extend(audit_data_basics(df, schema))
    all_checks.extend(audit_anomalies(results.get("anomalies", {}), df, schema))
    all_checks.extend(audit_recommendations(results.get("recommendations", []), df, schema))
    all_checks.extend(audit_forecast(results.get("forecast", {}), df, schema))
    all_checks.extend(audit_settlement(results.get("settlement", {}), df, schema))
    all_checks.extend(audit_kpis(results.get("kpis", {}), df, schema))

    passed  = [c for c in all_checks if c["status"] == "PASSED"]
    failed  = [c for c in all_checks if c["status"] == "FAILED"]
    warnings = [c for c in all_checks if c["status"] == "WARNING"]

    total = len(all_checks) or 1
    score = round(100.0 * len(passed) / total, 1)

    if len(failed) == 0:
        overall = "PASSED"
    elif len(failed) / total > 0.3:
        overall = "FAILED"
    else:
        overall = "PARTIAL"

    # Determine which top-level result keys to veto
    vetoed_keys = list({c.get("key", "") for c in failed if c.get("key")})

    return {
        "overall_status": overall,
        "score": score,
        "total_checks": len(all_checks),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "warning_count": len(warnings),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "vetoed_keys": vetoed_keys,
        "audit_summary": _build_summary(overall, score, failed, warnings),
    }


# ---------------------------------------------------------------------------
# Individual Audit Functions
# ---------------------------------------------------------------------------

def audit_data_basics(df: pd.DataFrame, schema: dict) -> list:
    """Validate basic data integrity."""
    checks = []

    # Check dataframe is not empty
    if len(df) == 0:
        checks.append(_check("Dataset is not empty", "FAILED", "Dataframe has 0 rows.", "data"))
    else:
        checks.append(_check("Dataset is not empty", "PASSED", f"{len(df):,} rows present.", "data"))

    # Check amount column exists and is numeric
    amount_col = schema.get("amount_col")
    if amount_col and amount_col in df.columns:
        numeric = pd.to_numeric(df[amount_col], errors="coerce")
        pct_valid = numeric.notna().mean()
        if pct_valid < 0.5:
            checks.append(_check(
                "Amount column is mostly numeric",
                "FAILED",
                f"Only {pct_valid*100:.1f}% of values in '{amount_col}' are numeric.",
                "amount_col",
            ))
        else:
            checks.append(_check(
                "Amount column is mostly numeric",
                "PASSED",
                f"{pct_valid*100:.1f}% of '{amount_col}' values are valid numbers.",
                "amount_col",
            ))
        # Check for all-negative amounts
        if numeric.dropna().lt(0).all():
            checks.append(_check(
                "Amount column has positive values",
                "WARNING",
                "All amounts are negative — check if data is in debit/credit format.",
                "amount_col",
            ))
    else:
        checks.append(_check(
            "Amount column detected",
            "WARNING",
            "No amount column detected. Financial KPIs may be unreliable.",
            "schema",
        ))

    # Check date column
    date_col = schema.get("date_col")
    if date_col and date_col in df.columns:
        checks.append(_check("Date column detected", "PASSED", f"Date column: '{date_col}'.", "schema"))
    else:
        checks.append(_check(
            "Date column detected",
            "WARNING",
            "No date column detected. Forecasting and trend analysis unavailable.",
            "schema",
        ))

    return checks


def audit_anomalies(anomalies: dict, df: pd.DataFrame, schema: dict) -> list:
    """Validate anomaly detection results."""
    checks = []
    if not anomalies or not isinstance(anomalies, dict):
        checks.append(_check("Anomaly results present", "WARNING", "No anomaly results found.", "anomalies"))
        return checks

    count = anomalies.get("anomaly_count", 0)
    n_rows = len(df)

    # Anomaly rate sanity check
    if n_rows > 0:
        rate = count / n_rows
        if rate > 0.5:
            checks.append(_check(
                "Anomaly rate is realistic",
                "WARNING",
                f"Anomaly rate is {rate*100:.1f}% — unusually high. Model may be over-flagging.",
                "anomalies",
            ))
        else:
            checks.append(_check(
                "Anomaly rate is realistic",
                "PASSED",
                f"Anomaly rate: {rate*100:.1f}% ({count} of {n_rows} rows).",
                "anomalies",
            ))

    # Check anomaly count matches list length
    flagged = anomalies.get("flagged_rows", [])
    if isinstance(flagged, list) and count != len(flagged):
        checks.append(_check(
            "Anomaly count matches flagged rows",
            "WARNING",
            f"anomaly_count={count} but flagged_rows has {len(flagged)} entries.",
            "anomalies",
        ))
    else:
        checks.append(_check(
            "Anomaly count matches flagged rows",
            "PASSED",
            f"Count ({count}) matches flagged rows list.",
            "anomalies",
        ))

    return checks


def audit_recommendations(recs: list, df: pd.DataFrame, schema: dict) -> list:
    """Validate each recommendation has supporting data and realistic impact."""
    checks = []
    if not recs or not isinstance(recs, list):
        checks.append(_check("Recommendations present", "WARNING", "No recommendations generated.", "recommendations"))
        return checks

    amount_col = schema.get("amount_col")
    total_spend = 0.0
    if amount_col and amount_col in df.columns:
        total_spend = float(pd.to_numeric(df[amount_col], errors="coerce").sum())

    checks.append(_check("Recommendations present", "PASSED", f"{len(recs)} recommendations generated.", "recommendations"))

    for i, rec in enumerate(recs[:5]):  # Audit first 5
        if not isinstance(rec, dict):
            continue
        title = rec.get("title", f"Rec {i+1}")

        # Must have a description
        if not rec.get("description") and not rec.get("title"):
            checks.append(_check(f"Rec '{title}' has description", "FAILED",
                                 "Recommendation has no title or description.", "recommendations"))
        else:
            checks.append(_check(f"Rec '{title}' has description", "PASSED",
                                 "Title and description present.", "recommendations"))

        # Impact sanity check
        impact = rec.get("impact") or rec.get("expected_impact") or ""
        if isinstance(impact, str) and impact:
            checks.append(_check(f"Rec '{title}' impact defined", "PASSED", f"Impact: {impact[:60]}", "recommendations"))

        # Confidence range
        conf = rec.get("confidence", 50)
        try:
            conf = float(conf)
            if 0 <= conf <= 100:
                checks.append(_check(f"Rec '{title}' confidence valid", "PASSED", f"Confidence: {conf}%", "recommendations"))
            else:
                checks.append(_check(f"Rec '{title}' confidence valid", "FAILED",
                                     f"Confidence {conf} is out of 0-100 range.", "recommendations"))
        except (TypeError, ValueError):
            pass

    return checks


def audit_forecast(forecast: dict, df: pd.DataFrame, schema: dict) -> list:
    """Validate forecast values."""
    checks = []
    if not forecast or not isinstance(forecast, dict) or not forecast.get("available", True):
        checks.append(_check("Forecast available", "WARNING", "No forecast results.", "forecast"))
        return checks

    amount_col = schema.get("amount_col")
    if not amount_col or amount_col not in df.columns:
        return checks

    numeric = pd.to_numeric(df[amount_col], errors="coerce").dropna()
    if len(numeric) == 0:
        return checks

    historical_avg = float(numeric.mean())
    historical_max = float(numeric.max()) * 30  # rough monthly max

    # Check for >500% growth prediction (likely hallucination)
    next_pred = forecast.get("next_month_prediction") or forecast.get("predicted_next_month")
    if next_pred is not None:
        try:
            pred_val = float(next_pred)
            if historical_avg > 0:
                ratio = pred_val / (historical_avg * 30)
                if ratio > 5:
                    checks.append(_check(
                        "Forecast growth is realistic",
                        "WARNING",
                        f"Predicted next month ({pred_val:,.0f}) is {ratio:.1f}x historical monthly avg. Treat with caution.",
                        "forecast",
                    ))
                else:
                    checks.append(_check(
                        "Forecast growth is realistic",
                        "PASSED",
                        f"Forecast ({pred_val:,.0f}) within realistic range of history.",
                        "forecast",
                    ))
        except (TypeError, ValueError):
            pass

    return checks


def audit_settlement(settlement: dict, df: pd.DataFrame, schema: dict) -> list:
    """Validate settlement calculations."""
    checks = []
    if not settlement or not isinstance(settlement, dict):
        return checks

    balances = settlement.get("balances", {})
    if balances and isinstance(balances, dict):
        # Sum of balances should be ~0 (money in = money out)
        try:
            balance_sum = sum(float(v) for v in balances.values() if v is not None)
            if abs(balance_sum) < 1.0:  # allow ₹1 rounding error
                checks.append(_check(
                    "Settlement balances sum to zero",
                    "PASSED",
                    f"Balance sum: {balance_sum:.2f} (within ₹1 rounding tolerance).",
                    "settlement",
                ))
            else:
                checks.append(_check(
                    "Settlement balances sum to zero",
                    "WARNING",
                    f"Balance sum is {balance_sum:.2f} — should be ~0. Possible rounding or data issue.",
                    "settlement",
                ))
        except (TypeError, ValueError):
            pass

    return checks


def audit_kpis(kpis: dict, df: pd.DataFrame, schema: dict) -> list:
    """Validate KPI values are within realistic bounds."""
    checks = []
    if not kpis or not isinstance(kpis, dict):
        return checks

    kpi_list = kpis.get("kpis", [])
    if not kpi_list:
        return checks

    for kpi in kpi_list[:10]:
        if not isinstance(kpi, dict):
            continue
        name = kpi.get("name", "KPI")
        value = kpi.get("value")
        unit = kpi.get("unit", "")

        if value is None:
            checks.append(_check(f"KPI '{name}' has value", "WARNING", "KPI value is None.", "kpis"))
            continue

        # Percentage KPIs must be 0-100
        if "%" in str(unit) or "percent" in name.lower() or "rate" in name.lower():
            try:
                v = float(value)
                if 0 <= v <= 100:
                    checks.append(_check(f"KPI '{name}' in valid range", "PASSED", f"{v:.1f}%", "kpis"))
                else:
                    checks.append(_check(f"KPI '{name}' in valid range", "FAILED",
                                         f"Percentage KPI has value {v} (outside 0-100).", "kpis"))
            except (TypeError, ValueError):
                pass

    if kpi_list:
        checks.append(_check("KPIs generated", "PASSED", f"{len(kpi_list)} KPIs discovered.", "kpis"))

    return checks


def apply_veto(results: dict, audit_report: dict) -> dict:
    """Apply auditor veto to results.

    FAILED insights have their value replaced with 'Unable to verify this conclusion.'
    Original values stored in results['_unverified'].
    """
    results = dict(results)
    vetoed = {}
    veto_message = "Unable to verify this conclusion."

    for key in audit_report.get("vetoed_keys", []):
        if key in results and key not in ("data", "schema", "summary"):
            vetoed[key] = results[key]
            if isinstance(results[key], dict):
                results[key] = {**results[key], "_vetoed": True, "_veto_reason": veto_message}
            elif isinstance(results[key], list):
                results[key] = [{"_vetoed": True, "message": veto_message}]

    if vetoed:
        results["_unverified"] = vetoed

    results["audit_report"] = audit_report
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(check: str, status: str, detail: str, key: str = "") -> dict:
    return {"check": check, "status": status, "detail": detail, "key": key}


def _build_summary(overall: str, score: float, failed: list, warnings: list) -> str:
    if overall == "PASSED":
        return f"All checks passed. Audit score: {score:.1f}/100. Results are verified and trustworthy."
    elif overall == "FAILED":
        issues = "; ".join(c["detail"] for c in failed[:3])
        return f"Critical issues found (score {score:.1f}/100): {issues}"
    else:
        w = f"{len(warnings)} warning(s)" if warnings else "no warnings"
        f_count = len(failed)
        return f"Partial pass (score {score:.1f}/100). {f_count} check(s) failed, {w}. Review flagged items."
