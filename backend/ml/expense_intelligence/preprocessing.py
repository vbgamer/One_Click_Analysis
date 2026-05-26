from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from difflib import get_close_matches
from typing import Any

import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "amount": ["amount", "amt", "price", "cost", "total", "debit", "withdrawal", "expense", "paid"],
    "date": ["date", "transaction_date", "txn_date", "order_date", "created_at", "paid_on"],
    "description": ["description", "desc", "note", "details", "merchant", "name", "title", "narration"],
    "payer": ["payer", "paid_by", "user", "person", "member", "from"],
    "participant": ["participant", "participants", "split_with", "shared_with", "to"],
    "category": ["category", "type", "label", "class"],
}


CANONICAL_CATEGORIES = {
    "food": ["food", "restaurant", "cafe", "swiggy", "zomato", "pizza", "meal", "lunch", "dinner"],
    "transport": ["uber", "ola", "rapido", "taxi", "cab", "fuel", "metro", "train", "bus", "transport"],
    "alcohol": ["bar", "beer", "wine", "liquor", "alcohol", "oaksmith", "whisky", "whiskey"],
    "shopping": ["amazon", "flipkart", "mall", "shopping", "clothes", "apparel"],
    "rent": ["rent", "lease", "house", "flat"],
    "utilities": ["electricity", "water", "wifi", "internet", "utility", "gas", "recharge"],
    "travel": ["hotel", "flight", "airbnb", "trip", "travel", "booking"],
    "health": ["medical", "pharmacy", "doctor", "hospital", "health"],
    "entertainment": ["movie", "netflix", "prime", "spotify", "game", "entertainment"],
}


@dataclass
class ValidationIssue:
    severity: str
    field: str
    message: str


def _standardize_column_name(name: Any) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())).strip("_")


def detect_schema(df: pd.DataFrame) -> dict[str, str | None]:
    columns = {_standardize_column_name(c): c for c in df.columns}
    detected: dict[str, str | None] = {key: None for key in COLUMN_ALIASES}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in columns:
                detected[canonical] = columns[alias]
                break
        if detected[canonical] is None:
            match = get_close_matches(canonical, columns.keys(), n=1, cutoff=0.78)
            if match:
                detected[canonical] = columns[match[0]]
    return detected


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9@&./ -]+", "", text)
    return text


def infer_category(description: str, existing_category: str = "") -> tuple[str, float, str]:
    source = f"{existing_category} {description}".lower()
    if existing_category:
        normalized_existing = normalize_text(existing_category)
        for canonical, keywords in CANONICAL_CATEGORIES.items():
            if normalized_existing == canonical or normalized_existing in keywords:
                return canonical, 0.95, "trusted existing category"

    scores = []
    for canonical, keywords in CANONICAL_CATEGORIES.items():
        hits = sum(1 for kw in keywords if kw in source)
        if hits:
            scores.append((canonical, hits / max(len(keywords), 1)))
    if not scores:
        return "uncategorized", 0.35, "no strong semantic match"
    best = max(scores, key=lambda item: item[1])
    confidence = min(0.90, 0.55 + best[1])
    return best[0], confidence, "keyword/semantic alias match"


def preprocess_expenses(df: pd.DataFrame) -> dict[str, Any]:
    original_rows = len(df)
    work = df.copy()
    work.columns = [_standardize_column_name(c) for c in work.columns]
    schema = detect_schema(work)

    issues: list[ValidationIssue] = []
    audit: list[str] = [f"Loaded {original_rows:,} rows and {len(work.columns):,} columns."]

    amount_col = _standardize_column_name(schema["amount"]) if schema.get("amount") else None
    date_col = _standardize_column_name(schema["date"]) if schema.get("date") else None
    desc_col = _standardize_column_name(schema["description"]) if schema.get("description") else None
    category_col = _standardize_column_name(schema["category"]) if schema.get("category") else None
    payer_col = _standardize_column_name(schema["payer"]) if schema.get("payer") else None

    if not amount_col or amount_col not in work:
        numeric_cols = work.select_dtypes(include="number").columns.tolist()
        amount_col = numeric_cols[0] if numeric_cols else None
        issues.append(ValidationIssue("warning", "amount", "Amount column inferred from numeric columns."))

    if amount_col:
        work["amount"] = pd.to_numeric(work[amount_col], errors="coerce").abs()
    else:
        work["amount"] = np.nan
        issues.append(ValidationIssue("error", "amount", "No usable amount column found."))

    if date_col and date_col in work:
        work["expense_date"] = pd.to_datetime(work[date_col], errors="coerce")
    else:
        work["expense_date"] = pd.NaT
        issues.append(ValidationIssue("warning", "date", "No usable date column found; forecasting will be limited."))

    work["description"] = work[desc_col].map(normalize_text) if desc_col and desc_col in work else ""
    work["payer"] = work[payer_col].map(normalize_text) if payer_col and payer_col in work else "unknown"
    existing_categories = work[category_col].map(normalize_text) if category_col and category_col in work else pd.Series([""] * len(work))

    inferred = [infer_category(d, c) for d, c in zip(work["description"], existing_categories)]
    work["category"] = [x[0] for x in inferred]
    work["category_confidence"] = [round(float(x[1]), 3) for x in inferred]
    work["category_reason"] = [x[2] for x in inferred]

    before = len(work)
    work = work.dropna(subset=["amount"])
    audit.append(f"Dropped {before - len(work):,} rows without valid amount.")

    duplicate_cols = [c for c in ["expense_date", "amount", "description", "payer"] if c in work]
    work["semantic_duplicate_key"] = (
        work["expense_date"].dt.strftime("%Y-%m-%d").fillna("unknown") + "|" +
        work["amount"].round(2).astype(str) + "|" +
        work["description"].str[:40] + "|" +
        work["payer"]
    )
    duplicate_count = int(work.duplicated(subset=duplicate_cols).sum()) if duplicate_cols else 0
    semantic_duplicate_count = int(work.duplicated(subset=["semantic_duplicate_key"]).sum())

    confidence = 1.0
    confidence -= 0.20 if any(i.severity == "error" for i in issues) else 0
    confidence -= min(0.25, float(work["amount"].isna().mean()))
    confidence -= 0.15 if work["expense_date"].isna().mean() > 0.5 else 0
    confidence -= 0.10 if float(work["category_confidence"].mean()) < 0.55 else 0
    confidence = round(max(0.0, confidence), 3)

    return {
        "data": work,
        "schema": schema,
        "quality": {
            "input_rows": int(original_rows),
            "usable_rows": int(len(work)),
            "duplicate_rows": duplicate_count,
            "semantic_duplicate_rows": semantic_duplicate_count,
            "mean_category_confidence": round(float(work["category_confidence"].mean()), 3) if len(work) else 0,
            "pipeline_confidence": confidence,
            "issues": [asdict(i) for i in issues],
            "audit": audit,
        },
    }
