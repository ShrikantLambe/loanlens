# LoanLens — Portfolio Intelligence Stack

**10,000 synthetic loans · 180,000 payment events · 3 SPVs · LLM-generated investor commentary**

LoanLens is a production-quality fintech portfolio intelligence platform built to demonstrate the work a Finance Data Lead does in the first 90 days at a Series C lending company. It goes from a raw loan tape to investor-ready dashboards, reconciliation auditing, and Claude-powered narrative in a single `make dev`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LoanLens Stack                           │
├───────────────┬─────────────────────┬───────────────────────────┤
│  Data Gen     │  Transformation     │  Serving                  │
│  (Python)     │  (dbt Core)         │  (Streamlit + Claude)     │
│               │                     │                           │
│  Faker +      │  staging/           │  5-tab dashboard          │
│  NumPy        │  → stg_loans        │  - Portfolio scorecard    │
│               │  → stg_payments     │  - Cohort heatmap         │
│  10K loans    │  → stg_platforms    │  - SPV covenant view      │
│  180K events  │  → stg_spv          │  - Reconciliation audit   │
│               │                     │  - AI investor memo       │
│  CSVs →       │  intermediate/      │                           │
│  Snowflake    │  → int_loan_status  │  Claude API               │
│  (or DuckDB)  │  → int_cohorts      │  → JSON commentary        │
│               │  → int_payments     │  → Anomaly detection      │
│               │                     │  → PDF export             │
│               │  marts/             │                           │
│               │  → fct_portfolio_   │                           │
│               │    daily            │                           │
│               │  → fct_originations │                           │
│               │  → fct_cohort_perf  │                           │
│               │  → fct_spv_alloc    │                           │
│               │  → rpt_summary      │                           │
│               │  → rpt_recon        │                           │
└───────────────┴─────────────────────┴───────────────────────────┘
```

---

## Quick Start

```bash
git clone https://github.com/your-username/loanlens.git
cd loanlens
cp .env.example .env          # fill in SNOWFLAKE_* and ANTHROPIC_API_KEY
                               # or set USE_DUCKDB_FALLBACK=true for local mode
