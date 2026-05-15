"""
overview.py — Portfolio health scorecard.

Layout (top to bottom):
  1. Status banner  — answers "is anything broken?" in one line
  2. KPI row        — four headline numbers with 30-day deltas
  3. Two charts     — delinquency trend (with covenant line) | origination volume
  4. SPV covenant   — compact headroom row per facility
  5. Recon badge    — data-integrity signal
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.chart_helpers import (
    BRAND_COLORS,
    delinquency_trend_chart,
    origination_volume_chart,
)
from app.utils.ui import page_header, section_header


@st.cache_data(ttl=300)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily        = db.table("fct_portfolio_daily")
    originations = db.table("fct_originations")
    spv          = db.table("fct_spv_allocation")
    recon        = db.table("rpt_reconciliation")
    return daily, originations, spv, recon


def _status_banner(spv: pd.DataFrame, current_delinq: float) -> None:
    """Single-line status at the top: the first thing a business user should read."""
    breaches = spv[spv["covenant_delinquency_breach"].astype(bool)]

    if not breaches.empty:
        names = ", ".join(breaches["spv_id"].tolist())
        st.error(
            f"**COVENANT BREACH — {names}**: delinquency exceeds facility limit. "
            "Lender has right to pull funding. Immediate review required.",
            icon="🔴",
        )
        return

    # Check headroom tightness (< 2pp headroom = amber)
    spv["headroom"] = spv["covenant_max_delinquency_pct"] - spv["delinquency_rate"]
    tight = spv[spv["headroom"] < 0.02]
    if not tight.empty:
        names = ", ".join(tight["spv_id"].tolist())
        st.warning(
            f"**WATCH — {names}**: delinquency within 2 pp of covenant limit. "
            "Monitor daily.",
            icon="🟡",
        )
    else:
        st.success(
            f"All covenants within limits · Portfolio delinquency {current_delinq:.2%}",
            icon="✅",
        )


def _spv_covenant_row(spv: pd.DataFrame) -> None:
    """
    Compact SPV health cards — one per facility.
    Each card is a fully self-contained HTML block (no split tags, no HTML comments).
    """
    cols = st.columns(len(spv))
    for col, (_, row) in zip(cols, spv.sort_values("spv_id").iterrows()):
        breach       = bool(row.get("covenant_delinquency_breach", False))
        delinq       = float(row.get("delinquency_rate", 0))
        limit        = float(row.get("covenant_max_delinquency_pct", 0.08))
        headroom     = max(limit - delinq, 0)
        util         = float(row.get("facility_utilization", 0))
        loans        = int(row.get("loan_count", 0))
        status_color = BRAND_COLORS["danger"] if breach else BRAND_COLORS["positive"]
        status_label = "⚠ BREACH" if breach else "✓ OK"
        used_pct     = f"{min(delinq/limit,1)*100:.1f}%"
        head_pct     = f"{min(headroom/limit,1)*100:.1f}%"
        used_color   = BRAND_COLORS["danger"] if breach else "#93c5fd"
        head_color   = "#fecaca" if breach else "#bbf7d0"

        with col:
            st.markdown(
                f"""<div style="border:1px solid #e2e8f0;border-radius:12px;
                                padding:16px 18px;background:#fff;">
                      <div style="display:flex;justify-content:space-between;
                                  align-items:center;margin-bottom:4px;">
                        <span style="font-size:17px;font-weight:800;
                                     color:#1e293b;">{row['spv_id']}</span>
                        <span style="font-size:11px;font-weight:700;
                                     color:{status_color};">{status_label}</span>
                      </div>
                      <div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">
                        {row.get('facility_name','')}
                      </div>
                      <div style="display:flex;height:8px;border-radius:4px;
                                  overflow:hidden;background:#f1f5f9;margin-bottom:6px;">
                        <div style="width:{used_pct};background:{used_color};"></div>
                        <div style="width:{head_pct};background:{head_color};"></div>
                      </div>
                      <div style="display:flex;justify-content:space-between;
                                  font-size:11px;color:#64748b;margin-bottom:8px;">
                        <span>Delinquency <strong style="color:#1e293b;">{delinq:.2%}</strong></span>
                        <span>Limit <strong>{limit:.2%}</strong></span>
                      </div>
                      <div style="font-size:12px;color:#475569;">
                        Headroom: <strong style="color:{status_color};">{headroom:.2%}</strong>
                        &nbsp;·&nbsp; {loans:,} loans
                        &nbsp;·&nbsp; Util: <strong>{util:.1%}</strong>
                      </div>
                    </div>""",
                unsafe_allow_html=True,
            )


def render() -> None:
    """Render the Portfolio Overview page."""
    page_header(
        "Portfolio Overview",
        "Real-time portfolio health — covenants, delinquency trends, "
        "origination volume, and data-integrity status.",
    )

    try:
        daily, originations, spv, recon = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.info("Run `make dev` to seed and transform data.")
        return

    daily["date_day"] = pd.to_datetime(daily["date_day"])
    daily = daily.sort_values("date_day")
    latest = daily.iloc[-1]

    prior_row = daily[
        daily["date_day"] <= daily["date_day"].max() - pd.Timedelta(days=30)
    ]
    prior = prior_row.iloc[-1] if not prior_row.empty else None

    def _delta(col: str) -> float | None:
        return float(latest[col]) - float(prior[col]) if prior is not None else None

    # 1. STATUS BANNER — most important signal, always at the top
    _status_banner(spv, float(latest["delinquency_rate"]))
    st.divider()

    # 2. KPI ROW
    c1, c2, c3, c4 = st.columns(4)
    total_originated = float(spv["total_principal"].sum())

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
        delinq        = float(latest["delinquency_rate"])
        delinq_delta  = _delta("delinquency_rate")
        st.metric(
            "Delinquency Rate",
            f"{delinq:.2%}",
            delta=f"{delinq_delta:+.2%} vs 30d" if delinq_delta is not None else None,
            delta_color="inverse",
            help="% of outstanding principal that is 30+ days past due.",
        )
    with c4:
        default_rate  = float(latest["default_rate"])
        default_delta = _delta("default_rate")
        st.metric(
            "Default Rate",
            f"{default_rate:.2%}",
            delta=f"{default_delta:+.2%} vs 30d" if default_delta is not None else None,
            delta_color="inverse",
            help="% of outstanding principal classified as defaulted (90+ DPD).",
        )

    st.divider()

    # 3. CHARTS SIDE BY SIDE — saves vertical scroll; trend left, volume right
    min_covenant = float(spv["covenant_max_delinquency_pct"].min()) if not spv.empty else None
    last_year    = daily[daily["date_day"] >= daily["date_day"].max() - pd.Timedelta(days=365)]

    st.plotly_chart(
        delinquency_trend_chart(last_year, covenant_limit=min_covenant),
        use_container_width=True,
    )
    st.plotly_chart(
        origination_volume_chart(originations),
        use_container_width=True,
    )

    st.divider()

    # 4. SPV COVENANT HEADROOM
    section_header("SPV Covenant Headroom",
                   "Green = available headroom before breach · Red = consumed by delinquency")
    _spv_covenant_row(spv)

    st.divider()

    # 5. RECONCILIATION BADGE — data integrity at a glance
    section_header("Data Integrity")
    if not recon.empty:
        all_pass  = all(r == "PASS" for r in recon["reconciliation_status"])
        ts        = str(recon.iloc[0].get("reconciled_at", ""))[:19]
        if all_pass:
            st.success(
                f"✅ All {len(recon)} reconciliation metrics PASS — "
                f"warehouse matches source system as of {ts}.",
            )
        else:
            fail_n = sum(1 for r in recon["reconciliation_status"] if r == "FAIL")
            st.error(
                f"❌ {fail_n}/{len(recon)} metrics FAIL — "
                "see **Reconciliation Audit** tab for details.",
            )
    else:
        st.info("Reconciliation data not available.")
