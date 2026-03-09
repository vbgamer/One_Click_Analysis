from huggingface_hub import InferenceClient
import os
import json

# Import the new agent module
try:
    from . import agents as agent_module
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False


def _build_rich_context(summary_stats: dict, target_col: str, model_metrics: dict) -> str:
    """
    Build a comprehensive statistical context for the LLM.
    A real analyst would present specific numbers, not just row counts.
    """
    lines = []
    
    # Basic dataset info
    lines.append(f"Dataset: {summary_stats.get('rows', '?')} rows × {summary_stats.get('cols', '?')} columns")
    lines.append(f"Missing Data: {summary_stats.get('missing_pct', 0)}% of all cells")
    lines.append(f"Duplicate Rows: {summary_stats.get('duplicate_pct', 0)}%")
    lines.append(f"Target Variable: {target_col}")
    
    # Column-level statistics
    column_stats = summary_stats.get('column_stats', {})
    if column_stats:
        lines.append("\n--- Key Column Statistics ---")
        for col, stats in list(column_stats.items())[:6]:
            skew = stats.get('skew_interpretation', 'unknown')
            outliers = stats.get('outlier_pct', 0)
            cv = stats.get('coefficient_of_variation', None)
            normal = "normal" if stats.get('is_normal') else "non-normal"
            lines.append(f"  {col}: mean={stats.get('mean')}, median={stats.get('median')}, "
                         f"skewness={stats.get('skewness')} ({skew}), "
                         f"outliers={outliers}%, distribution={normal}")
    
    # Correlations
    top_corrs = summary_stats.get('top_correlations', [])
    if top_corrs:
        lines.append("\n--- Top Correlations ---")
        for corr in top_corrs[:5]:
            lines.append(f"  {corr['col_a']} ↔ {corr['col_b']}: r={corr['correlation']} "
                         f"({corr['strength']} {corr['direction']})")
                         
    # Top Categories (Crucial for Business Insights)
    lines.append("\n--- Top Categories (Volume Drivers) ---")
    if column_stats:
        for col, stats in list(column_stats.items()):
            if 'top_values' in stats and stats['top_values']:
                top_items = list(stats['top_values'].items())[:3]
                top_str = ", ".join([f"{k} ({v} records)" for k, v in top_items])
                lines.append(f"  {col}: {top_str}")
    
    # Model performance
    if model_metrics:
        lines.append("\n--- Model Performance ---")
        for key in ['accuracy', 'precision', 'recall', 'f1_score', 'r2', 'rmse', 'mae', 'cv_mean', 'cv_std']:
            if key in model_metrics:
                lines.append(f"  {key}: {model_metrics[key]}")
    
    return "\n".join(lines)


def generate_insights(summary_stats: dict, target_col: str, model_metrics: dict):
    """
    Generate professional data analyst insights.
    Uses rich statistical context instead of just row/column counts.
    """
    
    # Build comprehensive context
    context = _build_rich_context(summary_stats, target_col, model_metrics)
    
    # --- Attempt Multi-Agent Analysis (Primary) ---
    if AGENTS_AVAILABLE:
        try:
            print("[INFO] Running Multi-Agent Analysis with AutoGen...")
            agent_insights = agent_module.run_agent_analysis(
                summary_stats=summary_stats,
                target_col=target_col,
                model_metrics=model_metrics
            )
            if agent_insights and "error" not in agent_insights.lower():
                return agent_insights
        except Exception as e:
            print(f"[WARN] Agent analysis failed, falling back to simple LLM: {e}")

    # --- Fallback: Simple Hugging Face Inference ---
    token = os.getenv("HF_TOKEN")
    
    if not token:
        return _generate_offline_insights(summary_stats, target_col, model_metrics)

    client = InferenceClient(token=token)
    
    prompt = f"""You are a Senior Data Analyst writing a professional analysis report.
    
Here is the complete statistical analysis of the dataset:

{context}

Write a structured analysis with these sections:
1. **Data Quality Assessment**: Comment on missing data, duplicates, outliers, and distribution shapes. Cite specific numbers.
2. **Key Patterns & Volume Drivers**: Highlight the strongest correlations, unusual distributions, and most importantly, the top categories/volumes that dominate the dataset. Explain what they mean in business terms.
3. **Model Performance Analysis**: Evaluate the ML model's accuracy, precision, recall, and ROC/AUC. Is the model reliable? What are its limitations?
4. **Strategic Business Recommendations**: This is the most crucial section for the executive team. Based on the volume drivers (top categories, countries, genres) and model patterns, what specific business decisions should the company make? (e.g., 'Invest more in X because...', 'Reduce focus on Y because...', 'Target Z demographic'). Provide 3 distinct, highly actionable recommendations.

Be specific — cite actual numbers from the statistics. Avoid generic statements. Write like a senior data analyst directly advising the CEO.
"""

    try:
        response = client.text_generation(
            prompt, 
            model="mistralai/Mistral-7B-Instruct-v0.2", 
            max_new_tokens=500
        )
        return response
    except Exception as e:
        return _generate_offline_insights(summary_stats, target_col, model_metrics)


