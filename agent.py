
import pandas as pd
import numpy as np
import os, uuid
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import accuracy_score, r2_score
import joblib
import traceback

BASE = Path(".").resolve()

def detect_file_type(path: str):
    lower = path.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return "excel"
    if lower.endswith(".json"):
        return "json"
    return "unknown"

def read_file(path: str):
    ftype = detect_file_type(path)
    if ftype == "csv":
        return pd.read_csv(path)
    if ftype == "excel":
        return pd.read_excel(path)
    if ftype == "json":
        return pd.read_json(path)
    raise ValueError("Unsupported file type")

def simple_clean(df: pd.DataFrame):
    # basic cleaning: strip column names, drop fully empty cols, convert whitespace strings to NaN
    df = df.copy()
    df.columns = [str(c).strip().replace("\\n", " ").replace("  ", " ") for c in df.columns]
    df.replace(r'^\s*$', np.nan, regex=True, inplace=True)
    # drop columns that are entirely null
    df.dropna(axis=1, how='all', inplace=True)
    return df

def generate_plots(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    plots = []
    numeric = df.select_dtypes(include=['number']).columns.tolist()
    # correlation
    if len(numeric) > 1:
        corr = df[numeric].corr()
        p = out_dir / "corr.png"
        plt.figure(figsize=(6,5))
        sns.heatmap(corr, annot=True, cmap='coolwarm')
        plt.tight_layout(); plt.savefig(p); plt.close()
        plots.append(str(p.name))
    # histograms (up to 6)
    for col in numeric[:6]:
        p = out_dir / f"{col}_hist.png"
        plt.figure(figsize=(4,3))
        sns.histplot(df[col].dropna(), kde=True)
        plt.tight_layout(); plt.savefig(p); plt.close()
        plots.append(str(p.name))
    return plots

def prepare_features(df: pd.DataFrame, target_col=None):
    df = df.copy()
    numeric = df.select_dtypes(include=['number']).columns.tolist()
    cats = df.select_dtypes(include=['object', 'category']).columns.tolist()
    X_num = df[numeric].fillna(0)
    X_cat = df[cats].fillna("NA")
    encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
    if len(cats) > 0:
        X_cat_enc = encoder.fit_transform(X_cat)
        cat_cols = encoder.get_feature_names_out(cats)
        X_cat_df = pd.DataFrame(X_cat_enc, columns=cat_cols, index=df.index)
        X = pd.concat([X_num, X_cat_df], axis=1)
    else:
        X = X_num
    scaler = StandardScaler()
    if not X.empty:
        X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)
    else:
        X_scaled = X
    y = None
    if target_col and target_col in df.columns:
        y = df[target_col]
    return X_scaled, y, {"encoder": encoder, "scaler": scaler}

def train_basic_model(X, y):
    # choose classification if y is binary-like
    if y is None:
        return None, None
    y_clean = y.dropna()
    X_clean = X.loc[y_clean.index]
    # detect binary
    if y_clean.nunique() <= 2 and set(y_clean.dropna().unique()).issubset({0,1}) or y_clean.nunique() == 2:
        # classification
        try:
            Xtr, Xte, ytr, yte = train_test_split(X_clean, y_clean, test_size=0.2, random_state=42)
            model = LogisticRegression(max_iter=1000)
            model.fit(Xtr, ytr)
            preds = model.predict(Xte)
            score = accuracy_score(yte, preds)
            return model, {"task":"classification", "score": float(score)}
        except Exception:
            return None, None
    else:
        # regression
        try:
            Xtr, Xte, ytr, yte = train_test_split(X_clean, y_clean, test_size=0.2, random_state=42)
            model = LinearRegression()
            model.fit(Xtr, ytr)
            preds = model.predict(Xte)
            score = r2_score(yte, preds)
            return model, {"task":"regression", "score": float(score)}
        except Exception:
            return None, None

