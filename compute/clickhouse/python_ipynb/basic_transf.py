"""
Basic data-quality checks for the lead-assignment demo (single-file script).

Validates:
    - the unified leads table built by sql/01_unify_leads.sql  (default: leads)
    - the sales people reference table                           (default: sales_people)
    - the cross-table rule "every lead can be served by at least one active seller"

Each check returns one row: check name, table, severity (error | warning),
number of failing rows and a sample of failing ids.

Usage (from Python):
    from basic_transf import run_checks
    report = run_checks()                                   # credentials from .env
    report = run_checks(leads_df=my_leads, sellers_df=my_sellers)   # offline, no DB

Usage (from the terminal):
    python basic_transf.py

In Intelek, schedule run_checks and inject the secret object as `creds`.
"""

import os
import re
from pathlib import Path

import pandas as pd
import clickhouse_connect
from dotenv import load_dotenv

# Local runs: compute/clickhouse/.env (git-ignored), see .env.example next to it
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
DEFAULT_LEADS_TABLE = "leads"            # tables of the DB_NAME database
DEFAULT_SELLERS_TABLE = "sales_people"

VALID_LANGUAGES = {"es", "ca", "en", "fr", "de", "pt"}
VALID_CONTENTS = {"data_engineering", "bi_analytics", "machine_learning",
                  "genai", "data_governance", "cloud_platforms"}
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)

# Raw Excel headers -> normalized names
SELLER_COLUMNS = {"Seller ID": "seller_id", "Full Name": "full_name", "Email": "email",
                  "Languages": "languages", "Specialties": "specialties",
                  "Max Open Leads": "max_open_leads", "Active": "active"}


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
def load_creds(creds=None) -> dict:
    """Credentials as a dict (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME): the dict
    Intelek injects or, if None, the same variables from compute/clickhouse/.env."""
    if creds is not None:
        return creds
    load_dotenv(ENV_FILE, override=True)
    return {key: os.environ[key] for key in CREDS_KEYS}


def read_table(creds, table: str) -> pd.DataFrame:
    """Read a full table from ClickHouse (port 8443 means HTTPS)."""
    creds = load_creds(creds)
    port = int(creds.get("DB_PORT", 8123))
    client = clickhouse_connect.get_client(
        host=creds["DB_HOST"], port=port, username=creds["DB_USER"],
        password=creds["DB_PASSWORD"], database=creds["DB_NAME"], secure=port == 8443)
    df = client.query_df(f"SELECT * FROM {table}")
    for col in df.columns:   # timestamps back to naive, as they were written
        if isinstance(df[col].dtype, pd.DatetimeTZDtype):
            df[col] = df[col].dt.tz_localize(None)
    return df


def split_list(value) -> set:
    """'es; CA ;en' -> {'es', 'ca', 'en'}. Empty/NULL -> empty set."""
    if value is None or pd.isna(value):
        return set()
    return {v.strip().lower() for v in str(value).split(";") if v.strip()}


# ---------------------------------------------------------------------------
# Checks: each check_* function returns a list of result rows (dicts)
# ---------------------------------------------------------------------------
def _result(name: str, table: str, severity: str, failing: pd.DataFrame, id_col: str) -> dict:
    return {
        "check": name,
        "table": table,
        "severity": severity,
        "failed_rows": len(failing),
        "status": "OK" if failing.empty else severity.upper(),
        "sample_ids": ", ".join(failing[id_col].astype(str).head(5)),
    }


def check_leads(leads: pd.DataFrame, table: str) -> list:
    results = []
    id_col = "lead_id"

    results.append(_result("lead_id is unique and not null", table, "error",
                           leads[leads[id_col].isna() | leads[id_col].duplicated(keep=False)], id_col))

    for col in ["email", "preferred_language", "content_of_interest"]:
        results.append(_result(f"{col} is not null", table, "error", leads[leads[col].isna()], id_col))

    has_email = leads["email"].notna()
    bad_email = has_email & ~leads["email"].fillna("").str.match(EMAIL_REGEX)
    results.append(_result("email has a valid format", table, "error", leads[bad_email], id_col))

    bad_lang = leads["preferred_language"].notna() & ~leads["preferred_language"].isin(VALID_LANGUAGES)
    results.append(_result("preferred_language is a supported language", table, "error",
                           leads[bad_lang], id_col))

    bad_content = leads["content_of_interest"].notna() & ~leads["content_of_interest"].isin(VALID_CONTENTS)
    results.append(_result("content_of_interest is a supported content", table, "error",
                           leads[bad_content], id_col))

    dup_email = has_email & leads["email"].duplicated(keep=False)
    results.append(_result("email is not duplicated across sources", table, "warning",
                           leads[dup_email], id_col))

    future = pd.to_datetime(leads["created_at"]) > pd.Timestamp.now()
    results.append(_result("created_at is not in the future", table, "warning", leads[future], id_col))
    return results


