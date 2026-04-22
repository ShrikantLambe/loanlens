"""
overview.py — Portfolio health scorecard page.

Shows: 4 metric cards, delinquency trend, origination volume by platform,
SPV covenant status badges, and last reconciliation status.
"""

import streamlit as st
import pandas as pd
from app.utils import snowflake_conn as db
from app.utils.chart_helpers import delinquency_trend_chart, origination_volume_chart


@st.cache_data(ttl=300)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all data needed for the overview page."""
    daily = db.table("fct_portfolio_daily")
    originations = db.table("fct_originations")
    spv = db.table("fct_spv_allocation")
    recon = db.table("rpt_reconciliation")
    return daily, originations, spv, recon


def render() -> None:
    """Render the Portfolio Overview page."""
    st.title("Portfolio Overview")
    st.caption("Real-time portfolio health across all loans and SPVs.")

    try:
        daily, originations, spv, recon = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.info("Make sure you have run `make dev` to seed and transform data.")
        return

    # Ensure date column is datetime
    daily["date_day"] = pd.to_datetime(daily["date_day"])

    latest = daily.sort_values("date_day").iloc[-1]

    # --- KPI cards ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Total Originated",
            f"${float(spv['total_principal'].sum()):,.0f}",
            help="Sum of principal across all SPVs.",
        )
    with c2:
        st.metric(
            "Outstanding Principal",
            f"${float(latest['outstanding_principal']):,.0f}",
        )
    with c3:
        st.metric(
            "Delinquency Rate",
            f"{float(latest['delinquency_rate']):.2%}",
        )
    with c4:
        st.metric(
            "Default Rate",
            f"{float(latest['default_rate']):.2%}",
        )

    st.divider()

    # --- Delinquency trend (last 365 days) ---
    last_year = daily[daily["date_day"] >= daily["date_day"].max() - pd.Timedelta(days=365)]
    st.plotly_chart(delinquency_trend_chart(last_year), use_container_width=True)

    # --- Origination volume by platform ---
    st.plotly_chart(origination_volume_chart(originations), use_container_width=True)

    st.divider()

    # --- SPV covenant status badges ---
    st.subheader("SPV Covenant Status")
    cols = st.columns(len(spv))
    for col, (_, row) in zip(cols, spv.iterrows()):
        with col:
            breach = bool(row.get("covenant_delinquency_breach", False))
            status_color = "🔴" if breach else "🟢"
            st.markdown(f"**{status_color} {row['spv_id']}**")
            st.caption(row.get("facility_name", ""))
            delinq = float(row.get("delinquency_rate", 0))
            limit = float(row.get("covenant_max_delinquency_pct", 0))
            st.metric(
                "Delinquency",
                f"{delinq:.2%}",
                delta=f"Limit: {limit:.2%}",
                delta_color="inverse" if breach else "off",
            )

    st.divider()

    # --- Reconciliation status ---
    st.subheader("Reconciliation Status")
    if not recon.empty:
        last_recon = recon.iloc[0]
        all_pass = all(r == "PASS" for r in recon["reconciliation_status"])
        badge = "✅ PASS" if all_pass else "❌ FAIL"
        st.markdown(f"**Last reconciled:** {last_recon.get('reconciled_at', 'N/A')}  —  {badge}")
        if not all_pass:
            st.warning("One or more reconciliation metrics failed. See Reconciliation Audit tab.")
    else:
        st.info("Reconciliation data not available.")