def generate_report_html(df: pd.DataFrame, plots, analysis, out_path: Path, job_id: str):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("<!doctype html><html><head><meta charset='utf-8'><title>AI Agent Report</title></head><body>")
        f.write(f"<h1>AI Agent Report - {job_id}</h1>")
        f.write("<h2>Summary</h2>")
        f.write(f"<p>Rows: {df.shape[0]} &nbsp; Columns: {df.shape[1]}</p>")
        f.write("<h3>Top columns & types</h3>")
        schema = df.dtypes.to_frame("dtype")
        schema['missing'] = df.isna().sum()
        f.write(schema.to_html())
        # plots
        if plots:
            f.write("<h3>Plots</h3>")
            for p in plots:
                # images are placed in same dir
                f.write(f'<img src="{p}" style="max-width:600px"/><br/>')
        # analysis
        f.write("<h3>Automated Analysis</h3><ul>")
        for a in analysis:
            f.write(f"<li>{a}</li>")
        f.write("</ul>")
        f.write("</body></html>")
    return str(out_path)

def process_file(path: str, job_id: str = None):
    job_id = job_id or str(uuid.uuid4())
    try:
        df = read_file(path)
    except Exception as e:
        # try read with utf-8 errors
        try:
            df = pd.read_csv(path, encoding='latin1')
        except Exception as ex:
            raise RuntimeError(f"Could not read file: {e}; fallback failed: {ex}")
    df = simple_clean(df)
    # ETL: ensure CSV saved
    proc_dir = BASE / "processed" / job_id
    proc_dir.mkdir(parents=True, exist_ok=True)
    csv_path = proc_dir / "data.csv"
    df.to_csv(csv_path, index=False)

    # validation & cleaning (basic)
    analysis = []
    # missingness
    miss = (df.isna().mean() * 100).round(2)
    high_missing = miss[miss > 30].index.tolist()
    if high_missing:
        analysis.append(f"High missingness (>30%) in columns: {', '.join(high_missing)}")
    # duplicates
    dups = df.duplicated().sum()
    if dups > 0:
        analysis.append(f"Found {dups} duplicate rows")
    # outliers
    num = df.select_dtypes(include=['number'])
    outlier_info = []
    for c in num.columns:
        q1 = df[c].quantile(0.25); q3 = df[c].quantile(0.75); iqr = q3-q1
        if iqr == 0: continue
        lower = q1 - 1.5*iqr; upper = q3 + 1.5*iqr
        pct = ((df[c] < lower) | (df[c] > upper)).mean() * 100
        if pct > 1:
            outlier_info.append(f"{c} ({pct:.1f}% outliers)")
    if outlier_info:
        analysis.append("Potential outlier columns: " + ", ".join(outlier_info))

    # plots
    plots = generate_plots(df, proc_dir)

    # feature prep & model (pick first binary-like column as target if exists)
    target = None
    for c in df.columns:
        nun = df[c].nunique(dropna=True)
        if nun == 2:
            target = c
            break
    X, y, _ = prepare_features(df, target_col=target)
    model_info = None
    model = None
    if y is not None and not y.dropna().empty and not X.empty:
        model, model_info = train_basic_model(X, y)
        if model is not None:
            model_path = proc_dir / "model.joblib"
            joblib.dump(model, model_path)
            analysis.append(f"Trained {model_info['task']} model; validation score: {model_info['score']:.3f}")
    else:
        analysis.append("No valid target found or insufficient data for training baseline model.")

    # generate report html
    report_path = proc_dir / "report.html"
    generate_report_html(df, plots, analysis, report_path, job_id)
    return str(report_path)

def get_status(job_id: str):
    proc_dir = BASE / "processed" / job_id
    report = proc_dir / "report.html"
    if report.exists():
        return "done"
    return "pending"

def get_report_path(job_id: str):
    proc_dir = BASE / "processed" / job_id
    report = proc_dir / "report.html"
    if report.exists():
        return str(report)
    return None
