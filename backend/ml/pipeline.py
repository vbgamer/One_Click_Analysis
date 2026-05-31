"""
pipeline.py — Main AI orchestrator for Autonomous Data Intelligence Platform (ADIP).

Functions
---------
run_full_analysis    : Orchestrate the entire ML pipeline end-to-end.
run_analytical_query : Answer a natural language query using saved results.
"""

import json
import os
import traceback
from datetime import datetime

import pandas as pd

from . import etl
from . import forecasting
from . import anomaly
from . import nlp
from . import recommendations
from . import settlement as settlement_mod
from . import explainability
from . import conversational

# ---------------------------------------------------------------------------
# ADIP New Modules (imported with graceful fallback)
# ---------------------------------------------------------------------------

def _try_import(module_name):
    try:
        import importlib
        return importlib.import_module(f".{module_name}", package="ml")
    except Exception as e:
        print(f"[pipeline] Could not import ml.{module_name}: {e}")
        return None

_evidence_engine  = _try_import("evidence_engine")
_auditor          = _try_import("auditor")
_root_cause       = _try_import("root_cause_engine")
_kpi_engine       = _try_import("kpi_engine")
_hypothesis_engine = _try_import("hypothesis_engine")
_insight_ranker   = _try_import("insight_ranker")
_self_critique    = _try_import("self_critique")
_lineage          = _try_import("lineage")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_HERE)
_RESULTS_DIR = os.path.join(_BACKEND_DIR, "static", "ai_results")


def _ensure_results_dir():
    os.makedirs(_RESULTS_DIR, exist_ok=True)


def _result_path(job_id: str) -> str:
    _ensure_results_dir()
    return os.path.join(_RESULTS_DIR, f"{job_id}.json")


