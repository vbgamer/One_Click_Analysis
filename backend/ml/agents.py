"""
Multi-Agent System for Data Insights using Microsoft AutoGen.
Upgraded with enriched statistical context for analyst-grade insights.
"""
import os
import autogen

# --- Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

config_list = [
    {
        "model": "openai/gpt-4o-mini",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.4,
    "cache_seed": None,
}


# --- Agent Definitions ---

def create_analyst_agent():
    """Creates the Data Analyst agent with professional analysis skills."""
    return autogen.AssistantAgent(
        name="DataAnalyst",
        system_message="""You are a Senior Data Analyst with 15 years of experience. Your job is to:
1.  Analyze the provided dataset statistics, column-level metrics, and ML model results.
2.  Identify patterns: Look at skewness, correlation strengths, and high-volume categories.
3.  Generate 5 key insights organized into: Data Quality, Volume Drivers, Model Performance, and Strategic Business Recommendations.
4.  Always cite SPECIFIC numbers (e.g., "Category X accounts for 45% of volume").
5.  In 'Strategic Business Recommendations', provide 3 actionable, specific decisions the company should make based on the top categories/volumes and model findings (e.g., "Invest more in X", "Target demographic Y").
Be concisely professional and always back up claims with data.""",
        llm_config=llm_config,
    )

def create_critic_agent():
    """Creates the Critic agent to refine the analysis."""
    return autogen.AssistantAgent(
        name="InsightCritic",
        system_message="""You are a Data Science Lead reviewing analyst work. Your job is to:
1.  Check if insights cite specific numbers (reject vague claims).
2.  Verify logical consistency — do the conclusions match the data?
3.  Ensure actionable recommendations are included.
4.  If insights are excellent and data-driven, reply with 'APPROVED'.
5.  If not, point out what's missing and ask for revision.
Be constructive and demand precision.""",
        llm_config=llm_config,
    )

def create_data_engineer_agent():
    """Creates a Data Engineer agent that suggests preprocessing improvements."""
    return autogen.AssistantAgent(
        name="DataEngineer",
        system_message="""You are a Data Engineer. After seeing the analyst's insights, add:
1.  Data preprocessing suggestions based on skewness/outliers (e.g., log-transform, winsorizing).
2.  Feature engineering ideas based on correlations.
3.  Data quality fixes (handling missing values, encoding strategies).
Keep suggestions brief and practical. End with 'APPROVED' if the analysis is complete.""",
        llm_config=llm_config,
    )

def create_user_proxy():
    """Creates the UserProxy agent."""
    return autogen.UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        is_termination_msg=lambda x: "APPROVED" in x.get("content", "").upper(),
        code_execution_config=False,
    )


# --- Context Building ---

def _build_agent_context(summary_stats: dict, target_col: str, model_metrics: dict) -> str:
    """Build comprehensive statistical context for agents."""
    lines = []
    
    lines.append(f"Dataset: {summary_stats.get('rows', '?')} rows × {summary_stats.get('cols', '?')} columns")
    lines.append(f"Missing: {summary_stats.get('missing_pct', 0)}% | Duplicates: {summary_stats.get('duplicate_pct', 0)}%")
    lines.append(f"Target: {target_col}")
    
    # Column statistics
    column_stats = summary_stats.get('column_stats', {})
    if column_stats:
        lines.append("\n--- Column-Level Statistics ---")
        for col, stats in list(column_stats.items())[:8]:
            lines.append(
                f"  {col}: mean={stats.get('mean')}, std={stats.get('std')}, "
                f"skew={stats.get('skewness')} ({stats.get('skew_interpretation', '')}), "
                f"outliers={stats.get('outlier_pct', 0)}%, "
                f"normal={'yes' if stats.get('is_normal') else 'no'}"
            )
    
    # Correlations
    top_corrs = summary_stats.get('top_correlations', [])
    if top_corrs:
        lines.append("\n--- Correlations ---")
        for c in top_corrs[:5]:
            lines.append(f"  {c['col_a']} ↔ {c['col_b']}: r={c['correlation']} ({c['strength']} {c['direction']})")
    
    # Categorical analysis
    cat_analysis = summary_stats.get('categorical_analysis', {})
    if cat_analysis:
        lines.append("\n--- Top Categories & Volume Drivers ---")
        for col, info in list(cat_analysis.items())[:5]:
            top_vals = [f"{k} ({v})" for k, v in list(info.get('top_values', {}).items())[:3]]
            lines.append(f"  {col}: {info.get('unique_count')} unique values. Top: {', '.join(top_vals)}")
            
    # From column_stats (if cat_analysis wasn't fully populated)
    elif column_stats:
        cat_lines_added = 0
        for col, stats in list(column_stats.items()):
            if 'top_values' in stats and stats['top_values']:
                top_items = list(stats['top_values'].items())[:3]
                top_str = ", ".join([f"{k} ({v})" for k, v in top_items])
                lines.append(f"  {col} Top Values: {top_str}")
                cat_lines_added += 1
            if cat_lines_added >= 5:
                break
    
    # Model metrics
    lines.append(f"\n--- ML Model Results ---")
    if model_metrics:
        for key in ['accuracy', 'precision', 'recall', 'f1_score', 'r2', 'rmse', 'mae', 'cv_mean']:
            if key in model_metrics:
                lines.append(f"  {key}: {model_metrics[key]}")
        best_model = model_metrics.get('best_model', 'N/A')
        lines.append(f"  Best Model: {best_model}")
    
    # Feature importance
    feat_imp = model_metrics.get('feature_importance') if model_metrics else None
    if feat_imp:
        top_feats = list(feat_imp.keys())[:5]
        lines.append(f"  Top Features: {', '.join(top_feats)}")
    
    return "\n".join(lines)


def run_agent_analysis(summary_stats: dict, target_col: str, model_metrics: dict) -> str:
    """
    Multi-agent analysis with enriched statistical context.
    """
    analyst = create_analyst_agent()
    critic = create_critic_agent()
    engineer = create_data_engineer_agent()
    user_proxy = create_user_proxy()

    groupchat = autogen.GroupChat(
        agents=[user_proxy, analyst, critic, engineer],
        messages=[],
        max_round=6,
        speaker_selection_method="round_robin",
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    context = _build_agent_context(summary_stats, target_col, model_metrics)

    task_prompt = f"""
    Analyze the following dataset and provide professional insights.
    Be SPECIFIC — cite exact numbers from the statistics below.

    {context}

    DataAnalyst, start with your analysis covering:
    1. Data Quality (missing data, outliers, duplicates)
    2. Statistical Patterns (distributions, correlations, anomalies)
    3. Model Evaluation (accuracy, precision/recall balance, cross-validation stability)
    4. Actionable Recommendations (what to do next, features to investigate)
    """

    try:
        user_proxy.initiate_chat(manager, message=task_prompt)

        # Extract the best insights from conversation
        insights = "Agent Analysis Completed."
        for msg in reversed(groupchat.messages):
            if msg.get("name") in ["DataAnalyst", "DataEngineer"] and msg.get("content"):
                content = msg["content"]
                if "APPROVED" not in content.upper():
                    insights = content
                    break

        return f"**🤖 AI Multi-Agent Analysis (Analyst + Engineer + Critic):**\n\n{insights}"

    except Exception as e:
        print(f"Agent Analysis Error: {e}")
        return f"Agent analysis encountered an error: {str(e)}. Falling back may be required."
