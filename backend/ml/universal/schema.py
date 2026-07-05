"""
schema.py — Semantic schema inference for the Universal Analysis Engine.

Goes beyond pandas dtypes to detect per-column *semantic* types:
datetime, numeric_continuous, numeric_discrete, currency, percentage,
category, binary, id, free_text, email, phone, url, geo.

Also identifies the dataset's key roles:
- primary date column
- primary measure(s) (the numbers worth analyzing)
- dimensions (categoricals worth grouping by)
- identifiers (excluded from statistics)

Public API
----------
infer_semantic_schema(df) -> dict
"""

import re

import numpy as np
import pandas as pd

_EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_URL_RE = re.compile(r"^https?://|^www\.")
_PHONE_RE = re.compile(r"^[\d\s()+\-.]{7,20}$")

_DATE_NAME_HINTS = [
    "date", "time", "timestamp", "created", "updated", "modified", "day",
    "month", "year", "period", "when", "dob", "birth", "joined", "hired",
    "start", "end", "due", "expiry", "invoice_date", "order_date",
]
_MEASURE_NAME_HINTS = [
    "amount", "total", "revenue", "sales", "price", "cost", "profit", "value",
    "spend", "salary", "wage", "income", "expense", "fee", "charge", "budget",
    "quantity", "qty", "count", "units", "score", "rating", "hours", "duration",
    "clicks", "impressions", "conversions", "views", "visits", "balance",
    "margin", "discount", "tax", "gmv", "arr", "mrr",
]
_ID_NAME_HINTS = [
    "id", "uuid", "guid", "key", "code", "number", "no", "num", "ref",
    "reference", "sku", "serial", "invoice", "order_id", "txn",
]
_GEO_NAME_HINTS = [
    "country", "state", "city", "region", "zip", "zipcode", "postal",
    "pincode", "latitude", "longitude", "lat", "lon", "lng", "address",
    "location", "province", "county",
]
_CURRENCY_NAME_HINTS = [
    "amount", "price", "cost", "revenue", "sales", "salary", "spend",
    "expense", "fee", "charge", "total", "profit", "budget", "balance",
    "income", "payment", "paid",
]
_PERCENT_NAME_HINTS = ["percent", "pct", "rate", "ratio", "share", "%", "conversion"]


def _name_matches(col: str, hints: list) -> bool:
    tokens = re.split(r"[_\s\-./]+", str(col).lower())
    joined = " ".join(tokens)
    for h in hints:
        if h in tokens or (len(h) > 3 and h in joined):
            return True
    return False


def _try_datetime(series: pd.Series) -> tuple:
    """Attempt datetime parse. Returns (success_ratio, parsed_series|None)."""
    s = series.dropna()
    if s.empty:
        return 0.0, None
    if pd.api.types.is_datetime64_any_dtype(series):
        return 1.0, series

    sample = s.astype(str).head(500)
    # Fast rejection: pure small ints / floats are not dates (unless year-like)
    numeric_like = pd.to_numeric(sample, errors="coerce")
    if numeric_like.notna().mean() > 0.9:
        vals = numeric_like.dropna()
        if not ((vals >= 1990) & (vals <= 2035)).mean() > 0.9:
            return 0.0, None

    for dayfirst in (False, True):
        try:
            parsed = pd.to_datetime(sample, errors="coerce", dayfirst=dayfirst, format="mixed")
        except (ValueError, TypeError):
            try:
                parsed = pd.to_datetime(sample, errors="coerce", dayfirst=dayfirst)
            except Exception:
                continue
        ratio = parsed.notna().mean()
        if ratio > 0.85:
            # Sanity: dates should span a plausible range
            valid = parsed.dropna()
            if valid.empty:
                continue
            years = valid.dt.year
            if years.between(1900, 2100).mean() > 0.95:
                try:
                    full = pd.to_datetime(series.astype(str), errors="coerce",
                                          dayfirst=dayfirst, format="mixed")
                except (ValueError, TypeError):
                    full = pd.to_datetime(series.astype(str), errors="coerce", dayfirst=dayfirst)
                return float(ratio), full
    return 0.0, None