def _safe_run(step_name: str, fn, *args, **kwargs):
    """Run *fn* with *args*/**kwargs*, isolating exceptions."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[pipeline] Step '{step_name}' failed: {exc}\n{tb}")
        return {"available": False, "reason": str(exc)}


def _json_safe(obj):
    """Recursively make an object JSON-serialisable."""
    import numpy as np

    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (pd.DataFrame,)):
        return obj.head(100).to_dict(orient="records")
    if isinstance(obj, (pd.Series,)):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime)):
        return str(obj)
    if isinstance(obj, (pd.Period,)):
        return str(obj)
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if hasattr(obj, "item"):  # numpy scalar
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_full_analysis(df: pd.DataFrame, job_id: str) -> dict:
    """Orchestrate the entire ADIP pipeline and return structured results.

    Steps 1-18 are the original analysis steps.
    Steps 19-26 are the new ADIP intelligence layers.
    """
    started_at = datetime.utcnow().isoformat()
    results: dict = {"job_id": job_id, "started_at": started_at, "platform": "ADIP v1.0"}

    # ------------------------------------------------------------------
    # PHASE 1: Data Foundation
    # ------------------------------------------------------------------

    schema = _safe_run("infer_schema", etl.infer_schema, df)
    if not isinstance(schema, dict):
        schema = {}
    results["schema"] = schema

    quality_score = _safe_run("compute_data_quality_score", etl.compute_data_quality_score, df)
    results["quality_score"] = quality_score

    normalise_result = _safe_run("normalize_entities", etl.normalize_entities, df, schema)
    if isinstance(normalise_result, tuple) and len(normalise_result) == 2:
        df_clean, entity_changes = normalise_result
    else:
        df_clean = df.copy()
        entity_changes = {}
    results["entity_changes"] = entity_changes

    results["leakage"] = []

    # ------------------------------------------------------------------
    # PHASE 2: Core Analytics (Original Steps)
    # ------------------------------------------------------------------

    anomalies = _safe_run("detect_anomalies", anomaly.detect_anomalies, df_clean, schema)
    results["anomalies"] = anomalies

    behavioral = _safe_run("detect_behavioral_anomalies", anomaly.detect_behavioral_anomalies, df_clean, schema)
    results["behavioral_anomalies"] = behavioral

    forecast = _safe_run("forecast_expenses", forecasting.forecast_expenses, df_clean, schema)
    results["forecast"] = forecast

    category_forecast = _safe_run("forecast_by_category", forecasting.forecast_by_category, df_clean, schema)
    results["category_forecast"] = category_forecast

    burn_rate = _safe_run("compute_burn_rate", forecasting.compute_burn_rate, df_clean, schema)
    results["burn_rate"] = burn_rate

    cat_result = _safe_run("categorize_expenses", nlp.categorize_expenses, df_clean, schema)
    if isinstance(cat_result, dict) and cat_result.get("available"):
        df_clean = cat_result.get("df_with_categories", df_clean)
        results["categories"] = {
            "available": True,
            "method": cat_result.get("method"),
            "category_summary": cat_result.get("category_summary"),
        }
    else:
        results["categories"] = cat_result

    merchants = _safe_run("extract_merchants", nlp.extract_merchants, df_clean, schema)
    results["merchants"] = merchants

    settlement = _safe_run("optimize_settlement", settlement_mod.optimize_settlement, df_clean, schema)
    results["settlement"] = settlement

    payer_network = _safe_run("build_payer_network", settlement_mod.build_payer_network, df_clean, schema)
    results["payer_network"] = payer_network

    fairness = _safe_run("compute_contribution_fairness", settlement_mod.compute_contribution_fairness, df_clean, schema)
    results["fairness"] = fairness

    recs = _safe_run("generate_recommendations", recommendations.generate_recommendations, df_clean, schema, anomalies, forecast)
    results["recommendations"] = recs

    opt_score = _safe_run("compute_optimization_score", recommendations.compute_optimization_score, df_clean, schema)
    results["optimization_score"] = opt_score

    confidence = _safe_run("compute_confidence_score", explainability.compute_confidence_score, df_clean, schema, results)
    results["confidence"] = confidence

    model_card = _safe_run("generate_model_card", explainability.generate_model_card, df_clean, schema, results)
    results["model_card"] = model_card

    # ------------------------------------------------------------------
    # PHASE 3: ADIP Intelligence Layer (New Modules)
    # ------------------------------------------------------------------

    # Step 19: KPI Discovery
    if _kpi_engine:
        kpis = _safe_run("discover_kpis", _kpi_engine.discover_kpis, df_clean, schema)
        results["kpis"] = kpis
        print(f"[pipeline] KPIs discovered: {kpis.get('total_kpis', 0)} ({kpis.get('domain', 'unknown')} domain)")

    # Step 20: Hypothesis Generation & Testing
    if _hypothesis_engine:
        hypotheses = _safe_run("generate_and_test_hypotheses", _hypothesis_engine.generate_and_test_hypotheses, df_clean, schema)
        results["hypotheses"] = hypotheses
        print(f"[pipeline] Hypotheses: {hypotheses.get('verified', 0)} verified, {hypotheses.get('rejected', 0)} rejected")

    # Step 21: Root Cause Analysis
    if _root_cause:
        root_cause = _safe_run("analyze_root_causes", _root_cause.analyze_root_causes, df_clean, schema, results)
        results["root_cause"] = root_cause
        print(f"[pipeline] Root cause: {root_cause.get('total_analyses', 0)} analyses")

    # Step 22: Self-Critique
    if _self_critique:
        critique = _safe_run("generate_self_critique", _self_critique.generate_self_critique, df_clean, schema, results)
        results["self_critique"] = critique
        print(f"[pipeline] Self-critique trust score: {critique.get('trust_score', 0):.1f}/100")

    # Step 23: Auditor Agent
    if _auditor:
        audit_report = _safe_run("audit_results", _auditor.audit_results, results, df_clean, schema)
        results["audit_report"] = audit_report
        print(f"[pipeline] Audit: {audit_report.get('overall_status', 'UNKNOWN')} (score {audit_report.get('score', 0):.1f})")

    # Step 24: Data Lineage
    if _lineage:
        lineage = _safe_run("build_lineage", _lineage.build_lineage, df_clean, schema, results)
        results["lineage"] = lineage
        print(f"[pipeline] Lineage: {lineage.get('total_tracked', 0)} entries tracked")

    # Step 25: Insight Ranking (must run after all other modules)
    if _insight_ranker:
        ranked = _safe_run("rank_insights", _insight_ranker.rank_insights, results, df_clean, schema)
        results["ranked_insights"] = ranked
        print(f"[pipeline] Top insights ranked: {len(ranked.get('top_insights', []))}")

    # Step 26: Summary block for frontend KPI cards
    if "summary" not in results:
        try:
            amount_col = schema.get("amount_col")
            total_amount = None
            if amount_col and amount_col in df_clean.columns:
                total_amount = float(pd.to_numeric(df_clean[amount_col], errors="coerce").sum())
            results["summary"] = {
                "rows": len(df_clean),
                "cols": df_clean.shape[1],
                "total_amount": total_amount,
            }
        except Exception:
            results["summary"] = {"rows": len(df_clean), "cols": df_clean.shape[1], "total_amount": None}

    # Normalize key names for frontend compatibility
    if "data_quality_score" not in results:
        qs = results.get("quality_score", {})
        results["data_quality_score"] = qs.get("overall", None) if isinstance(qs, dict) else qs

    if "confidence_score" not in results:
        cf = results.get("confidence", {})
        results["confidence_score"] = cf.get("overall", None) if isinstance(cf, dict) else cf

    # ------------------------------------------------------------------
    # Finalise
    # ------------------------------------------------------------------
    results["completed_at"]    = datetime.utcnow().isoformat()
    results["n_rows_analysed"] = int(len(df_clean))
    results["n_cols"]          = int(df_clean.shape[1])

    # Save to disk
    try:
        safe_results = _json_safe(results)
        result_path = _result_path(job_id)
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(safe_results, f, ensure_ascii=False, indent=2)
        print(f"[pipeline] Results saved to {result_path}")
    except Exception as e:
        print(f"[pipeline] Failed to save results: {e}")

    return _json_safe(results)


def run_analytical_query(
    job_id: str,
    question: str,
    df: pd.DataFrame,
    schema: dict,
    conversation_history: list | None = None,
) -> dict:
    """Answer a natural language question using saved analysis results."""
    analysis_results: dict = {}
    result_path = _result_path(job_id)
    if os.path.exists(result_path):
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                analysis_results = json.load(f)
        except Exception as e:
            print(f"[pipeline] Could not load saved results for {job_id}: {e}")

    return conversational.answer_question(
        question=question,
        df=df,
        schema=schema,
        analysis_results=analysis_results,
        conversation_history=conversation_history,
    )






def _ensure_results_dir():
    os.makedirs(_RESULTS_DIR, exist_ok=True)


def _result_path(job_id: str) -> str:
    _ensure_results_dir()
    return os.path.join(_RESULTS_DIR, f"{job_id}.json")


def _safe_run(step_name: str, fn, *args, **kwargs):
    """Run *fn* with *args*/**kwargs*, isolating exceptions.

    Returns the function result on success, or a dict with
    ``{"available": False, "reason": ...}`` on failure.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[pipeline] Step '{step_name}' failed: {exc}\n{tb}")
        return {"available": False, "reason": str(exc)}


def _json_safe(obj):
    """Recursively make an object JSON-serialisable."""
    import numpy as np  # local import to avoid circular dependency issues

    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (pd.DataFrame,)):
        return obj.head(100).to_dict(orient="records")
    if isinstance(obj, (pd.Series,)):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime)):
        return str(obj)
    if isinstance(obj, (pd.Period,)):
        return str(obj)
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if hasattr(obj, "item"):  # numpy scalar
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_full_analysis(df: pd.DataFrame, job_id: str) -> dict:
    """Orchestrate the entire AI pipeline and return structured results.

    Steps are run sequentially with isolated try/except blocks so a single
    step failure never crashes the whole pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        Raw (or lightly cleaned) expense dataframe.
    job_id : str
        Unique identifier for this analysis job (used for file naming).

    Returns
    -------
    dict
        Complete structured JSON-serialisable results dict.
    """
    started_at = datetime.utcnow().isoformat()
    results: dict = {"job_id": job_id, "started_at": started_at}

    # ------------------------------------------------------------------
    # Step 1: Schema detection
    # ------------------------------------------------------------------
    schema = _safe_run("infer_schema", etl.infer_schema, df)
    if not isinstance(schema, dict):
        schema = {}
    results["schema"] = schema

    # ------------------------------------------------------------------
    # Step 2: Data quality score
    # ------------------------------------------------------------------
    quality_score = _safe_run(
        "compute_data_quality_score", etl.compute_data_quality_score, df
    )
    results["quality_score"] = quality_score

    # ------------------------------------------------------------------
    # Step 3: Entity normalisation
    # ------------------------------------------------------------------
    normalise_result = _safe_run("normalize_entities", etl.normalize_entities, df, schema)
    if isinstance(normalise_result, tuple) and len(normalise_result) == 2:
        df_clean, entity_changes = normalise_result
    else:
        df_clean = df.copy()
        entity_changes = {}
    results["entity_changes"] = entity_changes

    # ------------------------------------------------------------------
    # Step 4: Leakage (skipped — no supervised target)
    # ------------------------------------------------------------------
    leakage: list = []
    results["leakage"] = leakage

    # ------------------------------------------------------------------
    # Step 5: Anomaly detection
    # ------------------------------------------------------------------
    anomalies = _safe_run(
        "detect_anomalies", anomaly.detect_anomalies, df_clean, schema
    )
    results["anomalies"] = anomalies

    # ------------------------------------------------------------------
    # Step 6: Behavioural anomalies
    # ------------------------------------------------------------------
    behavioral = _safe_run(
        "detect_behavioral_anomalies",
        anomaly.detect_behavioral_anomalies,
        df_clean,
        schema,
    )
    results["behavioral_anomalies"] = behavioral

    # ------------------------------------------------------------------
    # Step 7: Expense forecast
    # ------------------------------------------------------------------
    forecast = _safe_run(
        "forecast_expenses", forecasting.forecast_expenses, df_clean, schema
    )
    results["forecast"] = forecast

    # ------------------------------------------------------------------
    # Step 8: Category forecast
    # ------------------------------------------------------------------
    category_forecast = _safe_run(
        "forecast_by_category", forecasting.forecast_by_category, df_clean, schema
    )
    results["category_forecast"] = category_forecast

    # ------------------------------------------------------------------
    # Step 9: Burn rate
    # ------------------------------------------------------------------
    burn_rate = _safe_run(
        "compute_burn_rate", forecasting.compute_burn_rate, df_clean, schema
    )
    results["burn_rate"] = burn_rate

    # ------------------------------------------------------------------
    # Step 10: NLP categorisation
    # ------------------------------------------------------------------
    cat_result = _safe_run(
        "categorize_expenses", nlp.categorize_expenses, df_clean, schema
    )
    if isinstance(cat_result, dict) and cat_result.get("available"):
        df_clean = cat_result.get("df_with_categories", df_clean)
        results["categories"] = {
            "available": True,
            "method": cat_result.get("method"),
            "category_summary": cat_result.get("category_summary"),
        }
    else:
        results["categories"] = cat_result

    # ------------------------------------------------------------------
    # Step 11: Merchant extraction
    # ------------------------------------------------------------------
    merchants = _safe_run(
        "extract_merchants", nlp.extract_merchants, df_clean, schema
    )
    results["merchants"] = merchants

    # ------------------------------------------------------------------
    # Step 12: Settlement optimisation
    # ------------------------------------------------------------------
    settlement = _safe_run(
        "optimize_settlement", settlement_mod.optimize_settlement, df_clean, schema
    )
    results["settlement"] = settlement

    # ------------------------------------------------------------------
    # Step 13: Payer network
    # ------------------------------------------------------------------
    payer_network = _safe_run(
        "build_payer_network", settlement_mod.build_payer_network, df_clean, schema
    )
    results["payer_network"] = payer_network

    # ------------------------------------------------------------------
    # Step 14: Contribution fairness
    # ------------------------------------------------------------------
    fairness = _safe_run(
        "compute_contribution_fairness",
        settlement_mod.compute_contribution_fairness,
        df_clean,
        schema,
    )
    results["fairness"] = fairness

    # ------------------------------------------------------------------
    # Step 15: Recommendations
    # ------------------------------------------------------------------
    recs = _safe_run(
        "generate_recommendations",
        recommendations.generate_recommendations,
        df_clean,
        schema,
        anomalies,
        forecast,
    )
    results["recommendations"] = recs

    # ------------------------------------------------------------------
    # Step 16: Optimisation score
    # ------------------------------------------------------------------
    opt_score = _safe_run(
        "compute_optimization_score",
        recommendations.compute_optimization_score,
        df_clean,
        schema,
    )
    results["optimization_score"] = opt_score

    # ------------------------------------------------------------------
    # Step 17: Overall confidence
    # ------------------------------------------------------------------
    confidence = _safe_run(
        "compute_confidence_score",
        explainability.compute_confidence_score,
        df_clean,
        schema,
        results,
    )
    results["confidence"] = confidence

    # ------------------------------------------------------------------
    # Step 18: Model card
    # ------------------------------------------------------------------
    model_card = _safe_run(
        "generate_model_card",
        explainability.generate_model_card,
        df_clean,
        schema,
        results,
    )
    results["model_card"] = model_card

    # ------------------------------------------------------------------
    # Finalise
    # ------------------------------------------------------------------
    results["completed_at"] = datetime.utcnow().isoformat()
    results["n_rows_analysed"] = int(len(df_clean))
    results["n_cols"] = int(df_clean.shape[1])

    # Save to disk
    try:
        safe_results = _json_safe(results)
        result_path = _result_path(job_id)
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(safe_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[pipeline] Failed to save results: {e}")

    return _json_safe(results)


def run_analytical_query(
    job_id: str,
    question: str,
    df: pd.DataFrame,
    schema: dict,
    conversation_history: list | None = None,
) -> dict:
    """Answer a natural language question using saved analysis results.

    Parameters
    ----------
    job_id : str
        Job identifier used to load previously saved analysis results.
    question : str
        User's natural language question.
    df : pd.DataFrame
        The expense dataframe (needed for analytical queries).
    schema : dict
        Column schema from ``etl.infer_schema``.
    conversation_history : list, optional
        Prior conversation turns.

    Returns
    -------
    dict
        Answer dict from :func:`conversational.answer_question`.
    """
    # Load saved analysis results
    analysis_results: dict = {}
    result_path = _result_path(job_id)
    if os.path.exists(result_path):
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                analysis_results = json.load(f)
        except Exception as e:
            print(f"[pipeline] Could not load saved results for {job_id}: {e}")

    return conversational.answer_question(
        question=question,
        df=df,
        schema=schema,
        analysis_results=analysis_results,
        conversation_history=conversation_history,
    )
