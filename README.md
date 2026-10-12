# intelek-quickstarts

Ready-to-run examples for your [Intelek](https://intelek-docs.prenomics.com) account. Each one works on your laptop first, and then as-is in Intelek.

| Quickstart | What it shows |
|------------|---------------|
| [compute/](compute/) | Data pipelines with SQL, Python, Jupyter and dbt: a lead-assignment use case built end to end |

Sample data for the examples is in [reference_data/](reference_data/).

## Requirements

- Python 3.10+
- A PostgreSQL database you can write to

## Credentials

- **On your laptop:** copy [.env.example](.env.example) to `.env` and fill in your Postgres connection. This file is git-ignored.
- **In Intelek:** create a secret object with the same keys (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`) and inject it into the function as `creds`.

The code is the same in both cases. See [compute/README.md](compute/README.md#credentials) for details.

## License

[MIT](LICENSE)
