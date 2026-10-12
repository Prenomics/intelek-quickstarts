# Compute quickstart: lead assignment

A small end-to-end pipeline that shows the same business problem solved with each tool:
leads arrive from 3 sources in different formats, get unified, validated, assigned to the
sales person who speaks their language and knows their topic, and finally reported on.

**Pick your database:**

| Engine | Folder |
|--------|--------|
| PostgreSQL | [postgres/](postgres/) |
| ClickHouse | [clickhouse/](clickhouse/) |

Each folder is self-contained (its own code, `requirements.txt`, `.env` and README) and has the same structure,
so `diff -r postgres clickhouse` shows only what changes between engines. The sample data in
[../reference_data/](../reference_data/) is shared.

```
reference_data/*.xlsx ──load──▶ leads_web_form, leads_trade_fair,      (Excels as-is)
                                leads_linkedin, sales_people
                                    │
             sql/01_unify_leads.sql ▼
                               leads                    (unified + normalized)
                                    │
     python_ipynb/basic_transf.py   ├──▶ data-quality report
                                    │
  python_ipynb/assign_leads.py|ipynb▼
                               lead_assignments
                                    │
                               dbt  ▼
            mart_lead_assignments, mart_seller_workload
```

Both engines put every table and view in one place that must already exist: a schema in Postgres (`DB_SCHEMA`,
e.g. `bizdoc`), a database in ClickHouse (`DB_NAME`, e.g. `pre_bizdoc`). See each folder's README.

## Contents

Paths are relative to the engine folder.

| # | Demo | Files |
|---|------|-------|
| 1 | Reference data | `../../reference_data/*.xlsx` (built by `generate_reference_data.py`), loader `load_reference_data.py` |
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

To change the data, edit and re-run `reference_data/generate_reference_data.py` (seeded, so the output is deterministic).

### 4. Assignment rules

Leads are processed in order of arrival. For each lead:
1. **full_match**: an active seller who speaks the lead's language *and* is specialized in its content.
2. **language_only**: if no specialist is available, any active seller who speaks the language.
3. **unassigned**: nobody speaks the language, or every candidate is at capacity.

Within a tier, the seller with the lowest *assigned / capacity* ratio wins (ties go to the lower `seller_id`).
Each row stores the `match_type` and a human-readable `reason`.
The process is incremental: only leads not yet in `lead_assignments` are assigned, unless you use `--full-refresh`.

```
python_ipynb/
├── assign_leads.py          # main: run_assignment() + CLI, uses relative imports (from .utils...)
├── assign_leads.ipynb       # same flow as a notebook
└── utils/
    ├── db.py                # connection + read/write tables (the only engine-specific module)
    └── matching/
        ├── sellers.py       # normalize the raw sellers table
        ├── candidates.py    # candidate tiers + least-loaded pick
        └── assignment.py    # assign_leads() algorithm (pure pandas, no DB)
```

**About relative imports.** `assign_leads.py` uses `from .utils...`, so it has to run as a module
(`python -m python_ipynb.assign_leads`) from the engine folder. A notebook is not part of a package, so
`from .utils` fails there. Instead the notebook imports `utils` relative to its own folder, which is the
Jupyter working directory. Inside `utils/`, the modules still import each other relatively.

## Credentials

Every Python entry point takes a single `creds` argument:

| Value | When |
|-------|------|
| `dict` with keys `DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME` (+ `DB_SCHEMA` on Postgres) | **In Intelek.** The secret object is injected into the function as a dictionary |
| `None` (default) | **On your laptop.** Reads the same variables from the `.env` file in the engine folder |

**On your laptop:** copy the engine folder's `.env.example` to `.env` (git-ignored) and fill it in. Python loads it
automatically, and its values take precedence over variables with the same name already set in your shell.
dbt and the SQL client read the same variables from the shell, so load the file first:
`set -a; source .env; set +a`.

**In Intelek:**

1. Create a secret object with the keys `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` and `DB_NAME`
   (on Postgres, also `DB_SCHEMA`).
2. Create a Python task that points to the function, and inject the secret as `creds`:

| Task | Function (in the engine folder) | Secret injected as |
|------|----------------------------------|--------------------|
| Load reference data | `load_reference_data.py` → `load_reference_data` | `creds` |
| Data-quality checks | `python_ipynb/basic_transf.py` → `run_checks` | `creds` |
| Lead assignment | `python_ipynb/assign_leads.py` → `run_assignment` | `creds` |

**Notebook.** Intelek runs notebooks with papermill, which injects a cell with the parameters right after
the cell tagged `parameters`. In `assign_leads.ipynb` that cell only sets defaults (`creds = None`, table
names, flags). The database connection is opened in the next cell, so it uses the injected values.

**dbt** has no Python function, so `dbt/profiles.yml` reads the same `DB_*` environment variables.
The file holds no secrets and is committed. dbt picks it up from the project folder.

## Expected result with the bundled data

The same on every engine:

- **Checks:** 17 checks; 5 report errors (the injected issues) and 2 report warnings (the duplicate pair, and 18 leads with no specialist for their language + topic).
- **Assignment:** 100 leads, 10 unassigned (`FAIR-005` because nobody speaks Italian, 9 because candidates are at capacity), and S08 gets 0 leads.
- **dbt:** 3 views + 2 tables + 17 tests, all passing.
