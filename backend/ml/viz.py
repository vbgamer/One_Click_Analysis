"""
viz.py — Plotly-based interactive chart generator for Expense Intelligence System.

All functions return Plotly figure dicts (JSON-serialisable) using a consistent
dark theme with primary colour #6366f1 (indigo).

Functions
---------
generate_all_charts        : Generate the full chart suite.
chart_spending_over_time   : Line chart with optional forecast overlay.
chart_category_breakdown   : Donut/pie chart of category spend.
chart_payer_comparison     : Bar chart of payer contributions.
chart_anomaly_heatmap      : Calendar heatmap of anomaly scores.
chart_forecast             : Area chart with confidence bands.
chart_spending_heatmap     : Day-of-week × month spending heatmap.
chart_top_merchants        : Horizontal bar chart of top merchants.
chart_settlement_flow      : Sankey diagram of payment flows.
chart_recommendation_impact: Impact bars for recommendations.
"""

import json

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional: Plotly
# ---------------------------------------------------------------------------
try:
    import plotly.graph_objects as go
    import plotly.express as px
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

PRIMARY = "#6366f1"       # Indigo
SECONDARY = "#8b5cf6"     # Violet
SUCCESS = "#22c55e"       # Green
DANGER = "#ef4444"        # Red
WARNING = "#f59e0b"       # Amber
INFO = "#06b6d4"          # Cyan
GRAY = "#6b7280"
BG_COLOR = "#0f172a"      # Slate-900
SURFACE = "#1e293b"       # Slate-800
BORDER = "#334155"        # Slate-700
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"

PALETTE = [
    PRIMARY, SECONDARY, SUCCESS, WARNING, DANGER, INFO,
    "#f472b6", "#34d399", "#fb923c", "#a78bfa",
]

_BASE_LAYOUT = dict(
    paper_bgcolor=BG_COLOR,
    plot_bgcolor=SURFACE,
    font=dict(family="Inter, system-ui, sans-serif", color=TEXT_PRIMARY, size=12),
    title_font=dict(size=16, color=TEXT_PRIMARY, family="Inter, system-ui, sans-serif"),
    legend=dict(
        bgcolor="rgba(30,41,59,0.8)",
        bordercolor=BORDER,
        borderwidth=1,
        font=dict(color=TEXT_SECONDARY),
    ),
    xaxis=dict(
        gridcolor=BORDER,
        linecolor=BORDER,
        tickcolor=TEXT_SECONDARY,
        tickfont=dict(color=TEXT_SECONDARY),
    ),
    yaxis=dict(
        gridcolor=BORDER,
        linecolor=BORDER,
        tickcolor=TEXT_SECONDARY,
        tickfont=dict(color=TEXT_SECONDARY),
    ),
    margin=dict(l=60, r=30, t=60, b=60),
)


def _make_layout(**overrides) -> dict:
    """Merge base layout with overrides."""
    layout = dict(_BASE_LAYOUT)
    for key, val in overrides.items():
        if isinstance(val, dict) and key in layout and isinstance(layout[key], dict):
            layout[key] = {**layout[key], **val}
        else:
            layout[key] = val
    return layout


def _empty_chart(message: str = "No data available") -> dict:
    """Return an empty Plotly figure with a centred message."""
    if not _PLOTLY_AVAILABLE:
        return {"data": [], "layout": {"title": {"text": message}}}
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color=TEXT_SECONDARY),
    )
    fig.update_layout(**_make_layout(title={"text": message}))
    return json.loads(fig.to_json())


def _fig_to_dict(fig) -> dict:
    """Convert a Plotly figure to a JSON-safe dict."""
    return json.loads(fig.to_json())


def _get_col(df: pd.DataFrame, schema: dict, key: str) -> str | None:
    col = schema.get(key)
    return col if col and col in df.columns else None


# ---------------------------------------------------------------------------
# Individual chart functions
# ---------------------------------------------------------------------------