def _generate_offline_insights(summary_stats: dict, target_col: str, model_metrics: dict) -> str:
    """
    Generate insights without any API calls using pure statistical logic.
    This is what a data analyst would write by looking at the numbers.
    """
    insights = ["**📊 AI Data Quality & Analysis Report**\n"]
    
    # Data Quality
    missing = summary_stats.get('missing_pct', 0)
    duplicates = summary_stats.get('duplicate_pct', 0)
    
    insights.append("### 1. Data Quality Assessment")
    if missing < 1:
        insights.append(f"✅ **Excellent data completeness** — only {missing}% missing values.")
    elif missing < 10:
        insights.append(f"⚠️ **Acceptable missing data** — {missing}% cells are empty. Imputation was applied.")
    else:
        insights.append(f"🚨 **High missing data** — {missing}% of cells are empty. This may affect model reliability.")
    
    if duplicates > 0:
        insights.append(f"  - {duplicates}% duplicate rows detected and removed.")
    
    # Column-level insights
    column_stats = summary_stats.get('column_stats', {})
    if column_stats:
        skewed_cols = [col for col, s in column_stats.items() if abs(s.get('skewness', 0)) > 1]
        outlier_cols = [(col, s.get('outlier_pct', 0)) for col, s in column_stats.items() if s.get('outlier_pct', 0) > 2]
        
        if skewed_cols:
            insights.append(f"  - **Skewed distributions** detected in: {', '.join(skewed_cols[:3])}. Log transformation recommended.")
        if outlier_cols:
            worst = max(outlier_cols, key=lambda x: x[1])
            insights.append(f"  - **Outliers**: {worst[0]} has {worst[1]}% outliers. These may need investigation.")
    
    # Correlations
    top_corrs = summary_stats.get('top_correlations', [])
    if top_corrs:
        insights.append("\n### 2. Key Patterns & Relationships")
        for corr in top_corrs[:3]:
            direction = "increases with" if corr['direction'] == 'positive' else "decreases with"
            insights.append(f"  - **{corr['col_a']}** {direction} **{corr['col_b']}** "
                            f"(r={corr['correlation']}, {corr['strength']})")
    
    # Model performance
    if model_metrics:
        insights.append(f"\n### 3. Model Performance")
        acc = model_metrics.get('accuracy', model_metrics.get('r2'))
        if acc is not None:
            if acc > 0.9:
                insights.append(f"✅ **Strong performance** — accuracy/R² of {acc:.4f} ({acc*100:.1f}%).")
            elif acc > 0.7:
                insights.append(f"⚠️ **Moderate performance** — accuracy/R² of {acc:.4f}. Feature engineering may improve this.")
            else:
                insights.append(f"🚨 **Low performance** — accuracy/R² of {acc:.4f}. Consider more data or different features.")
        
        f1 = model_metrics.get('f1_score')
        if f1:
            insights.append(f"  - F1 Score: {f1:.4f} | Precision: {model_metrics.get('precision', 'N/A')} | Recall: {model_metrics.get('recall', 'N/A')}")
        
        cv_mean = model_metrics.get('cv_mean')
        if cv_mean:
            insights.append(f"  - Cross-validation: {cv_mean:.4f} ± {model_metrics.get('cv_std', 0):.4f} (robust estimate)")
            
    # Strategic Business Recommendations (Based on volume)
    insights.append("\n### 4. Strategic Business Recommendations")
    recommendations_made = 0
    if column_stats:
        # Find categorical columns with dominant values
        for col, stats in column_stats.items():
            if 'top_values' in stats and stats['top_values']:
                top_items = list(stats['top_values'].items())
                if len(top_items) > 0:
                    top_name, top_count = top_items[0]
                    # If the top item makes up a significant chunk (e.g. >10% of dataset)
                    pct = (top_count / summary_stats.get('rows', 1)) * 100
                    if pct > 10:
                        insights.append(f"  - **Capitalize on '{col}' dominance**: '{top_name}' represents {pct:.1f}% of your dataset ({top_count} records). Consider disproportionate investment or targeted campaigns toward this segment as it is your strongest historical driver.")
                        recommendations_made += 1
                        if recommendations_made >= 3:
                            break
                            
    if recommendations_made < 1:
        insights.append("  - **Improve data tracking**: The current dataset lacks strong categorical dominance. Consider collecting more targeted features (e.g., customer demographics, specific product categories) to identify high-ROI investment areas.")
        insights.append(f"  - **Focus on target optimization**: Model performance on `{target_col}` indicates room for improvement. Prioritize gathering higher-quality predictive signals.")
    
    return "\n".join(insights)


import requests

def ask_dataset_question(df, query: str):
    """
    Answer a user question about the dataset using OpenRouter API.
    Context includes: Column names, types, and first 5 rows (as CSV).
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    
    # Context Building
    csv_head = df.head(5).to_csv(index=False)
    columns_info = str(df.dtypes.to_dict())
    
    # Stats context
    stats_lines = []
    for col in df.select_dtypes(include='number').columns[:5]:
        stats_lines.append(f"  {col}: mean={df[col].mean():.2f}, std={df[col].std():.2f}, min={df[col].min():.2f}, max={df[col].max():.2f}")
    stats_context = "\n".join(stats_lines)
    
    system_prompt = "You are an expert Data Analyst Assistant. Always cite specific numbers from the data."
    user_prompt = f"""
    I have a dataset with the following structure:
    
    Columns & Types:
    {columns_info}
    
    Key Statistics:
    {stats_context}
    
    First 5 Rows (Sample):
    {csv_head}
    
    User Question: {query}
    
    Answer the question based on the data structure and sample provided. 
    If the question requires aggregation that you cannot see, explain the logic to calculate it.
    Keep the answer concise, professional, and helpful. Cite specific numbers.
    """
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
            },
            data=json.dumps({
                "model": "openai/gpt-oss-120b:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            })
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Error from AI Provider: {response.text}"
            
    except Exception as e:
        return f"I encountered an error trying to answer that: {str(e)}"
