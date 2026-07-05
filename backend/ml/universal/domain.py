"""
domain.py — Dataset domain detection for the Universal Analysis Engine.

Classifies a dataset into a business domain using column-name and value
signals. Domain drives KPI vocabulary and optional analysis modules
(e.g. expense settlement only runs for the finance domain).

Public API
----------
detect_domain(df, schema) -> dict
"""

import re

import pandas as pd

# Each domain: {keywords: {token: weight}, label, description}
_DOMAINS = {
    "sales": {
        "label": "Sales & Revenue",
        "keywords": {
            "revenue": 3, "sales": 3, "order": 2.5, "customer": 2, "product": 2,
            "price": 1.5, "quantity": 2, "discount": 2, "sku": 2.5, "invoice": 1.5,
            "deal": 2, "pipeline": 2, "units": 1.5, "gmv": 3, "cart": 2.5,
            "checkout": 2.5, "store": 1.5, "region": 1, "channel": 1.5,
        },
    },
    "finance": {
        "label": "Finance & Expenses",
        "keywords": {
            "expense": 3, "payment": 2, "paid": 2, "payer": 3, "settlement": 3,
            "merchant": 2.5, "transaction": 2, "debit": 2.5, "credit": 2.5,
            "balance": 2, "account": 1.5, "budget": 2, "spend": 2.5, "cost": 1.5,
            "reimburse": 3, "vendor": 1.5, "bill": 2, "tax": 1.5, "fee": 1.5,
        },
    },
    "hr": {
        "label": "HR & People",
        "keywords": {
            "employee": 3, "salary": 3, "department": 2, "hire": 2.5, "hired": 2.5,
            "manager": 2, "attrition": 3, "tenure": 2.5, "job": 1.5, "designation": 2.5,
            "leave": 2, "performance": 1.5, "promotion": 2.5, "wage": 2.5,
            "staff": 2, "position": 1.5, "gender": 1, "age": 1, "compensation": 3,
        },
    },
    "marketing": {
        "label": "Marketing & Campaigns",
        "keywords": {
            "campaign": 3, "clicks": 3, "impressions": 3, "ctr": 3, "cpc": 3,
            "conversion": 2.5, "ad": 2, "channel": 2, "lead": 2, "engagement": 2,
            "reach": 2, "audience": 2, "email": 1, "open_rate": 3, "bounce": 2,
            "spend": 1.5, "roas": 3, "utm": 3,
        },
    },
    "operations": {
        "label": "Operations & Inventory",
        "keywords": {
            "inventory": 3, "stock": 3, "warehouse": 3, "shipment": 2.5,
            "delivery": 2.5, "supplier": 2.5, "logistics": 3, "sku": 2,
            "lead_time": 3, "backorder": 3, "fulfillment": 2.5, "shipping": 2,
            "production": 2, "defect": 2.5, "downtime": 3, "machine": 2,
        },
    },
    "support": {
        "label": "Customer & Support",
        "keywords": {
            "ticket": 3, "issue": 2, "resolution": 2.5, "agent": 2, "csat": 3,
            "nps": 3, "complaint": 2.5, "churn": 3, "subscription": 2,
            "response_time": 3, "escalation": 3, "satisfaction": 2.5, "sla": 3,
            "feedback": 2, "support": 2.5,
        },
    },
    "survey": {
        "label": "Survey & Research",
        "keywords": {
            "survey": 3, "response": 2, "respondent": 3, "question": 2.5,
            "answer": 2, "rating": 2, "scale": 1.5, "agree": 2.5, "disagree": 2.5,
            "opinion": 2.5, "satisfaction": 1.5, "likert": 3,
        },
    },
    "health": {
        "label": "Health & Fitness",
        "keywords": {
            "patient": 3, "diagnosis": 3, "treatment": 2.5, "doctor": 2.5,
            "hospital": 2.5, "medication": 3, "symptom": 3, "bmi": 3,
            "blood": 2.5, "heart": 2, "weight": 1.5, "calories": 2.5,
            "steps": 2, "sleep": 2, "exercise": 2,
        },
    },
    "education": {
        "label": "Education & Academics",
        "keywords": {
            "student": 3, "grade": 2.5, "course": 2.5, "exam": 3, "school": 2.5,
            "teacher": 2.5, "score": 1.5, "attendance": 2.5, "subject": 2,
            "marks": 3, "gpa": 3, "semester": 3, "class": 1.5, "enrollment": 3,
        },
    },
}

