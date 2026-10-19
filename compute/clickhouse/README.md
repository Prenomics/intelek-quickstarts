# Compute quickstart on ClickHouse

The lead-assignment pipeline on ClickHouse. The use case, data, rules, credentials and expected results are described
in [../README.md](../README.md); this page covers what is specific to ClickHouse.

## Where the tables go

ClickHouse has no schemas, so every table and view lives in one **existing** database, `DB_NAME`
(for example `pre_bizdoc`). Nothing is created at the database level.

| Layer | Tables | Built by |
|-------|--------|----------|
| Raw | `leads_web_form`, `leads_linkedin`, `sales_people` | You: import from the Postgres origin |
| Raw | `leads_trade_fair` | You: import from `reference_data/leads_trade_fair.xlsx` |
| Staging | `leads`, `lead_assignments`, views `stg_*` | SQL, Python and dbt |
| Marts | `mart_lead_assignments`, `mart_seller_workload` | dbt |

The pipeline starts from the 4 raw tables, so import them into `DB_NAME` first, with the column names they have at
the origin (see [Raw tables](../README.md#1-raw-tables)). Each step after that drops and recreates its tables, so
make sure `DB_NAME` has no other tables with these names.
Your user needs to create, drop, insert into and select from tables and views in `DB_NAME`; it does not need
`CREATE DATABASE`.

`DB_PORT` is the HTTP port: `8123`, or `8443` for HTTPS (e.g. ClickHouse Cloud), which Python and dbt detect
automatically. dbt uses `DB_NAME` as its schema, which in ClickHouse is the database.

## How to run

Prerequisites: a ClickHouse database, `clickhouse client` for the SQL step, and the packages in `requirements.txt`
(dbt needs the **dbt-clickhouse** adapter). Commands run from this folder unless they say otherwise.

```bash
cd compute/clickhouse
pip install -r requirements.txt
cp .env.example .env              # then fill it in
set -a; source .env; set +a       # only needed for clickhouse client and dbt

# 1. Import the raw tables into DB_NAME (your ingestion step, not part of this folder):
#    leads_web_form, leads_linkedin, sales_people from Postgres; leads_trade_fair from the Excel

# 2. Unify the leads into the leads table
#    clickhouse client uses the native port (9000, or 9440 with --secure), not DB_PORT
clickhouse client --host $DB_HOST --user $DB_USER --password "$DB_PASSWORD" --database $DB_NAME \
    --multiquery < sql/01_unify_leads.sql

# 3. Data-quality checks (or, from Python: run_checks(fail_on_error=True))
python python_ipynb/basic_transf.py

# 4. Assign leads to sellers into lead_assignments
python -m python_ipynb.assign_leads                  # incremental
python -m python_ipynb.assign_leads --full-refresh   # rebuild everything
python -m python_ipynb.assign_leads --dry-run        # compute only

# 5. ...or run python_ipynb/assign_leads.ipynb top to bottom instead of step 4

# 6. dbt: stg_* views, mart_* tables, plus tests
cd dbt && dbt build
```
