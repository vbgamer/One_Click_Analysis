"""
kpi_engine.py — KPI Discovery Engine for Autonomous Data Intelligence Platform (ADIP).

Auto-detects business domain from column names and data patterns,
then generates relevant, evidence-backed KPIs automatically.

No manual KPI definitions required.
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Domain detection vocabulary
# ---------------------------------------------------------------------------

_DOMAIN_SIGNALS = {
    "expense_split": ["paid by", "payer", "split", "settled", "owes", "person", "member", "who paid"],
    "finance":       ["revenue", "profit", "budget", "variance", "expense", "cost", "margin", "ebitda"],
    "sales":         ["product", "units sold", "customer", "order", "deal", "pipeline", "quota", "lead"],
    "ecommerce":     ["sku", "cart", "checkout", "return", "refund", "shipping", "item", "basket"],
    "hr":            ["employee", "department", "salary", "tenure", "hire", "attrition", "headcount"],
    "marketing":     ["campaign", "clicks", "impressions", "cpa", "roas", "ctr", "conversion", "funnel"],
    "manufacturing": ["production", "units", "defect", "yield", "downtime", "sku", "batch", "quality"],
}


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def discover_kpis(df: pd.DataFrame, schema: dict) -> dict:
    """Detect domain and generate relevant KPIs with evidence.

    Returns
    -------
    dict
        {domain, domain_confidence, kpis: list, total_kpis: int}
    """
    domain, domain_conf = detect_domain(df, schema)

    kpi_fns = {
        "expense_split": compute_expense_split_kpis,
        "finance":       compute_finance_kpis,
        "sales":         compute_finance_kpis,   # similar metrics
        "ecommerce":     compute_finance_kpis,
        "hr":            compute_finance_kpis,
        "marketing":     compute_finance_kpis,
        "manufacturing": compute_finance_kpis,
    }

    fn = kpi_fns.get(domain, compute_generic_kpis)
    kpis = _safe_compute(fn, df, schema)

    # Always append generic KPIs
    generic = _safe_compute(compute_generic_kpis, df, schema)
    all_kpis = _dedupe_kpis(kpis + generic)

    return {
        "available": True,
        "domain": domain,
        "domain_confidence": round(domain_conf, 1),
        "kpis": all_kpis,
        "total_kpis": len(all_kpis),
    }


# ---------------------------------------------------------------------------
# Domain Detection
# ---------------------------------------------------------------------------

def detect_domain(df: pd.DataFrame, schema: dict) -> tuple:
    """Detect business domain from column names and data.

    Returns
    -------
    tuple[str, float]
        (domain_name, confidence_0_to_100)
    """
    col_text = " ".join(c.lower() for c in df.columns)
    schema_roles = " ".join(v.lower() for v in schema.values() if isinstance(v, str))

    # Score each domain by signal word hits
    scores = {}
    for domain, signals in _DOMAIN_SIGNALS.items():
        hits = sum(1 for s in signals if s in col_text or s in schema_roles)
        scores[domain] = hits

    # Special rule: expense_split if payer_col is detected
    if schema.get("payer_col"):
        scores["expense_split"] = scores.get("expense_split", 0) + 3

    if all(v == 0 for v in scores.values()):
        return ("generic", 50.0)

    best_domain = max(scores, key=lambda d: scores[d])
    total_signals = len(_DOMAIN_SIGNALS.get(best_domain, []))
    confidence = min(95.0, 50.0 + (scores[best_domain] / max(total_signals, 1)) * 50)

    return (best_domain, confidence)


# ---------------------------------------------------------------------------
# KPI Computation Functions
# ---------------------------------------------------------------------------

def compute_expense_split_kpis(df: pd.DataFrame, schema: dict) -> list:
    """KPIs for group expense tracking / split bills."""
    kpis = []
    amount_col = schema.get("amount_col")
    payer_col  = schema.get("payer_col")
    date_col   = schema.get("date_col")

    if not amount_col or amount_col not in df.columns:
        return kpis

    amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
    total   = float(amounts.sum())
    n_rows  = len(df)

    # 1. Total spend
    kpis.append(_kpi(
        name="Total Group Spend",
        value=round(total, 2),
        unit="₹",
        formula="SUM(Amount)",
        source_columns=[amount_col],
        confidence=_conf(n_rows),
        interpretation=f"Total recorded group expenses: ₹{total:,.2f}",
        status="good",
        benchmark="N/A",
    ))

    # 2. Per-person metrics
    if payer_col and payer_col in df.columns:
        payer_totals = amounts.groupby(df[payer_col].astype(str)).sum()
        n_payers     = len(payer_totals)
        fair_share   = total / n_payers if n_payers > 0 else total

        kpis.append(_kpi(
            name="Fair Share Per Person",
            value=round(fair_share, 2),
            unit="₹",
            formula="SUM(Amount) / COUNT(DISTINCT Payer)",
            source_columns=[amount_col, payer_col],
            confidence=_conf(n_rows),
            interpretation=f"Each of {n_payers} people should ideally pay ₹{fair_share:,.2f}",
            status="good",
            benchmark="N/A",
        ))

        # 3. Fairness Index (0-100, 100=perfectly equal)
        if n_payers > 1:
            min_paid = float(payer_totals.min())
            max_paid = float(payer_totals.max())
            fairness = (min_paid / max_paid * 100) if max_paid > 0 else 100
            kpis.append(_kpi(
                name="Fairness Index",
                value=round(fairness, 1),
                unit="%",
                formula="MIN(payer_total) / MAX(payer_total) × 100",
                source_columns=[amount_col, payer_col],
                confidence=_conf(n_rows),
                interpretation=(
                    f"Payment distribution is {'balanced' if fairness > 70 else 'imbalanced'} "
                    f"({fairness:.1f}% fairness score)"
                ),
                status="good" if fairness > 70 else ("warning" if fairness > 40 else "critical"),
                benchmark="Healthy: > 70%",
            ))

        # 4. Overpayment
        top_payer      = payer_totals.idxmax()
        top_paid       = float(payer_totals.max())
        overpayment    = top_paid - fair_share
        kpis.append(_kpi(
            name="Max Overpayment",
            value=round(overpayment, 2),
            unit="₹",
            formula="MAX(payer_total) - fair_share",
            source_columns=[amount_col, payer_col],
            confidence=_conf(n_rows),
            interpretation=f"'{top_payer}' overpaid by ₹{overpayment:,.2f} vs fair share",
            status="good" if overpayment < fair_share * 0.1 else "warning",
            benchmark="Healthy: < 10% of fair share",
        ))

    # 5. Spending velocity (avg per day)
    if date_col and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(dates) >= 2:
            days_span = max((dates.max() - dates.min()).days, 1)
            velocity  = total / days_span
            kpis.append(_kpi(
                name="Daily Spend Rate",
                value=round(velocity, 2),
                unit="₹/day",
                formula="SUM(Amount) / (MAX(Date) - MIN(Date)).days",
                source_columns=[amount_col, date_col],
                confidence=_conf(n_rows),
                interpretation=f"Group spends ₹{velocity:,.2f}/day on average over {days_span} days",
                status="good",
                benchmark="N/A",
            ))

            # Peak spending day of week
            work = df[[date_col, amount_col]].copy()
            work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
            work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
            work = work.dropna(subset=[date_col])
            day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            work["_dow"] = work[date_col].dt.dayofweek
            dow_avg = work.groupby("_dow")[amount_col].mean()
            if len(dow_avg) > 0:
                peak_dow = int(dow_avg.idxmax())
                kpis.append(_kpi(
                    name="Peak Spending Day",
                    value=day_names[peak_dow],
                    unit="day",
                    formula="MAX(AVG(Amount) GROUP BY DayOfWeek)",
                    source_columns=[amount_col, date_col],
                    confidence=_conf(n_rows),
                    interpretation=f"{day_names[peak_dow]}s have the highest average spending",
                    status="good",
                    benchmark="N/A",
                ))

    return kpis


def compute_finance_kpis(df: pd.DataFrame, schema: dict) -> list:
    """KPIs for finance/sales datasets: MoM growth, run rate, CV, trend."""
    kpis = []
    amount_col = schema.get("amount_col")
    date_col   = schema.get("date_col")

    if not amount_col or amount_col not in df.columns:
        return kpis

    amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
    total   = float(amounts.sum())
    n       = len(df)

    # MoM growth (requires date col)
    if date_col and date_col in df.columns:
        work = df[[date_col, amount_col]].copy()
        work[date_col]   = pd.to_datetime(work[date_col], errors="coerce")
        work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce").fillna(0)
        work = work.dropna(subset=[date_col])
        work["_month"] = work[date_col].dt.to_period("M")
        monthly = work.groupby("_month")[amount_col].sum().sort_index()

        if len(monthly) >= 2:
            cur_m  = float(monthly.iloc[-1])
            prev_m = float(monthly.iloc[-2])
            if prev_m > 0:
                mom_growth = (cur_m - prev_m) / prev_m * 100
                kpis.append(_kpi(
                    name="MoM Growth Rate",
                    value=round(mom_growth, 1),
                    unit="%",
                    formula="(Current_Month - Previous_Month) / Previous_Month × 100",
                    source_columns=[amount_col, date_col],
                    confidence=_conf(n),
                    interpretation=f"Spending {'grew' if mom_growth >= 0 else 'declined'} {abs(mom_growth):.1f}% vs last month",
                    status="good" if abs(mom_growth) < 20 else "warning",
                    benchmark="Healthy: < 20% swing MoM",
                ))

        # Run rate (annualized)
        if len(work) >= 2:
            days = max((work[date_col].max() - work[date_col].min()).days, 1)
            run_rate = total / days * 365
            kpis.append(_kpi(
                name="Annual Run Rate",
                value=round(run_rate, 2),
                unit="₹/year",
                formula="(SUM(Amount) / DateRange_days) × 365",
                source_columns=[amount_col, date_col],
                confidence=_conf(n),
                interpretation=f"At current pace, annual spend ≈ ₹{run_rate:,.0f}",
                status="good",
                benchmark="N/A",
            ))

    # Spending consistency (Coefficient of Variation — lower = more consistent)
    if len(amounts.dropna()) > 1:
        mean = float(amounts.mean())
        std  = float(amounts.std())
        cv   = (std / mean * 100) if mean > 0 else 0
        kpis.append(_kpi(
            name="Spending Consistency (CV)",
            value=round(cv, 1),
            unit="%",
            formula="StdDev(Amount) / Mean(Amount) × 100",
            source_columns=[amount_col],
            confidence=_conf(n),
            interpretation=f"Spending variability: {cv:.1f}% CV ({'consistent' if cv < 50 else 'volatile'})",
            status="good" if cv < 50 else "warning",
            benchmark="Healthy: CV < 50%",
        ))

    return kpis


def compute_generic_kpis(df: pd.DataFrame, schema: dict) -> list:
    """Fallback KPIs that work for any dataset."""
    kpis = []
    amount_col = schema.get("amount_col")
    if not amount_col or amount_col not in df.columns:
        return kpis

    amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
    n = len(amounts)
    if n == 0:
        return kpis

    total  = float(amounts.sum())
    mean   = float(amounts.mean())
    median = float(amounts.median())
    std    = float(amounts.std()) if n > 1 else 0

    kpis.append(_kpi("Total",  round(total, 2),  "₹", "SUM(Amount)",    [amount_col], _conf(n), f"₹{total:,.2f} total", "good", ""))
    kpis.append(_kpi("Mean",   round(mean, 2),   "₹", "MEAN(Amount)",   [amount_col], _conf(n), f"₹{mean:,.2f} average per transaction", "good", ""))
    kpis.append(_kpi("Median", round(median, 2), "₹", "MEDIAN(Amount)", [amount_col], _conf(n), f"₹{median:,.2f} typical transaction", "good", ""))
    if n > 1:
        kpis.append(_kpi("Std Dev", round(std, 2), "₹", "STDDEV(Amount)", [amount_col], _conf(n), f"₹{std:,.2f} spread around mean", "good", ""))

    # Data completeness
    total_cells   = len(df) * len(df.columns)
    missing_cells = df.isna().sum().sum()
    completeness  = round(100 * (1 - missing_cells / max(total_cells, 1)), 1)
    kpis.append(_kpi(
        name="Data Completeness",
        value=completeness,
        unit="%",
        formula="(1 - Missing_Cells / Total_Cells) × 100",
        source_columns=list(df.columns[:5]),
        confidence=99,
        interpretation=f"Dataset is {completeness:.1f}% complete",
        status="good" if completeness > 90 else ("warning" if completeness > 70 else "critical"),
        benchmark="Healthy: > 90%",
    ))

    return kpis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kpi(name, value, unit, formula, source_columns, confidence, interpretation, status, benchmark) -> dict:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "formula": formula,
        "source_columns": source_columns,
        "confidence": confidence,
        "interpretation": interpretation,
        "status": status,
        "benchmark": benchmark,
    }


def _conf(n: int) -> float:
    if n >= 200: return 95.0
    if n >= 100: return 90.0
    if n >= 30:  return 82.0
    if n >= 10:  return 65.0
    return 40.0


def _safe_compute(fn, df, schema):
    try:
        result = fn(df, schema)
        return result if isinstance(result, list) else []
    except Exception:
        return []


def _dedupe_kpis(kpis: list) -> list:
    seen = set()
    result = []
    for k in kpis:
        name = k.get("name", "")
        if name not in seen:
            seen.add(name)
            result.append(k)
    return result
