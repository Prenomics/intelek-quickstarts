"""
Load the reference Excels into Postgres *as they are* (original column names),
one table per file, in an existing schema (default: DB_SCHEMA from the credentials).

    leads_web_form.xlsx   -> leads_web_form
    leads_trade_fair.xlsx -> leads_trade_fair
    leads_linkedin.xlsx   -> leads_linkedin
    sales_people.xlsx     -> sales_people

Each table is replaced on every run.

Credentials: the dict Intelek injects (keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD,
DB_NAME and optional DB_SCHEMA, default public) or, locally, the same variables from
compute/postgres/.env (see .env.example).

Usage:
    python compute/postgres/load_reference_data.py                        # all files
    python compute/postgres/load_reference_data.py sales_people.xlsx      # only these
    python compute/postgres/load_reference_data.py --schema other_schema  # not DB_SCHEMA
"""

import argparse
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

DATA_DIR = Path(__file__).resolve().parents[2] / "reference_data"   # shared by every engine
ENV_FILE = Path(__file__).resolve().parent / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
FILES = ["leads_web_form.xlsx", "leads_trade_fair.xlsx", "leads_linkedin.xlsx", "sales_people.xlsx"]


def load_reference_data(creds=None, schema: str = None, data_dir: Path = DATA_DIR,
                        files: list = FILES) -> None:
    """(Re)load each Excel in `files` as a table of `schema`, which must exist.
    creds: dict injected by Intelek, or None to read the DB_* variables from .env.
    schema: target schema (default: DB_SCHEMA, or public).
    files: Excel file names inside data_dir (default: all the reference files)."""
    if creds is None:
        load_dotenv(ENV_FILE, override=True)
        creds = {key: os.environ[key] for key in CREDS_KEYS}
        creds["DB_SCHEMA"] = os.getenv("DB_SCHEMA", "public")
    schema = schema or creds.get("DB_SCHEMA", "public")
    engine = create_engine(URL.create(
        "postgresql+psycopg2", username=creds["DB_USER"], password=creds["DB_PASSWORD"],
        host=creds["DB_HOST"], port=int(creds.get("DB_PORT", 5432)), database=creds["DB_NAME"]))

    for file_name in files:
        df = pd.read_excel(data_dir / file_name)
        table_name = Path(file_name).stem
        df.to_sql(table_name, engine, schema=schema, if_exists="replace", index=False)
        print(f"{schema}.{table_name:<20} {len(df):>3} rows loaded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the reference Excels into Postgres.")
    parser.add_argument("files", nargs="*", default=FILES, help="Excel file names (default: all)")
    parser.add_argument("--schema", help="target schema (default: DB_SCHEMA)")
    args = parser.parse_args()
    load_reference_data(schema=args.schema, files=args.files)