cp dbt_loanlens/profiles.yml.example ~/.dbt/profiles.yml
pip install -r requirements.txt
make dev                       # seed → transform → launch dashboard
```

To run without Snowflake (local DuckDB):
```bash
# In .env:
USE_DUCKDB_FALLBACK=true
make dev
```

---

## What This Demonstrates

| Feature | Business Problem It Solves |
|---|---|
| **dbt staging → intermediate → mart** | Raw loan data is untrustworthy. A typed, tested lineage makes Finance's numbers auditable from source to dashboard. |
| **Reconciliation audit (rpt_reconciliation)** | Without a recon layer, analysts silently report wrong totals. This model compares warehouse output to a control file and fails the pipeline on any delta > 0.1%. |
| **SPV covenant monitoring (fct_spv_allocation)** | Facility investors can pull funding if delinquency exceeds a covenant threshold. This model surfaces headroom in real time so Finance knows before it's a problem. |
| **Cohort performance curves (fct_cohort_performance)** | Investors evaluate portfolio quality by vintage. These curves show how each origination cohort repays over time — the standard credit risk view. |
| **LLM portfolio narrator (Claude)** | A Finance Data Lead shouldn't just build charts. They should answer "what should the board know?" This model generates investor-grade commentary from live data. |
| **Anomaly detection agent** | Delinquency spikes and covenant breach risks emerge gradually. The anomaly agent monitors time-series data and surfaces early warnings with severity and recommended actions. |
| **PDF memo export** | Investor memos need to leave the dashboard. WeasyPrint renders structured HTML to a downloadable PDF that looks like a real credit research note. |

---

## Dashboard Pages

### 1 — Portfolio Overview
Four KPI cards (total originated, outstanding principal, delinquency rate, default rate), delinquency trend over the last 365 days, monthly origination volume by platform, per-SPV covenant status badges (green / red), and last reconciliation status.

### 2 — Cohort Analysis
Heatmap of cumulative default rate by cohort vintage × months-on-book. Multiselect cohort picker for comparing repayment curves. Summary table of final default rates per cohort.

### 3 — SPV Reporting
Three-column layout (one per SPV). Per-SPV: facility limit, drawn amount, utilization progress bar, delinquency rate vs. covenant limit, default rate, avg underwriting score. Red banner if any covenant is breached.

### 4 — Reconciliation Audit
Metric-level table: warehouse value, source value, delta, delta %, PASS/FAIL status. Expandable "how this works" explainer that maps each metric to its source. Demo moment: this is what financial data integrity looks like in practice.

### 5 — Investor Memo (AI)
Generate button → Claude reads rpt_portfolio_summary + fct_portfolio_daily + fct_spv_allocation → returns structured JSON → renders as: sentiment badge, executive summary, portfolio narrative, cohort observations, risk flags, anomaly alerts, recommended actions, covenant table. PDF download button.

---

## Design Decisions

**Why the reconciliation layer?**
In production fintech, Finance teams are held accountable to numbers that match the loan servicing system. Without a reconciliation model, every dashboard is technically unaudited. By building `rpt_reconciliation` as a first-class dbt model with a failing test, reconciliation integrity becomes part of the CI pipeline — not an afterthought.

**Why SPV allocation matters**
In MCA lending, capital facilities are structured as SPVs with legal covenants. If delinquency on SPV-B crosses 8%, the investor can trigger a "facility freeze" and stop funding new loans. A Finance Data Lead who doesn't monitor covenant headroom in real time is flying blind.

**Why the LLM uses structured JSON output**
The Claude system prompt instructs it to return a strict JSON schema. This means the commentary can be rendered in Streamlit, exported as a PDF, piped into a weekly email digest, or fed into a downstream alerting system — all without parsing freeform text. The structure is the contract.

**Why dbt ephemeral for intermediate models**
Intermediate models are pipeline logic, not financial facts. By setting them as ephemeral, they're inlined into downstream queries (no extra table storage) but remain modular and testable. Marts are the facts — those are persisted as tables.

---

## Running Tests

```bash
# Python unit tests (no Snowflake required)
pytest tests/ -v

# Run a single test file
pytest tests/test_data_gen.py -v

# dbt tests (requires warehouse connection)
cd dbt_loanlens && dbt test

# Run a specific dbt test
cd dbt_loanlens && dbt test --select assert_reconciliation_delta_lt_threshold
```

---

## dbt Model Reference

```bash
cd dbt_loanlens
dbt docs generate
dbt docs serve     # opens at http://localhost:8080
```

Key models to inspect in the DAG:
- `int_loan_status` — the core credit classification logic
- `fct_portfolio_daily` — uses date_spine for daily portfolio snapshots
- `rpt_reconciliation` — compares warehouse to control file
- `fct_spv_allocation` — covenant breach detection

---

## If This Were Production

| What I'd Add | Why |
|---|---|
| Airflow DAG | Schedule seed → transform → test → notify on a daily cadence |
| dbt Cloud | CI runs on PR, dbt Explorer for non-technical stakeholders |
| Real servicing system API | Replace `control_totals.csv` with a live API call to the loan servicer (e.g. LoanPro, Turnkey Lender) |
| Looker semantic layer | Expose dbt marts as a governed semantic layer so analysts can self-serve without writing SQL |
| Streaming payments | Replace daily batch with Kafka + dbt streaming for near-real-time delinquency monitoring |
| Role-based access | SPV data is investor-confidential. Row-level security in Snowflake by SPV → investor mapping |
| Alert routing | Covenant breach triggers a PagerDuty alert + Slack message to the Finance team, not just a dashboard badge |

---

*Built to demonstrate: dbt modeling rigor · fintech domain fluency · LLM integration in production workflows · financial data integrity through reconciliation · SPV-level reporting · investor-grade output generation.*
