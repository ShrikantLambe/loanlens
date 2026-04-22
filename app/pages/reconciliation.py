"""
reconciliation.py — Warehouse vs. source system reconciliation audit page.

Shows: metric-level PASS/FAIL table, delta amounts, delta%, last reconciled
timestamp, and an explanation of the reconciliation methodology.
"""

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Load reconciliation results."""
    return db.table("rpt_reconciliation")


def render() -> None:
    """Render the Reconciliation Audit page."""
    st.title("Reconciliation Audit")
    st.caption(
        "Warehouse totals compared to control file totals from the source system. "
        "Any delta > 0.1% is flagged as FAIL and surfaces in dbt tests."
    )

    try:
        recon = _load_data()
    except Exception as e:
        st.error(f"Failed to load reconciliation data: {e}")
        return

    if recon.empty:
        st.info("No reconciliation data. Run `make dev` first.")
        return

    # Status summary
    all_pass = all(r == "PASS" for r in recon["reconciliation_status"])
    fail_count = sum(1 for r in recon["reconciliation_status"] if r == "FAIL")

    if all_pass:
        st.success(f"✅ All {len(recon)} metrics reconciled successfully.")
    else:
        st.error(f"❌ {fail_count} metric(s) failed reconciliation. Investigate immediately.")

    # Last reconciled timestamp
    if "reconciled_at" in recon.columns:
        st.caption(f"Last reconciled: {recon['reconciled_at'].iloc[0]}")

    st.divider()

    # Reconciliation table with PASS/FAIL coloring
    st.subheader("Metric-Level Results")

    display = recon.copy()
    if "warehouse_value" in display.columns:
        display["warehouse_value"] = display["warehouse_value"].apply(
            lambda x: f"{float(x):,.2f}"
        )
    if "source_value" in display.columns:
        display["source_value"] = display["source_value"].apply(
            lambda x: f"{float(x):,.2f}"
        )
    if "delta" in display.columns:
        display["delta"] = display["delta"].apply(lambda x: f"{float(x):+,.2f}")
    if "delta_pct" in display.columns:
        display["delta_pct"] = display["delta_pct"].apply(lambda x: f"{float(x):.4f}%")

    def _color_status(val: str) -> str:
        if val == "PASS":
            return "color: #16a34a; font-weight: bold"
        return "color: #dc2626; font-weight: bold"

    styled = display.style.applymap(_color_status, subset=["reconciliation_status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()

    # Explainer
    with st.expander("How this reconciliation works"):
        st.markdown(
            """
**What is being reconciled?**

Four metrics are computed from the data warehouse (Snowflake / DuckDB) and
compared to a `control_totals.csv` file that simulates what a loan servicing
system would report as the source of truth:

| Metric | Warehouse Source | Control Source |
|---|---|---|
| `origination_count` | COUNT of rows in `stg_loans` | `control_totals.csv` |
| `origination_principal` | SUM of `principal_amount` | `control_totals.csv` |
| `total_collected` | SUM of `total_repaid` from `int_loan_status` | `control_totals.csv` |
| `default_count` | COUNT of loans with status = `default` | `control_totals.csv` |

**Pass/Fail threshold:** A metric fails if `|warehouse_value - source_value| / source_value > 0.1%`.

**In production:** This control file would be replaced by a nightly API call to the
loan servicing system (e.g. Turnkey Lender, LoanPro). The dbt test
`assert_reconciliation_delta_lt_threshold` fails the entire pipeline if any metric breaks.

**Why this matters:** Without a reconciliation layer, Finance teams silently report
wrong numbers. This model makes data integrity a first-class, testable artifact.
            """
        )
