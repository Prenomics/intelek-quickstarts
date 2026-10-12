# Compute quickstart on PostgreSQL

The lead-assignment pipeline on Postgres. The use case, data, rules, credentials and expected results are described
in [../README.md](../README.md); this page covers what is specific to Postgres.

## Where the tables go

Every table and view lives in one **existing** schema, `DB_SCHEMA` (for example `bizdoc`; `public` if you leave it
out). Nothing is created at the schema level.

| Layer | Tables | Built by |
|-------|--------|----------|
| Raw | `leads_web_form`, `leads_trade_fair`, `leads_linkedin`, `sales_people` | `load_reference_data.py` |
| Staging | `leads`, `lead_assignments`, views `stg_*` | SQL, Python and dbt |
| Marts | `mart_lead_assignments`, `mart_seller_workload` | dbt |

Each step drops and recreates its tables, so make sure `DB_SCHEMA` has no other tables with these names.
Your user needs to create tables and views in `DB_SCHEMA`; it does not need `CREATE` on the database.

Postgres needs one key more than ClickHouse: `DB_SCHEMA`, because a schema lives inside a database (`DB_NAME`).
Add it to the Intelek secret object too. Python and `psql` set it as the `search_path`, so the code uses
unqualified table names; dbt uses it as its target schema.

## How to run

Prerequisites: a Postgres database, `psql`, and the packages in `requirements.txt`
(dbt needs the **dbt-postgres** adapter, version 1.10 or later). Commands run from this folder unless they say otherwise.

```bash
cd compute/postgres
pip install -r requirements.txt
cp .env.example .env              # then fill it in
set -a; source .env; set +a       # only needed for psql and dbt

# 1. Load the Excels into DB_SCHEMA
python load_reference_data.py                     # or only some: python load_reference_data.py sales_people.xlsx

# 2. Unify the leads into the leads table
PGOPTIONS="-c search_path=$DB_SCHEMA" PGPASSWORD=$DB_PASSWORD \
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f sql/01_unify_leads.sql

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
