from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def _mape(y_true, y_pred) -> float | None:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mask = y_true != 0
    if not mask.any():
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def forecast_daily_spend(df: pd.DataFrame, horizon_days: int = 30) -> dict:
    dated = df.dropna(subset=["expense_date"]).copy()
    if dated.empty or dated["expense_date"].nunique() < 10:
        return {
            "status": "insufficient_data",
            "message": "At least 10 distinct expense dates are required for a reliable forecast.",
            "forecast": [],
            "validation": {},
        }

    daily = dated.groupby(dated["expense_date"].dt.date)["amount"].sum().reset_index()
    daily.columns = ["date", "amount"]
    daily["date"] = pd.to_datetime(daily["date"])
    full_dates = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    daily = daily.set_index("date").reindex(full_dates, fill_value=0).rename_axis("date").reset_index()

    daily["t"] = np.arange(len(daily))
    daily["dow"] = daily["date"].dt.dayofweek
    daily["month"] = daily["date"].dt.month
    daily["lag_1"] = daily["amount"].shift(1).fillna(0)
    daily["lag_7"] = daily["amount"].shift(7).fillna(0)
    daily["rolling_7"] = daily["amount"].rolling(7, min_periods=1).mean()

    feature_cols = ["t", "dow", "month", "lag_1", "lag_7", "rolling_7"]
    split = max(1, int(len(daily) * 0.8))
    train, test = daily.iloc[:split], daily.iloc[split:]
    if test.empty:
        train, test = daily.iloc[:-3], daily.iloc[-3:]

    model = RandomForestRegressor(n_estimators=150, random_state=42, min_samples_leaf=2)
    model.fit(train[feature_cols], train["amount"])
    preds = model.predict(test[feature_cols])
    validation = {
        "mae": round(float(mean_absolute_error(test["amount"], preds)), 2),
        "rmse": round(float(mean_squared_error(test["amount"], preds) ** 0.5), 2),
        "mape": round(_mape(test["amount"], preds), 2) if _mape(test["amount"], preds) is not None else None,
        "split": "time_ordered_80_20",
        "limitations": "Short or irregular histories increase uncertainty. Forecasts are directional, not guarantees.",
    }

    history = daily.copy()
    future_rows = []
    for i in range(horizon_days):
        next_date = history["date"].max() + pd.Timedelta(days=1)
        row = {
            "date": next_date,
            "t": len(history),
            "dow": next_date.dayofweek,
            "month": next_date.month,
            "lag_1": float(history.iloc[-1]["amount"]),
            "lag_7": float(history.iloc[-7]["amount"]) if len(history) >= 7 else 0.0,
            "rolling_7": float(history.tail(7)["amount"].mean()),
        }
        yhat = max(0.0, float(model.predict(pd.DataFrame([row])[feature_cols])[0]))
        future_rows.append({"date": next_date.date().isoformat(), "predicted_amount": round(yhat, 2)})
        history = pd.concat([history, pd.DataFrame([{**row, "amount": yhat}])], ignore_index=True)

    return {
        "status": "ok",
        "forecast": future_rows,
        "validation": validation,
        "explanation": "Model uses time index, day-of-week seasonality, month, recent spend, and 7-day rolling behavior.",
    }