def _classify_column(df: pd.DataFrame, col: str) -> dict:
    """Classify one column. Returns {semantic_type, extras...}."""
    series = df[col]
    n = len(series)
    non_null = series.dropna()
    n_valid = len(non_null)
    nunique = non_null.nunique()
    null_pct = float((n - n_valid) / n * 100) if n else 0.0

    info = {
        "name": col,
        "dtype": str(series.dtype),
        "null_pct": round(null_pct, 2),
        "nunique": int(nunique),
        "semantic_type": "unknown",
    }

    if n_valid == 0:
        info["semantic_type"] = "empty"
        return info

    # ---- Datetime ----
    dt_ratio, parsed = _try_datetime(series)
    if dt_ratio > 0.85 and (
        pd.api.types.is_datetime64_any_dtype(series)
        or _name_matches(col, _DATE_NAME_HINTS)
        or dt_ratio > 0.95
    ):
        info["semantic_type"] = "datetime"
        valid = parsed.dropna() if parsed is not None else pd.Series(dtype="datetime64[ns]")
        if not valid.empty:
            info["min"] = str(valid.min())
            info["max"] = str(valid.max())
            info["span_days"] = int((valid.max() - valid.min()).days)
        return info

    # ---- Numeric ----
    if pd.api.types.is_numeric_dtype(series):
        vals = pd.to_numeric(non_null, errors="coerce").dropna()

        # Binary flag
        uniq = set(vals.unique().tolist())
        if uniq <= {0, 1} or uniq <= {0.0, 1.0}:
            info["semantic_type"] = "binary"
            info["true_pct"] = round(float(vals.mean() * 100), 1)
            return info

        # ID-like: integer, near-unique, monotonic-ish or name hint
        is_int = bool((vals % 1 == 0).all()) if len(vals) else False
        unique_ratio = nunique / n_valid
        if is_int and unique_ratio > 0.95 and (_name_matches(col, _ID_NAME_HINTS) or unique_ratio > 0.99):
            info["semantic_type"] = "id"
            return info

        info["min"] = float(vals.min())
        info["max"] = float(vals.max())
        info["mean"] = float(vals.mean())
        info["median"] = float(vals.median())
        info["std"] = float(vals.std()) if len(vals) > 1 else 0.0

        if _name_matches(col, _PERCENT_NAME_HINTS) and vals.between(-1000, 1000).all():
            info["semantic_type"] = "percentage"
        elif _name_matches(col, _CURRENCY_NAME_HINTS):
            info["semantic_type"] = "currency"
        elif is_int and nunique <= max(20, n_valid * 0.05):
            info["semantic_type"] = "numeric_discrete"
        else:
            info["semantic_type"] = "numeric_continuous"
        return info

    # ---- Boolean dtype ----
    if pd.api.types.is_bool_dtype(series):
        info["semantic_type"] = "binary"
        info["true_pct"] = round(float(non_null.mean() * 100), 1)
        return info

    # ---- String-based types ----
    sample = non_null.astype(str).head(300)

    email_ratio = sum(bool(_EMAIL_RE.match(v.strip())) for v in sample) / len(sample)
    if email_ratio > 0.8:
        info["semantic_type"] = "email"
        return info

    url_ratio = sum(bool(_URL_RE.match(v.strip())) for v in sample) / len(sample)
    if url_ratio > 0.8:
        info["semantic_type"] = "url"
        return info

    if _name_matches(col, ["phone", "mobile", "tel", "contact"]):
        phone_ratio = sum(bool(_PHONE_RE.match(v.strip())) for v in sample) / len(sample)
        if phone_ratio > 0.7:
            info["semantic_type"] = "phone"
            return info

    # Binary text (yes/no, true/false, m/f)
    lowered = set(v.strip().lower() for v in non_null.astype(str).unique()[:10])
    binary_sets = [
        {"yes", "no"}, {"true", "false"}, {"y", "n"}, {"m", "f"},
        {"male", "female"}, {"pass", "fail"}, {"active", "inactive"},
    ]
    if nunique == 2 and any(lowered <= bs for bs in binary_sets):
        info["semantic_type"] = "binary"
        return info

    unique_ratio = nunique / n_valid
    avg_len = float(sample.str.len().mean())
    avg_words = float(sample.str.split().str.len().mean())

    # ID-like strings
    if unique_ratio > 0.95 and avg_words <= 2 and (_name_matches(col, _ID_NAME_HINTS) or avg_len < 40):
        info["semantic_type"] = "id"
        return info

    # Free text: long, wordy, mostly unique
    if avg_words > 6 or (avg_len > 60 and unique_ratio > 0.5):
        info["semantic_type"] = "free_text"
        return info

    # Geo
    if _name_matches(col, _GEO_NAME_HINTS) and nunique <= 5000:
        info["semantic_type"] = "geo"
        top = non_null.astype(str).value_counts().head(5)
        info["top_values"] = {str(k): int(v) for k, v in top.items()}
        return info

    # Default: category
    info["semantic_type"] = "category"
    top = non_null.astype(str).value_counts().head(8)
    info["top_values"] = {str(k): int(v) for k, v in top.items()}
    return info


