"""
chart_helpers.py — Reusable Plotly chart builders for the LoanLens dashboard.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


BRAND_COLORS = {
    "primary": "#1e3a5f",
    "accent": "#2563eb",
    "positive": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "neutral": "#6b7280",
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
    font=dict(size=12),
    margin=dict(l=60, r=20, t=50, b=60),
)


def delinquency_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Line chart of delinquency rate over time.
    Resamples to weekly to avoid over-crowded x-axis.
    """
    df = df.copy()
    df["date_day"] = pd.to_datetime(df["date_day"])
    df = df.set_index("date_day").resample("W")["delinquency_rate"].mean().reset_index()

    fig = px.line(
        df,
        x="date_day",
        y="delinquency_rate",
        title="Delinquency Rate — Weekly Average",
        labels={"date_day": "Week", "delinquency_rate": "Delinquency Rate"},
        color_discrete_sequence=[BRAND_COLORS["accent"]],
    )
    fig.update_layout(
        **_LAYOUT,
        yaxis=dict(tickformat=".1%", gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0", tickangle=-30),
        hovermode="x unified",
    )
    fig.update_traces(hovertemplate="%{y:.2%}")
    return fig


def origination_volume_chart(df: pd.DataFrame) -> go.Figure:
    """
    Stacked bar chart of monthly origination volume by platform.
    """
    df = df.copy()
    df["origination_month"] = pd.to_datetime(df["origination_month"])

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
    fig.update_layout(
        **_LAYOUT,
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f0f0f0"),
        xaxis=dict(tickangle=-30, gridcolor="#f0f0f0"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{fullData.name}: $%{y:,.0f}")
    return fig


def cohort_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap of cumulative default rate by cohort × months-on-book.
    Limits to the 18 most recent cohorts to keep it readable.
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
            z=pivot.values * 100,          # show as percentage numbers
            x=[f"Mo {c}" for c in pivot.columns.tolist()],
            y=pivot.index.tolist(),
            colorscale="Reds",
            colorbar=dict(title="Default %", ticksuffix="%"),
            hovertemplate="Cohort: %{y}<br>%{x}<br>Default Rate: %{z:.2f}%<extra></extra>",
            zmin=0,
        )
    )
    fig.update_layout(
        **_LAYOUT,
        title="Cumulative Default Rate by Cohort × Months on Book (18 most recent cohorts)",
        xaxis=dict(title="Months on Book", side="bottom"),
        yaxis=dict(title="Cohort (Vintage)", tickfont=dict(size=11)),
        height=520,
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
        yaxis=dict(tickformat=".0%", gridcolor="#f0f0f0", range=[0, 1.1]),
        xaxis=dict(gridcolor="#f0f0f0"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def spv_utilization_bar(spv_id: str, utilization: float, limit: float) -> go.Figure:
    """
    Horizontal progress bar showing facility utilization.
    Caps display at 100% even if over-utilized (shows red if > 85%).
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
        xaxis=dict(range=[0, 1], tickformat=".0%", gridcolor="#f0f0f0"),
        yaxis=dict(showticklabels=False),
        height=90,
        margin=dict(l=0, r=10, t=28, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    return fig
