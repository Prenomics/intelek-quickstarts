"""Postgres helpers: credentials, connection, read and write of 'schema.table' names."""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine

# Local runs: .env at the repo root (git-ignored), see .env.example
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]


def load_creds(creds=None) -> dict:
    """Return the credentials as a dict with keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.

    creds can be:
        - a dict:  the secret object Intelek injects into the function, used as-is
        - None:    read the same variables from the repo's .env file (local runs)
    """
    if creds is not None:
        return creds
    load_dotenv(ENV_FILE, override=True)
    return {key: os.environ[key] for key in CREDS_KEYS}


def get_engine(creds=None) -> Engine:
    """Create a SQLAlchemy engine from the injected creds dict, or from .env (see load_creds)."""
    creds = load_creds(creds)
    return create_engine(URL.create(
        "postgresql+psycopg2", username=creds["DB_USER"], password=creds["DB_PASSWORD"],
        host=creds["DB_HOST"], port=int(creds.get("DB_PORT", 5432)), database=creds["DB_NAME"]))


def _split(table: str) -> tuple:
    schema, name = table.split(".")
    return schema, name


def table_exists(engine: Engine, table: str) -> bool:
    schema, name = _split(table)
    return inspect(engine).has_table(name, schema=schema)


def read_table(engine: Engine, table: str) -> pd.DataFrame:
    schema, name = _split(table)
    return pd.read_sql_table(name, engine, schema=schema)


def write_table(df: pd.DataFrame, engine: Engine, table: str, if_exists: str = "append") -> None:
    """Write df to 'schema.table', creating the schema if needed.
    if_exists: 'append' | 'replace' | 'fail' (same as pandas.to_sql)."""
    schema, name = _split(table)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    df.to_sql(name, engine, schema=schema, if_exists=if_exists, index=False)
