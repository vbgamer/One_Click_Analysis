"""
lineage.py — Data Lineage Engine for Autonomous Data Intelligence Platform (ADIP).

Tracks: CSV column → transformation → KPI → insight.

Enterprises ask: "Where exactly did this number come from?"
This module answers that with a full, reproducible audit trail.
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def build_lineage(df: pd.DataFrame, schema: dict, results: dict) -> dict:
    """Build complete data lineage for all pipeline outputs.

    Returns
    -------
    dict
        {lineage_entries: list, total_tracked: int, source_file_columns: list}
    """
    entries = generate_lineage_for_results(df, schema, results)
    return {
        "available": True,
        "lineage_entries": entries,
        "total_tracked": len(entries),
        "source_file_columns": list(df.columns),
        "total_source_columns": len(df.columns),
        "total_rows": len(df),
    }


def generate_lineage_for_results(df: pd.DataFrame, schema: dict, results: dict) -> list:
    """Auto-generate lineage entries for all standard pipeline outputs."""
    entries = []
    amount_col   = schema.get("amount_col")
    date_col     = schema.get("date_col")
    payer_col    = schema.get("payer_col")
    category_col = schema.get("category_col")

    # 1. Total Spend
    if amount_col and amount_col in df.columns:
        amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
        total   = round(float(amounts.sum()), 2)
        entries.append(trace_kpi_lineage(
            kpi_name="Total Spend",
            formula="SUM(Amount)",
            source_columns=[amount_col],
            transformations=[
                {"step": 1, "operation": f"df['{amount_col}']", "description": "Select amount column", "output": "raw_amounts"},
                {"step": 2, "operation": "pd.to_numeric(errors='coerce').fillna(0)", "description": "Parse as numbers, fill NaN with 0", "output": "numeric_amounts"},
                {"step": 3, "operation": ".sum()", "description": "Sum all values", "output": f"₹{total:,.2f}"},
            ],
            derived_insights=["Fairness Index", "Fair Share Per Person", "Daily Spend Rate"],
            computed_value=total,
            reproducible_code=f"pd.to_numeric(df['{amount_col}'], errors='coerce').fillna(0).sum()",
        ))

    # 2. Anomalies
    if amount_col and amount_col in df.columns:
        anomalies = results.get("anomalies", {}) or {}
        count = anomalies.get("anomaly_count", 0)
        entries.append(trace_kpi_lineage(
            kpi_name="Anomaly Detection",
            formula="IsolationForest(contamination=auto) on [Amount, DayOfWeek, DayOfMonth]",
            source_columns=[c for c in [amount_col, date_col] if c],
            transformations=[
                {"step": 1, "operation": "Feature engineering: DayOfWeek, DayOfMonth from Date", "description": "Extract temporal features", "output": "feature_matrix"},
                {"step": 2, "operation": "StandardScaler().fit_transform(features)", "description": "Normalize features", "output": "scaled_features"},
                {"step": 3, "operation": "IsolationForest().fit_predict(scaled_features)", "description": "Train isolation forest", "output": "anomaly_scores"},
                {"step": 4, "operation": "score < threshold → flagged", "description": "Apply threshold to flag anomalies", "output": f"{count} anomalies flagged"},
            ],
            derived_insights=["Top Ranked Insight: Anomalous Transaction"],
            computed_value=f"{count} anomalies",
            reproducible_code="from sklearn.ensemble import IsolationForest; IsolationForest(random_state=42).fit_predict(X)",
        ))

    # 3. Monthly Forecast
    if date_col and amount_col:
        forecast = results.get("forecast", {}) or {}
        next_pred = forecast.get("next_month_prediction") or forecast.get("predicted_next_month")
        if next_pred is not None:
            entries.append(trace_kpi_lineage(
                kpi_name="Monthly Forecast",
                formula="Linear regression on monthly aggregates",
                source_columns=[c for c in [date_col, amount_col] if c],
                transformations=[
                    {"step": 1, "operation": f"GROUP BY month('{date_col}') → SUM('{amount_col}')", "description": "Aggregate to monthly totals", "output": "monthly_series"},
                    {"step": 2, "operation": "Fit LinearRegression on time index", "description": "Train trend model", "output": "trend_coefficients"},
                    {"step": 3, "operation": "Predict next period value", "description": "Extrapolate forecast", "output": f"₹{float(next_pred):,.0f}"},
                ],
                derived_insights=["Forecast: Next Month Spending"],
                computed_value=round(float(next_pred), 2),
                reproducible_code="monthly = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum(); np.polyfit(range(len(monthly)), monthly.values, 1)",
            ))

    # 4. Settlement Plan
    if payer_col and amount_col:
        settlement = results.get("settlement", {}) or {}
        payments   = settlement.get("optimal_payments", []) or []
        entries.append(trace_kpi_lineage(
            kpi_name="Settlement Plan",
            formula="Balance = Paid - Fair_Share; Minimize transactions to settle",
            source_columns=[c for c in [payer_col, amount_col] if c],
            transformations=[
                {"step": 1, "operation": f"GROUP BY '{payer_col}' → SUM('{amount_col}')", "description": "Calculate per-person total paid", "output": "payer_totals"},
                {"step": 2, "operation": "fair_share = total / n_payers", "description": "Calculate equal fair share", "output": "fair_share_per_person"},
                {"step": 3, "operation": "balance = paid - fair_share", "description": "Compute net balance per person", "output": "balances"},
                {"step": 4, "operation": "Greedy settlement: match positives with negatives", "description": "Optimize payment transactions", "output": f"{len(payments)} optimal transaction(s)"},
            ],
            derived_insights=["Fairness Index KPI"],
            computed_value=f"{len(payments)} transactions",
            reproducible_code=f"payer_totals = df.groupby('{payer_col}')['{amount_col}'].sum(); balance = payer_totals - payer_totals.sum()/len(payer_totals)",
        ))

    # 5. Spending Recommendations
    recs = results.get("recommendations", []) or []
    if recs:
        entries.append(trace_kpi_lineage(
            kpi_name="Spending Recommendations",
            formula="Pattern analysis: category concentration, payer imbalance, temporal spikes",
            source_columns=[c for c in [amount_col, date_col, category_col, payer_col] if c],
            transformations=[
                {"step": 1, "operation": "Analyze category spend distribution", "description": "Find dominant categories", "output": "category_shares"},
                {"step": 2, "operation": "Detect MoM growth > 20%", "description": "Flag high-growth categories", "output": "growth_flags"},
                {"step": 3, "operation": "Match patterns to recommendation templates", "description": "Generate actionable suggestions", "output": f"{len(recs)} recommendation(s)"},
            ],
            derived_insights=[r.get("title", "")[:60] for r in recs[:3]],
            computed_value=f"{len(recs)} recommendations",
            reproducible_code="category_spend = df.groupby(category_col)[amount_col].sum(); top = category_spend.idxmax()",
        ))

    # 6. KPIs
    kpis_result = results.get("kpis", {}) or {}
    kpi_list    = kpis_result.get("kpis", []) or []
    for kpi in kpi_list[:5]:
        if not isinstance(kpi, dict):
            continue
        entries.append(trace_kpi_lineage(
            kpi_name=kpi.get("name", "KPI"),
            formula=kpi.get("formula", ""),
            source_columns=kpi.get("source_columns", []),
            transformations=[
                {"step": 1, "operation": f"SELECT {', '.join(kpi.get('source_columns', [])[:3])}", "description": "Select source columns", "output": "raw_values"},
                {"step": 2, "operation": kpi.get("formula", "aggregate"), "description": "Apply formula", "output": f"{kpi.get('value', '?')} {kpi.get('unit', '')}"},
            ],
            derived_insights=[kpi.get("interpretation", "")[:80]],
            computed_value=kpi.get("value"),
            reproducible_code=kpi.get("formula", ""),
        ))

    return entries


# ---------------------------------------------------------------------------
# Lineage Builders
# ---------------------------------------------------------------------------

def trace_kpi_lineage(
    kpi_name: str,
    formula: str,
    source_columns: list,
    transformations: list,
    derived_insights: list,
    computed_value=None,
    reproducible_code: str = "",
) -> dict:
    """Build a lineage entry for a single KPI."""
    text_trail = _build_text_trail(source_columns, transformations, computed_value)
    return {
        "output_name": kpi_name,
        "output_type": "kpi",
        "source_columns": source_columns,
        "formula": formula,
        "transformations": transformations,
        "derived_from": [],
        "used_by": derived_insights,
        "computed_value": str(computed_value) if computed_value is not None else None,
        "reproducible_code": reproducible_code,
        "text_trail": text_trail,
    }


def trace_insight_lineage(
    insight_title: str,
    source_kpis: list,
    source_columns: list,
    calculation: str,
) -> dict:
    """Build a lineage entry for a derived insight."""
    return {
        "output_name": insight_title,
        "output_type": "insight",
        "source_columns": source_columns,
        "formula": calculation,
        "transformations": [{"step": 1, "operation": calculation, "description": "Derived from KPIs", "output": insight_title}],
        "derived_from": source_kpis,
        "used_by": [],
        "reproducible_code": calculation,
        "text_trail": " → ".join(source_kpis + [insight_title]),
    }


def format_lineage_as_text(lineage_entry: dict) -> str:
    """Format a lineage entry as a human-readable text trail."""
    return lineage_entry.get("text_trail", f"{lineage_entry.get('output_name', '?')} (no trail available)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_text_trail(source_columns: list, transformations: list, final_value) -> str:
    parts = list(source_columns[:2])
    for t in transformations:
        parts.append(t.get("output", t.get("operation", "?")))
    if final_value is not None:
        parts.append(str(final_value))
    return " → ".join(str(p) for p in parts)
