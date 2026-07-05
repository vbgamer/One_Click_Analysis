"""
ingest.py — Smart, robust file ingestion for the Universal Analysis Engine.

Handles: CSV, TSV, TXT, XLSX/XLS (multi-sheet), JSON (records / nested), Parquet.
Robust to: bad encodings, odd delimiters, title rows above the header,
thousands separators, currency symbols, percentage strings.

Public API
----------
load_file(filepath) -> (pd.DataFrame, dict)   # df + ingestion notes
"""

import json
import os
import re

import numpy as np
import pandas as pd

try:
    import chardet
    _CHARDET = True
except ImportError:
    _CHARDET = False

_CURRENCY_RE = re.compile(r"^\s*[-+]?\s*[\$€£₹¥]\s*[\d,.]+\s*$|^\s*[-+]?[\d,.]+\s*[\$€£₹¥]\s*$")
_NUMERIC_WITH_SEP_RE = re.compile(r"^\s*[-+]?[\d]{1,3}(,\d{3})+(\.\d+)?\s*$")
_PERCENT_RE = re.compile(r"^\s*[-+]?[\d.]+\s*%\s*$")

MAX_ROWS = 500_000  # hard cap to keep analysis fast


# ---------------------------------------------------------------------------
# Encoding & delimiter detection
# ---------------------------------------------------------------------------

def _detect_encoding(filepath: str) -> str:
    if _CHARDET:
        try:
            with open(filepath, "rb") as f:
                raw = f.read(65536)
            guess = chardet.detect(raw)
            enc = (guess.get("encoding") or "utf-8").lower()
            if enc in ("ascii",):
                return "utf-8"
            return enc
        except Exception:
            pass
    return "utf-8"


def _detect_delimiter(sample: str) -> str:
    candidates = [",", "\t", ";", "|"]
    lines = [l for l in sample.splitlines() if l.strip()][:20]
    if not lines:
        return ","
    best, best_score = ",", -1
    for d in candidates:
        counts = [line.count(d) for line in lines]
        if not counts or max(counts) == 0:
            continue
        # Consistency: same count across lines is a strong signal
        consistency = 1.0 / (1.0 + np.std(counts))
        score = np.median(counts) * consistency
        if score > best_score:
            best, best_score = d, score
    return best


def _detect_header_row(filepath: str, encoding: str, delimiter: str) -> int:
    """Detect how many junk/title rows precede the real header."""
    try:
        preview = pd.read_csv(
            filepath, encoding=encoding, sep=delimiter, header=None,
            nrows=15, dtype=str, on_bad_lines="skip", engine="python",
        )
    except Exception:
        return 0

    n_cols = preview.shape[1]
    if n_cols <= 1:
        return 0

    best_row, best_score = 0, -1.0
    for i in range(min(10, len(preview))):
        row = preview.iloc[i]
        non_null = row.notna().sum()
        # Header rows are mostly non-null, short strings, not numeric
        str_like = sum(
            1 for v in row.dropna()
            if not str(v).replace(".", "").replace("-", "").replace(",", "").strip().isdigit()
        )
        score = (non_null / n_cols) * 0.5 + (str_like / max(non_null, 1)) * 0.5
        if score > best_score + 0.05:
            best_row, best_score = i, score
    return best_row


# ---------------------------------------------------------------------------
# Value cleaning
# ---------------------------------------------------------------------------

def _clean_numeric_strings(df: pd.DataFrame, notes: list) -> pd.DataFrame:
    """Convert currency / thousands-separated / percent strings to numbers."""
    for col in df.columns:
        if df[col].dtype != object:
            continue
        sample = df[col].dropna().astype(str).head(200)
        if sample.empty:
            continue

        n = len(sample)
        cur = sum(bool(_CURRENCY_RE.match(v)) for v in sample)
        sep = sum(bool(_NUMERIC_WITH_SEP_RE.match(v)) for v in sample)
        pct = sum(bool(_PERCENT_RE.match(v)) for v in sample)

        if (cur + sep) / n > 0.7:
            cleaned = (
                df[col].astype(str)
                .str.replace(r"[\$€£₹¥,\s]", "", regex=True)
                .replace({"": None, "nan": None, "None": None})
            )
            converted = pd.to_numeric(cleaned, errors="coerce")
            if converted.notna().sum() >= df[col].notna().sum() * 0.7:
                df[col] = converted
                notes.append(f"Cleaned currency/number formatting in column '{col}'.")
        elif pct / n > 0.7:
            cleaned = df[col].astype(str).str.replace(r"[%\s]", "", regex=True)
            converted = pd.to_numeric(cleaned, errors="coerce")
            if converted.notna().sum() >= df[col].notna().sum() * 0.7:
                df[col] = converted
                notes.append(f"Converted percentage strings in column '{col}' to numbers.")
    return df


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    seen: dict = {}
    new_cols = []
    for c in df.columns:
        name = str(c).strip()
        if not name or name.lower().startswith("unnamed"):
            name = f"column_{len(new_cols) + 1}"
        base = name
        k = seen.get(base, 0)
        if k:
            name = f"{base}_{k + 1}"
        seen[base] = k + 1
        new_cols.append(name)
    df.columns = new_cols
    return df


