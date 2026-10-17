# intelek-quickstarts

Ready-to-run examples for your [Intelek](https://intelek-docs.prenomics.com) account. Each one works on your laptop first, and then as-is in Intelek.

| Quickstart | What it shows | Engines |
|------------|---------------|---------|
| [compute/](compute/) | Data pipelines with SQL, Python, Jupyter and dbt: a lead-assignment use case built end to end | [PostgreSQL](compute/postgres/) · [ClickHouse](compute/clickhouse/) |

Each quickstart has one self-contained folder per database engine: pick yours and follow its README.
Sample data shared by every example is in [reference_data/](reference_data/).

## Requirements

- Python 3.11+ (pinned dependencies need it; 3.12 recommended)
- A PostgreSQL or ClickHouse database you can create tables in

## Credentials

- **On your laptop:** in the engine folder, copy `.env.example` to `.env` and fill in your connection. This file is git-ignored.
- **In Intelek:** create a secret object with the same keys (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, plus `DB_SCHEMA` on Postgres) and inject it into the function as `creds`.

The code is the same in both cases. See [compute/README.md](compute/README.md#credentials) for details.

## License

[MIT](LICENSE)
