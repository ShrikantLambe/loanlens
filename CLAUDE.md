# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**LoanLens** — a portfolio intelligence stack for a synthetic fintech lending portfolio. It combines dbt on DuckDB/Snowflake, a Streamlit dashboard, and an Anthropic Claude AI layer for investor-grade commentary.

All commands below must be run from inside `loanlens/` (the project root).

---

## Commands

### Full dev cycle (seed → transform → app)
```bash
make dev
```

### Individual steps
```bash
make seed        # generate CSVs → load into DuckDB (or Snowflake)
make transform   # dbt deps + dbt run + dbt test
make app         # streamlit run app/main.py
make test        # pytest tests/ -v && dbt test
make docs        # dbt docs generate + serve (opens lineage DAG)
make clean       # remove dbt target/, __pycache__
```

### Run a single dbt model
```bash
.venv/bin/dbt run --select fct_portfolio_daily --profiles-dir .
```

### Run a single pytest test
```bash
.venv/bin/pytest tests/test_data_gen.py::test_loan_schema -v
```

All Python tooling lives in `.venv/`; the Makefile already uses `.venv/bin/python`, `.venv/bin/dbt`, etc.

---

## Environment

Copy `.env.example` → `.env`. The critical toggle:

```bash
USE_DUCKDB_FALLBACK=true   # local DuckDB (loanlens.duckdb) — no cloud needed
USE_DUCKDB_FALLBACK=false  # Snowflake (requires SNOWFLAKE_* vars)
```

With `USE_DUCKDB_FALLBACK=true` the full stack runs offline with no Snowflake credentials.

The `dbt_loanlens/profiles.yml` already points to DuckDB by default (`target: duckdb`).

---

## Architecture

### Data flow
```
data_gen/ → data_gen/output/*.csv → DuckDB raw schema
                                    ↓
                             dbt_loanlens/models/
                              staging/ (views)
                              intermediate/ (ephemeral)
                              marts/finance/ + marts/reporting/ (tables)
                                    ↓
                             app/ (Streamlit)
                             ai_layer/ (Claude API)
```

### dbt layer (dbt_loanlens/)
- **staging/** — typed views over raw tables, one-to-one with source tables, no joins, no business logic.
- **intermediate/** — ephemeral CTEs: `int_loan_status` (derives current status from payment history), `int_cohort_assignments` (monthly vintage labels), `int_payment_schedule`.
- **marts/finance/** — materialized tables: `fct_portfolio_daily` (daily snapshot, core model), `fct_originations`, `fct_cohort_performance`, `fct_spv_allocation`.
- **marts/reporting/** — `rpt_portfolio_summary` (single-row summary consumed by the AI layer), `rpt_reconciliation` (warehouse vs. control_totals delta), `rpt_covenant_compliance`.

DuckDB schema naming: `analytics_staging`, `analytics_finance`, `analytics_reporting` (dbt appends the sub-schema to the target schema name). This is mapped in `app/utils/snowflake_conn.py:_DUCKDB_TABLE_SCHEMA`.

### App layer (app/)
- `app/main.py` — Streamlit entry point, sidebar routing only.
- `app/pages/*.py` — each page exports a single `render()` function.
- `app/utils/snowflake_conn.py` — **single database access point**. All pages call `table(name)` or `query(sql)` from here. Never create connections directly in page files. Returns normalized pandas DataFrames.

### AI layer (ai_layer/)
- `portfolio_narrator.py` — calls `claude-sonnet-4-20250514`, returns structured JSON dict with `executive_summary`, `key_metrics_narrative`, `risk_flags`, `cohort_observations`, `recommended_actions`, `sentiment`.
- `anomaly_agent.py` — returns a list of anomaly dicts with `anomaly_type`, `severity`, `description`, `affected_entity`, `recommended_action`.
- `memo_generator.py` — assembles narrator + anomaly output into a memo dict for rendering and PDF export.
- `demo_commentary.py` — returns hardcoded commentary for offline demos without hitting the API.
- Prompts live in `ai_layer/prompts/` as plain `.txt` files.

### PDF export
WeasyPrint requires pango/gobject from Homebrew. The Makefile exports `DYLD_LIBRARY_PATH=/opt/homebrew/lib` for macOS. If WeasyPrint fails, check that Homebrew's pango is installed.

---

## Key conventions

- `_SafeEncoder` (defined in both `portfolio_narrator.py` and `anomaly_agent.py`) handles pandas Timestamps and numpy scalars when serializing data to JSON for LLM prompts.
- Streamlit pages use `@st.cache_data` on all data-fetching functions.
- Monetary values: `${:,.0f}`. Percentages: `{:.2f}%`.
- All Python functions are typed and have docstrings.
- `logging` module only — no `print()` in production code.
