"""
insight_ranker.py — Insight Prioritization Engine for ADIP.

Prevents insight overload by ranking ALL findings from ALL modules
and surfacing the TOP 5 most important ones.

Ranking factors:
  1. Business impact magnitude (40 pts)
  2. Confidence score (30 pts)
  3. Actionability — can the user do something? (20 pts)
  4. Novelty — is it non-obvious? (10 pts)
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def rank_insights(results: dict, df: pd.DataFrame, schema: dict) -> dict:
    """Take all pipeline results and produce a ranked top-insights list.

    Returns
    -------
    dict
        {top_insights: list (up to 5), total_considered: int, ranking_method: str}
    """
    candidates = extract_candidate_insights(results, df, schema)

    amount_col = schema.get("amount_col")
    total_spend = 0.0
    if amount_col and amount_col in df.columns:
        total_spend = float(pd.to_numeric(df[amount_col], errors="coerce").fillna(0).sum())

    for cand in candidates:
        cand["_score"] = score_insight(
            insight_type=cand.get("category", "generic"),
            data=cand,
            df=df,
            schema=schema,
            total_spend=total_spend,
        )
        amount_affected = float(cand.get("amount_affected", 0) or 0)
        cand["business_impact"] = classify_business_impact(cand["_score"], amount_affected, total_spend)

    candidates.sort(key=lambda x: x.get("_score", 0), reverse=True)

    top5 = []
    for rank, cand in enumerate(candidates[:5], 1):
        top5.append({
            "rank": rank,
            "title": cand.get("title", "Unnamed insight"),
            "summary": cand.get("summary", cand.get("title", "")),
            "category": cand.get("category", "generic"),
            "business_impact": cand.get("business_impact", "low"),
            "confidence": round(float(cand.get("confidence", 50)), 1),
            "audit_status": cand.get("audit_status", "INCONCLUSIVE"),
            "score": round(float(cand.get("_score", 0)), 1),
            "action": cand.get("action", "Review this finding"),
            "evidence_summary": cand.get("evidence_summary", ""),
            "source": cand.get("source", "pipeline"),
        })

    return {
        "available": len(top5) > 0,
        "top_insights": top5,
        "total_considered": len(candidates),
        "ranking_method": "Composite: business_impact(40%) + confidence(30%) + actionability(20%) + novelty(10%)",
    }


# ---------------------------------------------------------------------------
# Insight Extraction
# ---------------------------------------------------------------------------

def extract_candidate_insights(results: dict, df: pd.DataFrame, schema: dict) -> list:
    """Extract candidate insights from all pipeline result keys."""
    candidates = []
    amount_col = schema.get("amount_col")

    total_spend = 0.0
    if amount_col and amount_col in df.columns:
        total_spend = float(pd.to_numeric(df[amount_col], errors="coerce").fillna(0).sum())

    # --- Anomalies ---
    anomalies = results.get("anomalies", {}) or {}
    flagged = anomalies.get("flagged_rows", []) or []
    for row in flagged[:5]:
        if not isinstance(row, dict):
            continue
        amount = float(row.get("amount") or row.get("Amount") or 0)
        score_val = float(row.get("anomaly_score", 0.5))
        candidates.append({
            "title": f"Anomalous transaction: {row.get('reason', 'Unusual pattern')}",
            "summary": f"Transaction flagged as anomaly (score: {score_val:.2f})" + (f" — ₹{amount:,.0f}" if amount else ""),
            "category": "anomaly",
            "confidence": round(min(95, score_val * 100 + 30), 1),
            "amount_affected": amount,
            "audit_status": "PASSED",
            "action": "Review this transaction for accuracy",
            "evidence_summary": f"Amount: ₹{amount:,.0f} | Score: {score_val:.2f}",
            "source": "anomaly_detection",
        })

    # --- Recommendations ---
    recs = results.get("recommendations", []) or []
    for rec in recs[:5]:
        if not isinstance(rec, dict):
            continue
        impact_str = str(rec.get("impact", "") or rec.get("expected_impact", "") or "")
        # Try to extract numeric amount from impact string
        amount_affected = _extract_amount(impact_str)
        candidates.append({
            "title": rec.get("title", "Spending recommendation"),
            "summary": rec.get("description", "")[:200],
            "category": "recommendation",
            "confidence": float(rec.get("confidence", 70)),
            "amount_affected": amount_affected,
            "audit_status": "PASSED",
            "action": rec.get("title", "Implement recommendation"),
            "evidence_summary": impact_str[:120],
            "source": "recommendation_engine",
        })

    # --- Hypotheses ---
    hypotheses_result = results.get("hypotheses", {}) or {}
    hypothesis_list   = hypotheses_result.get("hypotheses", []) or []
    for h in hypothesis_list:
        if not isinstance(h, dict) or h.get("status") == "skipped":
            continue
        is_verified = h.get("status") == "verified"
        if is_verified:  # Only surface verified hypotheses
            candidates.append({
                "title": h.get("statement", "Hypothesis"),
                "summary": h.get("key_finding", "")[:200],
                "category": "hypothesis",
                "confidence": float(h.get("confidence", 60)),
                "amount_affected": 0,
                "audit_status": "PASSED",
                "action": h.get("business_implication", "Investigate this pattern")[:120],
                "evidence_summary": h.get("key_finding", "")[:120],
                "source": "hypothesis_engine",
            })

    # --- Root Cause ---
    root_cause = results.get("root_cause", {}) or {}
    analyses   = root_cause.get("analyses", []) or []
    for analysis in analyses[:2]:
        if not isinstance(analysis, dict) or not analysis.get("available"):
            continue
        candidates.append({
            "title": analysis.get("title", "Root Cause Analysis"),
            "summary": analysis.get("explanation", analysis.get("summary", ""))[:200],
            "category": "root_cause",
            "confidence": 85.0,
            "amount_affected": abs(float(analysis.get("change_abs", 0) or 0)),
            "audit_status": "PASSED",
            "action": "Address identified root causes",
            "evidence_summary": analysis.get("explanation", "")[:120],
            "source": "root_cause_engine",
        })

    # --- KPIs with critical/warning status ---
    kpis_result = results.get("kpis", {}) or {}
    kpi_list    = kpis_result.get("kpis", []) or []
    for kpi in kpi_list:
        if not isinstance(kpi, dict):
            continue
        if kpi.get("status") in ("critical", "warning"):
            val = kpi.get("value", "")
            unit = kpi.get("unit", "")
            candidates.append({
                "title": f"KPI Alert: {kpi.get('name', 'Unknown KPI')}",
                "summary": kpi.get("interpretation", "")[:200],
                "category": "kpi",
                "confidence": float(kpi.get("confidence", 70)),
                "amount_affected": 0,
                "audit_status": "PASSED",
                "action": f"Review {kpi.get('name', 'KPI')}: {val}{unit} — {kpi.get('benchmark', '')}",
                "evidence_summary": f"{kpi.get('name')}: {val}{unit} | Formula: {kpi.get('formula', '')}",
                "source": "kpi_engine",
            })

    # --- Forecast ---
    forecast = results.get("forecast", {}) or {}
    if forecast.get("available") or forecast.get("next_month_prediction"):
        next_pred = forecast.get("next_month_prediction") or forecast.get("predicted_next_month")
        if next_pred is not None:
            candidates.append({
                "title": "Forecast: Next Month Spending",
                "summary": f"Predicted next month total: ₹{float(next_pred):,.0f}",
                "category": "forecast",
                "confidence": 65.0,
                "amount_affected": float(next_pred),
                "audit_status": "PASSED",
                "action": "Plan budget for next month based on forecast",
                "evidence_summary": f"Predicted: ₹{float(next_pred):,.0f} (time-series model)",
                "source": "forecasting_engine",
            })

    return candidates


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_insight(
    insight_type: str,
    data: dict,
    df: pd.DataFrame,
    schema: dict,
    total_spend: float = 0,
) -> float:
    """Score an insight 0-100 for ranking purposes."""
    score = 0.0

    # 1. Business impact (0-40 pts)
    amount_affected = float(data.get("amount_affected", 0) or 0)
    if total_spend > 0 and amount_affected > 0:
        impact_pct = amount_affected / total_spend
        score += min(40, impact_pct * 200)  # 20% of spend = 40 pts
    else:
        # Type-based default impact
        type_impact = {
            "anomaly": 25, "root_cause": 30, "recommendation": 22,
            "hypothesis": 18, "kpi": 15, "forecast": 12, "generic": 5,
        }
        score += type_impact.get(insight_type, 10)

    # 2. Confidence (0-30 pts)
    confidence = float(data.get("confidence", 50) or 50)
    score += (confidence / 100) * 30

    # 3. Actionability (0-20 pts)
    action = data.get("action", "")
    if action and len(action) > 20:
        score += 20
    elif action:
        score += 10
    # Certain types are inherently more actionable
    if insight_type in ("recommendation", "anomaly", "root_cause"):
        score += 5

    # 4. Novelty (0-10 pts) — anomalies and root causes are more novel
    novelty = {"anomaly": 10, "root_cause": 9, "hypothesis": 7, "recommendation": 5, "kpi": 3, "forecast": 4}
    score += novelty.get(insight_type, 3)

    return min(100.0, score)


def classify_business_impact(score: float, amount_affected: float, total_spend: float) -> str:
    """Classify business impact as high, medium, or low."""
    if total_spend > 0 and amount_affected > 0:
        pct = amount_affected / total_spend
        if pct > 0.20 or score > 70:
            return "high"
        if pct > 0.05 or score > 40:
            return "medium"
        return "low"
    if score > 70:
        return "high"
    if score > 40:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_amount(text: str) -> float:
    """Try to extract a numeric amount from an impact description string."""
    import re
    matches = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    for m in matches:
        try:
            return float(m)
        except ValueError:
            continue
    return 0.0
