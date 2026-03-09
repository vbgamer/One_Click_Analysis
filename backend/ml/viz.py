import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# Professional color palette
COLORS = {
    'primary': '#2563eb',
    'secondary': '#7c3aed',
    'success': '#059669',
    'danger': '#dc2626',
    'warning': '#d97706',
    'info': '#0891b2',
    'gray': '#6b7280',
    'light_gray': '#e5e7eb',
    'bg': '#f8fafc',
}
PALETTE = ['#2563eb', '#7c3aed', '#059669', '#dc2626', '#d97706', '#0891b2', '#db2777', '#4f46e5']


def generate_charts(df: pd.DataFrame, output_dir: str, ml_results: dict = None, eda_stats: dict = None):
    """
    Generate analyst-grade charts with statistical annotations.
    Uses intelligent chart selection based on data patterns, not just column order.
    """
    os.makedirs(output_dir, exist_ok=True)

    charts = {
        "Distribution & Data Understanding": [],
        "Trend & Time-Series Analysis": [],
        "Comparison & Ranking": [],
        "Relationship & Correlation": [],
        "Composition & Proportion": [],
        "Geographic / Spatial Analysis": [],
        "KPI & Executive Visuals": [],
        "Advanced & Business Analysis": [],
    }

    # Identify Column Types
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime']).columns.tolist()

    # Try to convert object cols to datetime
    if not date_cols:
        for col in df.select_dtypes(include=['object']):
            try:
                if df[col].nunique() > 10:
                    temp = pd.to_datetime(df[col], errors='coerce')
                    if temp.notna().sum() > 0.8 * len(df):
                        df[col] = temp
                        date_cols.append(col)
                        if col in cat_cols:
                            cat_cols.remove(col)
            except:
                pass

    # Get column stats from EDA if available
    column_stats = {}
    if eda_stats:
        column_stats = eda_stats.get('column_stats', {})

    # ====================================================
    # SMART COLUMN RANKING: Pick most interesting columns
    # A real analyst looks at variance, skewness, outliers
    # ====================================================
    def _rank_numeric_columns(cols):
        """Rank numeric columns by analytical interest (variance, skewness, outlier %)."""
        scores = {}
        for col in cols:
            score = 0
            if col in column_stats:
                cs = column_stats[col]
                # Higher variance = more interesting
                cv = cs.get('coefficient_of_variation')
                if cv and cv > 10:
                    score += 2
                # Skewed data = interesting pattern
                skew = abs(cs.get('skewness', 0))
                if skew > 1:
                    score += 3
                # Has outliers = worth investigating
                outlier_pct = cs.get('outlier_pct', 0)
                if outlier_pct > 1:
                    score += 2
                # Non-normal = interesting
                if cs.get('is_normal') is False:
                    score += 1
            else:
                # Fallback: use raw variance
                score = float(df[col].std()) if df[col].std() > 0 else 0
            scores[col] = score
        return sorted(cols, key=lambda c: scores.get(c, 0), reverse=True)

    ranked_num_cols = _rank_numeric_columns(num_cols)
    # Pick top columns (up to 5 most interesting)
    top_num_cols = ranked_num_cols[:5]

    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'font.size': 11,
        'axes.titlesize': 13,
        'axes.titleweight': 'bold',
        'figure.facecolor': 'white',
    })

    # ==========================================
    # 1. Distribution & Data Understanding
    # ==========================================
    for col in top_num_cols[:4]:
        cs = column_stats.get(col, {})
        skewness = cs.get('skewness', df[col].skew())
        mean_val = cs.get('mean', df[col].mean())
        median_val = cs.get('median', df[col].median())
        outlier_count = cs.get('outlier_count', 0)
        outlier_pct = cs.get('outlier_pct', 0)

        # --- Histogram with statistical annotations ---
        fig, ax = plt.subplots(figsize=(9, 5))

        # Use log scale for highly skewed data (analyst technique)
        use_log = abs(skewness) > 2 and df[col].min() >= 0
        plot_data = np.log1p(df[col].dropna()) if use_log else df[col].dropna()
        title_suffix = " (Log Scale)" if use_log else ""

        sns.histplot(plot_data, kde=True, ax=ax, color=COLORS['primary'], alpha=0.7, edgecolor='white')

        # Annotate mean and median lines
        ax.axvline(plot_data.mean(), color=COLORS['danger'], linestyle='--', linewidth=1.5, label=f'Mean: {mean_val:.2f}')
        ax.axvline(plot_data.median(), color=COLORS['success'], linestyle='-.', linewidth=1.5, label=f'Median: {median_val:.2f}')

        # Add skewness annotation
        skew_label = cs.get('skew_interpretation', f'Skew: {skewness:.2f}')
        ax.text(0.98, 0.95, f'Skewness: {skewness:.2f}\n({skew_label})',
                transform=ax.transAxes, ha='right', va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='gray', alpha=0.8),
                fontsize=9)

        if outlier_count > 0:
            ax.text(0.98, 0.78, f'⚠ Outliers: {outlier_count} ({outlier_pct}%)',
                    transform=ax.transAxes, ha='right', va='top',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#fef2f2', edgecolor=COLORS['danger'], alpha=0.8),
                    fontsize=9, color=COLORS['danger'])

        ax.legend(fontsize=9)
        ax.set_title(f'Distribution: {col}{title_suffix}')
        ax.set_xlabel(col)
        ax.set_ylabel('Frequency')
        path = save_plot(output_dir, f"hist_{col}.png")
        charts["Distribution & Data Understanding"].append({"title": f"Distribution - {col}", "path": path})

        # --- Box Plot with outlier annotations ---
        fig, ax = plt.subplots(figsize=(9, 4))
        bp = sns.boxplot(x=df[col], ax=ax, color=COLORS['info'], width=0.5)

        # Annotate quartiles
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        stats_text = f'Q1: {Q1:.2f} | Median: {median_val:.2f} | Q3: {Q3:.2f}\nIQR: {IQR:.2f} | Outliers: {outlier_count} ({outlier_pct}%)'
        ax.set_title(f'Box Plot: {col}')
        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, ha='left', va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.9),
                fontsize=9)
        path = save_plot(output_dir, f"box_{col}.png")
        charts["Distribution & Data Understanding"].append({"title": f"Box Plot - {col}", "path": path})

    # ==========================================
    # 2. Trend & Time-Series Analysis
    # ==========================================
    if date_cols:
        time_col = date_cols[0]
        
        # --- Trend: Content / Activity Growth over Time ---
        # Group by year-month or year depending on data range
        df_time = df.dropna(subset=[time_col]).copy()
        
        # Determine frequency (Yearly if span > 5 years, else Monthly)
        time_span = (df_time[time_col].max() - df_time[time_col].min()).days
        if time_span > 1800: # > 5 years
            df_time['period'] = df_time[time_col].dt.to_period('Y').dt.to_timestamp()
            period_name = 'Yearly'
        else:
            df_time['period'] = df_time[time_col].dt.to_period('M').dt.to_timestamp()
            period_name = 'Monthly'
            
        trend_counts = df_time.groupby('period').size()
        
        if len(trend_counts) > 3:
            fig, ax = plt.subplots(figsize=(11, 6))
            
            # Plot bar chart for counts
            ax.bar(trend_counts.index, trend_counts.values, width=np.timedelta64(20 if period_name=='Monthly' else 300, 'D'), 
                   color=COLORS['primary'], alpha=0.6, label=f'New Records ({period_name})')
            
            # Add cumulative growth line on secondary axis (analyst technique)
            ax2 = ax.twinx()
            cum_growth = trend_counts.cumsum()
            ax2.plot(trend_counts.index, cum_growth.values, color=COLORS['danger'], linewidth=2.5, marker='o', markersize=4, label='Cumulative Growth')
            
            ax.set_title(f'Growth Trend Over Time ({time_col})')
            ax.set_ylabel('New Records')
            ax2.set_ylabel('Total Cumulative Records')
            
            # Ask matplotlib to format dates nicely
            fig.autofmt_xdate()
            
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax2.legend(lines + lines2, labels + labels2, loc='upper left', fontsize=9)
            
            path = save_plot(output_dir, f"growth_trend_{time_col}.png")
            charts["Trend & Time-Series Analysis"].append({"title": f"Growth Trend - {time_col}", "path": path})

        if num_cols:
            val_col = ranked_num_cols[0] if ranked_num_cols else num_cols[0]
            df_sorted = df.sort_values(by=time_col).dropna(subset=[time_col, val_col])

            if len(df_sorted) > 5:
                # --- Line Chart with Moving Average ---
                fig, ax = plt.subplots(figsize=(11, 6))
                ax.plot(df_sorted[time_col], df_sorted[val_col], alpha=0.5, color=COLORS['gray'], linewidth=0.8, label=f'Raw {val_col}')

                # Moving average (analyst technique for trend detection)
                window = max(3, len(df_sorted) // 20)
                ma = df_sorted[val_col].rolling(window=window, center=True).mean()
                ax.plot(df_sorted[time_col], ma, color=COLORS['secondary'], linewidth=2, label=f'{window}-Point Moving Avg')

                ax.set_title(f'Time Series: {val_col} over Time')
                ax.legend(fontsize=9)
                fig.autofmt_xdate()
                path = save_plot(output_dir, f"line_{val_col}.png")
                charts["Trend & Time-Series Analysis"].append({"title": f"Time Series - {val_col}", "path": path})
    else:
        charts["Trend & Time-Series Analysis"].append({"title": "No suitable time-series data found", "path": None})

    # ==========================================
    # 3. Comparison & Ranking
    # ==========================================
    if cat_cols:
        # Generate Top 10 charts for up to 4 interesting categorical columns
        # Sort categoricals by uniqueness: we want high enough uniqueness to be interesting (>2), but not IDs (<1000)
        valid_cats = [c for c in cat_cols if df[c].nunique() > 2 and df[c].nunique() < 1000]
        # Sort by number of unique values (ascending)
        valid_cats = sorted(valid_cats, key=lambda c: df[c].nunique())
        
        for cat_col in valid_cats[:4]:
            if num_cols:
                val_col = ranked_num_cols[0] if ranked_num_cols else num_cols[0]
                # Aggregate top categories by mean of the numeric column
                top_cats = df.groupby(cat_col)[val_col].mean().sort_values(ascending=False).head(10)
                
                if len(top_cats) >= 2:
                    # --- Horizontal Bar for readability (Top 10) ---
                    fig, ax = plt.subplots(figsize=(10, min(6, max(3, len(top_cats)*0.5))))
                    sorted_cats = top_cats.sort_values() # Ascending for correct display order
                    ax.barh(range(len(sorted_cats)), sorted_cats.values, color=COLORS['primary'], edgecolor='white')
                    ax.set_yticks(range(len(sorted_cats)))
                    # Shorten labels if too long
                    labels = [str(l)[:30] + '...' if len(str(l)) > 30 else str(l) for l in sorted_cats.index]
                    ax.set_yticklabels(labels)
                    
                    for i, val in enumerate(sorted_cats.values):
                        ax.text(val + sorted_cats.values.max() * 0.01, i, f'{val:,.1f}', va='center', fontsize=9)
                    
                    ax.set_title(f'Top 10: {cat_col} by Average {val_col}')
                    ax.set_xlabel(f'Mean {val_col}')
                    
                    # Clean filename to avoid special character issues
                    safe_col = "".join([c if c.isalnum() else "_" for c in cat_col])
                    path = save_plot(output_dir, f"hbar_mean_{safe_col}.png")
                    charts["Comparison & Ranking"].append({"title": f"Top 10 {cat_col} (Avg {val_col})", "path": path})
                    
            # Also do a volume chart (Top 10 by Count)
            top_counts = df[cat_col].value_counts().head(10)
            if len(top_counts) >= 2:
                fig, ax = plt.subplots(figsize=(10, min(6, max(3, len(top_counts)*0.5))))
                sorted_counts = top_counts.sort_values()
                ax.barh(range(len(sorted_counts)), sorted_counts.values, color=COLORS['info'], edgecolor='white')
                ax.set_yticks(range(len(sorted_counts)))
                labels = [str(l)[:30] + '...' if len(str(l)) > 30 else str(l) for l in sorted_counts.index]
                ax.set_yticklabels(labels)
                
                for i, val in enumerate(sorted_counts.values):
                    ax.text(val + sorted_counts.values.max() * 0.01, i, f'{val:,}', va='center', fontsize=9, fontweight='bold')
                
                ax.set_title(f'Most Frequent: Top 10 {cat_col} by Volume')
                ax.set_xlabel('Count / Volume')
                
                safe_col = "".join([c if c.isalnum() else "_" for c in cat_col])
                path = save_plot(output_dir, f"hbar_count_{safe_col}.png")
                charts["Comparison & Ranking"].append({"title": f"Top 10 by Volume: {cat_col}", "path": path})

    # ==========================================
    # 4. Relationship & Correlation
    # ==========================================
    if len(num_cols) >= 2:
        # Find the most correlated pair (analyst picks the most interesting relationship)
        top_corrs = eda_stats.get('top_correlations', []) if eda_stats else []
        if top_corrs:
            x_col = top_corrs[0]['col_a']
            y_col = top_corrs[0]['col_b']
            corr_val = top_corrs[0]['correlation']
        else:
            x_col = num_cols[0]
            y_col = num_cols[1]
            corr_val = df[x_col].corr(df[y_col])

        # --- Scatter Plot with regression line and R² ---
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.scatter(df[x_col], df[y_col], alpha=0.4, s=20, color=COLORS['primary'], edgecolors='white', linewidth=0.5)

        # Add regression line
        try:
            mask = df[[x_col, y_col]].dropna()
            z = np.polyfit(mask[x_col], mask[y_col], 1)
            p = np.poly1d(z)
            x_line = np.linspace(mask[x_col].min(), mask[x_col].max(), 100)
            ax.plot(x_line, p(x_line), color=COLORS['danger'], linewidth=2, linestyle='--',
                    label=f'y = {z[0]:.3f}x + {z[1]:.3f}')
        except:
            pass

        # Annotate R² and correlation
        r_sq = corr_val ** 2
        ax.text(0.02, 0.95, f'r = {corr_val:.3f}\nR² = {r_sq:.3f}',
                transform=ax.transAxes, ha='left', va='top',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', edgecolor='gray', alpha=0.9),
                fontsize=11, fontweight='bold')

        ax.set_title(f'Scatter: {x_col} vs {y_col}')
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.legend(fontsize=9)
        path = save_plot(output_dir, f"scatter_{x_col}_{y_col}.png")
        charts["Relationship & Correlation"].append({"title": f"Scatter - {x_col} vs {y_col}", "path": path})

        # --- Correlation Heatmap with significance ---
        fig, ax = plt.subplots(figsize=(10, 8))
        corr = df[num_cols].corr()
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        sns.heatmap(corr, mask=mask, annot=True, cmap='RdBu_r', center=0, fmt=".2f",
                    ax=ax, vmin=-1, vmax=1, linewidths=0.5, square=True,
                    cbar_kws={'label': 'Correlation Coefficient'})
        ax.set_title('Correlation Matrix (Lower Triangle)')
        path = save_plot(output_dir, "heatmap_corr.png")
        charts["Relationship & Correlation"].append({"title": "Correlation Matrix", "path": path})

        # --- Pair Plot for top 4 columns ---
        try:
            subset_cols = ranked_num_cols[:4]
            if len(subset_cols) >= 2:
                pp = sns.pairplot(df[subset_cols], diag_kind='kde',
                                  plot_kws={'alpha': 0.4, 's': 15, 'edgecolor': 'white'},
                                  diag_kws={'fill': True})
                pp.fig.suptitle('Pair Plot (Top Interesting Columns)', y=1.02, fontweight='bold')
                path = os.path.join(output_dir, "pairplot.png")
                pp.savefig(path, bbox_inches='tight')
                plt.close()
                charts["Relationship & Correlation"].append({"title": "Pair Plot", "path": "pairplot.png"})
        except:
            pass

    # ==========================================
    # 5. Composition & Proportion
    # ==========================================
    if cat_cols:
        cat_col = min(cat_cols, key=lambda c: df[c].nunique()) if cat_cols else cat_cols[0]
        vc = df[cat_col].value_counts()

        # "Others" bucket for clean charts (analyst technique)
        if len(vc) > 6:
            top_vc = vc.head(5)
            others = pd.Series({'Others': vc.iloc[5:].sum()})
            vc_display = pd.concat([top_vc, others])
        else:
            vc_display = vc

        # --- Donut Chart (more modern than pie) ---
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = PALETTE[:len(vc_display)]
        wedges, texts, autotexts = ax.pie(
            vc_display.values, labels=vc_display.index, autopct='%1.1f%%',
            wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
            colors=colors, pctdistance=0.8
        )
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
        ax.set_title(f'Composition: {cat_col}')
        # Add total count in center
        ax.text(0, 0, f'Total\n{len(df):,}', ha='center', va='center', fontsize=14, fontweight='bold',
                color=COLORS['gray'])
        path = save_plot(output_dir, f"donut_{cat_col}.png")
        charts["Composition & Proportion"].append({"title": f"Composition - {cat_col}", "path": path})

        # --- Stacked bar if 2 categoricals ---
        if len(cat_cols) > 1 and len(num_cols) > 0:
            cat_col_2 = [c for c in cat_cols if c != cat_col][0]
            if df[cat_col].nunique() < 15 and df[cat_col_2].nunique() < 15:
                try:
                    ct = pd.crosstab(df[cat_col], df[cat_col_2]).head(10)
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ct.plot(kind='bar', stacked=True, ax=ax, color=PALETTE[:ct.shape[1]], edgecolor='white')
                    ax.set_title(f'Stacked Bar: {cat_col} by {cat_col_2}')
                    ax.legend(title=cat_col_2, bbox_to_anchor=(1.05, 1), loc='upper left')
                    path = save_plot(output_dir, "stacked_bar.png")
                    charts["Composition & Proportion"].append({"title": "Stacked Bar Chart", "path": path})
                except:
                    pass

    # ==========================================
    # 6. Geographic / Spatial Analysis
    # ==========================================
    geo_cols = [c for c in df.columns if 'lat' in c.lower() or 'lon' in c.lower() or 'country' in c.lower()]
    if geo_cols and len(num_cols) > 0:
        charts["Geographic / Spatial Analysis"].append({"title": "Geographic analysis requires map library (folium)", "path": None})
    else:
        charts["Geographic / Spatial Analysis"].append({"title": "No geographic data detected", "path": None})

    # ==========================================
    # 7. KPI & Executive Visuals
    # ==========================================
    # Total Records KPI
    charts["KPI & Executive Visuals"].append(
        generate_kpi_card(output_dir, "Total Records", f"{len(df):,}", "kpi_rows.png")
    )

    # Missing Data KPI
    missing_pct = eda_stats.get('missing_pct', 0) if eda_stats else round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 1)
    color = COLORS['success'] if missing_pct < 5 else COLORS['warning'] if missing_pct < 20 else COLORS['danger']
    charts["KPI & Executive Visuals"].append(
        generate_kpi_card(output_dir, "Missing Data", f"{missing_pct}%", "kpi_missing.png", color=color)
    )

    # Duplicate Rows KPI
    dup_pct = eda_stats.get('duplicate_pct', 0) if eda_stats else round(df.duplicated().sum() / len(df) * 100, 1)
    color = COLORS['success'] if dup_pct < 1 else COLORS['warning'] if dup_pct < 10 else COLORS['danger']
    charts["KPI & Executive Visuals"].append(
        generate_kpi_card(output_dir, "Duplicate Rows", f"{dup_pct}%", "kpi_duplicates.png", color=color)
    )

    if num_cols:
        col = ranked_num_cols[0] if ranked_num_cols else num_cols[0]
        charts["KPI & Executive Visuals"].append(
            generate_kpi_card(output_dir, f"Mean {col}", f"{df[col].mean():,.2f}", f"kpi_mean_{col}.png")
        )

    # ==========================================
    # 8. Advanced & Business Analysis
    # ==========================================

    # --- Feature Importance Chart (from AutoML) ---
    if ml_results and ml_results.get('feature_importance'):
        feat_imp = ml_results['feature_importance']
        if feat_imp:
            fig, ax = plt.subplots(figsize=(10, max(4, len(feat_imp) * 0.4)))
            sorted_feats = dict(sorted(feat_imp.items(), key=lambda x: x[1]))
            top_feats = dict(list(sorted_feats.items())[-15:])  # Top 15

            colors_list = [COLORS['primary'] if v > 0.05 else COLORS['light_gray'] for v in top_feats.values()]
            ax.barh(list(top_feats.keys()), list(top_feats.values()), color=colors_list, edgecolor='white')
            for i, (name, val) in enumerate(top_feats.items()):
                ax.text(val + 0.002, i, f'{val:.3f}', va='center', fontsize=9)
            ax.set_title(f'Feature Importance ({ml_results.get("best_model", "Model")})')
            ax.set_xlabel('Importance Score')
            path = save_plot(output_dir, "feature_importance.png")
            charts["Advanced & Business Analysis"].append({"title": "Feature Importance", "path": path})

    # --- Class Distribution Chart (for classification) ---
    if ml_results and ml_results.get('class_info', {}).get('class_distribution'):
        class_dist = ml_results['class_info']['class_distribution']
        is_imbalanced = ml_results['class_info'].get('is_imbalanced', False)

        fig, ax = plt.subplots(figsize=(8, 5))
        labels = list(class_dist.keys())
        values = list(class_dist.values())
        bar_colors = [COLORS['danger'] if is_imbalanced else COLORS['primary']] * len(labels)
        ax.bar(labels, values, color=bar_colors, edgecolor='white')

        for i, val in enumerate(values):
            ax.text(i, val + max(values) * 0.01, f'{val:,}', ha='center', fontweight='bold', fontsize=10)

        title = f'Target Class Distribution'
        if is_imbalanced:
            ratio = ml_results['class_info'].get('imbalance_ratio', 0)
            title += f' (⚠ IMBALANCED - ratio {ratio:.1f}:1)'
            ax.text(0.5, 0.95, '⚠ Class imbalance detected!\nConsider SMOTE or class weights.',
                    transform=ax.transAxes, ha='center', va='top',
                    bbox=dict(boxstyle='round', facecolor='#fef2f2', edgecolor=COLORS['danger']),
                    fontsize=9, color=COLORS['danger'])
        ax.set_title(title)
        ax.set_ylabel('Count')
        path = save_plot(output_dir, "class_distribution.png")
        charts["Advanced & Business Analysis"].append({"title": "Class Distribution", "path": path})

    # --- Confusion Matrix Heatmap ---
    if ml_results and ml_results.get('metrics', {}).get('confusion_matrix'):
        cm = np.array(ml_results['metrics']['confusion_matrix'])
        fig, ax = plt.subplots(figsize=(7, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax, cbar=False,
                    linewidths=1, linecolor='white', square=True)
        ax.set_title('Confusion Matrix')
        ax.set_xlabel('Predicted')
        ax.set_ylabel('Actual')
        path = save_plot(output_dir, "confusion_matrix.png")
        charts["Advanced & Business Analysis"].append({"title": "Confusion Matrix", "path": path})

    # --- Model Metrics Summary Card ---
    if ml_results and ml_results.get('metrics'):
        metrics = ml_results['metrics']
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.axis('off')

        # Build metrics text
        metric_lines = []
        for key in ['accuracy', 'precision', 'recall', 'f1_score', 'r2', 'rmse', 'mae']:
            if key in metrics:
                display_name = key.replace('_', ' ').title()
                val = metrics[key]
                if isinstance(val, float) and val <= 1:
                    metric_lines.append(f'{display_name}: {val:.4f} ({val * 100:.1f}%)')
                else:
                    metric_lines.append(f'{display_name}: {val}')

        if 'cv_mean' in metrics:
            metric_lines.append(f'Cross-Val Mean: {metrics["cv_mean"]:.4f} ± {metrics.get("cv_std", 0):.4f}')

        text = '\n'.join(metric_lines)
        ax.text(0.5, 0.5, text, ha='center', va='center', fontsize=13,
                fontfamily='monospace', linespacing=1.8,
                bbox=dict(boxstyle='round,pad=0.8', facecolor=COLORS['bg'], edgecolor=COLORS['primary'], linewidth=2))
        ax.set_title(f'Model Performance: {ml_results.get("best_model", "AutoML")}', fontsize=14, fontweight='bold', pad=20)
        path = save_plot(output_dir, "model_metrics.png")
        charts["Advanced & Business Analysis"].append({"title": "Model Performance Summary", "path": path})

    # --- ROC Curve (for Classification) ---
    if ml_results and ml_results.get('metrics', {}).get('roc_curve'):
        try:
            roc_data = ml_results['metrics']['roc_curve']
            roc_auc = ml_results['metrics'].get('roc_auc', 0)
            
            fig, ax = plt.subplots(figsize=(7, 6))
            ax.plot(roc_data['fpr'], roc_data['tpr'], color=COLORS['info'], linewidth=3, 
                    label=f'AUC = {roc_auc:.4f}')
            ax.plot([0, 1], [0, 1], color=COLORS['gray'], linestyle='--', linewidth=1.5, label='Random Guess')
            
            ax.set_title('ROC Curve')
            ax.set_xlabel('False Positive Rate')
            ax.set_ylabel('True Positive Rate')
            ax.set_xlim([0.0, 1.05])
            ax.set_ylim([0.0, 1.05])
            ax.legend(loc="lower right", fontsize=11)
            
            path = save_plot(output_dir, "roc_curve.png")
            charts["Advanced & Business Analysis"].append({"title": "ROC Curve", "path": path})
        except:
            pass
            
    # --- Model Comparison Chart ---
    if ml_results and ml_results.get('models_compared') and len(ml_results['models_compared']) > 1:
        try:
            models = ml_results['models_compared']
            # We don't have individual scores easily accessible without retraining, 
            # so we just show the models explored and highlight the winner
            fig, ax = plt.subplots(figsize=(8, len(models) * 0.6 + 2))
            
            best_model = ml_results.get('best_model', '')
            # Try to get best_model name string since it might be an estimator object
            if hasattr(best_model, '__class__'):
                best_model_name = best_model.__class__.__name__
            else:
                best_model_name = str(best_model)
                
            y_pos = np.arange(len(models))
            
            # Simple visualization of explored models
            colors = [COLORS['success'] if best_model_name.lower() in str(m).lower() or str(m).lower() in best_model_name.lower() else COLORS['light_gray'] for m in models]
            
            ax.barh(y_pos, [1]*len(models), align='center', color=colors, edgecolor='white')
            ax.set_yticks(y_pos)
            # Shorten names for display
            display_names = [str(m).split('.')[-1].replace("Classifier", "").replace("Regressor", "") for m in models]
            ax.set_yticklabels(display_names)
            ax.invert_yaxis()  # labels read top-to-bottom
            
            ax.set_xticks([]) # Hide x axis
            ax.set_title('Models Evaluated by AutoML (Winner in Green)')
            
            path = save_plot(output_dir, "model_comparison.png")
            charts["Advanced & Business Analysis"].append({"title": "Models Explored", "path": path})
        except Exception as e:
            print(f"Error making model comparison: {e}")
            pass

    # --- Pareto Chart ---
    if len(cat_cols) > 0 and len(num_cols) > 0:
        cat_col = cat_cols[0]
        val_col = ranked_num_cols[0] if ranked_num_cols else num_cols[0]
        top_cats = df.groupby(cat_col)[val_col].sum().sort_values(ascending=False).head(8)

        if len(top_cats) >= 3:
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.bar(range(len(top_cats)), top_cats.values, color=COLORS['primary'], edgecolor='white')
                ax.set_xticks(range(len(top_cats)))
                ax.set_xticklabels(top_cats.index, rotation=45, ha='right')
                ax.set_ylabel(val_col, color=COLORS['primary'])

                # Cumulative line on twin axis
                ax2 = ax.twinx()
                cum_pct = top_cats.cumsum() / top_cats.sum() * 100
                ax2.plot(range(len(top_cats)), cum_pct.values, color=COLORS['danger'], marker='o', ms=6, linewidth=2)
                ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x)}%'))
                ax2.set_ylabel('Cumulative %', color=COLORS['danger'])
                ax2.axhline(80, color=COLORS['warning'], linestyle=':', alpha=0.5, label='80% threshold')

                ax.set_title(f'Pareto Analysis: {val_col} by {cat_col}')
                ax2.legend(fontsize=9)
                path = save_plot(output_dir, f"pareto_{val_col}.png")
                charts["Advanced & Business Analysis"].append({"title": f"Pareto - {cat_col}", "path": path})
            except:
                pass

    # --- Outlier Summary Chart ---
    if column_stats:
        outlier_cols = {col: stats['outlier_pct'] for col, stats in column_stats.items()
                        if stats.get('outlier_pct', 0) > 0}
        if outlier_cols:
            fig, ax = plt.subplots(figsize=(9, max(3, len(outlier_cols) * 0.4)))
            sorted_outliers = dict(sorted(outlier_cols.items(), key=lambda x: x[1]))
            colors_list = [COLORS['danger'] if v > 5 else COLORS['warning'] if v > 1 else COLORS['success']
                           for v in sorted_outliers.values()]
            ax.barh(list(sorted_outliers.keys()), list(sorted_outliers.values()), color=colors_list, edgecolor='white')
            for i, (name, val) in enumerate(sorted_outliers.items()):
                ax.text(val + 0.1, i, f'{val}%', va='center', fontsize=9, fontweight='bold')
            ax.set_title('Outlier Percentage by Column')
            ax.set_xlabel('Outlier %')
            ax.axvline(5, color=COLORS['danger'], linestyle=':', alpha=0.5, label='5% threshold')
            ax.legend(fontsize=9)
            path = save_plot(output_dir, "outlier_summary.png")
            charts["Advanced & Business Analysis"].append({"title": "Outlier Analysis", "path": path})

    plt.close('all')
    return charts


def generate_kpi_card(output_dir, title, value, filename, color=None):
    """Generates a professional KPI card image."""
    if color is None:
        color = COLORS['primary']

    fig, ax = plt.subplots(figsize=(4, 2.2))
    ax.text(0.5, 0.75, title, ha='center', va='center', fontsize=11, color=COLORS['gray'], fontweight='500')
    ax.text(0.5, 0.35, str(value), ha='center', va='center', fontsize=22, fontweight='bold', color=color)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    path = save_plot(output_dir, filename)
    return {"title": title, "path": path}


def save_plot(output_dir, filename):
    plt.tight_layout()
    path = os.path.join(output_dir, filename)
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return filename
