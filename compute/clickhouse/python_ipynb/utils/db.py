"""ClickHouse helpers: credentials, connection, read and write of tables."""

import os
from pathlib import Path

import clickhouse_connect
import pandas as pd
from clickhouse_connect.driver.client import Client
from dotenv import load_dotenv

# Local runs: compute/clickhouse/.env (git-ignored), see .env.example next to it
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
SECURE_PORTS = {8443}   # HTTPS, e.g. ClickHouse Cloud


def load_creds(creds=None) -> dict:
    """Return the credentials as a dict with keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.

    creds can be:
        - a dict:  the secret object Intelek injects into the function, used as-is
        - None:    read the same variables from compute/clickhouse/.env (local runs)
    """
    if creds is not None:
        return creds
    load_dotenv(ENV_FILE, override=True)
    return {key: os.environ[key] for key in CREDS_KEYS}


def get_client(creds=None) -> Client:
    """ClickHouse client from the injected creds dict, or from .env (see load_creds).
    Unqualified table names resolve to the DB_NAME database."""
    creds = load_creds(creds)
    port = int(creds.get("DB_PORT", 8123))
    return clickhouse_connect.get_client(
        host=creds["DB_HOST"], port=port, username=creds["DB_USER"],
        password=creds["DB_PASSWORD"], database=creds["DB_NAME"], secure=port in SECURE_PORTS)


def clickhouse_type(dtype) -> str:
    """pandas dtype -> Nullable ClickHouse type."""
    if pd.api.types.is_bool_dtype(dtype):
        base = "Bool"
    elif pd.api.types.is_integer_dtype(dtype):
        base = "Int64"
    elif pd.api.types.is_float_dtype(dtype):
        base = "Float64"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        base = "DateTime64(3, 'UTC')"   # naive timestamps, kept as-is
    else:
        base = "String"
    return f"Nullable({base})"


def table_exists(client: Client, table: str) -> bool:
    return bool(client.command(f"EXISTS TABLE {table}"))


def read_table(client: Client, table: str) -> pd.DataFrame:
    """Read a full table. Timestamps come back naive, as they were written."""
    df = client.query_df(f"SELECT * FROM {table}")
    for col in df.columns:
        if isinstance(df[col].dtype, pd.DatetimeTZDtype):
            df[col] = df[col].dt.tz_localize(None)
    return df


def write_table(df: pd.DataFrame, client: Client, table: str, if_exists: str = "append") -> None:
    """Write df to `table`, creating it from the DataFrame columns if needed.
    if_exists: 'append' | 'replace' | 'fail' (same as pandas.to_sql)."""
    exists = table_exists(client, table)
    if exists and if_exists == "fail":
        raise ValueError(f"Table {table} already exists")
    if exists and if_exists == "replace":
        client.command(f"DROP TABLE {table}")
        exists = False
    if not exists:
        columns = ", ".join(f"`{col}` {clickhouse_type(dtype)}" for col, dtype in df.dtypes.items())
        client.command(f"CREATE TABLE {table} ({columns}) ENGINE = MergeTree ORDER BY tuple()")
    rows = df.astype(object).where(df.notna(), None).values.tolist()   # NaN/NaT -> NULL
    client.insert(table, rows, column_names=list(df.columns))
