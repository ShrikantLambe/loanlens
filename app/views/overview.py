from __future__ import annotations
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
from app.utils.chart_helpers import BRAND_COLORS
from app.utils import echarts as ec
from app.utils.ui import page_header, section_header


@st.cache_data(ttl=300)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    weekly       = db.table("fct_delinquency_weekly")
    originations = db.table("fct_originations")
    spv          = db.table("fct_spv_allocation")
    recon        = db.table("rpt_reconciliation")
    summary      = db.table("rpt_portfolio_summary")
    return weekly, originations, spv, recon, summary


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

        card_bg = "rgba(239,68,68,0.04)" if breach else "#ffffff"
        bdr_l   = f"border-left:4px solid {status_color};"
        with col:
            st.html(
                f"<div style='border:1px solid #e4e9f0;{bdr_l}border-radius:12px;"
                f"padding:16px 18px;background:{card_bg};font-family:Inter,sans-serif;"
                f"box-shadow:0 1px 4px rgba(15,23,42,.05);'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;margin-bottom:4px;'>"
                f"<span style='font-size:17px;font-weight:800;color:#0f172a;'>{row['spv_id']}</span>"
                f"<span style='font-size:11px;font-weight:700;color:{status_color};"
                f"background:{'rgba(239,68,68,.1)' if breach else 'rgba(16,185,129,.1)'};"
                f"padding:2px 8px;border-radius:10px;'>{status_label}</span>"
                f"</div>"
                f"<div style='font-size:11px;color:#94a3b8;margin-bottom:10px;'>{row.get('facility_name','')}</div>"
                f"<div style='display:flex;height:10px;border-radius:5px;"
                f"overflow:hidden;background:#f0f4f8;margin-bottom:6px;'>"
                f"<div style='width:{used_pct};background:{used_color};border-radius:5px 0 0 5px;'></div>"
                f"<div style='width:{head_pct};background:{head_color};'></div>"
                f"</div>"
                f"<div style='display:flex;justify-content:space-between;"
                f"font-size:11px;color:#64748b;margin-bottom:8px;'>"
                f"<span>Delinquency <strong style='color:#0f172a;'>{delinq:.2%}</strong></span>"
                f"<span>Limit <strong>{limit:.2%}</strong></span>"
                f"</div>"
                f"<div style='font-size:12px;color:{status_color};font-weight:600;'>"
                f"Headroom: {headroom:.2%}"
                f"<span style='color:#8898aa;font-weight:400;'>"
                f"&nbsp;·&nbsp;{loans:,} loans&nbsp;·&nbsp;Util {util:.1%}</span>"
                f"</div>"
                f"</div>"
            )


