from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_anomalies(df: pd.DataFrame) -> dict:
    work = df.copy()
    if len(work) < 8:
        return {"status": "insufficient_data", "anomalies": [], "summary": "Need at least 8 transactions."}

    category_medians = work.groupby("category")["amount"].transform("median").replace(0, work["amount"].median())
    work["category_amount_ratio"] = work["amount"] / category_medians
    work["amount_zscore"] = (work["amount"] - work["amount"].mean()) / (work["amount"].std() or 1)

    features = work[["amount", "category_amount_ratio", "amount_zscore"]].fillna(0)
    contamination = min(0.12, max(0.02, 5 / len(work)))
    model = IsolationForest(contamination=contamination, random_state=42)
    work["anomaly_flag"] = model.fit_predict(features) == -1
    work["anomaly_score"] = -model.score_samples(features)

    anomalies = []
    for _, row in work[work["anomaly_flag"]].sort_values("anomaly_score", ascending=False).head(20).iterrows():
        reasons = []
        if abs(row["amount_zscore"]) > 2:
            reasons.append(f"amount is {row['amount_zscore']:.1f} standard deviations from the mean")
        if row["category_amount_ratio"] > 2:
            reasons.append(f"amount is {row['category_amount_ratio']:.1f}x the typical spend for {row['category']}")
        if not reasons:
            reasons.append("unusual combination of amount and category behavior")
        anomalies.append({
            "date": row["expense_date"].date().isoformat() if pd.notna(row["expense_date"]) else None,
            "amount": round(float(row["amount"]), 2),
            "category": row["category"],
            "description": row.get("description", ""),
            "score": round(float(row["anomaly_score"]), 4),
            "explanation": "; ".join(reasons),
        })

    return {
        "status": "ok",
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "model": "IsolationForest + category-relative statistical explanations",
    }
