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

    if "reconciled_at" in recon.columns:
        ts = str(recon["reconciled_at"].iloc[0])[:19]
        st.caption(f"Last reconciled: {ts} UTC")

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

    # Format numbers for readability
    for col in ["Warehouse", "Source System", "Delta"]:
        if col in display.columns:
            display[col] = display[col].apply(lambda x: f"{float(x):,.2f}")
    if "Delta %" in display.columns:
        display["Delta %"] = display["Delta %"].apply(lambda x: f"{float(x):.4f}%")

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
