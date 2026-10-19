"""
Data quality for the lead-assignment demo (single-file script): fix what can be fixed
and set aside what cannot.

run_cleaning()  reads the unified leads table built by sql/01_unify_leads.sql (leads) and writes:
    leads_clean     leads ready to assign: fixes applied, cross-source duplicates merged,
                    and a dq_issues column with the problems that could not be fixed
                    but do not block the assignment (e.g. missing e-mail)
    leads_rejected  leads that cannot be assigned (e.g. unsupported language),
                    with a rejection_reason
It returns (and prints) one row per action taken.

Rules, in order:
    lead_id missing                  -> rejected (missing_lead_id)
    lead_id repeated                 -> keep the first row, drop the rest (duplicate_lead_id)
    language not supported           -> rejected (unsupported_language)
    e-mail with an invalid format    -> set to NULL, flagged (invalid_email)
    e-mail missing                   -> kept, flagged (missing_email)
    same e-mail in several leads     -> keep the oldest lead, merge the others into it
                                        (merged_lead_ids lists the merged ids)
    content not supported / missing  -> set to NULL, flagged (unknown_content)
    created_at in the future         -> kept, flagged (future_created_at)

run_checks() is the read-only diagnosis: it runs every check on leads and sales_people
and returns a report (check name, table, severity, failing rows, sample ids).

Usage (from Python):
    from basic_transf import run_cleaning, run_checks
    actions = run_cleaning()                                # credentials from .env
    actions = run_cleaning(dry_run=True)                    # compute, write nothing
    report = run_checks(leads_df=my_leads, sellers_df=my_sellers)   # offline, no DB

Usage (from the terminal):
    python basic_transf.py              # clean
    python basic_transf.py --dry-run    # clean, write nothing
    python basic_transf.py --checks     # diagnosis report only

In Intelek, schedule run_cleaning and inject the secret object as `creds`.
"""

import argparse
import os
import re
from pathlib import Path

import pandas as pd
import clickhouse_connect
from dotenv import load_dotenv

# Local runs: compute/.env (git-ignored), see .env.example next to it
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# Keys of the Intelek secret object, and names of the variables in .env
CREDS_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
DEFAULT_LEADS_TABLE = "leads"            # tables of the DB_NAME database
DEFAULT_SELLERS_TABLE = "sales_people"
DEFAULT_CLEAN_TABLE = "leads_clean"
DEFAULT_REJECTED_TABLE = "leads_rejected"
SECURE_PORTS = {8443}   # HTTPS, e.g. ClickHouse Cloud

VALID_LANGUAGES = {"es", "ca", "en", "fr", "de", "pt"}
VALID_CONTENTS = {"data_engineering", "bi_analytics", "machine_learning",
                  "genai", "data_governance", "cloud_platforms"}
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
def load_creds(creds=None) -> dict:
    """Credentials as a dict (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME): the dict
    Intelek injects or, if None, the same variables from compute/.env."""
    if creds is not None:
        return creds
    load_dotenv(ENV_FILE, override=True)
    return {key: os.environ[key] for key in CREDS_KEYS}


def get_client(creds=None):
    """ClickHouse client for the DB_NAME database (port 8443 means HTTPS)."""
    creds = load_creds(creds)
    port = int(creds.get("DB_PORT", 8123))
    return clickhouse_connect.get_client(
        host=creds["DB_HOST"], port=port, username=creds["DB_USER"],
        password=creds["DB_PASSWORD"], database=creds["DB_NAME"], secure=port in SECURE_PORTS)


def read_table(creds, table: str, client=None) -> pd.DataFrame:
    """Read a full table from ClickHouse."""
    client = client or get_client(creds)
    df = client.query_df(f"SELECT * FROM {table}")
    for col in df.columns:   # timestamps back to naive, as they were written
        if isinstance(df[col].dtype, pd.DatetimeTZDtype):
            df[col] = df[col].dt.tz_localize(None)
    return df


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


