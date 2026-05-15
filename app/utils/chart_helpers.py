"""
chart_helpers.py — Reusable Plotly chart builders for the LoanLens dashboard.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


BRAND_COLORS = {
    "primary":      "#1e3a5f",
    "accent":       "#2563eb",
    "positive":     "#16a34a",
    "warning":      "#d97706",
    "danger":       "#dc2626",
    "neutral":      "#6b7280",
    "accent_light": "#dbeafe",
}

PLATFORM_PALETTE = {
    "doordash": "#ff3008",
    "amazon":   "#ff9900",
    "mindbody": "#00b5ad",
    "worldpay": "#003087",
    "shopify":  "#96bf48",
}

_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1e293b"),
    margin=dict(l=60, r=20, t=56, b=60),
)


def delinquency_trend_chart(
    df: pd.DataFrame,
    covenant_limit: float | None = None,
) -> go.Figure:
    """
    Area + line chart of delinquency rate with 4-week rolling avg.
    Optionally overlays a red dashed covenant threshold line so users
    can see how much headroom remains at a glance.
    """
    df = df.copy()
    # Accept either fct_delinquency_weekly (week_date) or fct_portfolio_daily (date_day)
    date_col = "week_date" if "week_date" in df.columns else "date_day"
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df["rolling"] = df["delinquency_rate"].rolling(4, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df[date_col],
            y=df["delinquency_rate"],
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.08)",
            line=dict(color=BRAND_COLORS["accent"], width=2),
            name="Delinquency rate",
            hovertemplate="%{x|%b %d, %Y}<br>Delinquency: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df[date_col],
            y=df["rolling"],
            line=dict(color=BRAND_COLORS["warning"], width=2, dash="dot"),
            name="4-wk rolling avg",
            hovertemplate="%{x|%b %d, %Y}<br>Rolling avg: %{y:.2%}<extra></extra>",
        )
    )

    if covenant_limit is not None:
        fig.add_hline(
            y=covenant_limit,
            line_dash="dash",
            line_color=BRAND_COLORS["danger"],
            line_width=1.5,
            opacity=0.8,
            annotation_text=f"  Tightest covenant: {covenant_limit:.1%}",
            annotation_position="top left",
            annotation_font=dict(size=11, color=BRAND_COLORS["danger"]),
        )

    fig.update_layout(
        **_LAYOUT,
        title=dict(
            text="Delinquency Rate — Rolling 12 Months",
            font=dict(size=15, weight=700),
        ),
        yaxis=dict(tickformat=".1%", gridcolor="#f0f4f8", zeroline=False),
        xaxis=dict(gridcolor="#f0f4f8", tickangle=-20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def origination_volume_chart(df: pd.DataFrame) -> go.Figure:
    """
    Stacked bar of monthly origination volume by platform with:
    - Total dollar volume (primary y-axis, stacked bars)
    - Loan count line (secondary y-axis) so users distinguish volume vs deal size.
    """
    df = df.copy()
    df["origination_month"] = pd.to_datetime(df["origination_month"])

    monthly_total = df.groupby("origination_month").agg(
        origination_volume=("origination_volume", "sum"),
        loan_count=("loan_count", "sum"),
    ).reset_index()

    fig = px.bar(
        df,
        x="origination_month",
        y="origination_volume",
        color="platform",
        labels={
            "origination_month": "Month",
            "origination_volume": "Volume ($)",
            "platform": "Platform",
        },
        color_discrete_map=PLATFORM_PALETTE,
        barmode="stack",
    )

    # Loan count on secondary axis — tells a different story from dollar volume
    fig.add_trace(
        go.Scatter(
            x=monthly_total["origination_month"],
            y=monthly_total["loan_count"],
            mode="lines+markers",
            line=dict(color="#1e293b", width=2),
            marker=dict(size=4),
            name="Loan count",
            yaxis="y2",
            hovertemplate="%{x|%b %Y}<br>Loans: %{y:,}<extra></extra>",
        )
    )

    fig.update_layout(
        **_LAYOUT,
        title=dict(
            text="Monthly Origination Volume & Loan Count by Platform",
            font=dict(size=15, weight=700),
        ),
        yaxis=dict(
            title="Volume ($)",
            tickprefix="$", tickformat=",.0f",
            gridcolor="#f0f4f8", zeroline=False,
        ),
        yaxis2=dict(
            title="Loan Count",
            overlaying="y", side="right",
            showgrid=False, zeroline=False,
            tickformat=",",
        ),
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
    Heatmap: cumulative default rate by cohort × months-on-book (18 most recent cohorts).
    Rows sorted newest-to-oldest so recent cohorts are at top.
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
            text="Cumulative Default Rate — Cohort × Months on Book",
            font=dict(size=15, weight=700),
        ),
        xaxis=dict(title="Months on Book", side="bottom"),
        yaxis=dict(title="Origination Cohort", tickfont=dict(size=11)),
        height=540,
    )
    return fig


def cohort_default_ranking_chart(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart: final (peak) default rate per cohort, sorted worst-to-best.
    Color-coded: red > 6%, amber 3–6%, green < 3%.
    Business question answered: which cohorts do I need to worry about?
    """
    summary = (
        df.groupby("cohort_label")
        .agg(final_default_rate=("cumulative_default_rate", "max"))
        .reset_index()
        .sort_values("final_default_rate", ascending=True)
    )

    colors = [
        BRAND_COLORS["danger"]   if r > 0.06 else
        BRAND_COLORS["warning"]  if r > 0.03 else
        BRAND_COLORS["positive"]
        for r in summary["final_default_rate"]
    ]

    fig = go.Figure(
        go.Bar(
            x=summary["final_default_rate"],
            y=summary["cohort_label"],
            orientation="h",
            marker_color=colors,
            text=[f"{r:.1%}" for r in summary["final_default_rate"]],
            textposition="outside",
            hovertemplate="%{y}<br>Peak Default Rate: %{x:.2%}<extra></extra>",
        )
    )

    # Threshold reference lines
    max_x = float(summary["final_default_rate"].max())
    for threshold, label, color in [
        (0.03, "3% (amber)", BRAND_COLORS["warning"]),
        (0.06, "6% (red)", BRAND_COLORS["danger"]),
    ]:
        if threshold <= max_x * 1.3:
            fig.add_vline(
                x=threshold,
                line_dash="dash",
                line_color=color,
                line_width=1,
                opacity=0.6,
                annotation_text=label,
                annotation_position="top",
                annotation_font=dict(size=10, color=color),
            )

    fig.update_layout(
        **_LAYOUT,
        title=dict(
            text="Peak Default Rate by Cohort — Worst to Best",
            font=dict(size=15, weight=700),
        ),
        xaxis=dict(tickformat=".1%", gridcolor="#f0f4f8", zeroline=False),
        yaxis=dict(tickfont=dict(size=10)),
        height=max(300, len(summary) * 24 + 100),
        showlegend=False,
    )
    return fig


