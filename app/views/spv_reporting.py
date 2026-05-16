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
from app.utils.chart_helpers import spv_covenant_comparison_chart, BRAND_COLORS
from app.utils.ui import page_header, section_header


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
    status_c  = BRAND_COLORS["danger"] if breach else BRAND_COLORS["positive"]
    status_lbl= "⚠ BREACH" if breach else "✓ OK"
    used_pct  = min(delinq / limit, 1.0) * 100
    head_pct  = min(headroom / limit, 1.0) * 100
    bar_used  = "#fca5a5" if breach else "#93c5fd"
    bar_head  = "#fecaca" if breach else "#bbf7d0"
    val_color = "#dc2626" if breach else "#0f172a"

    metrics_html = (
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;margin-top:16px;'>"
        + _metric_row("Loan Count",      f"{loans:,}")
        + _metric_row("Total Principal", f"${principal:,.0f}")
        + _metric_row("Facility Limit",  f"${fac_lim:,.0f}")
        + _metric_row("Utilization",     f"{util:.1%}")
        + _metric_row("Default Rate",    f"{default:.2%}")
        + _metric_row("Avg UW Score",    f"{uw_score:.1f} / 100")
        + "</div>"
    )

    st.html(
        f"<div style='border:2px solid {border_c};border-radius:14px;"
        f"padding:20px 22px;background:#fff;font-family:Inter,sans-serif;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;margin-bottom:4px;'>"
        f"<div style='font-size:20px;font-weight:800;color:#1e293b;'>{row['spv_id']}</div>"
        f"<span style='font-size:11px;font-weight:700;color:{status_c};margin-top:4px;'>{status_lbl}</span>"
        f"</div>"
        f"<div style='font-size:12px;color:#94a3b8;margin-bottom:14px;'>{row.get('facility_name','')}</div>"
        f"<div style='font-size:10px;font-weight:600;color:#64748b;text-transform:uppercase;"
        f"letter-spacing:.07em;margin-bottom:5px;'>Delinquency Covenant</div>"
        f"<div style='display:flex;height:8px;border-radius:4px;"
        f"overflow:hidden;background:#f1f5f9;margin-bottom:5px;'>"
        f"<div style='width:{used_pct:.1f}%;background:{bar_used};'></div>"
        f"<div style='width:{head_pct:.1f}%;background:{bar_head};'></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:0;'>"
        f"<span>Actual <strong style='color:{val_color}'>{delinq:.2%}</strong></span>"
        f"<span>Headroom <strong style='color:{status_c}'>{headroom:.2%}</strong></span>"
        f"<span>Limit <strong>{limit:.2%}</strong></span>"
        f"</div>"
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

    # 2. COMPARISON CHART — all SPVs in one view
    section_header(
        "Delinquency Rate vs. Covenant Limit",
        "Blue = within limit · Red = breach · Grey = covenant ceiling · Gap = operating headroom",
    )
    st.plotly_chart(spv_covenant_comparison_chart(spv), use_container_width=True)

    st.divider()

    # 3. DETAIL CARDS
    section_header("Facility Detail")
    cols = st.columns(len(spv))
    for col, (_, row) in zip(cols, spv.sort_values("spv_id").iterrows()):
        with col:
            _detail_card(row)

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
