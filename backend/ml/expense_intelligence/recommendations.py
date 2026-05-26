from __future__ import annotations

import pandas as pd


def generate_recommendations(df: pd.DataFrame, behavior: dict, anomalies: dict, forecast: dict) -> list[dict]:
    recommendations: list[dict] = []
    total = behavior.get("total_spend", 0) or 0

    for item in behavior.get("top_categories", [])[:3]:
        share = float(item["sum"]) / total if total else 0
        if share >= 0.25:
            recommendations.append({
                "type": "budget_optimization",
                "priority": "high" if share >= 0.40 else "medium",
                "title": f"Review {item['category']} spending",
                "recommendation": f"{item['category']} accounts for {share:.1%} of total spend. Set a category cap and monitor weekly drift.",
                "why": f"High concentration: {item['sum']:.2f} across {int(item['count'])} transactions.",
            })

    if behavior.get("weekend_spend_ratio", 0) > 0.45:
        recommendations.append({
            "type": "behavioral",
            "priority": "medium",
            "title": "Weekend spending guardrail",
            "recommendation": "Create a weekend budget alert because weekend transactions dominate spend.",
            "why": f"Weekend spend ratio is {behavior['weekend_spend_ratio']:.1%}.",
        })

    if anomalies.get("anomaly_count", 0):
        recommendations.append({
            "type": "risk",
            "priority": "high",
            "title": "Investigate anomalous expenses",
            "recommendation": "Review the top flagged transactions before reimbursement or settlement.",
            "why": f"{anomalies['anomaly_count']} unusual transactions were detected with explainable anomaly scoring.",
        })

    if forecast.get("status") == "ok":
        predicted_total = sum(x["predicted_amount"] for x in forecast["forecast"])
        recommendations.append({
            "type": "forecast",
            "priority": "medium",
            "title": "Plan next-month burn rate",
            "recommendation": f"Reserve approximately {predicted_total:.2f} for the next forecast window, then compare actuals weekly.",
            "why": f"Forecast validation: {forecast.get('validation', {})}.",
        })

    if not recommendations:
        recommendations.append({
            "type": "data_quality",
            "priority": "low",
            "title": "Improve transaction metadata",
            "recommendation": "Add consistent merchant, payer, participant, and category fields to unlock stronger recommendations.",
            "why": "Current data does not show dominant categories, anomalies, or enough temporal history.",
        })

    return recommendations
