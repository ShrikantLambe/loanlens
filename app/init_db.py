"""
init_db.py — One-time DuckDB initialization for Streamlit Community Cloud.

On first run (no loanlens.duckdb present), seeds raw tables from committed CSVs
then executes dbt to build all analytics views and tables.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent          # loanlens/
_DUCKDB = _ROOT / "loanlens.duckdb"
_DBT_DIR = _ROOT / "dbt_loanlens"
_DATA_DIR = _ROOT / "data_gen" / "output"


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

    Called once per Streamlit process startup. Shows a progress UI while
    seeding + transforming; no-ops if the DuckDB file already exists.
    """
    if not needs_init():
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
