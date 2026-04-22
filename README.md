# LoanLens — Portfolio Intelligence Stack

**10,000 synthetic loans · 1.35M payment events · 3 SPVs · LLM-generated investor commentary**

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
│  1.35M events │  → stg_spv          │  - Reconciliation audit   │
│  36 cohorts   │                     │  - AI investor memo       │
│               │  intermediate/      │                           │
│  CSVs →       │  → int_loan_status  │  Claude API               │
│  DuckDB       │  → int_cohorts      │  → structured JSON        │
│  (or SF)      │  → int_payments     │  → anomaly detection      │
│               │                     │  → PDF export             │
│               │  marts/             │                           │
│               │  → fct_portfolio_   │  11 dbt models            │
│               │    daily            │  65 schema tests          │
│               │  → fct_originations │                           │
│               │  → fct_cohort_perf  │                           │
│               │  → fct_spv_alloc    │                           │
│               │  → rpt_summary      │                           │
│               │  → rpt_recon        │                           │
└───────────────┴─────────────────────┴───────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Data generation | Python 3.9 + Faker | Synthetic loan tape — not real data |
| Warehouse | DuckDB (local) / Snowflake | DuckDB is the default; no cloud account required |
| Transformation | dbt Core 1.8 + dbt-duckdb | Full staging → intermediate → mart lineage |
| AI layer | Anthropic Claude (claude-sonnet-4) | Portfolio narrator + anomaly agent |
| Dashboard | Streamlit 1.35 | 5-tab app |
| PDF export | WeasyPrint | Investor memo as downloadable PDF |
| Testing | dbt tests + pytest | 65 schema tests + Python unit tests |

---

## Prerequisites