def repayment_curves_chart(df: pd.DataFrame, cohorts: list[str]) -> go.Figure:
    """
    Line chart of repayment progress curves for selected cohorts.
    100% = loan fully repaid.
    """
    filtered = df[df["cohort_label"].isin(cohorts)].copy()
    fig = px.line(
        filtered,
        x="months_on_book",
        y="avg_pct_repaid",
        color="cohort_label",
        title="Repayment Progress by Cohort",
        labels={
            "months_on_book": "Months on Book",
            "avg_pct_repaid": "Avg Repayment Progress",
            "cohort_label": "Cohort",
        },
        markers=True,
    )

    # 100% reference
    fig.add_hline(
        y=1.0,
        line_dash="dot",
        line_color=BRAND_COLORS["positive"],
        line_width=1,
        opacity=0.5,
        annotation_text="  Fully repaid",
        annotation_position="right",
        annotation_font=dict(size=10, color=BRAND_COLORS["positive"]),
    )

    fig.update_layout(
        **_LAYOUT,
        title=dict(font=dict(size=15, weight=700)),
        yaxis=dict(
            tickformat=".0%",
            gridcolor="#f0f4f8",
            range=[0, 1.15],
            zeroline=False,
            title="Repayment Progress (0% → 100% = fully paid)",
        ),
        xaxis=dict(gridcolor="#f0f4f8"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_traces(hovertemplate="%{y:.1%}")
    return fig


def spv_covenant_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar: delinquency rate (colored red if breach) vs covenant limit per SPV.
    The gap between the bars is the headroom — instantly readable.
    """
    spv = df.sort_values("spv_id")

    bar_colors = [
        BRAND_COLORS["danger"] if b else BRAND_COLORS["accent"]
        for b in spv["covenant_delinquency_breach"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Actual Delinquency Rate",
            x=spv["spv_id"],
            y=spv["delinquency_rate"],
            marker_color=bar_colors,
            text=[f"{r:.2%}" for r in spv["delinquency_rate"]],
            textposition="outside",
            hovertemplate="%{x}<br>Delinquency: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Covenant Limit",
            x=spv["spv_id"],
            y=spv["covenant_max_delinquency_pct"],
            marker_color="rgba(107,114,128,0.18)",
            marker_line=dict(color="#94a3b8", width=1.5),
            text=[f"{r:.2%} limit" for r in spv["covenant_max_delinquency_pct"]],
            textposition="outside",
            hovertemplate="%{x}<br>Covenant Limit: %{y:.2%}<extra></extra>",
        )
    )

    fig.update_layout(
        **_LAYOUT,
        title=dict(
            text="Delinquency Rate vs. Covenant Limit — All SPVs",
            font=dict(size=15, weight=700),
        ),
        barmode="group",
        yaxis=dict(tickformat=".1%", gridcolor="#f0f4f8", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=340,
    )
    return fig


def spv_utilization_bar(spv_id: str, utilization: float, limit: float) -> go.Figure:
    """Horizontal progress bar showing facility utilization."""
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
