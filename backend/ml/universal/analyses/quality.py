"""
quality.py — Data quality assessment: completeness, duplicates, constants,
mixed types, suspicious values. Produces a 0-100 quality score plus findings
with concrete fix suggestions.
"""

import numpy as np
import pandas as pd

from . import make_finding


def analyze_quality(df: pd.DataFrame, schema: dict) -> dict:
    findings = []
    n_rows, n_cols = df.shape
    if n_rows == 0 or n_cols == 0:
        return {"available": False, "reason": "empty dataset", "score": 0, "findings": []}

    deductions = 0.0

    # ---- Completeness ----
    null_pcts = (df.isna().sum() / n_rows * 100).round(2)
    overall_null = float(df.isna().sum().sum() / (n_rows * n_cols) * 100)
    bad_cols = null_pcts[null_pcts > 20].sort_values(ascending=False)
    if not bad_cols.empty:
        worst = bad_cols.index[0]
        deductions += min(25, overall_null)
        findings.append(make_finding(
            "quality.missing",
            "quality",
            f"{len(bad_cols)} column(s) have significant missing data",
            f"Column '{worst}' is missing {bad_cols.iloc[0]:.0f}% of its values"
            + (f", and {len(bad_cols) - 1} other column(s) are missing over 20%." if len(bad_cols) > 1 else ".")
            + " Results involving these columns are less reliable. Consider filling gaps at the source.",
            severity="warning" if bad_cols.iloc[0] < 50 else "critical",
            impact=min(9, 3 + overall_null / 10),
            metric={"columns": {str(k): float(v) for k, v in bad_cols.head(6).items()},
                    "overall_missing_pct": round(overall_null, 2)},
        ))

    # ---- Duplicates ----
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        dup_pct = dup_count / n_rows * 100
        deductions += min(15, dup_pct)
        findings.append(make_finding(
            "quality.duplicates",
            "quality",
            f"{dup_count:,} duplicate rows found ({dup_pct:.1f}%)",
            f"{dup_count:,} rows ({dup_pct:.1f}% of the data) are exact duplicates. "
            "Duplicates inflate totals and averages. They were kept in this analysis; "
            "remove them at the source if they are data-entry errors.",
            severity="warning" if dup_pct < 5 else "critical",
            impact=min(8, 2 + dup_pct / 5),
            metric={"duplicate_rows": dup_count, "duplicate_pct": round(dup_pct, 2)},
        ))

    # ---- Constant columns ----
    constant_cols = [c for c in df.columns if df[c].dropna().nunique() <= 1]
    if constant_cols:
        deductions += 3
        findings.append(make_finding(
            "quality.constants",
            "quality",
            f"{len(constant_cols)} column(s) contain a single value",
            f"Column(s) {', '.join(repr(c) for c in constant_cols[:4])} have only one value across all rows, "
            "so they add no analytical value and were excluded from statistics.",
            severity="notice",
            impact=2,
            metric={"columns": constant_cols[:10]},
        ))

    # ---- Mixed types in object columns ----
    mixed = []
    for c in df.select_dtypes(include="object").columns:
        sample = df[c].dropna().head(500)
        if sample.empty:
            continue
        numeric_ratio = pd.to_numeric(sample, errors="coerce").notna().mean()
        if 0.2 < numeric_ratio < 0.8:
            mixed.append((c, round(float(numeric_ratio * 100), 1)))
    if mixed:
        deductions += 5
        names = ", ".join(repr(m[0]) for m in mixed[:3])
        findings.append(make_finding(
            "quality.mixed_types",
            "quality",
            f"Mixed text and numbers in {len(mixed)} column(s)",
            f"Column(s) {names} contain a mix of numbers and text (e.g. 'N/A' typed into a number column). "
            "This usually indicates inconsistent data entry and can hide values from calculations.",
            severity="warning",
            impact=4,
            metric={"columns": dict(mixed[:6])},
        ))

    # ---- Suspicious values ----
    suspicious = []
    for col_meta in schema.get("columns", []):
        name = col_meta["name"]
        stype = col_meta.get("semantic_type")
        if stype == "datetime" and name in df.columns:
            from ..schema import get_parsed_dates
            dates = get_parsed_dates(df, name).dropna()
            if not dates.empty:
                future = int((dates > pd.Timestamp.now() + pd.Timedelta(days=1)).sum())
                if future > 0 and future < len(dates) * 0.5:
                    suspicious.append(f"'{name}' has {future} date(s) in the future")
        if stype in ("numeric_continuous", "currency") and name in df.columns:
            lname = name.lower()
            vals = pd.to_numeric(df[name], errors="coerce").dropna()
            if vals.empty:
                continue
            if any(h in lname for h in ("age",)) and ((vals < 0) | (vals > 120)).any():
                bad = int(((vals < 0) | (vals > 120)).sum())
                suspicious.append(f"'{name}' has {bad} impossible value(s) (negative or >120)")
            elif any(h in lname for h in ("quantity", "qty", "count", "units")) and (vals < 0).any():
                bad = int((vals < 0).sum())
                suspicious.append(f"'{name}' has {bad} negative value(s)")
    if suspicious:
        deductions += 5
        findings.append(make_finding(
            "quality.suspicious",
            "quality",
            "Suspicious values detected",
            "Some values look implausible: " + "; ".join(suspicious[:4]) + ". "
            "These may be data-entry errors worth verifying.",
            severity="warning",
            impact=5,
            metric={"issues": suspicious[:8]},
        ))

    # ---- Score ----
    score = max(0.0, min(100.0, 100.0 - deductions))
    grade = "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 55 else "Poor"

    if score >= 90 and not findings:
        findings.append(make_finding(
            "quality.clean",
            "quality",
            "Data is clean and analysis-ready",
            f"The dataset scored {score:.0f}/100 on data quality: minimal missing values, "
            "no duplicate rows, and consistent formatting throughout.",
            severity="info",
            impact=3,
            metric={"score": round(score, 1)},
        ))

    return {
        "available": True,
        "score": round(score, 1),
        "grade": grade,
        "overall_missing_pct": round(overall_null, 2),
        "duplicate_rows": dup_count,
        "column_null_pcts": {str(k): float(v) for k, v in null_pcts.items() if v > 0},
        "findings": findings,
    }
