"""
Assign new leads to sales people and materialize the result in Postgres.

Pipeline:
    leads  +  sales_people  ->  lead_assignments        (tables of the DB_SCHEMA schema)

"New" leads are the ones not yet present in the output table, so the script can
be re-run incrementally; use full_refresh=True to rebuild every assignment.

This file uses *relative imports*, so it must be run as a module from the
compute/postgres folder (the parent of the python_ipynb package):

    cd compute/postgres
    python -m python_ipynb.assign_leads                      # credentials from .env
    python -m python_ipynb.assign_leads --full-refresh
    python -m python_ipynb.assign_leads --dry-run

or from Python:

    from python_ipynb.assign_leads import run_assignment
    run_assignment(full_refresh=True)

In Intelek, schedule run_assignment and inject the secret object as `creds`.
"""

import argparse

import pandas as pd

from .utils.db import get_engine, read_table, table_exists, write_table
from .utils.matching import assign_leads, current_load, normalize_sellers, summarize

LEADS_TABLE = "leads"
SELLERS_TABLE = "sales_people"
OUTPUT_TABLE = "lead_assignments"


def run_assignment(creds=None,
                   leads_table: str = LEADS_TABLE,
                   sellers_table: str = SELLERS_TABLE,
                   output_table: str = OUTPUT_TABLE,
                   full_refresh: bool = False,
                   dry_run: bool = False) -> pd.DataFrame:
    """
    Read the new leads and the active sellers, assign leads to sellers and write
    the assignments to `output_table`.

    Args:
        creds:        dict with keys DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (injected by Intelek).
                      None: read from .env.
        leads_table / sellers_table / output_table: table names in DB_SCHEMA.
        full_refresh: ignore previous assignments and rebuild the output table.
        dry_run:      compute the assignments but do not write them.

    Returns:
        DataFrame with the assignments created in this run.
    """
    engine = get_engine(creds)

    # 1. Read inputs
    leads = read_table(engine, leads_table)
    sellers = normalize_sellers(read_table(engine, sellers_table))

    existing = None
    if not full_refresh and table_exists(engine, output_table):
        existing = read_table(engine, output_table)
        leads = leads[~leads["lead_id"].isin(existing["lead_id"])]

    print(f"{len(leads)} new leads | {len(sellers)} active sellers | "
          f"{0 if existing is None else len(existing)} previous assignments")
    if leads.empty:
        print("Nothing to assign.")
        return leads

    # 2. Assign (pure function, no DB access)
    assignments = assign_leads(leads, sellers, load=current_load(existing))
    print(summarize(assignments).to_string())

    # 3. Materialize
    if dry_run:
        print("Dry run: nothing written.")
    else:
        write_table(assignments, engine, output_table,
                    if_exists="replace" if full_refresh else "append")
        print(f"{len(assignments)} rows written to {output_table}")
    return assignments


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign new leads to sales people.")
    parser.add_argument("--full-refresh", action="store_true", help="rebuild all assignments")
    parser.add_argument("--dry-run", action="store_true", help="do not write the output table")
    args = parser.parse_args()
    run_assignment(full_refresh=args.full_refresh, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
