# intelek-quickstarts

Ready-to-run examples for your [Intelek](https://intelek-docs.prenomics.com) account. Each one works on your laptop first, and then as-is in Intelek.

| Quickstart | What it shows | Engine |
|------------|---------------|--------|
| [compute/](compute/) | Data pipelines with SQL, Python, Jupyter and dbt: a lead-assignment use case built end to end, from raw data imported out of a Postgres database and an Excel file | [ClickHouse](compute/clickhouse/) |

Sample data is in [reference_data/](reference_data/); the Postgres origin tables are created with
[config/connectors/psql/create_reference_data.sql](config/connectors/psql/create_reference_data.sql).

## Requirements

- Python 3.11+ (pinned dependencies need it; 3.12 recommended)
- A ClickHouse database you can create tables in
- A Postgres database (e.g. Neon) for the origin tables

## Credentials

- **On your laptop:** in `compute/clickhouse/`, copy `.env.example` to `.env` and fill in your connection. This file is git-ignored.
- **In Intelek:** create a secret object with the same keys (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`) and inject it into the function as `creds`.

The code is the same in both cases. See [compute/README.md](compute/README.md#credentials) for details.

## License

[MIT](LICENSE)
