"""
overview.py — Portfolio health scorecard page.

Shows: 4 metric cards with period deltas, delinquency trend with rolling avg,
origination volume by platform, SPV covenant status cards, reconciliation badge.
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.chart_helpers import delinquency_trend_chart, origination_volume_chart, BRAND_COLORS


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
    st.caption("Portfolio health across all loans, SPVs, and origination channels.")

    try:
        daily, originations, spv, recon = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.info("Make sure you have run `make dev` to seed and transform data.")
        return

    daily["date_day"] = pd.to_datetime(daily["date_day"])
    daily = daily.sort_values("date_day")
    latest = daily.iloc[-1]

    # 30-day comparison for deltas
    thirty_days_ago = daily[daily["date_day"] <= daily["date_day"].max() - pd.Timedelta(days=30)]
    prior = thirty_days_ago.iloc[-1] if not thirty_days_ago.empty else None

    def _delta(col: str) -> float | None:
        return float(latest[col]) - float(prior[col]) if prior is not None else None

    # --- KPI cards ---
    c1, c2, c3, c4 = st.columns(4)
    total_originated = float(spv["total_principal"].sum())
    total_30d_ago = total_originated  # static, use loan count delta instead

    with c1:
        st.metric(
            "Total Originated",
            f"${total_originated:,.0f}",
            help="Sum of funded principal across all SPVs.",
        )
    with c2:
        outstanding = float(latest["outstanding_principal"])
        outstanding_delta = _delta("outstanding_principal")
        st.metric(
            "Outstanding Principal",
            f"${outstanding:,.0f}",
            delta=f"${outstanding_delta:+,.0f} vs 30d" if outstanding_delta else None,
        )
    with c3:
        delinq = float(latest["delinquency_rate"])
        delinq_delta = _delta("delinquency_rate")
        st.metric(
            "Delinquency Rate",
            f"{delinq:.2%}",
            delta=f"{delinq_delta:+.2%} vs 30d" if delinq_delta is not None else None,
            delta_color="inverse",
            help="% of outstanding principal currently 30+ DPD.",
        )
    with c4:
        default_rate = float(latest["default_rate"])
        default_delta = _delta("default_rate")
        st.metric(
            "Default Rate",
            f"{default_rate:.2%}",
            delta=f"{default_delta:+.2%} vs 30d" if default_delta is not None else None,
            delta_color="inverse",
            help="% of outstanding principal classified as defaulted.",
        )

    st.divider()

    # --- Delinquency trend ---
    last_year = daily[daily["date_day"] >= daily["date_day"].max() - pd.Timedelta(days=365)]
    st.plotly_chart(delinquency_trend_chart(last_year), use_container_width=True)

    # --- Origination volume ---
    st.plotly_chart(origination_volume_chart(originations), use_container_width=True)

    st.divider()

    # --- SPV covenant status ---
    st.subheader("SPV Covenant Status")
    cols = st.columns(len(spv))
    for col, (_, row) in zip(cols, spv.sort_values("spv_id").iterrows()):
        with col:
            breach = bool(row.get("covenant_delinquency_breach", False))
            border = BRAND_COLORS["danger"] if breach else BRAND_COLORS["positive"]
            badge = "🔴 BREACH" if breach else "🟢 OK"

            st.markdown(
                f"""
                <div style="border:2px solid {border}; border-radius:10px; padding:16px 18px; background:#fff;">
                    <div style="font-size:18px; font-weight:800; color:#1e293b">{row['spv_id']}</div>
                    <div style="font-size:12px; color:#64748b; margin-bottom:10px">{row.get('facility_name','')}</div>
                    <div style="font-size:13px; margin-bottom:4px">
                        <span style="color:#64748b">Delinquency</span>
                        <span style="float:right; font-weight:700; color:{'#dc2626' if breach else '#1e293b'}">{float(row.get('delinquency_rate',0)):.2%}</span>
                    </div>
                    <div style="font-size:12px; color:#94a3b8; margin-bottom:10px">
                        Limit: {float(row.get('covenant_max_delinquency_pct',0)):.2%}
                    </div>
                    <div style="font-size:12px; color:#64748b">
                        Utilization: <strong>{float(row.get('facility_utilization',0)):.1%}</strong>
                    </div>
                    <div style="margin-top:10px; font-size:12px; font-weight:700; color:{border}">{badge}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # --- Reconciliation status ---
    st.subheader("Reconciliation Status")
    if not recon.empty:
        all_pass = all(r == "PASS" for r in recon["reconciliation_status"])
        if all_pass:
            st.success(f"✅ All {len(recon)} metrics reconciled — last checked {recon.iloc[0].get('reconciled_at', 'N/A')}")
        else:
            fail_count = sum(1 for r in recon["reconciliation_status"] if r == "FAIL")
            st.error(f"❌ {fail_count}/{len(recon)} metrics failed — see Reconciliation Audit tab.")
    else:
        st.info("Reconciliation data not available.")