def infer_semantic_schema(df: pd.DataFrame) -> dict:
    """Infer the full semantic schema plus dataset roles."""
    columns = [_classify_column(df, c) for c in df.columns]
    by_type: dict = {}
    for c in columns:
        by_type.setdefault(c["semantic_type"], []).append(c["name"])

    # ---- Primary date column ----
    date_cols = by_type.get("datetime", [])
    primary_date = None
    if date_cols:
        # Prefer name-hinted, widest span
        def date_rank(name):
            meta = next(c for c in columns if c["name"] == name)
            hinted = 1 if _name_matches(name, ["date", "time", "created", "order", "invoice", "transaction"]) else 0
            return (hinted, meta.get("span_days", 0))
        primary_date = max(date_cols, key=date_rank)

    # ---- Measures (ranked) ----
    measure_types = ("currency", "numeric_continuous", "percentage", "numeric_discrete")
    measure_candidates = []
    for c in columns:
        if c["semantic_type"] not in measure_types:
            continue
        score = 0.0
        if c["semantic_type"] == "currency":
            score += 3
        if _name_matches(c["name"], _MEASURE_NAME_HINTS):
            score += 2
        if c["semantic_type"] == "numeric_continuous":
            score += 1
        std = c.get("std") or 0
        if std > 0:
            score += 0.5
        score -= c.get("null_pct", 0) / 100.0
        measure_candidates.append((score, c["name"]))
    measure_candidates.sort(reverse=True)
    measures = [name for _, name in measure_candidates]
    primary_measure = measures[0] if measures else None

    # ---- Dimensions ----
    n_rows = max(len(df), 1)
    dimensions = []
    for c in columns:
        if c["semantic_type"] in ("category", "geo", "binary"):
            if 2 <= c["nunique"] <= max(50, n_rows * 0.5):
                dimensions.append(c["name"])

    identifiers = by_type.get("id", []) + by_type.get("email", []) + \
        by_type.get("phone", []) + by_type.get("url", [])
    text_cols = by_type.get("free_text", [])

    return {
        "columns": columns,
        "by_type": by_type,
        "primary_date": primary_date,
        "date_columns": date_cols,
        "primary_measure": primary_measure,
        "measures": measures[:6],
        "dimensions": dimensions[:10],
        "identifiers": identifiers,
        "text_columns": text_cols,
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
    }


def get_parsed_dates(df: pd.DataFrame, date_col: str) -> pd.Series:
    """Return the date column parsed as datetimes (helper for analyses)."""
    if pd.api.types.is_datetime64_any_dtype(df[date_col]):
        return df[date_col]
    _, parsed = _try_datetime(df[date_col])
    if parsed is not None:
        return parsed
    return pd.to_datetime(df[date_col], errors="coerce")
