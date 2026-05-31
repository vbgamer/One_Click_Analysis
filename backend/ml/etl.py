"""
etl.py — Enhanced ETL pipeline for Expense Intelligence System.

Provides data loading, cleaning, schema inference, leakage detection,
entity normalisation (fuzzy matching), and data-quality scoring.
"""

import io
import os
import re

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional heavy imports (graceful fallback if not installed)
# ---------------------------------------------------------------------------
try:
    from thefuzz import fuzz, process as fuzz_process
    _FUZZ_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process as fuzz_process  # legacy alias
        _FUZZ_AVAILABLE = True
    except ImportError:
        _FUZZ_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants — expense-domain column name hints
# ---------------------------------------------------------------------------
_DATE_HINTS = [
    "date", "time", "datetime", "timestamp", "txn_date", "transaction_date",
    "purchase_date", "expense_date", "created_at", "updated_at", "paid_on",
    "billing_date", "invoice_date",
]
_AMOUNT_HINTS = [
    "amount", "total", "cost", "price", "value", "spend", "spending",
    "debit", "credit", "payment", "paid", "fee", "charge", "sum", "amt",
    "expense", "rupees", "inr", "usd", "eur",
]
_PAYER_HINTS = [
    "payer", "paid_by", "person", "name", "member", "user", "who", "payee",
    "paid_by", "paid by", "buyer", "owner", "employee", "individual",
]
_CATEGORY_HINTS = [
    "category", "cat", "type", "group", "label", "tag", "department",
    "expense_type", "bucket", "head", "classification",
]
_MERCHANT_HINTS = [
    "merchant", "vendor", "shop", "store", "outlet", "company", "brand",
    "retailer", "payee", "biller", "service", "description", "narration",
    "particulars", "remarks", "note", "details",
]


# ---------------------------------------------------------------------------
# Original functions (preserved for backward-compatibility)
# ---------------------------------------------------------------------------

def load_data(filepath: str) -> pd.DataFrame:
    """Load dataset from CSV, Excel, or JSON.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the data file.

    Returns
    -------
    pd.DataFrame
        Raw dataframe loaded from the file.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(filepath)
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(filepath)
    elif ext == ".json":
        df = pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Basic ETL: fix types, handle missing values, clean headers.

    Parameters
    ----------
    df : pd.DataFrame
        Raw input dataframe.

    Returns
    -------
    pd.DataFrame
        Cleaned dataframe with standardised headers.
    """
    # Standardise headers
    df = df.copy()
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in df.columns
    ]

    # Drop completely empty columns / rows
    df.dropna(how="all", axis=1, inplace=True)
    df.dropna(how="all", axis=0, inplace=True)

    # Simple missing-value imputation
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].mean())
        else:
            mode_vals = df[col].mode()
            fill_val = mode_vals[0] if not mode_vals.empty else "Unknown"
            df[col] = df[col].fillna(fill_val)

    # Remove duplicates
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# ---------------------------------------------------------------------------
# New helper — score how well a column name matches a set of hints
# ---------------------------------------------------------------------------

def _hint_score(col_name: str, hints: list) -> int:
    """Return a fuzzy-match score (0-100) between *col_name* and hint list."""
    col_lower = col_name.lower().replace("_", " ").replace("-", " ")

    best = 0
    for hint in hints:
        # Exact substring match → very high score
        if hint in col_lower or col_lower in hint:
            best = max(best, 90)
        elif _FUZZ_AVAILABLE:
            score = fuzz.partial_ratio(col_lower, hint)
            best = max(best, score)
        else:
            # Simple character-overlap ratio
            common = len(set(col_lower) & set(hint))
            total = max(len(col_lower), len(hint), 1)
            best = max(best, int(common / total * 100))
    return best


# ---------------------------------------------------------------------------
# FILE 1 — New functions
# ---------------------------------------------------------------------------

