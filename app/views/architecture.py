from __future__ import annotations
"""
architecture.py — Architecture and data model reference page.

Describes the full stack: synthetic data generation, DuckDB, dbt layer,
Claude AI memo generation, and Streamlit dashboard.
"""

import streamlit as st
from app.utils.ui import page_header, section_header


def render() -> None:
    """Render the Architecture reference page."""
    page_header(
        "Architecture",
        "How LoanLens works — from raw loan tape to investor-ready portfolio intelligence.",
        badge="Reference",
        badge_color="#f1f5f9",
        badge_text_color="#475569",
    )

    # ── Data flow diagram ─────────────────────────────────────────────────────
    section_header("Data Flow")
    _DIAGRAM = (
        "┌─────────────────────────┐\n"
        "│   Synthetic Data Gen    │  generate_loans.py · generate_payments.py\n"
        "│   10K loans · 1.3M pmts │  Faker + NumPy · deterministic seed(42)\n"
        "└──────────┬──────────────┘\n"
        "           │ seed_snowflake.py\n"
        "           ▼\n"
        "┌─────────────────────────┐\n"
        "│   DuckDB  (raw schema)  │  loans · payments · platforms\n"
        "│   Local file, no cloud  │  spv_allocation · control_totals\n"
        "└──────────┬──────────────┘\n"
        "           │ dbt run\n"
        "           ▼\n"
        "┌──────────────────────────────────────────────────────┐\n"
        "│   dbt Core 1.8  (analytics schema)                   │\n"
        "│                                                       │\n"
        "│  staging/   stg_loans · stg_payments · stg_platforms │\n"
        "│     │       (typed views, no business logic)          │\n"
        "│     ▼                                                 │\n"
        "│  intermediate/   int_loan_status  ← core credit model│\n"
        "│                  int_cohort_assignments               │\n"
        "│     ▼                                                 │\n"
        "│  marts/finance/   fct_portfolio_daily                 │\n"
        "│                   fct_delinquency_weekly  ← trend     │\n"
        "│                   fct_originations                    │\n"
        "│                   fct_cohort_performance  ← J-curves  │\n"
        "│                   fct_spv_allocation      ← covenants │\n"
        "│  marts/reporting/ rpt_portfolio_summary   ← AI input  │\n"
        "│                   rpt_reconciliation      ← audit     │\n"
        "│                   rpt_covenant_compliance             │\n"
        "└──────────┬───────────────────────────────────────────┘\n"
        "           │\n"
        "     ┌─────┴─────┐\n"
        "     ▼           ▼\n"
        "┌─────────┐ ┌──────────────────────────────┐\n"
        "│Streamlit│ │   Claude AI (Anthropic SDK)  │\n"
        "│Dashboard│ │   portfolio_narrator.py       │\n"
        "│ 5 tabs  │ │   anomaly_agent.py            │\n"
        "│         │ │   → structured JSON memo      │\n"
        "└─────────┘ └──────────────────────────────┘"
    )
    st.html(
        "<div style='font-family:Inter,monospace;font-size:12px;color:#374151;"
        "background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;"
        "padding:20px 24px;line-height:2;overflow-x:auto;'>"
        "<div style='font-family:monospace;white-space:pre;'>"
        + _DIAGRAM.replace("\n", "&#10;")
        + "</div></div>"
    )

    st.divider()

    # ── Layer descriptions ────────────────────────────────────────────────────
    section_header("Layer by Layer")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
**Synthetic Data Generation**

10,000 MCA loans originating Jan 2022 – Dec 2024 across 5 platforms
(60% DoorDash, 20% Amazon, 10% Mindbody, 10% other). Payment simulation
produces 1.3M events with realistic default curves: 5.4% portfolio default
rate, earlier vintages at 15–20% peak cumulative default, 2024 cohorts still
developing. Random seed 42 — fully reproducible.

**DuckDB as the Warehouse**

