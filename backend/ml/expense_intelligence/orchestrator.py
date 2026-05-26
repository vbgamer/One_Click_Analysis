from __future__ import annotations

import pandas as pd

from .anomaly import detect_anomalies
from .features import build_expense_features
from .forecasting import forecast_daily_spend
from .preprocessing import preprocess_expenses
from .recommendations import generate_recommendations
from .settlement import optimize_settlements


def run_expense_intelligence(df: pd.DataFrame) -> dict:
    preprocessing = preprocess_expenses(df)
    clean = preprocessing["data"]
    features = build_expense_features(clean)
    anomalies = detect_anomalies(clean)
    forecast = forecast_daily_spend(clean)
    settlement = optimize_settlements(clean)
    recommendations = generate_recommendations(clean, features["behavior"], anomalies, forecast)

    return {
        "quality": preprocessing["quality"],
        "schema": preprocessing["schema"],
        "behavioral_intelligence": features["behavior"],
        "daily_features": features["daily_features"][-60:],
        "category_features": features["category_features"],
        "payer_features": features["payer_features"],
        "forecasting": forecast,
        "anomaly_detection": anomalies,
        "settlement_optimization": settlement,
        "recommendations": recommendations,
        "xai": {
            "principle": "Every prediction, anomaly, and recommendation includes source features, validation metrics, or explicit limitations.",
            "leakage_controls": [
                "Forecast validation uses time-ordered split.",
                "Recommendations are generated from historical aggregates only.",
                "No target-derived features are used for forecast labels.",
            ],
        },
    }
