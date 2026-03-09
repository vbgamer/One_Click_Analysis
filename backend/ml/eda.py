import pandas as pd
import numpy as np
from ydata_profiling import ProfileReport
from scipy import stats as scipy_stats
import os
import warnings
warnings.filterwarnings('ignore')


def perform_eda(df: pd.DataFrame, output_path: str = None) -> dict:
    """
    Generate a comprehensive EDA report with professional-grade statistics.
    Returns enriched stats dict for downstream AI insights and chart generation.
    """

    # 1. Generate YData Profiling Report (HTML)
    profile = ProfileReport(
        df,
        title="One Click Analysis Report",
        minimal=len(df) > 10000,
        explorative=True
    )

    if output_path:
        profile.to_file(output_path)

    # 2. Basic Summary
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    summary = {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "missing_cells": int(df.isnull().sum().sum()),
        "missing_pct": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_pct": round(df.duplicated().sum() / len(df) * 100, 2),
        "columns": list(df.columns),
        "numeric_columns": num_cols,
        "categorical_columns": cat_cols,
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
    }

    # 3. Per-Column Numeric Statistics (what a data analyst would compute)
    column_stats = {}
    for col in num_cols:
        col_data = df[col].dropna()
        if len(col_data) == 0:
            continue

        skewness = float(col_data.skew())
        kurtosis = float(col_data.kurtosis())

        # Outlier detection using IQR method
        Q1 = col_data.quantile(0.25)
        Q3 = col_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outlier_count = int(((col_data < lower_bound) | (col_data > upper_bound)).sum())
        outlier_pct = round(outlier_count / len(col_data) * 100, 2)

        # Normality test
        normality_pvalue = None
        is_normal = None
        try:
            if len(col_data) < 5000:
                # Shapiro-Wilk for small samples (more powerful)
                _, normality_pvalue = scipy_stats.shapiro(col_data.sample(min(len(col_data), 500)))
            else:
                # D'Agostino-Pearson for larger samples
                _, normality_pvalue = scipy_stats.normaltest(col_data.sample(min(len(col_data), 5000)))
            normality_pvalue = round(float(normality_pvalue), 6)
            is_normal = normality_pvalue > 0.05
        except:
            pass

        column_stats[col] = {
            "mean": round(float(col_data.mean()), 4),
            "median": round(float(col_data.median()), 4),
            "std": round(float(col_data.std()), 4),
            "min": round(float(col_data.min()), 4),
            "max": round(float(col_data.max()), 4),
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
            "skew_interpretation": (
                "highly right-skewed" if skewness > 2 else
                "moderately right-skewed" if skewness > 1 else
                "slightly right-skewed" if skewness > 0.5 else
                "approximately symmetric" if abs(skewness) <= 0.5 else
                "slightly left-skewed" if skewness > -1 else
                "moderately left-skewed" if skewness > -2 else
                "highly left-skewed"
            ),
            "outlier_count": outlier_count,
            "outlier_pct": outlier_pct,
            "is_normal": is_normal,
            "normality_pvalue": normality_pvalue,
            "iqr": round(float(IQR), 4),
            "coefficient_of_variation": round(float(col_data.std() / col_data.mean() * 100), 2) if col_data.mean() != 0 else None,
        }

    summary["column_stats"] = column_stats

    # 4. Correlation analysis (top correlated pairs)
    if len(num_cols) >= 2:
        corr_matrix = df[num_cols].corr()
        top_correlations = []
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.3:  # Only meaningful correlations
                    top_correlations.append({
                        "col_a": num_cols[i],
                        "col_b": num_cols[j],
                        "correlation": round(float(corr_val), 4),
                        "strength": (
                            "strong" if abs(corr_val) > 0.7 else
                            "moderate" if abs(corr_val) > 0.5 else
                            "weak"
                        ),
                        "direction": "positive" if corr_val > 0 else "negative"
                    })
        # Sort by absolute correlation strength
        top_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        summary["top_correlations"] = top_correlations[:10]  # Top 10
        summary["correlation_matrix"] = {
            col: {c: round(float(v), 4) for c, v in corr_matrix[col].items()}
            for col in num_cols
        }

    # 5. Categorical column analysis
    cat_analysis = {}
    for col in cat_cols:
        vc = df[col].value_counts()
        cat_analysis[col] = {
            "unique_count": int(df[col].nunique()),
            "top_values": {str(k): int(v) for k, v in vc.head(5).items()},
            "is_high_cardinality": df[col].nunique() > 20,
            "missing_count": int(df[col].isnull().sum()),
        }
    summary["categorical_analysis"] = cat_analysis

    return summary