_GENERIC = {"domain": "generic", "label": "General Data", "confidence": 0.0}


def _tokenize(name: str) -> list:
    return [t for t in re.split(r"[_\s\-./]+", str(name).lower()) if t]


def detect_domain(df: pd.DataFrame, schema: dict) -> dict:
    """Score the dataset against known domains.

    Returns
    -------
    dict : {domain, label, confidence, scores, signals}
    """
    # Collect signal tokens from column names
    tokens: list = []
    for col in df.columns:
        tokens.extend(_tokenize(col))
    token_set = set(tokens)
    joined = " ".join(tokens)

    # Also sample categorical values as weak signals
    value_tokens: set = set()
    for col_meta in schema.get("columns", []):
        if col_meta.get("semantic_type") in ("category", "geo"):
            for v in list(col_meta.get("top_values", {}).keys())[:5]:
                value_tokens.update(_tokenize(v))

    scores: dict = {}
    signals: dict = {}
    for domain, spec in _DOMAINS.items():
        score = 0.0
        matched = []
        for kw, weight in spec["keywords"].items():
            if kw in token_set:
                score += weight
                matched.append(kw)
            elif len(kw) > 4 and kw in joined:
                score += weight * 0.6
                matched.append(kw)
            elif kw in value_tokens:
                score += weight * 0.3
                matched.append(f"{kw} (value)")
        scores[domain] = round(score, 2)
        signals[domain] = matched

    best = max(scores, key=scores.get)
    best_score = scores[best]
    runner_up = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0

    # Confidence: needs both absolute evidence and separation from runner-up
    if best_score < 4:
        result = dict(_GENERIC)
        result["scores"] = scores
        result["signals"] = []
        return result

    separation = (best_score - runner_up) / max(best_score, 1)
    confidence = min(0.95, (best_score / 15) * 0.6 + separation * 0.4)
    confidence = round(max(confidence, 0.3), 2)

    return {
        "domain": best,
        "label": _DOMAINS[best]["label"],
        "confidence": confidence,
        "scores": scores,
        "signals": signals.get(best, [])[:8],
    }


def kpi_vocabulary(domain: str) -> dict:
    """Domain-appropriate names for the KPI strip."""
    vocab = {
        "sales":      {"total": "Total Revenue", "avg": "Avg Order Value", "count": "Transactions", "top": "Top Product/Segment"},
        "finance":    {"total": "Total Spend", "avg": "Avg Transaction", "count": "Transactions", "top": "Top Expense Category"},
        "hr":         {"total": "Total Payroll", "avg": "Avg Salary", "count": "Employees", "top": "Largest Department"},
        "marketing":  {"total": "Total Spend/Reach", "avg": "Avg per Campaign", "count": "Campaigns/Records", "top": "Best Channel"},
        "operations": {"total": "Total Volume", "avg": "Avg per Record", "count": "Records", "top": "Top Category"},
        "support":    {"total": "Total Volume", "avg": "Avg Resolution", "count": "Tickets", "top": "Top Issue Type"},
        "survey":     {"total": "Total Responses", "avg": "Avg Rating", "count": "Respondents", "top": "Most Common Answer"},
        "health":     {"total": "Total", "avg": "Average", "count": "Records", "top": "Top Category"},
        "education":  {"total": "Total", "avg": "Avg Score", "count": "Students/Records", "top": "Top Group"},
    }
    return vocab.get(domain, {"total": "Total", "avg": "Average", "count": "Records", "top": "Top Segment"})
