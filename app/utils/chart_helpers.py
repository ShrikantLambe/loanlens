"""
chart_helpers.py — Reusable Plotly chart builders for the LoanLens dashboard.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


BRAND_COLORS = {
    "primary": "#1e3a5f",
    "accent": "#2563eb",
    "positive": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "neutral": "#6b7280",
    "accent_light": "#dbeafe",
}

PLATFORM_PALETTE = {
    "doordash": "#ff3008",
    "amazon": "#ff9900",
    "mindbody": "#00b5ad",
    "worldpay": "#003087",
    "shopify": "#96bf48",
}

_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1e293b"),
    margin=dict(l=60, r=20, t=56, b=60),
)


def delinquency_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Area + line chart of delinquency rate over time with a 4-week rolling average.
    Resamples input to weekly averages to avoid over-crowded x-axis.
    """
    df = df.copy()
    df["date_day"] = pd.to_datetime(df["date_day"])
    weekly = df.set_index("date_day").resample("W")["delinquency_rate"].mean().reset_index()
    weekly["rolling"] = weekly["delinquency_rate"].rolling(4, min_periods=1).mean()

    fig = go.Figure()

    # Area fill
    fig.add_trace(
        go.Scatter(
            x=weekly["date_day"],
            y=weekly["delinquency_rate"],
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.08)",
            line=dict(color=BRAND_COLORS["accent"], width=2),
            name="Weekly avg",
            hovertemplate="%{x|%b %d, %Y}<br>Delinquency: %{y:.2%}<extra></extra>",
        )
    )

    # 4-week rolling average
    fig.add_trace(
        go.Scatter(
            x=weekly["date_day"],
            y=weekly["rolling"],
            line=dict(color=BRAND_COLORS["warning"], width=2, dash="dot"),
            name="4-wk rolling avg",
            hovertemplate="%{x|%b %d, %Y}<br>Rolling avg: %{y:.2%}<extra></extra>",
        )
    )

    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Delinquency Rate — Weekly", font=dict(size=15, weight=700)),
        yaxis=dict(tickformat=".1%", gridcolor="#f0f4f8", zeroline=False),
        xaxis=dict(gridcolor="#f0f4f8", tickangle=-20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def origination_volume_chart(df: pd.DataFrame) -> go.Figure:
    """
    Stacked bar chart of monthly origination volume by platform with total line overlay.
    """
    df = df.copy()
    df["origination_month"] = pd.to_datetime(df["origination_month"])

    monthly_total = (
        df.groupby("origination_month")["origination_volume"].sum().reset_index()
    )

    fig = px.bar(
        df,
        x="origination_month",
        y="origination_volume",
        color="platform",
        title="Monthly Origination Volume by Platform",
        labels={
            "origination_month": "Month",
            "origination_volume": "Volume ($)",
            "platform": "Platform",
        },
        color_discrete_map=PLATFORM_PALETTE,
        barmode="stack",
    )

    # Total line overlay
    fig.add_trace(
        go.Scatter(
            x=monthly_total["origination_month"],
            y=monthly_total["origination_volume"],
            mode="lines",
            line=dict(color="#1e293b", width=2),
            name="Total",
            hovertemplate="%{x|%b %Y}<br>Total: $%{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        **_LAYOUT,
        title=dict(font=dict(size=15, weight=700)),
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f0f4f8", zeroline=False),
        xaxis=dict(tickangle=-20, gridcolor="#f0f4f8"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_traces(
        selector=dict(type="bar"),
        hovertemplate="%{x|%b %Y}<br>%{fullData.name}: $%{y:,.0f}",
    )
    return fig


def cohort_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap of cumulative default rate by cohort × months-on-book (18 most recent cohorts).
    """
    df = df.copy()
    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    recent_cohorts = (
        df.groupby("cohort_label")["cohort_month"]
        .max()
        .sort_values(ascending=False)
        .head(18)
        .index.tolist()
    )
    df = df[df["cohort_label"].isin(recent_cohorts)]

    pivot = df.pivot_table(
        index="cohort_label",
        columns="months_on_book",
        values="cumulative_default_rate",
        aggfunc="mean",
    ).sort_index(ascending=False)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values * 100,
            x=[f"Mo {c}" for c in pivot.columns.tolist()],
            y=pivot.index.tolist(),
            colorscale=[
                [0.0, "#f0fdf4"],
                [0.3, "#fef9c3"],
                [0.6, "#fed7aa"],
                [1.0, "#dc2626"],
            ],
            colorbar=dict(title="Default %", ticksuffix="%", thickness=14),
            hovertemplate="Cohort: %{y}<br>%{x}<br>Default Rate: %{z:.2f}%<extra></extra>",
            zmin=0,
        )
    )
    fig.update_layout(
        **_LAYOUT,
        title=dict(
            text="Cumulative Default Rate — Cohort × Months on Book (18 most recent)",
            font=dict(size=15, weight=700),
        ),
        xaxis=dict(title="Months on Book", side="bottom"),
        yaxis=dict(title="Cohort (Vintage)", tickfont=dict(size=11)),
        height=540,
    )
    return fig


def repayment_curves_chart(df: pd.DataFrame, cohorts: list[str]) -> go.Figure:
    """
    Line chart of avg_pct_repaid curves for selected cohorts.
    """
    filtered = df[df["cohort_label"].isin(cohorts)].copy()
    fig = px.line(
        filtered,
        x="months_on_book",
        y="avg_pct_repaid",
        color="cohort_label",
        title="Repayment Curves by Cohort",
        labels={
            "months_on_book": "Months on Book",
            "avg_pct_repaid": "Avg % Repaid",
            "cohort_label": "Cohort",
        },
        markers=True,
    )
    fig.update_layout(
        **_LAYOUT,
        title=dict(font=dict(size=15, weight=700)),
        yaxis=dict(tickformat=".0%", gridcolor="#f0f4f8", range=[0, 1.1], zeroline=False),
        xaxis=dict(gridcolor="#f0f4f8"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_traces(hovertemplate="%{y:.1%}")
    return fig


def spv_utilization_bar(spv_id: str, utilization: float, limit: float) -> go.Figure:
    """
    Horizontal progress bar showing facility utilization.
    Turns red above 85% utilization.
    """
    display_val = min(utilization, 1.0)
    color = BRAND_COLORS["danger"] if utilization > 0.85 else BRAND_COLORS["accent"]
    fig = go.Figure(
        go.Bar(
            x=[display_val],
            y=[""],
            orientation="h",
            marker_color=color,
            text=[f"{utilization:.1%}"],
            textposition="inside" if display_val > 0.15 else "outside",
            textfont=dict(size=13, color="white" if display_val > 0.15 else color),
        )
    )
    fig.update_layout(
        title=dict(text=f"Utilization vs ${limit/1e6:.0f}M limit", font=dict(size=12)),
        xaxis=dict(range=[0, 1], tickformat=".0%", gridcolor="#f0f4f8"),
        yaxis=dict(showticklabels=False),
        height=90,
        margin=dict(l=0, r=10, t=28, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    return fig
