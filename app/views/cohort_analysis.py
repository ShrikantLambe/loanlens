"""
cohort_analysis.py — Vintage cohort performance analysis.

Story told top-to-bottom:
  1. Insight callout   — which cohort is worst / best? (decision anchor)
  2. Default ranking   — all cohorts sorted worst-to-best (bar chart)
  3. Heatmap           — full vintage × months-on-book view
  4. Repayment curves  — user selects cohorts to compare trajectories
  5. Summary table     — sortable reference data
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.chart_helpers import (
    cohort_heatmap,
    cohort_default_ranking_chart,
    repayment_curves_chart,
)


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    return db.table("fct_cohort_performance")


def _insight_callout(summary: pd.DataFrame) -> None:
    """
    One-sentence headline that answers the most common business question:
    'Which cohort should I be worried about, and which is my best performer?'
    """
    worst = summary.loc[summary["final_default_rate"].idxmax()]
    best  = summary.loc[summary["final_default_rate"].idxmin()]
    avg   = summary["final_default_rate"].mean()

    worst_label = worst["cohort_label"]
    best_label  = best["cohort_label"]
    worst_rate  = float(worst["final_default_rate"])
    best_rate   = float(best["final_default_rate"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Worst Cohort",
            worst_label,
            f"{worst_rate:.2%} default rate",
            delta_color="inverse",
            help="Cohort with highest peak cumulative default rate.",
        )
    with c2:
        st.metric(
            "Best Cohort",
            best_label,
            f"{best_rate:.2%} default rate",
            help="Cohort with lowest peak cumulative default rate.",
        )
    with c3:
        st.metric(
            "Portfolio Average",
            f"{avg:.2%}",
            help="Mean peak default rate across all cohorts.",
        )


def render() -> None:
    """Render the Cohort Analysis page."""
    st.title("Cohort Analysis")
    st.caption(
        "How do loans perform over time, grouped by the month they were originated? "
        "Earlier cohorts are mature; recent cohorts are still developing. "
        "Deteriorating curves signal underwriting or macro stress."
    )

    try:
        df = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    if df.empty:
        st.info("No cohort data available. Run `make dev` first.")
        return

    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    df = df.sort_values(["cohort_month", "months_on_book"])

    # Build summary once (reused across sections)
    summary = (
        df.groupby("cohort_label")
        .agg(
            cohort_size        =("cohort_size",            "max"),
            cohort_principal   =("cohort_principal",       "max"),
            max_months_on_book =("months_on_book",         "max"),
            final_default_rate =("cumulative_default_rate","max"),
        )
        .reset_index()
        .sort_values("cohort_label")
    )

    all_cohorts = sorted(df["cohort_label"].unique().tolist())

    # 1. INSIGHT CALLOUT
    _insight_callout(summary)
    st.divider()

    # 2. DEFAULT RANKING — bar chart sorted worst to best
    st.subheader("Default Rate by Cohort — Worst to Best")
    st.caption(
        "Peak cumulative default rate observed for each cohort. "
        "Red = above 6%, amber = 3–6%, green = below 3%."
    )
    st.plotly_chart(cohort_default_ranking_chart(df), use_container_width=True)

    st.divider()

    # 3. HEATMAP — vintage × months-on-book
    st.subheader("Vintage Heatmap — Default Rate Develops Over Time")
    st.caption(
        "Each row is an origination cohort (month). Each column is months since funding. "
        "Read left-to-right: defaults accumulate as loans age. "
        "Darker cells = higher cumulative defaults. "
        "Compare rows to spot which vintages are aging worse than peers."
    )
    st.plotly_chart(cohort_heatmap(df), use_container_width=True)

    st.divider()

    # 4. REPAYMENT CURVES — user-selected cohorts
    st.subheader("Repayment Progress Curves")
    st.caption(
        "Track how quickly each cohort repays. Flat or declining curves indicate "
        "missed payments or defaults. 100% = cohort fully paid off."
    )

    worst_label = summary.loc[summary["final_default_rate"].idxmax(), "cohort_label"]
    default_sel = [worst_label] + [c for c in all_cohorts[:5] if c != worst_label]

    selected = st.multiselect(
        "Select cohorts to compare (worst performer pre-selected)",
        options=all_cohorts,
        default=default_sel[:6],
        help="Each label is a monthly origination vintage (MV-YYYY-MM).",
    )

    if selected:
        st.plotly_chart(repayment_curves_chart(df, selected), use_container_width=True)
    else:
        st.info("Select at least one cohort above.")

    st.divider()

    # 5. SUMMARY TABLE — sortable reference
    st.subheader("Cohort Summary")
    disp = summary.copy()
    disp["cohort_principal"]    = disp["cohort_principal"].apply(lambda x: f"${x:,.0f}")
    disp["final_default_rate"]  = disp["final_default_rate"].apply(lambda x: f"{x:.2%}")
    disp = disp.rename(columns={
        "cohort_label":        "Cohort",
        "cohort_size":         "Loans",
        "cohort_principal":    "Principal",
        "max_months_on_book":  "Months Tracked",
        "final_default_rate":  "Peak Default Rate",
    })
    st.dataframe(disp, use_container_width=True, hide_index=True)
