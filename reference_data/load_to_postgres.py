"""
Load the reference Excels into Postgres *as they are* (original column names),
one table per file, in the raw schema (default: demo_raw).

    leads_web_form.xlsx   -> demo_raw.leads_web_form
    leads_trade_fair.xlsx -> demo_raw.leads_trade_fair
    leads_linkedin.xlsx   -> demo_raw.leads_linkedin
    sales_people.xlsx     -> demo_raw.sales_people

Credentials: the dict Intelek injects (keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD,
DB_NAME) or, locally, the same variables from the repo's .env file (see .env.example).

Usage:
    python reference_data/load_to_postgres.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

DATA_DIR = Path(__file__).resolve().parent
ENV_FILE = DATA_DIR.parent / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
FILES = ["leads_web_form.xlsx", "leads_trade_fair.xlsx", "leads_linkedin.xlsx", "sales_people.xlsx"]


def load_reference_data(creds=None, schema: str = "demo_raw", data_dir: Path = DATA_DIR) -> None:
    """Create `schema` if needed and (re)load every reference Excel as a table.
    creds: dict injected by Intelek, or None to read the DB_* variables from .env."""
    if creds is None:
        load_dotenv(ENV_FILE, override=True)
        creds = {key: os.environ[key] for key in CREDS_KEYS}
    engine = create_engine(URL.create(
        "postgresql+psycopg2", username=creds["DB_USER"], password=creds["DB_PASSWORD"],
        host=creds["DB_HOST"], port=int(creds.get("DB_PORT", 5432)), database=creds["DB_NAME"]))

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    for file_name in FILES:
        df = pd.read_excel(data_dir / file_name)
        table_name = Path(file_name).stem
        df.to_sql(table_name, engine, schema=schema, if_exists="replace", index=False)
        print(f"{schema}.{table_name:<20} {len(df):>3} rows loaded")


if __name__ == "__main__":
    load_reference_data()
