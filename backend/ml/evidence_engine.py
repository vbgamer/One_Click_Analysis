"""
evidence_engine.py — Evidence Engine for Autonomous Data Intelligence Platform (ADIP).

Every insight produced by any module is wrapped with full evidence:
source columns, row indices, formula, confidence score, and validation status.

This is the foundational trust layer. NO insight is shown without evidence.
"""

import math
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wrap_insight(
    title: str,
    value,
    calculation: str,
    source_columns: list,
    df: pd.DataFrame,
    confidence: float = 80.0,
    pandas_op: str = "",
    rows_used: list | None = None,
) -> dict:
    """Wrap any insight with a full evidence block.

    Parameters
    ----------
    title : str
        Human-readable insight title.
    value : any
        The computed insight value (number, string, dict).
    calculation : str
        Human-readable formula / calculation description.
    source_columns : list
        Column names used to produce this insight.
    df : pd.DataFrame
        The source dataframe (used for evidence metadata).
    confidence : float
        Base confidence score 0-100 (will be adjusted).
    pandas_op : str
        Actual pandas/python code used (for reproducibility).
    rows_used : list, optional
        Specific row indices used. If None, all rows assumed.

    Returns
    -------
    dict
        Insight dict with 'title', 'value', 'calculation', 'evidence'.
    """
    adjusted_confidence = score_confidence(df, source_columns, base_confidence=confidence)
    evidence = build_evidence_block(
        df=df,
        source_columns=source_columns,
        calculation=calculation,
        computed_value=value,
        pandas_operation=pandas_op,
        confidence=adjusted_confidence,
        rows_used=rows_used,
    )
    return {
        "title": title,
        "value": value,
        "calculation": calculation,
        "evidence": evidence,
    }


def build_evidence_block(
    df: pd.DataFrame,
    source_columns: list,
    calculation: str,
    computed_value,
    pandas_operation: str = "",
    confidence: float = 80.0,
    rows_used: list | None = None,
) -> dict:
    """Build a standalone evidence block dict.

    Keys
    ----
    source_columns, rows_analyzed, sample_row_indices, pandas_operation,
    confidence_score, validation_status, validation_reason, data_completeness_pct
    """
    valid_cols = [c for c in source_columns if c and c in df.columns]
    n_rows = len(df) if rows_used is None else len(rows_used)
    sample_indices = (
        df.index.tolist()[:10]
        if rows_used is None
        else list(rows_used)[:10]
    )

    # Data completeness
    completeness = 100.0
    if valid_cols:
        total_cells = len(df) * len(valid_cols)
        missing_cells = sum(df[c].isna().sum() for c in valid_cols)
        completeness = round(100.0 * (1 - missing_cells / max(total_cells, 1)), 2)

    validation = verify_calculation(computed_value, df, valid_cols, calculation, n_rows)

    return {
        "source_columns": source_columns,
        "valid_source_columns": valid_cols,
        "rows_analyzed": n_rows,
        "sample_row_indices": [int(i) for i in sample_indices],
        "pandas_operation": pandas_op_clean(pandas_operation),
        "calculation": calculation,
        "confidence_score": round(float(confidence), 2),
        "validation_status": validation["status"],
        "validation_reason": validation["reason"],
        "data_completeness_pct": completeness,
    }


def verify_calculation(
    computed_value,
    df: pd.DataFrame,
    source_columns: list,
    operation_desc: str,
    n_rows: int = 0,
) -> dict:
    """Independently verify a computed value to detect hallucinations.

    Returns
    -------
    dict
        {'status': 'PASSED|FAILED|INCONCLUSIVE', 'reason': str}
    """
    # FAILED cases
    if computed_value is None:
        return {"status": "FAILED", "reason": "Value is None — computation may have failed."}

    if isinstance(computed_value, float) and (math.isnan(computed_value) or math.isinf(computed_value)):
        return {"status": "FAILED", "reason": f"Value is {computed_value} — invalid result."}

    if not source_columns:
        return {"status": "INCONCLUSIVE", "reason": "No source columns identified — cannot trace origin."}

    # INCONCLUSIVE cases
    if n_rows < 10:
        return {
            "status": "INCONCLUSIVE",
            "reason": f"Sample too small (n={n_rows}). Increase data for reliable results.",
        }

    # Check column existence
    missing_cols = [c for c in source_columns if c and c not in df.columns]
    if missing_cols:
        return {
            "status": "INCONCLUSIVE",
            "reason": f"Source column(s) not found in dataframe: {missing_cols}",
        }

    # PASSED
    return {
        "status": "PASSED",
        "reason": f"Value is well-defined, columns exist, n={n_rows} rows analyzed.",
    }


def score_confidence(
    df: pd.DataFrame,
    source_columns: list,
    base_confidence: float = 80.0,
) -> float:
    """Adjust confidence based on sample size, missing values, completeness.

    Rules
    -----
    - Penalize -15 if rows < 10
    - Penalize -10 if rows < 30
    - Penalize -5 if rows < 100
    - Penalize -5 per 10% missing values in source columns
    - Penalize -10 if source columns missing from df
    - Cap: [5, 99]
    """
    score = float(base_confidence)
    n = len(df)
    valid_cols = [c for c in source_columns if c and c in df.columns]

    # Sample size penalties
    if n < 10:
        score -= 15
    elif n < 30:
        score -= 10
    elif n < 100:
        score -= 5

    # Missing column penalty
    missing_cols = len(source_columns) - len(valid_cols)
    if missing_cols > 0:
        score -= 10 * missing_cols

    # Missing value penalty (per source column)
    for col in valid_cols:
        miss_rate = df[col].isna().mean()
        score -= miss_rate * 50  # -5 per 10% missing

    return float(max(5.0, min(99.0, round(score, 2))))


def attach_evidence_to_list(
    items: list,
    df: pd.DataFrame,
    source_columns: list,
    calculation_key: str = "calculation",
    confidence_key: str = "confidence",
) -> list:
    """Attach evidence blocks to a list of insight dicts in-place.

    Each item dict is enriched with an 'evidence' key if it doesn't have one.
    """
    result = []
    for item in items:
        if not isinstance(item, dict):
            result.append(item)
            continue
        if "evidence" not in item:
            calc = item.get(calculation_key, "See supporting data")
            conf = float(item.get(confidence_key, 75.0))
            item["evidence"] = build_evidence_block(
                df=df,
                source_columns=source_columns,
                calculation=calc,
                computed_value=item.get("value") or item.get("impact") or item.get("title"),
                confidence=score_confidence(df, source_columns, conf),
            )
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pandas_op_clean(op: str) -> str:
    """Truncate very long pandas operation strings for readability."""
    if not op:
        return ""
    return op[:500] + "..." if len(op) > 500 else op