def infer_schema(df: pd.DataFrame) -> dict:
    """Detect expense-specific columns using fuzzy name matching.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe (column names already cleaned/lowercased).

    Returns
    -------
    dict
        Mapping like::

            {
                "date_col": "date",
                "amount_col": "amount",
                "payer_col": "paid_by",
                "category_col": "category",
                "merchant_col": "merchant",
            }

        Any undetected mapping has a ``None`` value.
    """
    schema = {
        "date_col": None,
        "amount_col": None,
        "payer_col": None,
        "category_col": None,
        "merchant_col": None,
    }

    hint_map = {
        "date_col": _DATE_HINTS,
        "amount_col": _AMOUNT_HINTS,
        "payer_col": _PAYER_HINTS,
        "category_col": _CATEGORY_HINTS,
        "merchant_col": _MERCHANT_HINTS,
    }

    # Score every column against every role
    assigned: set = set()
    for role, hints in hint_map.items():
        best_score = 0
        best_col = None
        for col in df.columns:
            if col in assigned:
                continue
            score = _hint_score(col, hints)

            # Boost score if dtype matches the role expectation
            if role == "date_col":
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    score = min(score + 20, 100)
                elif df[col].dtype == object:
                    # Try parsing a sample
                    sample = df[col].dropna().head(20)
                    try:
                        parsed = pd.to_datetime(sample, errors="coerce")
                        if parsed.notna().mean() > 0.7:
                            score = min(score + 15, 100)
                    except Exception:
                        pass
            elif role == "amount_col":
                if pd.api.types.is_numeric_dtype(df[col]):
                    score = min(score + 15, 100)

            if score > best_score:
                best_score = score
                best_col = col

        if best_col and best_score >= 40:
            schema[role] = best_col
            assigned.add(best_col)

    return schema


def detect_leakage(df: pd.DataFrame, target_col: str) -> list:
    """Check if any column is mathematically derived from *target_col*.

    Detection heuristics:
    * Pearson correlation > 0.99 with the target.
    * Column name contains suspicious keywords (``has_to_pay``, ``derived``,
      ``formula``, ``calc``, ``predicted``).

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    target_col : str
        Name of the target column (e.g. the amount to predict).

    Returns
    -------
    list of dict
        Each entry: ``{"column": str, "reason": str}``.
        Returns an empty list if *target_col* not found or no leakage detected.
    """
    if target_col not in df.columns:
        return []

    suspicious_patterns = [
        r"has_to_pay",
        r"derived",
        r"formula",
        r"calc",
        r"predicted",
        r"target",
        r"label",
        r"output",
    ]

    suspicious: list = []
    target_series = pd.to_numeric(df[target_col], errors="coerce").dropna()

    for col in df.columns:
        if col == target_col:
            continue
        reasons = []

        # --- Name-based check ---
        col_lower = col.lower()
        for pat in suspicious_patterns:
            if re.search(pat, col_lower):
                reasons.append(f"Column name matches suspicious pattern '{pat}'")
                break

        # --- Correlation check ---
        col_numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(col_numeric) > 10 and len(target_series) > 10:
            try:
                aligned = pd.concat(
                    [col_numeric.rename("col"), target_series.rename("target")],
                    axis=1,
                ).dropna()
                if len(aligned) > 10:
                    corr = aligned["col"].corr(aligned["target"])
                    if abs(corr) > 0.99:
                        reasons.append(
                            f"Correlation with target = {corr:.4f} (>0.99, likely data leakage)"
                        )
            except Exception:
                pass

        if reasons:
            suspicious.append({"column": col, "reason": "; ".join(reasons)})

    return suspicious