def chart_spending_over_time(df: pd.DataFrame, schema: dict) -> dict:
    """Line chart of daily spending with optional forecast overlay.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    date_col = _get_col(df, schema, "date_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not date_col or not amount_col:
        return _empty_chart("Date or amount column not detected")

    try:
        ts = df[[date_col, amount_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[amount_col] = pd.to_numeric(ts[amount_col], errors="coerce").fillna(0)
        ts = ts.dropna(subset=[date_col])
        daily = ts.groupby(ts[date_col].dt.date)[amount_col].sum().reset_index()
        daily.columns = ["date", "amount"]
        daily = daily.sort_values("date")

        # 7-day rolling average
        daily["rolling_avg"] = daily["amount"].rolling(7, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=daily["date"].astype(str),
                y=daily["amount"],
                name="Daily Spend",
                marker_color=f"rgba(99,102,241,0.4)",
                marker_line_color=PRIMARY,
                marker_line_width=0.5,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily["date"].astype(str),
                y=daily["rolling_avg"],
                name="7-Day Average",
                line=dict(color=SECONDARY, width=2.5),
                mode="lines",
            )
        )
        fig.update_layout(
            **_make_layout(
                title={"text": "💸 Daily Spending Over Time"},
                xaxis={"title": {"text": "Date"}},
                yaxis={"title": {"text": "Amount (₹)"}},
                barmode="overlay",
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_category_breakdown(df: pd.DataFrame, schema: dict) -> dict:
    """Donut / pie chart of category spend breakdown.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    category_col = _get_col(df, schema, "category_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not category_col:
        return _empty_chart("Category column not detected")

    try:
        df_work = df.copy()
        if amount_col:
            df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
            cat_totals = df_work.groupby(category_col)[amount_col].sum()
        else:
            cat_totals = df_work[category_col].value_counts()

        cat_totals = cat_totals.sort_values(ascending=False)

        # Bucket small categories into "Other"
        threshold = cat_totals.sum() * 0.02
        small_mask = cat_totals < threshold
        if small_mask.sum() > 1:
            other_total = cat_totals[small_mask].sum()
            cat_totals = cat_totals[~small_mask]
            if other_total > 0:
                cat_totals["Other"] = other_total

        fig = go.Figure(
            go.Pie(
                labels=cat_totals.index.tolist(),
                values=[round(float(v), 2) for v in cat_totals.values],
                hole=0.45,
                marker=dict(
                    colors=PALETTE[: len(cat_totals)],
                    line=dict(color=BG_COLOR, width=2),
                ),
                textfont=dict(color=TEXT_PRIMARY, size=11),
                hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
            )
        )
        fig.update_layout(
            **_make_layout(
                title={"text": "🏷 Spending by Category"},
                showlegend=True,
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_payer_comparison(df: pd.DataFrame, schema: dict) -> dict:
    """Grouped bar chart comparing payer contributions.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    payer_col = _get_col(df, schema, "payer_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not payer_col:
        return _empty_chart("Payer column not detected")

    try:
        df_work = df.copy()
        if amount_col:
            df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
            payer_stats = df_work.groupby(payer_col)[amount_col].agg(
                ["sum", "mean", "count"]
            ).reset_index()
        else:
            payer_stats = df_work.groupby(payer_col).size().reset_index(name="count")
            payer_stats["sum"] = payer_stats["count"]
            payer_stats["mean"] = payer_stats["count"]

        payer_stats = payer_stats.sort_values("sum", ascending=False)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=payer_stats[payer_col].astype(str).tolist(),
                y=[round(float(v), 2) for v in payer_stats["sum"]],
                name="Total Paid",
                marker_color=PRIMARY,
                text=[f"₹{v:,.0f}" for v in payer_stats["sum"]],
                textposition="outside",
                textfont=dict(color=TEXT_PRIMARY, size=10),
                hovertemplate="<b>%{x}</b><br>Total: ₹%{y:,.0f}<extra></extra>",
            )
        )
        if "mean" in payer_stats.columns:
            fig.add_trace(
                go.Bar(
                    x=payer_stats[payer_col].astype(str).tolist(),
                    y=[round(float(v), 2) for v in payer_stats["mean"]],
                    name="Avg Transaction",
                    marker_color=SECONDARY,
                    hovertemplate="<b>%{x}</b><br>Avg: ₹%{y:,.0f}<extra></extra>",
                )
            )
        fig.update_layout(
            **_make_layout(
                title={"text": "👥 Payer Contribution Comparison"},
                xaxis={"title": {"text": "Payer"}},
                yaxis={"title": {"text": "Amount (₹)"}},
                barmode="group",
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_anomaly_heatmap(df: pd.DataFrame, anomalies: dict, schema: dict) -> dict:
    """Scatter/timeline heatmap of anomaly scores.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    anomalies : dict
        Output of ``anomaly.detect_anomalies``.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    if not anomalies or not anomalies.get("available"):
        return _empty_chart("No anomaly data available")

    try:
        heatmap_data = anomalies.get("plotly_heatmap_data", {})
        x = heatmap_data.get("x", [])
        y = heatmap_data.get("y", [])
        texts = heatmap_data.get("text", [])

        if not x:
            return _empty_chart("No anomalies detected")

        colors = [DANGER if s >= 0.7 else WARNING if s >= 0.4 else INFO for s in y]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                marker=dict(
                    color=y,
                    colorscale=[[0, INFO], [0.4, WARNING], [1.0, DANGER]],
                    size=12,
                    colorbar=dict(
                        title="Anomaly Score",
                        tickfont=dict(color=TEXT_SECONDARY),
                        titlefont=dict(color=TEXT_SECONDARY),
                    ),
                    line=dict(width=1, color=BG_COLOR),
                ),
                text=texts,
                hovertemplate="<b>Date:</b> %{x}<br><b>Score:</b> %{y:.2f}<br>%{text}<extra></extra>",
            )
        )
        fig.update_layout(
            **_make_layout(
                title={"text": "🚨 Anomaly Detection Timeline"},
                xaxis={"title": {"text": "Date"}},
                yaxis={"title": {"text": "Anomaly Score (0-1)"}, "range": [0, 1.05]},
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_forecast(forecast_data: dict) -> dict:
    """Area chart with confidence bands for spending forecast.

    Parameters
    ----------
    forecast_data : dict
        Output of ``forecasting.forecast_expenses``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    if not forecast_data or not forecast_data.get("available"):
        return _empty_chart("No forecast data available")

    try:
        plotly_data = forecast_data.get("plotly_data", {})
        hist_x = plotly_data.get("historical_x", [])
        hist_y = plotly_data.get("historical_y", [])
        fc_x = plotly_data.get("forecast_x", [])
        fc_y = plotly_data.get("forecast_y", [])
        fc_lower = plotly_data.get("forecast_lower", [])
        fc_upper = plotly_data.get("forecast_upper", [])

        fig = go.Figure()

        # Historical
        if hist_x:
            fig.add_trace(
                go.Scatter(
                    x=hist_x,
                    y=hist_y,
                    name="Historical",
                    line=dict(color=INFO, width=2),
                    mode="lines",
                )
            )

        # Confidence band (upper → lower filled)
        if fc_x:
            fig.add_trace(
                go.Scatter(
                    x=fc_x + fc_x[::-1],
                    y=fc_upper + fc_lower[::-1],
                    fill="toself",
                    fillcolor=f"rgba(99,102,241,0.15)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="95% Confidence",
                    showlegend=True,
                )
            )
            # Forecast line
            fig.add_trace(
                go.Scatter(
                    x=fc_x,
                    y=fc_y,
                    name="Forecast",
                    line=dict(color=PRIMARY, width=2.5, dash="dot"),
                    mode="lines",
                )
            )

        trend = forecast_data.get("trend_direction", "stable")
        next_pred = forecast_data.get("next_month_prediction", 0)
        fig.update_layout(
            **_make_layout(
                title={
                    "text": f"📈 Spending Forecast — Trend: {trend.title()} | Next 30 days: ₹{next_pred:,.0f}"
                },
                xaxis={"title": {"text": "Date"}},
                yaxis={"title": {"text": "Amount (₹)"}},
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_spending_heatmap(df: pd.DataFrame, schema: dict) -> dict:
    """Day-of-week × month spending heatmap.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    date_col = _get_col(df, schema, "date_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not date_col or not amount_col:
        return _empty_chart("Date or amount column not detected")

    try:
        df_work = df.copy()
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors="coerce")
        df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
        df_work = df_work.dropna(subset=[date_col])

        df_work["_dow"] = df_work[date_col].dt.day_name()
        df_work["_month"] = df_work[date_col].dt.month_name()

        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        pivot = df_work.pivot_table(
            index="_dow", columns="_month", values=amount_col, aggfunc="mean"
        )
        pivot = pivot.reindex(
            index=[d for d in dow_order if d in pivot.index],
            columns=[m for m in month_order if m in pivot.columns],
        )

        fig = go.Figure(
            go.Heatmap(
                z=pivot.values.tolist(),
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale=[
                    [0, SURFACE],
                    [0.5, SECONDARY],
                    [1.0, DANGER],
                ],
                hoverongaps=False,
                hovertemplate="<b>%{y}, %{x}</b><br>Avg: ₹%{z:,.0f}<extra></extra>",
                colorbar=dict(
                    title="Avg Spend (₹)",
                    tickfont=dict(color=TEXT_SECONDARY),
                    titlefont=dict(color=TEXT_SECONDARY),
                ),
            )
        )
        fig.update_layout(
            **_make_layout(
                title={"text": "🗓 Spending Heatmap — Day of Week × Month"},
                xaxis={"title": {"text": "Month"}},
                yaxis={"title": {"text": "Day of Week"}},
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_top_merchants(df: pd.DataFrame, schema: dict, n: int = 10) -> dict:
    """Horizontal bar chart of top *n* merchants by total spend.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    n : int
        Number of merchants to display.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    merchant_col = _get_col(df, schema, "merchant_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not merchant_col:
        return _empty_chart("Merchant column not detected")

    try:
        df_work = df.copy()
        if amount_col:
            df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
            top = (
                df_work.groupby(merchant_col)[amount_col]
                .sum()
                .sort_values(ascending=False)
                .head(n)
                .sort_values(ascending=True)  # ascending for horizontal bar readability
            )
        else:
            top = (
                df_work[merchant_col]
                .value_counts()
                .head(n)
                .sort_values(ascending=True)
            )

        fig = go.Figure(
            go.Bar(
                x=[round(float(v), 2) for v in top.values],
                y=[str(m)[:30] for m in top.index],
                orientation="h",
                marker=dict(
                    color=list(range(len(top))),
                    colorscale=[[0, SECONDARY], [1.0, PRIMARY]],
                    line=dict(color=BG_COLOR, width=1),
                ),
                text=[f"₹{v:,.0f}" for v in top.values],
                textposition="outside",
                textfont=dict(color=TEXT_PRIMARY, size=10),
                hovertemplate="<b>%{y}</b><br>Total: ₹%{x:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(
            **_make_layout(
                title={"text": f"🏪 Top {n} Merchants by Spend"},
                xaxis={"title": {"text": "Total Spend (₹)"}},
                yaxis={"title": {"text": "Merchant"}},
                height=max(350, n * 42),
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_settlement_flow(payer_network: dict) -> dict:
    """Sankey diagram of optimal payment flows.

    Parameters
    ----------
    payer_network : dict
        Output of ``settlement.build_payer_network``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    if not payer_network or not payer_network.get("available"):
        return _empty_chart("No settlement network data available")

    try:
        nodes = payer_network.get("nodes", [])
        edges = payer_network.get("edges", [])

        if not nodes or not edges:
            return _empty_chart("No settlement transactions required — all even!")

        node_labels = [n["label"] for n in nodes]
        node_index = {n["id"]: i for i, n in enumerate(nodes)}

        source_indices = [node_index.get(e["source"], 0) for e in edges]
        target_indices = [node_index.get(e["target"], 0) for e in edges]
        values = [round(float(e["amount"]), 2) for e in edges]

        fig = go.Figure(
            go.Sankey(
                node=dict(
                    pad=20,
                    thickness=25,
                    line=dict(color=BORDER, width=0.5),
                    label=node_labels,
                    color=PALETTE[: len(node_labels)],
                    hovertemplate="<b>%{label}</b><br>Total flow: ₹%{value:,.0f}<extra></extra>",
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=values,
                    color=[f"rgba(99,102,241,0.35)"] * len(values),
                    hovertemplate=(
                        "<b>%{source.label}</b> → <b>%{target.label}</b>"
                        "<br>₹%{value:,.0f}<extra></extra>"
                    ),
                ),
            )
        )
        fig.update_layout(
            **_make_layout(title={"text": "💱 Settlement Flow — Optimal Payment Plan"})
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


def chart_recommendation_impact(recommendations: list) -> dict:
    """Horizontal bar chart visualising recommendation priorities.

    Parameters
    ----------
    recommendations : list
        Output of ``recommendations.generate_recommendations``.

    Returns
    -------
    dict
        Plotly figure JSON.
    """
    if not _PLOTLY_AVAILABLE:
        return _empty_chart("Plotly not installed")

    if not recommendations:
        return _empty_chart("No recommendations available")

    try:
        priority_map = {"high": 3, "medium": 2, "low": 1}
        color_map = {"high": DANGER, "medium": WARNING, "low": SUCCESS}

        recs = recommendations[:8]  # Top 8
        titles = [r.get("title", f"Rec {i+1}")[:45] for i, r in enumerate(recs)]
        confidence = [round(float(r.get("confidence", 0.5)) * 100, 1) for r in recs]
        priorities = [r.get("priority", "low") for r in recs]
        colors = [color_map.get(p, GRAY) for p in priorities]
        priority_scores = [priority_map.get(p, 1) for p in priorities]

        # Sort by priority descending
        order = sorted(range(len(recs)), key=lambda i: priority_scores[i])
        titles = [titles[i] for i in order]
        confidence = [confidence[i] for i in order]
        colors = [colors[i] for i in order]

        fig = go.Figure(
            go.Bar(
                x=confidence,
                y=titles,
                orientation="h",
                marker_color=colors,
                text=[f"{c:.0f}%" for c in confidence],
                textposition="outside",
                textfont=dict(color=TEXT_PRIMARY, size=10),
                hovertemplate="<b>%{y}</b><br>Confidence: %{x:.1f}%<extra></extra>",
            )
        )
        fig.update_layout(
            **_make_layout(
                title={"text": "💡 Recommendations — Confidence & Priority"},
                xaxis={"title": {"text": "Confidence (%)"}, "range": [0, 115]},
                yaxis={"title": {"text": ""}},
                height=max(300, len(recs) * 52),
            )
        )
        return _fig_to_dict(fig)

    except Exception as e:
        return _empty_chart(f"Error generating chart: {e}")


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

def generate_all_charts(
    df: pd.DataFrame,
    schema: dict,
    analysis_results: dict,
) -> dict:
    """Generate the complete interactive chart suite for the expense data.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    analysis_results : dict
        Aggregated pipeline output (contains forecast, anomalies, etc.).

    Returns
    -------
    dict
        Chart names → Plotly figure JSON dicts.
    """
    charts: dict = {}

    charts["spending_over_time"] = chart_spending_over_time(df, schema)
    charts["category_breakdown"] = chart_category_breakdown(df, schema)
    charts["payer_comparison"] = chart_payer_comparison(df, schema)

    anomalies = analysis_results.get("anomalies", {})
    charts["anomaly_heatmap"] = chart_anomaly_heatmap(df, anomalies, schema)

    forecast = analysis_results.get("forecast", {})
    charts["forecast"] = chart_forecast(forecast)

    charts["spending_heatmap"] = chart_spending_heatmap(df, schema)
    charts["top_merchants"] = chart_top_merchants(df, schema)

    payer_network = analysis_results.get("payer_network", {})
    charts["settlement_flow"] = chart_settlement_flow(payer_network)

    recommendations_list = analysis_results.get("recommendations", [])
    charts["recommendation_impact"] = chart_recommendation_impact(recommendations_list)

    return charts