def replace_table(df: pd.DataFrame, client, table: str) -> None:
    """Drop `table` and recreate it from the DataFrame columns (even if df is empty)."""
    columns = ", ".join(f"`{col}` {clickhouse_type(dtype)}" for col, dtype in df.dtypes.items())
    client.command(f"DROP TABLE IF EXISTS {table}")
    client.command(f"CREATE TABLE {table} ({columns}) ENGINE = MergeTree ORDER BY tuple()")
    if not df.empty:
        rows = df.astype(object).where(df.notna(), None).values.tolist()   # NaN/NaT -> NULL
        client.insert(table, rows, column_names=list(df.columns))


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
# Cleaning: fix, flag or reject (pure pandas, no DB)
# ---------------------------------------------------------------------------
def clean_leads(leads: pd.DataFrame) -> tuple:
    """Apply the rules in the module docstring.

    Returns (clean, rejected, actions):
        clean:    leads ready to assign, plus dq_issues and merged_lead_ids
        rejected: leads that cannot be assigned, plus rejection_reason
        actions:  one row per action taken (lead_id, issue, action)
    """
    df = leads.copy()
    actions = []
    flags = {}   # lead_id -> [issue, ...] kept in leads_clean

    def log(ids, issue, action, flag=False):
        for lead_id in ids:
            actions.append({"lead_id": lead_id, "issue": issue, "action": action})
            if flag:
                flags.setdefault(lead_id, []).append(issue)

    rejected_parts = []

    def reject(mask, reason):
        nonlocal df
        log(df.loc[mask, "lead_id"], reason, "rejected")
        rejected_parts.append(df[mask].assign(rejection_reason=reason))
        df = df[~mask]

    # 1. Identity: a lead without id cannot be tracked; a repeated id is a reload
    reject(df["lead_id"].isna(), "missing_lead_id")
    repeated = df["lead_id"].duplicated(keep="first")
    log(df.loc[repeated, "lead_id"], "duplicate_lead_id", "dropped")
    df = df[~repeated]

    # 2. Nobody can serve a lead in a language we do not support
    reject(~df["preferred_language"].isin(VALID_LANGUAGES), "unsupported_language")

    # 3. E-mail: an invalid address is as useless as a missing one, but the lead stays
    df["email"] = df["email"].str.strip().str.lower()
    missing = df["email"].isna()
    invalid = ~missing & ~df["email"].fillna("").str.match(EMAIL_REGEX)
    log(df.loc[missing, "lead_id"], "missing_email", "kept, flagged", flag=True)
    log(df.loc[invalid, "lead_id"], "invalid_email", "e-mail set to NULL, flagged", flag=True)
    df.loc[invalid, "email"] = None

    # 4. Same person in several sources: keep the oldest lead, merge the rest into it
    df = df.sort_values(["created_at", "lead_id"], na_position="last")
    has_email = df["email"].notna()
    kept_id = df[has_email].groupby("email")["lead_id"].transform("first")
    merged = kept_id[kept_id != df.loc[has_email, "lead_id"]]
    for row_index, into in merged.items():
        log([df.at[row_index, "lead_id"]], "duplicate_email", f"merged into {into}")
    merged_ids = df.loc[merged.index, "lead_id"].groupby(merged.values).agg(", ".join)
    df = df.drop(index=merged.index)
    df["merged_lead_ids"] = df["lead_id"].map(merged_ids)

    # 5. Content: unknown values become NULL, the lead can still go to a language-only match
    unknown = ~df["content_of_interest"].isin(VALID_CONTENTS)
    log(df.loc[unknown, "lead_id"], "unknown_content", "content set to NULL, flagged", flag=True)
    df.loc[unknown, "content_of_interest"] = None

    # 6. Dates in the future are suspicious, but not a reason to drop the lead
    future = pd.to_datetime(df["created_at"]) > pd.Timestamp.now()
    log(df.loc[future, "lead_id"], "future_created_at", "kept, flagged", flag=True)

    df["dq_issues"] = df["lead_id"].map(lambda i: ", ".join(flags[i]) if i in flags else None)
    clean = df.sort_values("lead_id").reset_index(drop=True)
    rejected = pd.concat(rejected_parts) if rejected_parts else leads.iloc[0:0].assign(rejection_reason=None)
    actions = pd.DataFrame(actions, columns=["lead_id", "issue", "action"])
    return clean, rejected.sort_values("lead_id").reset_index(drop=True), actions


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def run_cleaning(creds=None,
                 leads_table: str = DEFAULT_LEADS_TABLE,
                 clean_table: str = DEFAULT_CLEAN_TABLE,
                 rejected_table: str = DEFAULT_REJECTED_TABLE,
                 leads_df: pd.DataFrame = None,
                 dry_run: bool = False,
                 verbose: bool = True) -> pd.DataFrame:
    """
    Clean the unified leads and write `clean_table` and `rejected_table` (both replaced).

    Args:
        creds:       dict with keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (injected by Intelek).
                     None: read from .env.
        leads_table: unified leads table (input).
        clean_table / rejected_table: output tables.
        leads_df:    optional DataFrame to clean instead of reading leads_table.
        dry_run:     compute but do not write (no DB needed if leads_df is given).
        verbose:     print the actions taken.

    Returns:
        DataFrame with one row per action taken (lead_id, issue, action).
    """
    client = None if (dry_run and leads_df is not None) else get_client(creds)
    leads = leads_df if leads_df is not None else read_table(creds, leads_table, client)

    clean, rejected, actions = clean_leads(leads)

    if verbose:
        print(actions.to_string(index=False) if not actions.empty else "No issues found.")
        print(f"\n{len(leads)} leads -> {len(clean)} in {clean_table}, {len(rejected)} in {rejected_table}, "
              f"{len(leads) - len(clean) - len(rejected)} merged or dropped")
    if dry_run:
        print("Dry run: nothing written.")
    else:
        replace_table(clean, client, clean_table)
        replace_table(rejected, client, rejected_table)
    return actions


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
    parser = argparse.ArgumentParser(description="Clean the unified leads (or only report).")
    parser.add_argument("--dry-run", action="store_true", help="compute but do not write")
    parser.add_argument("--checks", action="store_true", help="only print the diagnosis report")
    args = parser.parse_args()
    if args.checks:
        run_checks()
    else:
        run_cleaning(dry_run=args.dry_run)