def check_sellers(sellers: pd.DataFrame, table: str) -> list:
    results = []
    id_col = "seller_id"

    results.append(_result("seller_id is unique and not null", table, "error",
                           sellers[sellers[id_col].isna() | sellers[id_col].duplicated(keep=False)], id_col))

    langs = sellers["languages"].map(split_list)
    specs = sellers["specialties"].map(split_list)
    results.append(_result("seller speaks at least one supported language", table, "error",
                           sellers[langs.map(lambda s: not s & VALID_LANGUAGES)], id_col))
    results.append(_result("seller languages are all supported", table, "warning",
                           sellers[langs.map(lambda s: bool(s - VALID_LANGUAGES))], id_col))
    results.append(_result("seller specialties are all supported contents", table, "error",
                           sellers[specs.map(lambda s: not s or bool(s - VALID_CONTENTS))], id_col))

    results.append(_result("max_open_leads is a positive number", table, "error",
                           sellers[~(pd.to_numeric(sellers["max_open_leads"], errors="coerce") > 0)], id_col))
    results.append(_result("active is Yes/No", table, "error",
                           sellers[~sellers["active"].isin(["Yes", "No"])], id_col))
    return results


def check_coverage(leads: pd.DataFrame, sellers: pd.DataFrame, table: str) -> list:
    """Every lead should have at least one active seller speaking its language
    (error if not) and, ideally, also specialized in its content (warning if not)."""
    active = sellers[sellers["active"] == "Yes"]
    seller_skills = [(split_list(r.languages), split_list(r.specialties)) for r in active.itertuples()]

    def speaks(lead):
        return any(lead.preferred_language in langs for langs, _ in seller_skills)

    def full_match(lead):
        return any(lead.preferred_language in langs and lead.content_of_interest in specs
                   for langs, specs in seller_skills)

    no_language = leads[[not speaks(l) for l in leads.itertuples()]]
    no_full = leads[[speaks(l) and not full_match(l) for l in leads.itertuples()]]
    return [
        _result("lead language is spoken by an active seller", table, "error", no_language, "lead_id"),
        _result("lead language + content covered by an active seller", table, "warning", no_full, "lead_id"),
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_checks(creds=None,
               leads_table: str = DEFAULT_LEADS_TABLE,
               sellers_table: str = DEFAULT_SELLERS_TABLE,
               leads_df: pd.DataFrame = None,
               sellers_df: pd.DataFrame = None,
               fail_on_error: bool = False,
               verbose: bool = True) -> pd.DataFrame:
    """
    Run all data-quality checks and return a report DataFrame.

    Args:
        creds:         dict with keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (injected by Intelek).
                       None: read from .env. Not used if both leads_df and sellers_df are given.
        leads_table:   unified leads table.
        sellers_table: raw sales people table.
        leads_df / sellers_df: optional DataFrames to validate instead of reading the DB.
        fail_on_error: raise ValueError if any 'error' check fails (useful in pipelines).
        verbose:       print the report.
    """
    leads = leads_df if leads_df is not None else read_table(creds, leads_table)
    sellers = sellers_df if sellers_df is not None else read_table(creds, sellers_table)
    sellers = sellers.rename(columns=SELLER_COLUMNS)

    report = pd.DataFrame(
        check_leads(leads, leads_table)
        + check_sellers(sellers, sellers_table)
        + check_coverage(leads, sellers, f"{leads_table} x {sellers_table}")
    )

    n_errors = int((report["status"] == "ERROR").sum())
    n_warnings = int((report["status"] == "WARNING").sum())
    if verbose:
        with pd.option_context("display.max_colwidth", 60, "display.width", 200):
            print(report.to_string(index=False))
        print(f"\n{len(report)} checks: {n_errors} with errors, {n_warnings} with warnings")

    if fail_on_error and n_errors:
        raise ValueError(f"Data-quality check failed: {n_errors} checks with errors")
    return report


if __name__ == "__main__":
    run_checks()
