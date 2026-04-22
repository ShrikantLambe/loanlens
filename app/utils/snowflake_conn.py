"""
snowflake_conn.py — Database connection factory.

Returns a DuckDB connection if USE_DUCKDB_FALLBACK=true, otherwise Snowflake.
All Streamlit pages import from here — never create connections directly in pages.
"""

import logging
import os

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_USE_DUCKDB = os.environ.get("USE_DUCKDB_FALLBACK", "false").lower() == "true"
_DUCKDB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "loanlens.duckdb")

_DBT_SCHEMA = os.environ.get("SNOWFLAKE_SCHEMA_DBT", "analytics").lower()

# dbt appends sub-schema names to the target schema when +schema is set in dbt_project.yml.
# e.g. target=analytics + schema=finance → analytics_finance in DuckDB.
_DUCKDB_TABLE_SCHEMA = {
    "stg_loans":              "analytics_staging",
    "stg_payments":           "analytics_staging",
    "stg_platforms":          "analytics_staging",
    "stg_spv_allocation":     "analytics_staging",
    "fct_portfolio_daily":    "analytics_finance",
    "fct_originations":       "analytics_finance",
    "fct_cohort_performance": "analytics_finance",
    "fct_spv_allocation":     "analytics_finance",
    "rpt_portfolio_summary":  "analytics_reporting",
    "rpt_reconciliation":     "analytics_reporting",
    "rpt_covenant_compliance": "analytics_reporting",
}


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert DuckDB-specific types to plain Python-compatible pandas types.

    - datetime64 columns → datetime64[ns] (keeps them as proper dates for Plotly,
      but converts to a standard pandas datetime that is JSON-safe via .isoformat()).
    - boolean columns stay as Python bool (already JSON-safe).
    - float32 → float64 (avoids numpy float32 serialization edge cases).
    """
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # Keep as datetime for Plotly, but use ns precision (standard pandas)
            df[col] = pd.to_datetime(df[col]).dt.normalize()
        elif df[col].dtype == "float32":
            df[col] = df[col].astype("float64")
    return df


def _snowflake_conn():
    """Return a Snowflake connection."""
    import snowflake.connector
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ.get("SNOWFLAKE_ROLE", "SYSADMIN"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA_DBT", "ANALYTICS"),
    )


def query(sql: str) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a DataFrame.

    Args:
        sql: SQL string. Use schema-qualified table names.

    Returns:
        Normalized pandas DataFrame (datetime64[ns], float64, no float32).
    """
    if _USE_DUCKDB:
        import duckdb
        conn = duckdb.connect(_DUCKDB_PATH, read_only=True)
        df = conn.execute(sql).df()
        conn.close()
        return _normalize(df)

    conn = _snowflake_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0].lower() for c in cursor.description]
        rows = cursor.fetchall()
        return _normalize(pd.DataFrame(rows, columns=cols))
    finally:
        conn.close()


def table(name: str) -> pd.DataFrame:
    """
    Fetch an entire dbt output table by name.

    Args:
        name: Table name without schema prefix (e.g. 'fct_portfolio_daily').

    Returns:
        Normalized pandas DataFrame.
    """
    if _USE_DUCKDB:
        schema = _DUCKDB_TABLE_SCHEMA.get(name, f"{_DBT_SCHEMA}_{name}")
    else:
        schema = os.environ.get("SNOWFLAKE_SCHEMA_DBT", "ANALYTICS")
    return query(f"SELECT * FROM {schema}.{name}")
