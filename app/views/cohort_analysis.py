from __future__ import annotations
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
from app.utils import echarts as ec
from app.utils.ui import page_header, section_header


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
            f"↑ {worst_rate:.2%} default rate",
            delta_color="inverse",   # red — rising defaults are adverse
            help=(
                "The origination vintage with the highest peak cumulative default rate. "
                "Source: fct_cohort_performance · Metric: MAX(cumulative_default_rate). "
                "Earlier vintages typically have higher rates because they've had more time "
                "to season — defaults emerge 6–18 months after origination."
            ),
        )
    with c2:
        st.metric(
            "Best Cohort",
            best_label,
            f"{best_rate:.2%} default rate",
            delta_color="off",       # neutral grey — no directional arrow; low is good
            help=(
                "The origination vintage with the lowest peak cumulative default rate. "
                "Recent 2024 cohorts often rank best because they haven't yet had enough "
                "time to accumulate defaults — a J-curve effect, not better underwriting. "
                "Source: fct_cohort_performance."
            ),
        )
    with c3:
        st.metric(
            "Portfolio Average",
            f"{avg:.2%}",
            help=(
                "Unweighted mean of each cohort's peak cumulative default rate. "
                "Weighted by cohort principal would give a higher number for portfolios "
                "with large late-vintage originations. Source: fct_cohort_performance."
            ),
        )


def render() -> None:
    """Render the Cohort Analysis page."""
    page_header(
        "Cohort Analysis",
        "How do loans perform over time, grouped by the month they were originated? "
        "Earlier cohorts are mature; recent cohorts are still developing. "
        "Deteriorating curves signal underwriting or macro stress.",
        badge="Vintage View",
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
    section_header(
        "Default Rate by Cohort — Worst to Best",
        "Peak cumulative default rate · Red > 6% · Amber 3–6% · Green < 3%",
    )
    _col_toggle, _col_n = st.columns([3, 1])
    with _col_toggle:
        show_all = st.toggle("Show all cohorts", value=False,
                             help="Default: top 10 worst. Toggle to see every vintage.")
    with _col_n:
        top_n = st.select_slider(
            "Top N", options=[5, 10, 15, 20], value=10,
            disabled=show_all,
            label_visibility="collapsed",
        ) if not show_all else None

    _top_n_arg = None if show_all else top_n
    ec.render(
        ec.cohort_ranking_option(df, top_n=_top_n_arg),
        height="480px",
        key="cohort_ranking",
    )

    st.divider()

    # 3. HEATMAP — vintage × months-on-book
    section_header(
        "Vintage Heatmap — Default Rate Over Loan Life",
        "Each row = origination cohort · Each column = months since funding · Darker = higher defaults",
    )
    ec.render(ec.cohort_heatmap_option(df), height="520px", key="cohort_heatmap")

    st.divider()

    # 4. REPAYMENT CURVES — user-selected cohorts
    section_header(
        "Repayment Progress Curves",
        "Flat or declining curves = missed payments or defaults · 100% = fully paid off",
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
        ec.render(ec.repayment_curves_option(df, selected), height="400px", key="repayment_curves")
    else:
        st.info("Select at least one cohort above.")

    st.divider()

    # 5. SUMMARY TABLE — sortable reference
    section_header("Cohort Summary")
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