DuckDB runs in-process as a local `.duckdb` file — no credentials, no
cloud account, no network latency. The same SQL dialect (DuckDB-flavoured
Postgres) works on Snowflake with a two-line profile change. Chosen because
a Finance Data Lead building a portfolio demo shouldn't need to spin up cloud
infrastructure just to demonstrate the modeling.

**dbt Core 1.8**

Full staging → intermediate → mart lineage. 65+ schema tests. Staging models
are views (lightweight); intermediates are ephemeral (CTEs, no physical table);
marts are materialized tables. The reconciliation layer (`rpt_reconciliation`)
compares warehouse totals to a control file, making data integrity a testable,
pipeline-gating artifact.
            """
        )
    with col2:
        st.markdown(
            """
**Reconciliation Layer**

`rpt_reconciliation` compares four warehouse metrics against `control_totals.csv`
(simulating a loan servicing system export). A $0.57 delta on $929M total
collected (0.000000061%) is visible in the audit table even though it passes
the 0.1% PASS threshold — demonstrating the layer catches floating-point
divergence that a manual process would miss entirely.

**Claude AI Integration**

Two agents share the structured portfolio data:

- `portfolio_narrator.py` — reads `rpt_portfolio_summary` and generates
  investor-grade commentary as strict JSON: executive summary, risk flags,
  cohort observations, recommended actions, sentiment rating.

- `anomaly_agent.py` — reads 60-day delinquency time series and SPV data,
  flags delinquency spikes, covenant breach risks, and default clusters.

Both agents fall back to `demo_commentary.py` if the API is unavailable,
ensuring the demo runs offline with realistic pre-computed commentary.

**Streamlit Dashboard**

Five pages served from pre-built Parquet snapshots (67 KB total) on
Streamlit Community Cloud — no dbt or Snowflake credentials needed. The
snapshot strategy means cold-start is under 3 seconds regardless of
Python version constraints on the cloud runtime.
            """
        )

    st.divider()

    # ── Stack versions ────────────────────────────────────────────────────────
    section_header("Stack")

    versions = [
        ("Python",           "3.12"),
        ("Streamlit",        "1.50"),
        ("dbt-core",         "1.8.7+"),
        ("dbt-duckdb",       "1.9+"),
        ("DuckDB",           "1.1+"),
        ("Anthropic SDK",    "0.28+"),
        ("pandas",           "2.2+"),
        ("Plotly",           "5.22+"),
        ("NumPy",            "2.0+"),
        ("Faker",            "24.0+"),
    ]
    cols = st.columns(5)
    for i, (name, ver) in enumerate(versions):
        with cols[i % 5]:
            st.html(
                f"<div style='background:#f8fafc;border:1px solid #e2e8f0;"
                f"border-radius:8px;padding:10px 12px;margin-bottom:8px;"
                f"font-family:Inter,sans-serif;'>"
                f"<div style='font-size:12px;font-weight:700;color:#1e293b;'>{name}</div>"
                f"<div style='font-size:11px;color:#64748b;'>{ver}</div>"
                f"</div>"
            )

    st.divider()

    # ── Links ─────────────────────────────────────────────────────────────────
    section_header("Links")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button(
            "GitHub — View Source",
            "https://github.com/ShrikantLambe/loanlens",
            use_container_width=True,
        )
    with c2:
        st.link_button(
            "dbt Docs — Model Lineage",
            "https://github.com/ShrikantLambe/loanlens/tree/main/dbt_loanlens/models",
            use_container_width=True,
        )
    with c3:
        st.link_button(
            "Portfolio — Shrikant Lambe",
            "https://shrikantlambe.github.io",
            use_container_width=True,
        )

    st.divider()
    st.caption(
        "This project demonstrates: dbt modeling rigor · fintech domain fluency · "
        "LLM integration in production workflows · financial data integrity through "
        "reconciliation · SPV-level reporting · investor-grade output generation. "
        "All loan data is synthetic — no real borrower information is used."
    )
