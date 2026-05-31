"""
conversational.py — Conversational AI engine for Expense Intelligence System.

Functions
---------
build_context          : Build a rich LLM context from expense data.
answer_question        : Answer a natural language question about the data.
detect_query_intent    : Classify question intent and extract parameters.
handle_analytical_query : Handle common queries directly without LLM.
"""

import json
import os
import re

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "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",
)
LLM_MODEL = "openai/gpt-oss-120b:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

INTENT_PATTERNS: dict = {
    "spending_query": [
        r"how much",
        r"total spend",
        r"spent on",
        r"spending on",
        r"expenses for",
        r"amount for",
        r"cost of",
    ],
    "comparison": [
        r"who spend",
        r"who paid",
        r"compare",
        r"vs",
        r"versus",
        r"highest",
        r"lowest",
        r"most",
        r"least",
    ],
    "prediction": [
        r"predict",
        r"forecast",
        r"next month",
        r"next week",
        r"future",
        r"will.*spend",
        r"expect",
        r"projection",
    ],
    "anomaly": [
        r"anomal",
        r"unusual",
        r"suspicious",
        r"outlier",
        r"weird",
        r"strange",
        r"fraud",
    ],
    "recommendation": [
        r"recommend",
        r"suggest",
        r"advice",
        r"improve",
        r"save",
        r"reduce",
        r"tips",
        r"optimise",
        r"optimize",
    ],
    "settlement": [
        r"settle",
        r"owe",
        r"owes",
        r"payment plan",
        r"who.*pay",
        r"split",
        r"balance",
        r"reimburse",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_col(df: pd.DataFrame, schema: dict, key: str) -> str | None:
    col = schema.get(key)
    return col if col and col in df.columns else None


def _safe_json_serialise(obj):
    """Recursively convert numpy/pandas types to native Python for JSON."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _safe_json_serialise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json_serialise(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_context(
    df: pd.DataFrame,
    schema: dict,
    analysis_results: dict,
) -> str:
    """Build a rich context string for the LLM.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    analysis_results : dict
        Aggregated pipeline output.

    Returns
    -------
    str
        Context paragraph summarising the dataset.
    """
    try:
        n_rows = len(df)
        amount_col = _get_col(df, schema, "amount_col")
        payer_col = _get_col(df, schema, "payer_col")
        category_col = _get_col(df, schema, "category_col")
        date_col = _get_col(df, schema, "date_col")

        lines = [
            f"This expense dataset has {n_rows} transactions.",
        ]

        if amount_col:
            amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
            lines.append(
                f"Total spending: ₹{amounts.sum():,.0f}. "
                f"Average transaction: ₹{amounts.mean():,.0f}. "
                f"Largest: ₹{amounts.max():,.0f}."
            )

        if payer_col:
            payers = df[payer_col].dropna().unique().tolist()
            payer_totals = (
                pd.to_numeric(df[amount_col], errors="coerce")
                .groupby(df[payer_col])
                .sum()
                if amount_col
                else None
            )
            if payer_totals is not None:
                top_payer = payer_totals.idxmax()
                lines.append(
                    f"Payers: {', '.join(str(p) for p in payers)}. "
                    f"Top spender: {top_payer} (₹{float(payer_totals.max()):,.0f})."
                )

        if category_col:
            cat_counts = df[category_col].value_counts().head(5)
            cat_str = ", ".join(f"{c} ({n})" for c, n in cat_counts.items())
            lines.append(f"Top categories: {cat_str}.")

        if date_col:
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if len(dates) > 0:
                lines.append(
                    f"Date range: {dates.min().date()} to {dates.max().date()}."
                )

        # Key findings from analysis
        anomalies = analysis_results.get("anomalies", {})
        if anomalies and anomalies.get("available") and anomalies.get("anomaly_count", 0) > 0:
            lines.append(
                f"Anomaly detection: {anomalies['anomaly_count']} suspicious transactions "
                f"({anomalies.get('anomaly_rate_pct', 0):.1f}% of total)."
            )

        forecast = analysis_results.get("forecast", {})
        if forecast and forecast.get("available"):
            trend = forecast.get("trend_direction", "stable")
            next_pred = forecast.get("next_month_prediction", 0)
            lines.append(
                f"Forecast: spending trend is {trend}. "
                f"Next month estimate: ₹{next_pred:,.0f}."
            )

        return " ".join(lines)

    except Exception as e:
        return f"Expense dataset with {len(df)} transactions. (Context error: {e})"


def detect_query_intent(question: str) -> dict:
    """Classify a question into one of the known intents.

    Parameters
    ----------
    question : str
        Natural language question.

    Returns
    -------
    dict
        Keys: ``intent`` (str), ``params`` (dict), ``confidence`` (float).
    """
    question_lower = question.lower()
    intent_scores: dict = {intent: 0 for intent in INTENT_PATTERNS}

    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, question_lower):
                intent_scores[intent] += 1

    best_intent = max(intent_scores, key=lambda i: intent_scores[i])
    best_score = intent_scores[best_intent]

    if best_score == 0:
        best_intent = "spending_query"
        confidence = 0.3
    else:
        total = sum(intent_scores.values())
        confidence = round(best_score / max(total, 1), 2)

    # Extract parameters from question
    params: dict = {}

    # Time period extraction
    month_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december|\bjan\b|\bfeb\b|\bmar\b|\bapr\b|\bjun\b|\bjul\b|\baug\b|\bsep\b|\boct\b|\bnov\b|\bdec\b)",
        question_lower,
    )
    if month_match:
        params["month"] = month_match.group(1)

    # Person/payer extraction (very basic — any capitalized word preceded by name-like context)
    name_match = re.findall(r"\b[A-Z][a-z]{2,}\b", question)
    if name_match:
        params["mentioned_names"] = name_match

    # Category extraction
    from . import nlp as _nlp_mod
    for cat in _nlp_mod.CATEGORIES:
        if cat.lower() in question_lower:
            params["category"] = cat
            break

    return {"intent": best_intent, "params": params, "confidence": confidence}


def handle_analytical_query(
    intent: str,
    params: dict,
    df: pd.DataFrame,
    schema: dict,
    analysis_results: dict,
) -> dict | None:
    """Handle common analytical queries directly without an LLM.

    Returns ``None`` if the query cannot be handled analytically.

    Parameters
    ----------
    intent : str
        Intent string from :func:`detect_query_intent`.
    params : dict
        Extracted parameters.
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    analysis_results : dict
        Aggregated pipeline results.

    Returns
    -------
    dict or None
        Answer dict with ``answer``, ``data``, ``visualization``,
        ``confidence``; or ``None``.
    """
    try:
        amount_col = _get_col(df, schema, "amount_col")
        payer_col = _get_col(df, schema, "payer_col")
        category_col = _get_col(df, schema, "category_col")
        date_col = _get_col(df, schema, "date_col")

        if amount_col:
            df_work = df.copy()
            df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
        else:
            return None

        # --- spending_query ---
        if intent == "spending_query":
            cat = params.get("category")
            month = params.get("month")
            subset = df_work.copy()

            if cat and category_col:
                subset = subset[subset[category_col].str.lower() == cat.lower()]
            if month and date_col:
                dates = pd.to_datetime(subset[date_col], errors="coerce")
                subset = subset[dates.dt.month_name().str.lower() == month.lower()]

            total = float(subset[amount_col].sum())
            count = len(subset)

            filter_desc = ""
            if cat:
                filter_desc += f" on {cat}"
            if month:
                filter_desc += f" in {month.title()}"

            answer = f"Total spending{filter_desc}: ₹{total:,.0f} across {count} transactions."
            return {
                "answer": answer,
                "data": {"total": total, "count": count, "filters": params},
                "visualization": None,
                "confidence": 0.95,
            }

        # --- comparison (who spends most) ---
        elif intent == "comparison" and payer_col:
            payer_totals = df_work.groupby(payer_col)[amount_col].sum().sort_values(ascending=False)
            top_payer = str(payer_totals.idxmax())
            top_amount = float(payer_totals.max())

            rows = [
                {"payer": str(p), "total": round(float(v), 2)}
                for p, v in payer_totals.items()
            ]
            answer = (
                f"{top_payer} has the highest spending at ₹{top_amount:,.0f}. "
                + " | ".join(f"{r['payer']}: ₹{r['total']:,.0f}" for r in rows)
            )
            return {
                "answer": answer,
                "data": {"payer_totals": rows},
                "visualization": {
                    "type": "bar",
                    "x": [r["payer"] for r in rows],
                    "y": [r["total"] for r in rows],
                    "title": "Spending by Payer",
                },
                "confidence": 0.95,
            }

        # --- prediction ---
        elif intent == "prediction":
            forecast = analysis_results.get("forecast", {})
            if forecast and forecast.get("available"):
                next_month = forecast.get("next_month_prediction", 0)
                trend = forecast.get("trend_direction", "stable")
                monthly_avg = forecast.get("monthly_avg", 0)
                answer = (
                    f"Based on current trends ({trend}), next month's spending is "
                    f"projected at ₹{next_month:,.0f} (average: ₹{monthly_avg:,.0f})."
                )
                return {
                    "answer": answer,
                    "data": {
                        "next_month_prediction": next_month,
                        "trend": trend,
                        "monthly_avg": monthly_avg,
                    },
                    "visualization": forecast.get("plotly_data"),
                    "confidence": 0.75,
                }
            return None

        # --- anomaly ---
        elif intent == "anomaly":
            anomalies = analysis_results.get("anomalies", {})
            if anomalies and anomalies.get("available"):
                count = anomalies.get("anomaly_count", 0)
                rate = anomalies.get("anomaly_rate_pct", 0)
                total_anomalous = anomalies.get("total_anomalous_amount", 0)
                answer = (
                    f"Found {count} anomalous transactions ({rate:.1f}% of all expenses). "
                    f"Total anomalous amount: ₹{total_anomalous:,.0f}."
                )
                return {
                    "answer": answer,
                    "data": {
                        "count": count,
                        "rate_pct": rate,
                        "total_amount": total_anomalous,
                    },
                    "visualization": anomalies.get("plotly_heatmap_data"),
                    "confidence": 0.88,
                }
            return None

        # --- settlement ---
        elif intent == "settlement":
            settlement = analysis_results.get("settlement", {})
            if settlement and settlement.get("available"):
                txns = settlement.get("optimal_transactions", [])
                answer_parts = [
                    f"{t['payer']} → {t['payee']}: ₹{t['amount']:,.0f}"
                    for t in txns
                ]
                answer = (
                    f"Optimal settlement plan ({len(txns)} transactions): "
                    + "; ".join(answer_parts)
                )
                return {
                    "answer": answer,
                    "data": {"transactions": txns},
                    "visualization": None,
                    "confidence": 0.98,
                }
            return None

    except Exception:
        pass

    return None


def answer_question(
    question: str,
    df: pd.DataFrame,
    schema: dict,
    analysis_results: dict,
    conversation_history: list | None = None,
) -> dict:
    """Answer a natural language question about the expense data.

    First tries to compute the answer analytically; falls back to the
    OpenRouter LLM API for complex questions.

    Parameters
    ----------
    question : str
        User's question.
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    analysis_results : dict
        Aggregated pipeline output.
    conversation_history : list, optional
        Previous turns as [{"role": "user"|"assistant", "content": str}].

    Returns
    -------
    dict
        Keys: ``answer``, ``data``, ``visualization``, ``confidence``,
        ``method`` ("analytical" | "llm" | "fallback").
    """
    if conversation_history is None:
        conversation_history = []

    # Step 1: Detect intent
    intent_result = detect_query_intent(question)
    intent = intent_result["intent"]
    params = intent_result["params"]

    # Step 2: Try analytical handling
    try:
        analytical = handle_analytical_query(intent, params, df, schema, analysis_results)
        if analytical is not None:
            analytical["method"] = "analytical"
            analytical["intent"] = intent
            return analytical
    except Exception:
        pass

    # Step 3: Fall back to LLM
    try:
        context = build_context(df, schema, analysis_results)
        system_prompt = (
            "You are an expert financial analyst for an Expense Intelligence System. "
            "Answer the user's question about their expense data concisely and accurately. "
            "Use ₹ for amounts. Keep answers under 150 words unless detail is needed.\n\n"
            f"Dataset context: {context}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in conversation_history[-6:]:  # Last 3 exchanges
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": question})

        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://expense-intelligence.app",
                "X-Title": "Expense Intelligence System",
            },
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.3,
            },
            timeout=30,
        )

        if response.status_code == 200:
            resp_json = response.json()
            llm_answer = resp_json["choices"][0]["message"]["content"].strip()
            return {
                "answer": llm_answer,
                "data": {},
                "visualization": None,
                "confidence": 0.65,
                "method": "llm",
                "intent": intent,
            }
        else:
            raise ValueError(f"LLM API error: {response.status_code}")

    except Exception as e:
        # Final fallback
        return {
            "answer": (
                f"I can see you're asking about {intent.replace('_', ' ')}. "
                f"The dataset has {len(df)} transactions. "
                f"Unfortunately I couldn't compute a precise answer: {e}"
            ),
            "data": {},
            "visualization": None,
            "confidence": 0.2,
            "method": "fallback",
            "intent": intent,
        }