def normalize_entities(
    df: pd.DataFrame, schema: dict, threshold: int = 80
) -> tuple:
    """Unify typos in payer / merchant / category columns using fuzzy matching.

    Uses *thefuzz* (or *fuzzywuzzy*) for approximate string matching.
    Falls back to exact lowercasing if neither library is available.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    schema : dict
        Output of :func:`infer_schema`.
    threshold : int, optional
        Minimum similarity score (0-100) to merge two strings.  Default 80.

    Returns
    -------
    tuple[pd.DataFrame, dict]
        * Normalised dataframe.
        * Dict of changes: ``{col_name: {old_value: new_value, ...}}``.
    """
    df = df.copy()
    changes: dict = {}

    entity_cols = [
        schema.get("payer_col"),
        schema.get("merchant_col"),
        schema.get("category_col"),
    ]
    entity_cols = [c for c in entity_cols if c and c in df.columns]

    for col in entity_cols:
        col_changes: dict = {}
        values = df[col].dropna().astype(str).tolist()
        unique_vals = list(dict.fromkeys(v.strip() for v in values if v.strip()))

        if len(unique_vals) < 2:
            continue

        # Build canonical list (sorted by frequency so most-common is canonical)
        freq = df[col].astype(str).str.strip().value_counts()
        canonicals: list = []

        # Map each value to the best matching canonical
        mapping: dict = {}
        for val in unique_vals:
            if val in mapping:
                continue

            if _FUZZ_AVAILABLE:
                # Find best match among already-established canonicals
                if canonicals:
                    best_match, best_score, *_ = fuzz_process.extractOne(
                        val, canonicals, scorer=fuzz.token_sort_ratio
                    ) or (None, 0)
                    if best_match and best_score >= threshold:
                        # Pick the more common version as canonical
                        canonical = (
                            best_match
                            if freq.get(best_match, 0) >= freq.get(val, 0)
                            else val
                        )
                        mapping[val] = canonical
                        if best_match != canonical:
                            mapping[best_match] = canonical
                        # Update canonical list entry
                        idx = canonicals.index(best_match)
                        canonicals[idx] = canonical
                    else:
                        canonicals.append(val)
                        mapping[val] = val
                else:
                    canonicals.append(val)
                    mapping[val] = val
            else:
                # Fallback: simple title-casing normalisation
                canonical = val.strip().title()
                mapping[val] = canonical

        # Apply mapping and record changes
        for old_val, new_val in mapping.items():
            if old_val != new_val:
                col_changes[old_val] = new_val

        if col_changes:
            df[col] = df[col].astype(str).str.strip().map(
                lambda v, m=mapping: m.get(v, v)
            )
            changes[col] = col_changes

    return df, changes


def compute_data_quality_score(df: pd.DataFrame) -> dict:
    """Compute a 0-100 data quality score.

    Sub-scores (each 0-100, weighted equally):

    * **completeness** — 100 minus the missing-value percentage.
    * **uniqueness** — 100 minus the duplicate-row percentage.
    * **consistency** — penalises columns with mixed types or high outlier rates.
    * **outlier_health** — 100 minus the percentage of outlier cells.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.

    Returns
    -------
    dict
        ``{"score": float, "completeness": float, "uniqueness": float,
           "consistency": float, "outlier_health": float,
           "missing_pct": float, "duplicate_pct": float}``
    """
    if df.empty:
        return {
            "score": 0,
            "completeness": 0,
            "uniqueness": 100,
            "consistency": 0,
            "outlier_health": 100,
            "missing_pct": 100.0,
            "duplicate_pct": 0.0,
        }

    n_cells = df.shape[0] * df.shape[1]

    # --- Completeness ---
    n_missing = df.isnull().sum().sum()
    missing_pct = round(n_missing / n_cells * 100, 2)
    completeness = max(0.0, 100.0 - missing_pct)

    # --- Uniqueness ---
    n_dup = df.duplicated().sum()
    dup_pct = round(n_dup / max(len(df), 1) * 100, 2)
    uniqueness = max(0.0, 100.0 - dup_pct)

    # --- Outlier health ---
    num_cols = df.select_dtypes(include="number").columns.tolist()
    outlier_cells = 0
    total_numeric_cells = 0
    for col in num_cols:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        n_out = ((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum()
        outlier_cells += n_out
        total_numeric_cells += len(series)

    if total_numeric_cells > 0:
        outlier_pct = outlier_cells / total_numeric_cells * 100
        outlier_health = max(0.0, 100.0 - outlier_pct * 2)  # penalise x2
    else:
        outlier_pct = 0.0
        outlier_health = 100.0

    # --- Consistency ---
    consistency_penalties = 0
    for col in df.columns:
        col_data = df[col].dropna()
        if col_data.empty:
            continue
        if df[col].dtype == object:
            # Check for mixed numeric/non-numeric
            n_numeric = pd.to_numeric(col_data, errors="coerce").notna().sum()
            ratio = n_numeric / len(col_data)
            if 0.05 < ratio < 0.95:  # Mixed column
                consistency_penalties += 10
    consistency = max(0.0, 100.0 - consistency_penalties)

    # --- Overall ---
    score = round(
        0.35 * completeness
        + 0.25 * uniqueness
        + 0.20 * outlier_health
        + 0.20 * consistency,
        1,
    )

    return {
        "score": score,
        "completeness": round(completeness, 1),
        "uniqueness": round(uniqueness, 1),
        "consistency": round(consistency, 1),
        "outlier_health": round(outlier_health, 1),
        "missing_pct": missing_pct,
        "duplicate_pct": dup_pct,
        "outlier_pct": round(outlier_pct, 2),
    }
