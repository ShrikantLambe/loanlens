"""
cohort_analysis.py — Vintage cohort analysis page.

Shows: cohort selector, heatmap of cumulative default rate,
and repayment curves by cohort.
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.chart_helpers import cohort_heatmap, repayment_curves_chart


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Load cohort performance data."""
    return db.table("fct_cohort_performance")


def render() -> None:
    """Render the Cohort Analysis page."""
    st.title("Cohort Analysis")
    st.caption(
        "Vintage repayment curves and default rates by origination cohort. "
        "Each cohort is a monthly vintage (e.g. MV-2022-06)."
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

    all_cohorts = sorted(df["cohort_label"].unique().tolist())

    # --- Heatmap (all cohorts) ---
    st.subheader("Cumulative Default Rate Heatmap")
    st.plotly_chart(cohort_heatmap(df), use_container_width=True)

    st.divider()

    # --- Repayment curves (user-selected cohorts) ---
    st.subheader("Repayment Curves")
    default_selection = all_cohorts[:6] if len(all_cohorts) >= 6 else all_cohorts
    selected = st.multiselect(
        "Select cohorts to compare",
        options=all_cohorts,
        default=default_selection,
        help="Each cohort is a monthly vintage label (MV-YYYY-MM).",
    )

    if selected:
        st.plotly_chart(
            repayment_curves_chart(df, selected),
            use_container_width=True,
        )
    else:
        st.info("Select at least one cohort above.")

    st.divider()

    # --- Summary table ---
    st.subheader("Cohort Summary Table")
    summary = (
        df.groupby("cohort_label")
        .agg(
            cohort_size=("cohort_size", "max"),
            cohort_principal=("cohort_principal", "max"),
            max_months_on_book=("months_on_book", "max"),
            final_default_rate=("cumulative_default_rate", "max"),
        )
        .reset_index()
        .sort_values("cohort_label")
    )
    summary["cohort_principal"] = summary["cohort_principal"].apply(lambda x: f"${x:,.0f}")
    summary["final_default_rate"] = summary["final_default_rate"].apply(lambda x: f"{x:.2%}")
    st.dataframe(summary, use_container_width=True, hide_index=True)
