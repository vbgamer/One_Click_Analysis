"""
forecasting.py — Time-series forecasting engine for Expense Intelligence System.

Functions
---------
forecast_expenses       : Forecast total daily spending N periods ahead.
forecast_by_category    : Per-category forecasts.
compute_burn_rate       : Daily/weekly/monthly burn rate + runway.
"""

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional: Facebook Prophet
# ---------------------------------------------------------------------------
try:
    from prophet import Prophet
    _PROPHET_AVAILABLE = True
except ImportError:
    _PROPHET_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_cols(df: pd.DataFrame, schema: dict):
    """Return (date_col, amount_col) or raise ValueError."""
    date_col = schema.get("date_col")
    amount_col = schema.get("amount_col")
    if not date_col or date_col not in df.columns:
        raise ValueError("date_col not found in schema/dataframe")
    if not amount_col or amount_col not in df.columns:
        raise ValueError("amount_col not found in schema/dataframe")
    return date_col, amount_col


def _prepare_daily_series(df: pd.DataFrame, date_col: str, amount_col: str) -> pd.DataFrame:
    """Group spend by calendar day, return DataFrame with [ds, y]."""
    ts = df[[date_col, amount_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
    ts = ts.dropna(subset=[date_col])
    ts[amount_col] = pd.to_numeric(ts[amount_col], errors="coerce").fillna(0)
    daily = (
        ts.groupby(ts[date_col].dt.date)[amount_col]
        .sum()
        .reset_index()
        .rename(columns={date_col: "ds", amount_col: "y"})
    )
    daily["ds"] = pd.to_datetime(daily["ds"])
    daily = daily.sort_values("ds").reset_index(drop=True)
    return daily


def _linear_forecast(daily: pd.DataFrame, periods: int) -> pd.DataFrame:
    """Simple linear-trend fallback when Prophet is unavailable."""
    x = np.arange(len(daily))
    y = daily["y"].values
    if len(x) < 2:
        slope, intercept = 0.0, float(y.mean()) if len(y) > 0 else 0.0
    else:
        slope, intercept = np.polyfit(x, y, 1)

    last_date = daily["ds"].iloc[-1]
    future_dates = pd.date_range(
        start=last_date + timedelta(days=1), periods=periods, freq="D"
    )
    future_x = np.arange(len(daily), len(daily) + periods)
    yhat = slope * future_x + intercept
    yhat = np.clip(yhat, 0, None)  # spend cannot be negative
    std_err = float(daily["y"].std()) if len(daily) > 1 else 0.0

    future_df = pd.DataFrame(
        {
            "ds": future_dates,
            "yhat": yhat,
            "yhat_lower": np.clip(yhat - 1.96 * std_err, 0, None),
            "yhat_upper": yhat + 1.96 * std_err,
        }
    )
    return future_df


def _prophet_forecast(daily: pd.DataFrame, periods: int) -> pd.DataFrame:
    """Forecast using Facebook Prophet."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95,
        )
        m.fit(daily[["ds", "y"]])
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
    forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)
    forecast["yhat"] = forecast["yhat"].clip(lower=0)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
    return forecast


def _compute_trend(daily: pd.DataFrame) -> str:
    """Return 'increasing', 'decreasing', or 'stable' based on linear trend."""
    if len(daily) < 7:
        return "stable"
    y = daily["y"].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    mean_y = np.mean(y) if np.mean(y) != 0 else 1
    relative_slope = slope / mean_y
    if relative_slope > 0.01:
        return "increasing"
    elif relative_slope < -0.01:
        return "decreasing"
    return "stable"


def _build_plotly_data(daily: pd.DataFrame, future_df: pd.DataFrame) -> dict:
    """Build Plotly-compatible x/y arrays."""
    hist_x = [str(d.date()) for d in daily["ds"]]
    hist_y = daily["y"].tolist()
    fc_x = [str(d.date()) for d in future_df["ds"]]
    fc_y = [round(v, 2) for v in future_df["yhat"].tolist()]
    fc_lower = [round(v, 2) for v in future_df["yhat_lower"].tolist()]
    fc_upper = [round(v, 2) for v in future_df["yhat_upper"].tolist()]
    return {
        "historical_x": hist_x,
        "historical_y": hist_y,
        "forecast_x": fc_x,
        "forecast_y": fc_y,
        "forecast_lower": fc_lower,
        "forecast_upper": fc_upper,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast_expenses(df: pd.DataFrame, schema: dict, periods: int = 30) -> dict:
    """Forecast total daily spending for the next *periods* days.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    periods : int
        Number of days to forecast.

    Returns
    -------
    dict
        Keys: ``forecast``, ``trend_direction``, ``monthly_avg``,
        ``next_month_prediction``, ``plotly_data``, ``available``,
        ``method``.
    """
    try:
        date_col, amount_col = _get_cols(df, schema)
    except ValueError as e:
        return {"available": False, "reason": str(e)}

    try:
        daily = _prepare_daily_series(df, date_col, amount_col)
        if len(daily) < 3:
            return {
                "available": False,
                "reason": "Insufficient data: fewer than 3 daily observations",
            }

        # Forecast
        if _PROPHET_AVAILABLE and len(daily) >= 14:
            try:
                future_df = _prophet_forecast(daily, periods)
                method = "prophet"
            except Exception:
                future_df = _linear_forecast(daily, periods)
                method = "linear"
        else:
            future_df = _linear_forecast(daily, periods)
            method = "linear"

        trend = _compute_trend(daily)
        monthly_avg = round(float(daily["y"].mean()) * 30, 2)
        next_month_prediction = round(float(future_df["yhat"].sum()), 2)

        forecast_records = [
            {
                "ds": str(row["ds"].date()),
                "yhat": round(row["yhat"], 2),
                "yhat_lower": round(row["yhat_lower"], 2),
                "yhat_upper": round(row["yhat_upper"], 2),
            }
            for _, row in future_df.iterrows()
        ]

        plotly_data = _build_plotly_data(daily, future_df)

        return {
            "available": True,
            "method": method,
            "forecast": forecast_records,
            "trend_direction": trend,
            "monthly_avg": monthly_avg,
            "next_month_prediction": next_month_prediction,
            "plotly_data": plotly_data,
        }

    except Exception as e:
        return {"available": False, "reason": f"Forecasting error: {e}"}


def forecast_by_category(df: pd.DataFrame, schema: dict, periods: int = 30) -> dict:
    """Forecast spending per expense category.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    periods : int
        Days to forecast per category.

    Returns
    -------
    dict
        Keys are category names; values are the same structure as
        :func:`forecast_expenses` return value.
    """
    try:
        date_col, amount_col = _get_cols(df, schema)
    except ValueError as e:
        return {"available": False, "reason": str(e)}

    cat_col = schema.get("category_col")
    if not cat_col or cat_col not in df.columns:
        return {
            "available": False,
            "reason": "category_col not found in schema/dataframe",
        }

    results: dict = {}
    categories = df[cat_col].dropna().unique().tolist()

    for cat in categories:
        cat_df = df[df[cat_col] == cat].copy()
        try:
            daily = _prepare_daily_series(cat_df, date_col, amount_col)
            if len(daily) < 3:
                results[str(cat)] = {
                    "available": False,
                    "reason": "Insufficient data for this category",
                }
                continue

            if _PROPHET_AVAILABLE and len(daily) >= 14:
                try:
                    future_df = _prophet_forecast(daily, periods)
                    method = "prophet"
                except Exception:
                    future_df = _linear_forecast(daily, periods)
                    method = "linear"
            else:
                future_df = _linear_forecast(daily, periods)
                method = "linear"

            trend = _compute_trend(daily)
            forecast_records = [
                {
                    "ds": str(row["ds"].date()),
                    "yhat": round(row["yhat"], 2),
                    "yhat_lower": round(row["yhat_lower"], 2),
                    "yhat_upper": round(row["yhat_upper"], 2),
                }
                for _, row in future_df.iterrows()
            ]
            plotly_data = _build_plotly_data(daily, future_df)

            results[str(cat)] = {
                "available": True,
                "method": method,
                "forecast": forecast_records,
                "trend_direction": trend,
                "monthly_avg": round(float(daily["y"].mean()) * 30, 2),
                "next_month_prediction": round(float(future_df["yhat"].sum()), 2),
                "plotly_data": plotly_data,
            }
        except Exception as e:
            results[str(cat)] = {"available": False, "reason": str(e)}

    return results


def compute_burn_rate(df: pd.DataFrame, schema: dict) -> dict:
    """Compute daily / weekly / monthly burn rate and runway.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``daily_rate``, ``weekly_rate``, ``monthly_rate``,
        ``peak_month``, ``peak_amount``, ``available``.
    """
    try:
        date_col, amount_col = _get_cols(df, schema)
    except ValueError as e:
        return {"available": False, "reason": str(e)}

    try:
        ts = df[[date_col, amount_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts = ts.dropna(subset=[date_col])
        ts[amount_col] = pd.to_numeric(ts[amount_col], errors="coerce").fillna(0)

        if ts.empty:
            return {"available": False, "reason": "No valid date-amount pairs"}

        # Daily
        daily = ts.groupby(ts[date_col].dt.date)[amount_col].sum()
        daily_rate = round(float(daily.mean()), 2)
        weekly_rate = round(daily_rate * 7, 2)
        monthly_rate = round(daily_rate * 30, 2)

        # Peak month
        ts["month"] = ts[date_col].dt.to_period("M").astype(str)
        monthly = ts.groupby("month")[amount_col].sum()
        peak_month = str(monthly.idxmax()) if not monthly.empty else "N/A"
        peak_amount = round(float(monthly.max()), 2) if not monthly.empty else 0.0

        return {
            "available": True,
            "daily_rate": daily_rate,
            "weekly_rate": weekly_rate,
            "monthly_rate": monthly_rate,
            "peak_month": peak_month,
            "peak_amount": peak_amount,
            "n_days_observed": int(len(daily)),
            "total_spend": round(float(ts[amount_col].sum()), 2),
        }

    except Exception as e:
        return {"available": False, "reason": f"Burn rate error: {e}"}