- Python 3.9+ (project uses a `.venv` — see setup below)
- `ANTHROPIC_API_KEY` — get one at [console.anthropic.com](https://console.anthropic.com)
- Snowflake account (optional — set `USE_DUCKDB_FALLBACK=true` to run entirely locally)

---

## Quick Start (DuckDB — no cloud account required)

```bash
git clone https://github.com/ShrikantLambe/loanlens.git
cd loanlens

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and USE_DUCKDB_FALLBACK=true

# Copy dbt profile (DuckDB target is pre-configured)
cp dbt_loanlens/profiles.yml.example dbt_loanlens/profiles.yml

# Seed → transform → launch
make dev
```

The dashboard opens at **http://localhost:8501**.

### Snowflake Setup (optional)

```bash
cp .env.example .env
# Edit .env: fill in all SNOWFLAKE_* vars, set USE_DUCKDB_FALLBACK=false
cp dbt_loanlens/profiles.yml.example dbt_loanlens/profiles.yml
# Edit profiles.yml: set target: dev (Snowflake)
make dev
```

---

## What This Demonstrates

| Feature | Business Problem It Solves |
|---|---|
| **dbt staging → intermediate → mart** | Raw loan data is untrustworthy. A typed, tested lineage makes Finance's numbers auditable from source to dashboard. |
| **Reconciliation audit (`rpt_reconciliation`)** | Without a recon layer, analysts silently report wrong totals. This model compares warehouse output to a control file and fails the pipeline on any delta > 0.1%. |
| **SPV covenant monitoring (`fct_spv_allocation`)** | Facility investors can pull funding if delinquency exceeds a covenant threshold. This model surfaces headroom in real time so Finance knows before it's a problem. |
| **Cohort performance curves (`fct_cohort_performance`)** | Investors evaluate portfolio quality by vintage. These curves show how each origination cohort repays over time — the standard credit risk view. |
| **LLM portfolio narrator (Claude)** | A Finance Data Lead shouldn't just build charts. They should answer "what should the board know?" Claude generates investor-grade commentary from live data and returns structured JSON. |
| **Anomaly detection agent** | Delinquency spikes and covenant breach risks emerge gradually. The agent monitors 60 days of time-series data and surfaces early warnings with severity and recommended actions. |
| **PDF memo export** | Investor memos need to leave the dashboard. WeasyPrint renders the structured HTML output to a downloadable PDF that looks like a credit research note. |

---

## Dashboard Pages

### 1 — Portfolio Overview
Four KPI cards (total originated, outstanding principal, delinquency rate, default rate), delinquency trend (weekly resampled), monthly origination volume by platform, per-SPV covenant status badges, and last reconciliation timestamp with PASS/FAIL badge.

### 2 — Cohort Analysis
Heatmap of cumulative default rate by cohort vintage × months-on-book (36 cohorts, capped at 18 most recent for readability). Multiselect cohort picker for comparing repayment curves side by side.

### 3 — SPV Reporting
Three-column layout — one per SPV. Per-SPV: facility limit, drawn amount, utilization progress bar, delinquency rate vs. covenant limit, default rate, avg underwriting score. Red banner on any covenant breach.

### 4 — Reconciliation Audit
Metric-level table: warehouse value, control value, delta, delta %, PASS/FAIL status. Expandable "how this works" explainer that traces each metric to its dbt source. This is what financial data integrity looks like in practice.

### 5 — Investor Memo (AI)
Generate button → Claude reads `rpt_portfolio_summary` + `fct_portfolio_daily` + `fct_spv_allocation` → returns structured JSON → renders as: sentiment badge, executive summary, portfolio narrative, cohort observations, risk flags, anomaly alerts, recommended actions, SPV covenant table. PDF download button. Falls back to pre-built demo commentary if the API is unavailable.

---

## Design Decisions

**Why the reconciliation layer?**
In production fintech, Finance teams are held accountable to numbers that match the loan servicing system. Without a reconciliation model, every dashboard is technically unaudited. By building `rpt_reconciliation` as a first-class dbt model with a failing test, reconciliation integrity becomes part of the CI pipeline — not an afterthought.

**Why SPV allocation matters**
In MCA lending, capital facilities are structured as SPVs with legal covenants. If delinquency on SPV-B crosses 8%, the investor can trigger a "facility freeze" and stop funding new loans. A Finance Data Lead who doesn't monitor covenant headroom in real time is flying blind.

**Why the LLM uses structured JSON output**
The Claude system prompt instructs it to return a strict JSON schema. This means the commentary can be rendered in Streamlit, exported as a PDF, piped into a weekly email digest, or fed into a downstream alerting system — all without parsing freeform text. The structure is the contract.

**Why DuckDB as the local warehouse**
Snowflake is the production target, but requiring a cloud account blocks anyone from running the demo cold. DuckDB runs in-process with zero setup, supports the same SQL dialect, and persists to a single file. The `USE_DUCKDB_FALLBACK=true` flag swaps the connector transparently — the dbt models and dashboard code are identical in both modes.

---

## Running Tests

```bash
# Python unit tests
make test

# Or individually:
.venv/bin/pytest tests/ -v
.venv/bin/pytest tests/test_data_gen.py -v          # data generation only
.venv/bin/pytest tests/test_ai_layer.py -v          # AI layer (mocked)

# dbt tests (65 schema + singular tests)
cd dbt_loanlens && ../dbt test --profiles-dir .

# Run a specific dbt test
cd dbt_loanlens && ../dbt test --profiles-dir . --select assert_reconciliation_delta_lt_threshold
```

---

## dbt Model Reference

```bash
make docs    # generates + serves dbt docs at http://localhost:8080
```

| Model | Layer | Description |
|---|---|---|
| `stg_loans` | staging | Typed, renamed raw loan tape |
| `stg_payments` | staging | Payment events with `is_missed` flag |
| `int_loan_status` | intermediate | Derives current status (current / delinquent\_30/60/90 / default / paid\_off) |
| `int_cohort_assignments` | intermediate | Monthly vintage labels (`MV-2022-01`) |
| `fct_portfolio_daily` | mart | Daily portfolio snapshot via date\_spine — the core dashboard model |
| `fct_originations` | mart | Monthly origination volume by platform + SPV |
| `fct_cohort_performance` | mart | Cohort × months-on-book repayment and default curves |
| `fct_spv_allocation` | mart | SPV-level totals, covenant breach flags, utilization |
| `rpt_portfolio_summary` | reporting | Single-row summary consumed by the AI narrator |
| `rpt_reconciliation` | reporting | Warehouse vs. control file delta — fails pipeline if > 0.1% |
| `rpt_covenant_compliance` | reporting | SPV covenant status over time |

---

## If This Were Production

| What I'd Add | Why |
|---|---|
| Airflow DAG | Schedule seed → transform → test → notify on a daily cadence |
| dbt Cloud | CI runs on PR; dbt Explorer for non-technical stakeholders |
| Real servicing system API | Replace `control_totals.csv` with a live API call to the loan servicer (e.g. LoanPro, Turnkey Lender) |
| Looker semantic layer | Expose dbt marts as a governed semantic layer so analysts can self-serve without writing SQL |
| Streaming payments | Replace daily batch with Kafka + dbt streaming for near-real-time delinquency monitoring |
| Row-level security | SPV data is investor-confidential — Snowflake RLS by SPV → investor mapping |
| Alert routing | Covenant breach triggers a PagerDuty alert + Slack message to Finance, not just a dashboard badge |

---

*Built to demonstrate: dbt modeling rigor · fintech domain fluency · LLM integration in production workflows · financial data integrity through reconciliation · SPV-level reporting · investor-grade output generation.*
