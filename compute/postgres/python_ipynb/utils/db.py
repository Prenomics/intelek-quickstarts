"""Postgres helpers: credentials, connection, read and write of tables."""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL, Engine

# Local runs: compute/postgres/.env (git-ignored), see .env.example next to it
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
DEFAULT_SCHEMA = "public"   # used when the optional DB_SCHEMA key is missing


def load_creds(creds=None) -> dict:
    """Return the credentials as a dict with keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD,
    DB_NAME and DB_SCHEMA (optional).

    creds can be:
        - a dict:  the secret object Intelek injects into the function, used as-is
        - None:    read the same variables from compute/postgres/.env (local runs)
    """
    if creds is not None:
        return creds
    load_dotenv(ENV_FILE, override=True)
    creds = {key: os.environ[key] for key in CREDS_KEYS}
    creds["DB_SCHEMA"] = os.getenv("DB_SCHEMA", DEFAULT_SCHEMA)
    return creds


def get_engine(creds=None) -> Engine:
    """Create a SQLAlchemy engine from the injected creds dict, or from .env (see load_creds).
    The search_path is set to DB_SCHEMA, so unqualified table names resolve to that schema."""
    creds = load_creds(creds)
    schema = creds.get("DB_SCHEMA", DEFAULT_SCHEMA)
    return create_engine(URL.create(
        "postgresql+psycopg2", username=creds["DB_USER"], password=creds["DB_PASSWORD"],
        host=creds["DB_HOST"], port=int(creds.get("DB_PORT", 5432)), database=creds["DB_NAME"]),
        connect_args={"options": f"-csearch_path={schema}"})


def table_exists(engine: Engine, table: str) -> bool:
    return inspect(engine).has_table(table)


def read_table(engine: Engine, table: str) -> pd.DataFrame:
    return pd.read_sql_table(table, engine)


def write_table(df: pd.DataFrame, engine: Engine, table: str, if_exists: str = "append") -> None:
    """Write df to `table` in DB_SCHEMA, which must exist.
    if_exists: 'append' | 'replace' | 'fail' (same as pandas.to_sql)."""
    df.to_sql(table, engine, if_exists=if_exists, index=False)
