"""
Load the reference Excels into ClickHouse *as they are* (original column names),
one table per file, in an existing database (default: DB_NAME from the credentials).

    leads_web_form.xlsx   -> leads_web_form
    leads_trade_fair.xlsx -> leads_trade_fair
    leads_linkedin.xlsx   -> leads_linkedin
    sales_people.xlsx     -> sales_people

Each table is dropped and recreated on every run. Every column is Nullable and tables use MergeTree with no sorting key, which is
enough for a raw landing zone.

Credentials: the dict Intelek injects (keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD,
DB_NAME) or, locally, the same variables from compute/clickhouse/.env (see .env.example).
DB_PORT is the HTTP(S) port: 8123 (HTTP) or 8443 (HTTPS, e.g. ClickHouse Cloud).

Usage:
    python compute/clickhouse/load_reference_data.py                        # all files
    python compute/clickhouse/load_reference_data.py sales_people.xlsx      # only these
    python compute/clickhouse/load_reference_data.py --database other_db    # not DB_NAME
"""

import argparse
import os
from pathlib import Path

import clickhouse_connect
import pandas as pd
from dotenv import load_dotenv

DATA_DIR = Path(__file__).resolve().parents[2] / "reference_data"   # shared by every engine
ENV_FILE = Path(__file__).resolve().parent / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
FILES = ["leads_web_form.xlsx", "leads_trade_fair.xlsx", "leads_linkedin.xlsx", "sales_people.xlsx"]
SECURE_PORTS = {8443}


def clickhouse_type(dtype) -> str:
    """pandas dtype -> Nullable ClickHouse type."""
    if pd.api.types.is_bool_dtype(dtype):
        base = "Bool"
    elif pd.api.types.is_integer_dtype(dtype):
        base = "Int64"
    elif pd.api.types.is_float_dtype(dtype):
        base = "Float64"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        base = "DateTime64(3, 'UTC')"   # naive Excel timestamps, kept as-is
    else:
        base = "String"
    return f"Nullable({base})"


def load_reference_data(creds=None, database: str = None, data_dir: Path = DATA_DIR,
                        files: list = FILES) -> None:
    """(Re)load each Excel in `files` as a table of `database`, which must exist.
    creds: dict injected by Intelek, or None to read the DB_* variables from .env.
    database: target database (default: DB_NAME).
    files: Excel file names inside data_dir (default: all the reference files)."""
    if creds is None:
        load_dotenv(ENV_FILE, override=True)
        creds = {key: os.environ[key] for key in CREDS_KEYS}
    port = int(creds.get("DB_PORT", 8123))
    client = clickhouse_connect.get_client(
        host=creds["DB_HOST"], port=port, username=creds["DB_USER"],
        password=creds["DB_PASSWORD"], database=creds["DB_NAME"], secure=port in SECURE_PORTS)

    database = database or creds["DB_NAME"]

    for file_name in files:
        df = pd.read_excel(data_dir / file_name)
        table = f"`{database}`.`{Path(file_name).stem}`"
        columns = ",\n    ".join(f"`{col}` {clickhouse_type(dtype)}" for col, dtype in df.dtypes.items())

        client.command(f"DROP TABLE IF EXISTS {table}")
        client.command(f"CREATE TABLE {table} (\n    {columns}\n) ENGINE = MergeTree ORDER BY tuple()")

        rows = df.astype(object).where(df.notna(), None).values.tolist()   # NaN/NaT -> NULL
        client.insert(Path(file_name).stem, rows, column_names=list(df.columns), database=database)
        print(f"{database}.{Path(file_name).stem:<20} {len(df):>3} rows loaded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the reference Excels into ClickHouse.")
    parser.add_argument("files", nargs="*", default=FILES, help="Excel file names (default: all)")
    parser.add_argument("--database", help="target database (default: DB_NAME)")
    args = parser.parse_args()
    load_reference_data(database=args.database, files=args.files)
