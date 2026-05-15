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


def _detail_card(row: pd.Series) -> None:
    """Per-SPV card with all key metrics and visual headroom indicator."""
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
    collected= float(row.get("total_collected",              0))
    yield_   = (collected / principal) if principal else 0

    border_c = BRAND_COLORS["danger"] if breach else "#e2e8f0"
    head_c   = BRAND_COLORS["danger"] if breach else BRAND_COLORS["positive"]

    # Headroom bar: red consumed portion + green headroom portion
    used_pct = min(delinq / limit, 1.0) * 100
    head_pct = min(headroom / limit, 1.0) * 100

    st.markdown(
        f"""
        <div style="border:2px solid {border_c}; border-radius:12px;
                    padding:20px 22px; background:#fff; height:100%;">
          <div style="font-size:20px; font-weight:800; color:#1e293b;
                      margin-bottom:2px">{row['spv_id']}</div>
          <div style="font-size:12px; color:#64748b;
                      margin-bottom:14px">{row.get('facility_name','')}</div>

          <!-- Covenant headroom bar -->
          <div style="font-size:11px; color:#64748b; margin-bottom:4px; font-weight:600">
            DELINQUENCY COVENANT
          </div>
          <div style="display:flex; height:10px; border-radius:5px; overflow:hidden;
                      background:#f1f5f9; margin-bottom:4px;">
            <div style="width:{used_pct:.1f}%; background:{'#fca5a5' if breach else '#93c5fd'};"></div>
            <div style="width:{head_pct:.1f}%; background:{'#fecaca' if breach else '#bbf7d0'};"></div>
          </div>
          <div style="display:flex; justify-content:space-between;
                      font-size:11px; color:#64748b; margin-bottom:14px;">
            <span>Actual: <strong style="color:{'#dc2626' if breach else '#1e293b'}">{delinq:.2%}</strong></span>
            <span>Headroom: <strong style="color:{head_c}">{headroom:.2%}</strong></span>
            <span>Limit: <strong>{limit:.2%}</strong></span>
          </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Loan Count",       f"{loans:,}")
        st.metric("Total Principal",  f"${principal:,.0f}")
        st.metric("Default Rate",     f"{default:.2%}")
    with c2:
        st.metric("Facility Limit",   f"${fac_lim:,.0f}")
        st.metric("Utilization",      f"{util:.1%}")
        st.metric("Avg UW Score",     f"{uw_score:.1f} / 100")

    st.markdown("</div>", unsafe_allow_html=True)


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
