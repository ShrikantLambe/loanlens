from __future__ import annotations
"""
spv_reporting.py — SPV facility monitoring and covenant compliance.

Story told top-to-bottom:
  1. Breach banner          — immediate alert if any covenant is broken
  2. Comparison chart       — all SPVs side-by-side (delinquency vs limit)
  3. SPV detail cards       — per-facility deep-dive with headroom context
  4. Covenant cheat sheet   — what each metric means and why it matters
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.chart_helpers import BRAND_COLORS
from app.utils import echarts as ec
from app.utils.ui import page_header, section_header
from streamlit_echarts import st_echarts


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    return db.table("fct_spv_allocation")


def _metric_row(label: str, value: str) -> str:
    """Returns an HTML snippet for one metric in the SPV detail card."""
    return (
        f"<div style='margin-bottom:12px;'>"
        f"<div style='font-size:10px;font-weight:600;color:#94a3b8;"
        f"text-transform:uppercase;letter-spacing:.07em;margin-bottom:3px;'>{label}</div>"
        f"<div style='font-size:17px;font-weight:700;color:#0f172a;"
        f"font-variant-numeric:tabular-nums;letter-spacing:-.02em;'>{value}</div>"
        f"</div>"
    )


def _detail_card(row: pd.Series) -> None:
    """
    Per-SPV card rendered as a single self-contained HTML block.
    No split tags, no st.metric inside HTML — avoids the Streamlit
    'each st.markdown is its own container' limitation.
    """
    breach   = bool(row.get("covenant_delinquency_breach", False))
    delinq   = float(row.get("delinquency_rate",             0))
    limit    = float(row.get("covenant_max_delinquency_pct", 0.08))
    headroom = max(limit - delinq, 0)
    util     = float(row.get("facility_utilization",         0))
    principal= float(row.get("total_principal",              0))
    fac_lim  = float(row.get("facility_limit",               0))
    default  = float(row.get("default_rate",                 0))
    uw_score = float(row.get("avg_underwriting_score",       0))
    loans    = int(row.get("loan_count",                     0))

    border_c  = BRAND_COLORS["danger"] if breach else "#e2e8f0"
    border_w  = "2px" if breach else "1px"
    # Faint tinted background — readable at a glance without reading text
    card_bg   = "rgba(239,68,68,0.04)" if breach else "#ffffff"
    status_c  = BRAND_COLORS["danger"] if breach else BRAND_COLORS["positive"]
    status_lbl= "⚠ BREACH" if breach else "✓ OK"
    used_pct  = min(delinq / limit, 1.0) * 100
    head_pct  = min(headroom / limit, 1.0) * 100
    # Covenant bar fill color by headroom
    if breach:
        bar_used = "#ef4444"
    elif headroom < 0.02:
        bar_used = "#f59e0b"   # amber: within 2pp of limit
    else:
        bar_used = "#2563eb"
    bar_head  = "#fecaca" if breach else "#bbf7d0"
    val_color = "#dc2626" if breach else "#060d1f"
    # Utilization alert — flag >100% in red
    util_color = "#ef4444" if util > 1.0 else "#060d1f"
    util_str  = f"<strong style='color:{util_color};'>{util:.1%}</strong>"

    metrics_html = (
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;margin-top:16px;'>"
        + _metric_row("Loan Count",      f"{loans:,}")
        + _metric_row("Total Principal", f"${principal:,.0f}")
        + _metric_row("Facility Limit",  f"${fac_lim:,.0f}")
        + _metric_row("Utilization",     util_str)
        + _metric_row("Default Rate",    f"{default:.2%}")
        + _metric_row("Avg UW Score",    f"{uw_score:.1f} / 100")
        + "</div>"
    )

    st.html(
        f"<div style='border:{border_w} solid {border_c};border-left:4px solid {status_c};"
        f"border-radius:14px;padding:20px 22px;background:{card_bg};"
        f"font-family:Inter,sans-serif;box-shadow:0 1px 4px rgba(15,23,42,.05);'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;margin-bottom:4px;'>"
        f"<div style='font-size:20px;font-weight:800;color:#0f172a;'>{row['spv_id']}</div>"
        f"<span style='font-size:11px;font-weight:700;color:{status_c};margin-top:4px;"
        f"background:{'rgba(239,68,68,.1)' if breach else 'rgba(16,185,129,.1)'};"
        f"padding:2px 10px;border-radius:12px;'>{status_lbl}</span>"
        f"</div>"
        f"<div style='font-size:12px;color:#94a3b8;margin-bottom:14px;'>{row.get('facility_name','')}</div>"
        # Bar label row
        f"<div style='display:flex;justify-content:space-between;font-size:10.5px;"
        f"font-weight:600;color:#8898aa;margin-bottom:5px;'>"
        f"<span>DELINQUENCY COVENANT</span>"
        f"<span>Actual <strong style='color:{val_color}'>{delinq:.2%}</strong>"
        f" / Limit <strong>{limit:.2%}</strong></span>"
        f"</div>"
        # Taller covenant bar (12px)
        f"<div style='position:relative;height:12px;border-radius:6px;"
        f"overflow:hidden;background:#f0f4f8;margin-bottom:8px;'>"
        f"<div style='width:{used_pct:.1f}%;height:100%;background:{bar_used};"
        f"border-radius:6px 0 0 6px;transition:width .3s;'></div>"
        f"<div style='position:absolute;top:0;left:{used_pct:.1f}%;width:{head_pct:.1f}%;"
        f"height:100%;background:{bar_head};'></div>"
        f"</div>"
        f"<div style='font-size:11px;color:{status_c};font-weight:600;margin-bottom:0;'>"
        f"Headroom: {headroom:.2%}</div>"
        f"{metrics_html}"
        f"</div>"
    )


def render() -> None:
    """Render the SPV Reporting page."""
    page_header(
        "SPV Reporting",
        "Each Special Purpose Vehicle is a ring-fenced legal entity funded by a specific "
        "lending facility. A covenant breach gives the lender the right to stop advancing "
        "new capital — directly limiting origination capacity.",
        badge="3 Active Facilities",
        badge_color="#ede9fe",
        badge_text_color="#6d28d9",
    )

    try:
        spv = _load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    if spv.empty:
        st.info("No SPV data available. Run `make dev` first.")
        return

    # 1. BREACH BANNER
    breaches = spv[spv["covenant_delinquency_breach"].astype(bool)]
    if not breaches.empty:
        names = ", ".join(breaches["spv_id"].tolist())
        st.error(
            f"⚠ **COVENANT BREACH on {names}** — delinquency rate exceeds facility threshold. "
            "Lender has contractual right to suspend funding. Escalate to treasury immediately.",
        )
    else:
        spv["headroom"] = spv["covenant_max_delinquency_pct"] - spv["delinquency_rate"]
        tightest        = spv.loc[spv["headroom"].idxmin()]
        st.success(
            f"All {len(spv)} facilities within covenant limits. "
            f"Tightest headroom: **{tightest['spv_id']}** "
            f"({float(tightest['headroom']):.2%} before breach)."
        )

    st.divider()

    # 2. COMPARISON CHART — ECharts grouped bar with click cross-filter
    section_header(
        "Delinquency Rate vs. Covenant Limit",
        "Click a bar to highlight that facility below · Blue = OK · Amber = near limit · Red = breach",
    )
    clicked = st_echarts(
        options=ec._deep_merge(ec.BASE_OPTION, ec.spv_bar_option(spv)),
        height="340px",
        key="spv_comparison",
        events={"click": "function(params){return params.name}"},
    )
    if clicked and clicked in spv["spv_id"].values:
        st.session_state["spv_focus"] = clicked
    elif "spv_focus" not in st.session_state:
        st.session_state["spv_focus"] = None

    st.divider()

    # 3. DETAIL CARDS — with ECharts gauge replacing the flat progress bar
    focus = st.session_state.get("spv_focus")
    section_header(
        "Facility Detail",
        f"Highlighting: {focus}" if focus else "Click a bar above to focus a facility",
    )
    cols = st.columns(len(spv))
    for col, (_, row) in zip(cols, spv.sort_values("spv_id").iterrows()):
        is_focused = focus is not None and row["spv_id"] == focus
        with col:
            if is_focused:
                st.html(
                    "<div style='background:#eff6ff;border:2px solid #2563eb;"
                    "border-radius:14px;padding:6px 12px;margin-bottom:6px;"
                    "font-size:11px;font-weight:700;color:#2563eb;"
                    "font-family:Inter,sans-serif;text-align:center;"
                    "letter-spacing:.06em;'>▶ SELECTED</div>"
                )
            _detail_card(row)
            # Covenant gauge below the card (same column)
            ec.render(
                ec.covenant_gauge_option(
                    actual=float(row.get("delinquency_rate", 0)),
                    limit=float(row.get("covenant_max_delinquency_pct", 0.08)),
                ),
                height="180px",
                key=f"gauge_{row['spv_id']}",
            )

    st.divider()

    # 4. COVENANT CHEAT SHEET
    with st.expander("What do these covenants mean?"):
        st.markdown(
            """
**Delinquency Covenant** — the maximum percentage of outstanding principal that
can be 30+ days past due. If exceeded, the lending facility can:
- Pause new loan advances (stops origination)
- Demand early repayment of outstanding facility draws
- Appoint a backup servicer

**Facility Utilization** — how much of the approved credit line is drawn.
High utilization (> 85%) limits your ability to fund new loans without
raising additional facility capacity.

**Underwriting Score** — internal 1–100 score assigned at origination.
A declining score on newer cohorts signals looser underwriting standards,
which typically leads to higher delinquency with a 3–6 month lag.

**Why this matters**: These aren't just reporting metrics — they are
contractual tripwires. A Finance Data Lead who monitors these daily
prevents a breach surprise that could halt the entire lending operation.
            """
        )