def render() -> None:
    """Render the Portfolio Overview page."""
    page_header(
        "Portfolio Overview",
        "Real-time portfolio health — covenants, delinquency trends, "
        "origination volume, and data-integrity status.",
    )

    try:
        weekly, originations, spv, recon, summary = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.info("Run `make dev` to seed and transform data.")
        return

    weekly["week_date"] = pd.to_datetime(weekly["week_date"])
    weekly = weekly.sort_values("week_date")

    # ── Apply sidebar filters ────────────────────────────────────────────────
    _period_days = {"3 Months": 90, "6 Months": 180, "12 Months": 365, "All Time": 99999}
    _period      = st.session_state.get("filter_period", "12 Months")
    _sel_plat    = [p.lower() for p in st.session_state.get("filter_platforms", ["DoorDash","Amazon","Mindbody","Worldpay","Shopify"])]
    _sel_spvs    = st.session_state.get("filter_spvs", ["SPV-A","SPV-B","SPV-C"])

    _days = _period_days.get(_period, 365)
    if _days < 99999:
        weekly = weekly[weekly["week_date"] >= weekly["week_date"].max() - pd.Timedelta(days=_days)]
    if _sel_plat:
        originations = originations[originations["platform"].isin(_sel_plat)]
    if _sel_spvs:
        spv = spv[spv["spv_id"].isin(_sel_spvs)]

    latest_week  = weekly.iloc[-1] if not weekly.empty else None
    prior_week   = weekly[weekly["week_date"] <= weekly["week_date"].max() - pd.Timedelta(days=30)] if not weekly.empty else weekly
    prior        = prior_week.iloc[-1] if not prior_week.empty else None

    def _delta(col: str) -> float | None:
        if latest_week is None or prior is None:
            return None
        return float(latest_week[col]) - float(prior[col])

    # Summary row — single source of truth for KPI cards
    row = summary.iloc[0] if not summary.empty else {}

    # 1. STATUS BANNER
    current_delinq = float(row.get("delinquency_rate_pct", 0)) / 100
    _status_banner(spv, current_delinq)
    st.divider()

    # ── 2. KPI ROW with sparklines ────────────────────────────────────────────
    # Sparkline history: last 16 weeks of weekly data
    spark_weeks = weekly.sort_values("week_date").tail(16)
    delinq_hist  = (spark_weeks["delinquency_rate"] * 100).tolist()
    default_hist = (spark_weeks["default_rate"] * 100).tolist()
    # Outstanding principal history (normalised to 0-100 for sparkline shape)
    principal_hist = spark_weeks["outstanding_principal"].tolist()

    delinq_pct   = float(row.get("delinquency_rate_pct", 0))
    default_pct  = float(row.get("default_rate_pct",     0))
    total_orig   = float(row.get("total_originated",     0))
    outstanding  = float(row.get("outstanding_principal",0))
    delinq_delta = _delta("delinquency_rate")
    default_delta= _delta("default_rate")

    _d_label = (
        f"{delinq_delta*100:+.2f}pp (30d)"
        if delinq_delta is not None and abs(delinq_delta) > 0.0001 else None
    )
    _def_label = (
        f"{default_delta*100:+.2f}pp (30d)"
        if default_delta is not None and abs(default_delta) > 0.0001 else None
    )

    # Semantic color: rising delinquency/default = red even if sign is "up"
    delinq_color  = ec.PALETTE["danger"]  if delinq_pct  > 5 else ec.PALETTE["amber"] if delinq_pct > 2 else ec.PALETTE["success"]
    default_color = ec.PALETTE["danger"]  if default_pct > 4 else ec.PALETTE["amber"] if default_pct > 2 else ec.PALETTE["success"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Originated",    f"${total_orig:,.0f}",
                  help="Cumulative principal funded across all loans.")
        ec.render(ec.kpi_sparkline_option(principal_hist, ec.PALETTE["primary"]),
                  height="52px", key="spark_principal")
    with c2:
        st.metric("Outstanding Principal", f"${outstanding:,.0f}",
                  help="Principal of loans not yet paid off.")
        ec.render(ec.kpi_sparkline_option(principal_hist, ec.PALETTE["purple"]),
                  height="52px", key="spark_outstanding")
    with c3:
        st.metric("Delinquency Rate", f"{delinq_pct:.2f}%",
                  delta=_d_label, delta_color="inverse",
                  help="% of outstanding principal 30+ DPD (rpt_portfolio_summary).")
        ec.render(ec.kpi_sparkline_option(delinq_hist, delinq_color),
                  height="52px", key="spark_delinq")
    with c4:
        st.metric("Default Rate", f"{default_pct:.2f}%",
                  delta=_def_label, delta_color="inverse",
                  help="% of outstanding principal 90+ DPD (rpt_portfolio_summary).")
        ec.render(ec.kpi_sparkline_option(default_hist, default_color),
                  height="52px", key="spark_default")

    st.divider()

    # ── 3. CHARTS — side-by-side 2-column grid ───────────────────────────────
    min_covenant = float(spv["covenant_max_delinquency_pct"].min()) if not spv.empty else None
    # `weekly` is already filtered to the selected reporting period

    ch_left, ch_right = st.columns(2)
    with ch_left:
        section_header(
            "📉 Delinquency Trend",
            f"{_period} · 4-wk avg · Covenant limit marked",
        )
        ec.render(
            ec.delinquency_trend_option(weekly, covenant_limit=min_covenant),
            height="400px", key="trend_delinq",
        )
    with ch_right:
        section_header(
            "📦 Origination Volume",
            "Stacked by platform · Loan count on secondary axis",
        )
        ec.render(
            ec.origination_volume_option(originations),
            height="400px", key="chart_originations",
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