# ---------------------------------------------------------------------------
# Format loaders
# ---------------------------------------------------------------------------

def _load_csv_like(filepath: str, notes: list) -> pd.DataFrame:
    encoding = _detect_encoding(filepath)
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(32768)
    delimiter = _detect_delimiter(sample)
    skip = _detect_header_row(filepath, encoding, delimiter)
    if skip:
        notes.append(f"Skipped {skip} title/blank row(s) above the data header.")
    if delimiter != ",":
        pretty = {"\t": "tab", ";": "semicolon", "|": "pipe"}.get(delimiter, delimiter)
        notes.append(f"Detected {pretty}-separated values.")
    return pd.read_csv(
        filepath, encoding=encoding, sep=delimiter, skiprows=skip,
        on_bad_lines="skip", engine="python", thousands=",",
    )


def _load_excel(filepath: str, notes: list) -> pd.DataFrame:
    xls = pd.ExcelFile(filepath)
    sheets = xls.sheet_names
    if len(sheets) == 1:
        df = pd.read_excel(xls, sheet_name=sheets[0])
        return df

    # Multi-sheet: pick the sheet with the most data cells
    best_sheet, best_df, best_cells = None, None, -1
    for s in sheets:
        try:
            d = pd.read_excel(xls, sheet_name=s)
            cells = int(d.notna().sum().sum())
            if cells > best_cells:
                best_sheet, best_df, best_cells = s, d, cells
        except Exception:
            continue
    others = [s for s in sheets if s != best_sheet]
    notes.append(
        f"Workbook has {len(sheets)} sheets. Analyzed '{best_sheet}' "
        f"({len(best_df)} rows). Other sheets not analyzed: {', '.join(others[:5])}."
    )
    return best_df if best_df is not None else pd.read_excel(xls, sheet_name=sheets[0])


def _load_json(filepath: str, notes: list) -> pd.DataFrame:
    with open(filepath, "r", encoding=_detect_encoding(filepath), errors="replace") as f:
        data = json.load(f)

    if isinstance(data, list):
        df = pd.json_normalize(data)
    elif isinstance(data, dict):
        # Find the largest list-of-dicts inside
        best_key, best_list = None, None
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                if best_list is None or len(v) > len(best_list):
                    best_key, best_list = k, v
        if best_list is not None:
            df = pd.json_normalize(best_list)
            notes.append(f"Used the '{best_key}' array from the JSON file ({len(best_list)} records).")
        else:
            df = pd.json_normalize(data)
    else:
        raise ValueError("JSON file does not contain tabular data.")

    # Flattened nested keys use dots -> keep readable
    df.columns = [str(c).replace(".", "_") for c in df.columns]
    if any("." in str(c) for c in df.columns) or df.shape[1] > 0:
        pass
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_file(filepath: str) -> tuple:
    """Load any supported structured file.

    Returns
    -------
    (df, ingestion) : (pd.DataFrame, dict)
        ingestion = {notes: [str], original_rows, original_cols, format}
    """
    ext = os.path.splitext(filepath)[1].lower()
    notes: list = []

    if ext in (".csv", ".txt", ".tsv"):
        df = _load_csv_like(filepath, notes)
        fmt = "csv"
    elif ext in (".xlsx", ".xls", ".xlsm"):
        df = _load_excel(filepath, notes)
        fmt = "excel"
    elif ext == ".json":
        df = _load_json(filepath, notes)
        fmt = "json"
    elif ext == ".parquet":
        df = pd.read_parquet(filepath)
        fmt = "parquet"
    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            "Supported: CSV, TSV, Excel (.xlsx/.xls), JSON, Parquet."
        )

    original_rows, original_cols = int(df.shape[0]), int(df.shape[1])

    # Drop fully empty rows/cols
    df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)
    dropped_rows = original_rows - df.shape[0]
    dropped_cols = original_cols - df.shape[1]
    if dropped_rows:
        notes.append(f"Removed {dropped_rows} completely empty row(s).")
    if dropped_cols:
        notes.append(f"Removed {dropped_cols} completely empty column(s).")

    df = _standardize_columns(df)
    df = _clean_numeric_strings(df, notes)

    if len(df) > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42).sort_index()
        notes.append(
            f"File is very large ({original_rows:,} rows). "
            f"Analysis uses a representative sample of {MAX_ROWS:,} rows."
        )

    df = df.reset_index(drop=True)

    ingestion = {
        "format": fmt,
        "original_rows": original_rows,
        "original_cols": original_cols,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "notes": notes,
    }
    return df, ingestion
