from __future__ import annotations
"""
init_db.py — One-time DuckDB initialization for Streamlit Community Cloud.

Fast path (cloud): if pre-built Parquet files exist in app/data/, load them
directly into DuckDB — no dbt, no seeding, no Python-version constraints.

Full path (local): seed from CSVs then run dbt deps/run/test as before.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

_ROOT     = Path(__file__).parent.parent          # loanlens/
_DUCKDB   = _ROOT / "loanlens.duckdb"
_DBT_DIR  = _ROOT / "dbt_loanlens"
_DATA_DIR = _ROOT / "data_gen" / "output"
_PARQUET_DIR = Path(__file__).parent / "data"     # app/data/

# Parquet files committed to git — schema__table.parquet
_PARQUET_TABLES = [
    ("analytics_finance",   "fct_portfolio_daily"),
    ("analytics_finance",   "fct_delinquency_weekly"),
    ("analytics_finance",   "fct_originations"),
    ("analytics_finance",   "fct_cohort_performance"),
    ("analytics_finance",   "fct_spv_allocation"),
    ("analytics_reporting", "rpt_portfolio_summary"),
    ("analytics_reporting", "rpt_reconciliation"),
    ("analytics_reporting", "rpt_covenant_compliance"),
]


def _parquet_path(schema: str, table: str) -> Path:
    return _PARQUET_DIR / f"{schema}__{table}.parquet"


def _has_parquet_snapshots() -> bool:
    """Return True when all pre-built Parquet snapshots are present."""
    return all(_parquet_path(s, t).exists() for s, t in _PARQUET_TABLES)


def _load_from_parquet() -> None:
    """Create DuckDB by reading pre-built Parquet files — no dbt required."""
    import duckdb
    conn = duckdb.connect(str(_DUCKDB))
    for schema, table in _PARQUET_TABLES:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        path = _parquet_path(schema, table)
        conn.execute(
            f"CREATE OR REPLACE TABLE {schema}.{table} AS "
            f"SELECT * FROM read_parquet('{path}')"
        )
        logger.info("Loaded %s.%s from Parquet", schema, table)
    conn.close()


def _dbt(*args: str) -> None:
    """Run a dbt sub-command inside dbt_loanlens/, raising on failure."""
    cmd = ["dbt", *args, "--profiles-dir", "."]
    result = subprocess.run(cmd, cwd=str(_DBT_DIR), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"dbt {' '.join(args)} failed:\n{result.stderr[-2000:]}")
    logger.info("dbt %s OK", " ".join(args))


def _seed() -> None:
    """Import and run seed_snowflake with the DuckDB backend."""
    os.environ.setdefault("USE_DUCKDB_FALLBACK", "true")
    sys.path.insert(0, str(_ROOT))
    from data_gen.seed_snowflake import main as _seed_main
    _seed_main()


def needs_init() -> bool:
    """Return True when the DuckDB file doesn't exist yet."""
    return not _DUCKDB.exists()


def ensure_initialized() -> None:
    """
    Idempotent initialization guard.

    Fast path: if pre-built Parquet snapshots exist (committed to git), load
    them directly — no dbt or seeding needed, works on any Python version.

    Full path: seed from CSVs then dbt deps/run/test (local dev only).
    """
    if not needs_init():
        return

    if _has_parquet_snapshots():
        with st.spinner("Loading analytics database from snapshots…"):
            _load_from_parquet()
        logger.info("DuckDB initialized from Parquet snapshots")
        return

    st.info("First-run setup: building the analytics database from source CSVs…")
    bar = st.progress(0, text="Seeding raw tables…")

    try:
        _seed()
        bar.progress(40, text="Running dbt deps…")
        _dbt("deps")
        bar.progress(60, text="Running dbt models…")
        _dbt("run")
        bar.progress(90, text="Running dbt tests…")
        _dbt("test")
        bar.progress(100, text="Done!")
        st.success("Database initialized. Loading dashboard…")
        st.rerun()
    except Exception as exc:
        bar.empty()
        st.error(f"Initialization failed: {exc}")
        st.stop()
