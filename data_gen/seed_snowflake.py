"""
seed_snowflake.py — Loads all generated CSVs into Snowflake (or DuckDB fallback).

Reads USE_DUCKDB_FALLBACK from .env:
  - false (default): loads into Snowflake RAW schema
  - true: loads into loanlens.duckdb local file

Run: python data_gen/seed_snowflake.py
"""

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"

TABLES = {
    "loans": "loans.csv",
    "payments": "payments.csv",
    "platform_metadata": "platform_metadata.csv",
    "spv_allocation": "spv_allocation.csv",
    "control_totals": "control_totals.csv",
}


def _get_duckdb_conn():
    """Return a DuckDB connection to loanlens.duckdb."""
    import duckdb
    db_path = Path(__file__).parent.parent / "loanlens.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    return conn


def _load_duckdb(conn, table_name: str, df: pd.DataFrame) -> None:
    """Load a DataFrame into DuckDB raw schema."""
    conn.execute(f"DROP TABLE IF EXISTS raw.{table_name}")
    conn.execute(f"CREATE TABLE raw.{table_name} AS SELECT * FROM df")
    logger.info("DuckDB: loaded %d rows into raw.%s", len(df), table_name)


def _get_snowflake_conn():
    """Return a Snowflake connection using env vars."""
    import snowflake.connector
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ.get("SNOWFLAKE_ROLE", "SYSADMIN"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA_RAW", "RAW"),
    )


def _load_snowflake(conn, table_name: str, df: pd.DataFrame) -> None:
    """Load a DataFrame into Snowflake RAW schema via write_pandas."""
    from snowflake.connector.pandas_tools import write_pandas

    schema = os.environ.get("SNOWFLAKE_SCHEMA_RAW", "RAW")
    database = os.environ["SNOWFLAKE_DATABASE"]

    # Ensure schema exists
    cursor = conn.cursor()
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {database}.{schema}")
    cursor.execute(f"DROP TABLE IF EXISTS {database}.{schema}.{table_name.upper()}")

    success, nchunks, nrows, _ = write_pandas(
        conn,
        df,
        table_name=table_name.upper(),
        database=database,
        schema=schema,
        auto_create_table=True,
        overwrite=True,
    )
    logger.info(
        "Snowflake: loaded %d rows into %s.%s.%s (success=%s)",
        nrows, database, schema, table_name.upper(), success,
    )


def main() -> None:
    """Seed all tables from CSV files."""
    use_duckdb = os.environ.get("USE_DUCKDB_FALLBACK", "false").lower() == "true"
    logger.info("Seeding with %s...", "DuckDB" if use_duckdb else "Snowflake")

    if use_duckdb:
        conn = _get_duckdb_conn()
        load_fn = lambda name, df: _load_duckdb(conn, name, df)
    else:
        conn = _get_snowflake_conn()
        load_fn = lambda name, df: _load_snowflake(conn, name, df)

    for table_name, filename in TABLES.items():
        csv_path = OUTPUT_DIR / filename
        if not csv_path.exists():
            logger.warning("CSV not found, skipping: %s", csv_path)
            continue
        df = pd.read_csv(csv_path)
        load_fn(table_name, df)

    conn.close()
    logger.info("Seeding complete.")


if __name__ == "__main__":
    main()
