# Data pipeline demo: lead assignment

A small end-to-end pipeline that shows the same business problem solved with each tool:
leads arrive from 3 sources in different formats, get unified, validated, assigned to the
sales person who speaks their language and knows their topic, and finally reported on.

```
reference_data/*.xlsx ──load──▶ demo_raw.*            (Excels as-is)
                                    │
             sql/01_unify_leads.sql ▼
                               demo_stg.leads          (unified + normalized)
                                    │
     python_ipynb/basic_transf.py   ├──▶ data-quality report
                                    │
  python_ipynb/assign_leads.py|ipynb▼
                               demo_stg.lead_assignments
                                    │
                               dbt  ▼
            demo_mart.mart_lead_assignments, demo_mart.mart_seller_workload
```

## Contents

| # | Demo | Files |
|---|------|-------|
| 1 | Reference data | `../reference_data/*.xlsx` (built by `generate_reference_data.py`), loader `load_to_postgres.py` |
| 2 | SQL | `sql/01_unify_leads.sql` |
| 3 | Python basic (single file) | `python_ipynb/basic_transf.py` → `run_checks(...)` |
| 4 | Python complex (package) | `python_ipynb/assign_leads.py` → `run_assignment(...)`, helpers in `python_ipynb/utils/` |
| 5 | Jupyter | `python_ipynb/assign_leads.ipynb` |
| 6 | dbt | `dbt/` |

### 1. Reference data

| File | Rows | Format quirks |
|------|-----:|---------------|
| `leads_web_form.xlsx` | 40 | Headers with spaces (`"Lead ID"`), language as English name (`Spanish`), interest as label (`BI & Analytics`) |
| `leads_trade_fair.xlsx` | 25 | Spanish headers (`idioma`, `tema_interes`), ISO codes with messy casing (`CA`, `en `), Spanish labels |
| `leads_linkedin.xlsx` | 35 | Numeric ids, locale codes (`es_ES`), campaign codes (`GENAI`) |
| `sales_people.xlsx` | 9 | `Languages` / `Specialties` as `;`-separated lists, capacity (`Max Open Leads`), `Active` flag |

Canonical values: languages `es, ca, en, fr, de, pt`; contents `data_engineering, bi_analytics,
machine_learning, genai, data_governance, cloud_platforms`.

Some data-quality issues are injected on purpose, so the checks and the assignment have something to show:

| Record | Issue |
|--------|-------|
| `WEB-0007` | missing e-mail |
| `WEB-0012` | malformed e-mail (no `.com`) |
| `FAIR-005` | language `it`: no seller speaks Italian, so the lead ends up unassigned |
| `FAIR-011` | interest `Blockchain`: not a content we offer, so it maps to NULL |
| `LI-90003` | same person as `WEB-0003` (cross-source duplicate) |
| `S08` | inactive seller, who must never get leads |

To change the data, edit and re-run `generate_reference_data.py` (seeded, so the output is deterministic).

### 4. Assignment rules

Leads are processed in order of arrival. For each lead:
1. **full_match**: an active seller who speaks the lead's language *and* is specialized in its content.
2. **language_only**: if no specialist is available, any active seller who speaks the language.
3. **unassigned**: nobody speaks the language, or every candidate is at capacity.

Within a tier, the seller with the lowest *assigned / capacity* ratio wins (ties go to the lower `seller_id`).
Each row stores the `match_type` and a human-readable `reason`.
The process is incremental: only leads not yet in `demo_stg.lead_assignments` are assigned, unless you use `--full-refresh`.

```
python_ipynb/
├── assign_leads.py          # main: run_assignment() + CLI, uses relative imports (from .utils...)
├── assign_leads.ipynb       # same flow as a notebook
└── utils/
    ├── db.py                # engine, read/write 'schema.table'
    └── matching/
        ├── sellers.py       # normalize the raw sellers table
        ├── candidates.py    # candidate tiers + least-loaded pick
        └── assignment.py    # assign_leads() algorithm (pure pandas, no DB)
```

**About relative imports.** `assign_leads.py` uses `from .utils...`, so it has to run as a module
(`python -m python_ipynb.assign_leads`) from `compute/`. A notebook is not part of a package, so
`from .utils` fails there. Instead the notebook imports `utils` relative to its own folder, which is the
Jupyter working directory. Inside `utils/`, the modules still import each other relatively.

## Credentials

Every Python entry point takes a single `creds` argument:

| Value | When |
|-------|------|
| `dict` with keys `DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME` | **In Intelek.** The secret object is injected into the function as a dictionary |
| `None` (default) | **On your laptop.** Reads the same variables from the `.env` file at the repo root |

**On your laptop**

```bash
cp .env.example .env   # git-ignored, then fill it in
```

`.env` uses the same names as the secret object, so one file works for Python, dbt and `psql`.
Python loads it automatically, and its values take precedence over variables with the same name already
set in your shell. For dbt and `psql`, load it into the shell first:

```bash
set -a; source .env; set +a
```

**In Intelek**

1. Create a secret object with the keys `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` and `DB_NAME`.
2. Create a Python task that points to the function, and inject the secret as `creds`:

| Task | Function | Secret injected as |
|------|----------|--------------------|
| Load reference data | `reference_data/load_to_postgres.py` → `load_reference_data` | `creds` |
| Data-quality checks | `compute/python_ipynb/basic_transf.py` → `run_checks` | `creds` |
| Lead assignment | `compute/python_ipynb/assign_leads.py` → `run_assignment` | `creds` |

**Notebook.** Intelek runs notebooks with papermill, which injects a cell with the parameters right after
the cell tagged `parameters`. In `assign_leads.ipynb` that cell only sets defaults (`creds = None`, table
names, flags). The database connection is opened in the next cell, so it uses the injected values.

**dbt** has no Python function, so [dbt/profiles.yml](dbt/profiles.yml) reads the same `DB_*` environment
variables. The file holds no secrets and is committed. dbt picks it up from the project folder.

## How to run

Prerequisites: Postgres, and the packages in `requirements.txt` (dbt needs the **dbt-postgres** adapter, version 1.10 or later).
Commands run from the repo root unless they say otherwise.

```bash
pip install -r compute/requirements.txt
cp .env.example .env              # then fill it in
set -a; source .env; set +a       # only needed for psql and dbt

# 1. Load the Excels into demo_raw (optional: regenerate them first)
python reference_data/generate_reference_data.py
python reference_data/load_to_postgres.py

# 2. Unify the leads into demo_stg.leads
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f compute/sql/01_unify_leads.sql

# 3. Data-quality checks (or, from Python: run_checks(fail_on_error=True))
python compute/python_ipynb/basic_transf.py

# 4. Assign leads to sellers into demo_stg.lead_assignments (run as a module from compute/)
cd compute
python -m python_ipynb.assign_leads                  # incremental
python -m python_ipynb.assign_leads --full-refresh   # rebuild everything
python -m python_ipynb.assign_leads --dry-run        # compute only

# 5. ...or run python_ipynb/assign_leads.ipynb top to bottom instead of step 4

# 6. dbt
cd dbt && dbt build      # staging views in demo_stg, marts in demo_mart, plus tests
```

### Expected result with the bundled data

- **Checks:** 17 checks; 5 report errors (the injected issues) and 2 report warnings (the duplicate pair, and 18 leads with no specialist for their language + topic).
- **Assignment:** 100 leads, 10 unassigned (`FAIR-005` because nobody speaks Italian, 9 because candidates are at capacity), and S08 gets 0 leads.
- **dbt:** 3 views + 2 tables + 17 tests, all passing.
