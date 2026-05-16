from __future__ import annotations
"""
reconciliation.py — Warehouse vs. source system reconciliation audit.

Story told top-to-bottom:
  1. Status headline    — PASS / FAIL in large, unambiguous terms
  2. Metric table       — friendly names, formatted numbers, colour-coded status
  3. Methodology        — always visible (not buried in expander)
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.ui import page_header, section_header

# Map snake_case metric names → business-friendly display names
_METRIC_LABELS = {
    "origination_count":     "Total Loans Originated (count)",
    "origination_principal": "Total Principal Funded ($)",
    "total_collected":       "Total Repayments Collected ($)",
    "default_count":         "Defaulted Loans (count)",
}


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    return db.table("rpt_reconciliation")


def render() -> None:
    """Render the Reconciliation Audit page."""
    page_header(
        "Reconciliation Audit",
        "Every metric is compared to a control file simulating the loan servicing system. "
        "Any discrepancy > 0.1% is a hard FAIL that would block the pipeline in production.",
        badge="4 Checks",
        badge_color="#f0fdf4",
        badge_text_color="#15803d",
    )

    try:
        recon = _load_data()
    except Exception as e:
        st.error(f"Failed to load reconciliation data: {e}")
        return

    if recon.empty:
        st.info("No reconciliation data. Run `make dev` first.")
        return

    all_pass  = all(r == "PASS" for r in recon["reconciliation_status"])
    fail_count = sum(1 for r in recon["reconciliation_status"] if r == "FAIL")

    # 1. LARGE STATUS HEADLINE
    if all_pass:
        st.html(
            f"<div style='text-align:center;padding:28px 0 20px;font-family:Inter,sans-serif;'>"
            f"<div style='font-size:48px;'>✅</div>"
            f"<div style='font-size:22px;font-weight:800;color:#15803d;margin-top:8px;'>ALL METRICS RECONCILED</div>"
            f"<div style='font-size:14px;color:#64748b;margin-top:4px;'>Warehouse matches source system across all {len(recon)} checks</div>"
            f"</div>"
        )
    else:
        st.html(
            f"<div style='text-align:center;padding:28px 0 20px;font-family:Inter,sans-serif;'>"
            f"<div style='font-size:48px;'>❌</div>"
            f"<div style='font-size:22px;font-weight:800;color:#b91c1c;margin-top:8px;'>RECONCILIATION FAILURE</div>"
            f"<div style='font-size:14px;color:#64748b;margin-top:4px;'>{fail_count} of {len(recon)} metrics exceed the 0.1% tolerance threshold</div>"
            f"</div>"
        )

    # Freshness badge + simulated rerun
    recon_ts = str(recon.get("reconciled_at", pd.Series([None])).iloc[0])[:19]
    # Use session_state override if user pressed "Rerun" in this session
    if "recon_rerun_time" in st.session_state:
        recon_ts = st.session_state["recon_rerun_time"]

    try:
        recon_dt    = pd.to_datetime(recon_ts)
        hours_since = (pd.Timestamp.now() - recon_dt).total_seconds() / 3600
        if hours_since < 24:
            badge_txt   = f"🟢 Fresh · {int(hours_since)}h ago"
            badge_bg, badge_fg = "#f0fdf4", "#15803d"
        elif hours_since < 168:
            badge_txt   = f"🟡 Stale · {int(hours_since/24)}d ago — Rerun recommended"
            badge_bg, badge_fg = "#fef9c3", "#b45309"
        else:
            badge_txt   = f"🔴 Stale · {int(hours_since/24)}d ago — Rerun required"
            badge_bg, badge_fg = "#fee2e2", "#b91c1c"
    except Exception:
        badge_txt   = f"Last reconciled: {recon_ts}"
        badge_bg, badge_fg = "#f1f5f9", "#64748b"

    col_ts, col_btn = st.columns([4, 1])
    with col_ts:
        st.html(
            f"<span style='background:{badge_bg};color:{badge_fg};"
            f"padding:4px 12px;border-radius:20px;font-size:12px;"
            f"font-weight:600;font-family:Inter,sans-serif;'>{badge_txt}</span>"
        )
    with col_btn:
        if st.button("↻ Rerun", use_container_width=True, help="Simulate a pipeline re-run"):
            st.session_state["recon_rerun_time"] = (
                pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            _load_data.clear()
            st.rerun()

    st.divider()

    # 2. METRIC TABLE — friendly names, human-readable numbers
    section_header("Metric-Level Results")

    display = recon.copy()
    display["metric_name"] = display["metric_name"].map(
        lambda x: _METRIC_LABELS.get(x, x.replace("_", " ").title())
    )
    display = display.rename(columns={
        "metric_name":           "Metric",
        "warehouse_value":       "Warehouse",
        "source_value":          "Source System",
        "delta":                 "Delta",
        "delta_pct":             "Delta %",
        "reconciliation_status": "Status",
    })

    # Recompute delta_pct with full Python-float precision.
    # The dbt model stores delta_pct rounded to 4 decimal places, which makes
    # a legitimate $0.57 delta on $929M appear as 0.0000% — indistinguishable
    # from true zero. Recomputing here preserves the signal.
    raw_delta  = pd.to_numeric(recon["delta"],        errors="coerce")
    raw_source = pd.to_numeric(recon["source_value"], errors="coerce")

    def _fmt_delta_pct(delta: float, source: float) -> str:
        if source == 0 and delta == 0:
            return "—"           # true zero / zero — can't compute %
        if source == 0:
            return "n/a"         # division undefined
        pct = abs(delta / source) * 100
        if pct == 0:
            return "0.0000%"
        if pct < 0.001:
            return f"< 0.001%  (actual: {pct:.8f}%)"
        return f"{pct:.4f}%"

    display["Delta %"] = [
        _fmt_delta_pct(d, s) for d, s in zip(raw_delta, raw_source)
    ]

    # Format other numeric columns for readability
    for col in ["Warehouse", "Source System"]:
        if col in display.columns:
            display[col] = display[col].apply(lambda x: f"{float(x):,.2f}")
    if "Delta" in display.columns:
        display["Delta"] = display["Delta"].apply(
            lambda x: f"{float(x):+,.4f}" if float(x) != 0 else "0.00"
        )

    # Drop the timestamp column from the table view
    display = display[[c for c in display.columns if c not in ("reconciled_at",)]]

    def _color_status(val: str) -> str:
        if val == "PASS":
            return "color: #16a34a; font-weight: bold"
        return "color: #dc2626; font-weight: bold"

    styled = display.style.map(_color_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()

    # 3. METHODOLOGY — always visible, not buried
    section_header("How This Works")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            """
**What is being compared?**

Four aggregate metrics are computed two ways:
1. **Warehouse** — calculated from the dbt mart models in DuckDB / Snowflake
2. **Source System** — from `control_totals.csv`, which simulates what a loan
   servicing system (e.g. LoanPro, Turnkey Lender) would report via its API

If the numbers diverge by more than **0.1%**, the reconciliation fails.
In production, the `assert_reconciliation_delta_lt_threshold` dbt test
would block the entire pipeline run.
            """
        )
    with col_b:
        st.markdown(
            """
**Why does this matter?**

Finance teams at lending companies routinely report wrong numbers because
warehouse totals silently drift from the servicing system — due to late
payment postings, timezone issues, or ETL bugs.

A reconciliation layer makes data integrity a **first-class, testable
artifact** rather than a Friday afternoon surprise before the board pack.

**In this demo**, the control file is synthetic. In production, you would
replace it with a nightly API call to your servicing system, normalized
into the same schema.
            """
        )
