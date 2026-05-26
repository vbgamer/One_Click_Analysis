from __future__ import annotations

import numpy as np
import pandas as pd


def build_expense_features(df: pd.DataFrame) -> dict:
    work = df.copy()
    if "expense_date" in work:
        work = work.sort_values("expense_date")
        work["day_of_week"] = work["expense_date"].dt.day_name()
        work["is_weekend"] = work["expense_date"].dt.dayofweek.isin([5, 6])
        work["month"] = work["expense_date"].dt.to_period("M").astype(str)
    else:
        work["is_weekend"] = False

    daily = (
        work.dropna(subset=["expense_date"])
        .groupby(work["expense_date"].dt.date)["amount"]
        .sum()
        .rename("daily_total")
        .reset_index()
    )
    if not daily.empty:
        daily["rolling_7d_avg"] = daily["daily_total"].rolling(7, min_periods=2).mean()
        daily["trend_velocity"] = daily["daily_total"].diff()

    category_spend = work.groupby("category")["amount"].agg(["sum", "count", "mean"]).sort_values("sum", ascending=False)
    payer_spend = work.groupby("payer")["amount"].agg(["sum", "count", "mean"]).sort_values("sum", ascending=False)

    total = float(work["amount"].sum()) if len(work) else 0.0
    food = float(category_spend.loc["food", "sum"]) if "food" in category_spend.index else 0.0
    travel = float(category_spend.loc["travel", "sum"]) if "travel" in category_spend.index else 0.0
    transport = float(category_spend.loc["transport", "sum"]) if "transport" in category_spend.index else 0.0

    volatility = float(work["amount"].std() / work["amount"].mean()) if work["amount"].mean() else 0.0
    weekend_ratio = float(work.loc[work["is_weekend"], "amount"].sum() / total) if total else 0.0

    behavior = {
        "total_spend": round(total, 2),
        "average_transaction": round(float(work["amount"].mean()), 2) if len(work) else 0,
        "spending_volatility_score": round(volatility, 3),
        "weekend_spend_ratio": round(weekend_ratio, 3),
        "travel_transport_to_food_ratio": round((travel + transport) / food, 3) if food else None,
        "top_categories": category_spend.head(8).reset_index().to_dict(orient="records"),
        "payer_contribution_ratios": (
            (payer_spend["sum"] / total).round(3).reset_index(name="ratio").to_dict(orient="records")
            if total else []
        ),
    }

    return {
        "transaction_features": work,
        "daily_features": daily.to_dict(orient="records"),
        "category_features": category_spend.reset_index().to_dict(orient="records"),
        "payer_features": payer_spend.reset_index().to_dict(orient="records"),
        "behavior": behavior,
    }
