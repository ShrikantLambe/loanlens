"""
spv_reporting.py — SPV-level portfolio breakdown and covenant monitoring.

Shows: three SPV columns with facility metrics, utilization bars,
delinquency vs. covenant, and a breach warning banner.
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.chart_helpers import spv_utilization_bar, BRAND_COLORS


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Load SPV allocation data."""
    return db.table("fct_spv_allocation")


def render() -> None:
    """Render the SPV Reporting page."""
    st.title("SPV Reporting")
    st.caption(
        "Per-SPV portfolio breakdown, facility utilization, and covenant monitoring. "
        "Covenant breach triggers a lender's right to pull funding."
    )

    try:
        spv = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    if spv.empty:
        st.info("No SPV data available. Run `make dev` first.")
        return

    # Breach warning banner
    breaches = spv[spv["covenant_delinquency_breach"].astype(bool)]
    if not breaches.empty:
        breach_list = ", ".join(breaches["spv_id"].tolist())
        st.error(
            f"⚠️ COVENANT BREACH DETECTED on {breach_list}. "
            "Delinquency rate exceeds facility threshold. Immediate review required."
        )
    else:
        st.success("✅ All SPV covenants are within limits.")

    st.divider()

    # Three-column SPV layout
    cols = st.columns(len(spv))
    for col, (_, row) in zip(cols, spv.sort_values("spv_id").iterrows()):
        with col:
            breach = bool(row.get("covenant_delinquency_breach", False))
            header_color = BRAND_COLORS["danger"] if breach else BRAND_COLORS["primary"]

            st.markdown(
                f"<h3 style='color:{header_color}'>{row['spv_id']}</h3>",
                unsafe_allow_html=True,
            )
            st.caption(row.get("facility_name", ""))

            st.metric("Loan Count", f"{int(row.get('loan_count', 0)):,}")
            st.metric(
                "Total Principal",
                f"${float(row.get('total_principal', 0)):,.0f}",
            )
            st.metric(
                "Facility Limit",
                f"${float(row.get('facility_limit', 0)):,.0f}",
            )

            # Utilization bar
            util = float(row.get("facility_utilization", 0))
            st.plotly_chart(
                spv_utilization_bar(
                    row["spv_id"],
                    util,
                    float(row.get("facility_limit", 0)),
                ),
                use_container_width=True,
            )

            delinq = float(row.get("delinquency_rate", 0))
            covenant = float(row.get("covenant_max_delinquency_pct", 0))
            headroom = covenant - delinq
            st.metric(
                "Delinquency Rate",
                f"{delinq:.2%}",
                delta=f"{'−' if headroom < 0 else '+'}{abs(headroom):.2%} vs {covenant:.2%} limit",
                delta_color="inverse" if breach else "normal",
            )

            st.metric(
                "Default Rate",
                f"{float(row.get('default_rate', 0)):.2%}",
            )
            st.metric(
                "Avg UW Score",
                f"{float(row.get('avg_underwriting_score', 0)):.1f}",
            )

    st.divider()

    # Full data table
    st.subheader("SPV Detail Table")
    display_cols = [
        "spv_id", "facility_name", "loan_count", "total_principal",
        "facility_limit", "facility_utilization", "delinquency_rate",
        "covenant_max_delinquency_pct", "default_rate",
        "avg_underwriting_score", "covenant_delinquency_breach",
    ]
    available = [c for c in display_cols if c in spv.columns]
    st.dataframe(spv[available], use_container_width=True, hide_index=True)
