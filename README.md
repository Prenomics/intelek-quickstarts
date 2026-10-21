# intelek-quickstarts

Ready-to-run examples for your [Intelek](https://intelek-docs.prenomics.com) account. Each one works on your laptop first, and then as-is in Intelek.

> **This is a demo project.** All the data is synthetic (no real people or companies), some data-quality
> issues are injected on purpose, and a few steps are done in a way that only makes sense for a demo, to keep
> it realistic and easy to follow. Use it to learn the tools, not as a production template: see
> [About this demo](compute/README.md#about-this-demo) for what would change in a real project.

| Quickstart | What it shows | Engine |
|------------|---------------|--------|
| [compute/](compute/) | Data pipelines with SQL, Python, Jupyter and dbt: a lead-assignment use case built end to end (unify, clean, assign, report), from raw data imported out of a Postgres database and Excel files | ClickHouse |

Sample data is in [reference_data/](reference_data/):

| File | What it is |
|------|------------|
| `create_reference_data.sql` | Creates and fills the Postgres origin tables (`leads_web_form`, `leads_linkedin`, `sales_people`). Run it once, e.g. in the Neon SQL Editor |
| `leads_trade_fair.xlsx`, `leads_trade_fair_2.xlsx` | Excel origin: leads from two trade fairs, same format, loaded into `leads_trade_fair` |
| `generate_reference_data.py` | Regenerates the Excels (seeded, deterministic) |

## Requirements

- Python 3.11+ (pinned dependencies need it; 3.12 recommended)
- A ClickHouse database you can create tables in
- A Postgres database (e.g. Neon) for the origin tables
- A way to import the Postgres tables and the Excels into ClickHouse (the pipeline starts from them)

## Credentials

- **On your laptop:** in `compute/`, copy `.env.example` to `.env` and fill in your connection. This file is git-ignored.
- **In Intelek:** create a secret object with the same keys (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`) and inject it into the function as `creds`.

The code is the same in both cases. See [compute/README.md](compute/README.md#credentials) for details.

## License

[MIT](LICENSE)
