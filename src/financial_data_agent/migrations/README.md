# Alembic migrations

Schema revisions for the Postgres database, generated from the SQLAlchemy models.

## Prerequisites

Postgres running locally and `DATABASE_URL` set in the repository-root `.env` — see [../db/README.md](../db/README.md).

## Apply migrations

Run from `src/financial_data_agent/` (the parent of this directory), where `alembic.ini` lives.

```bash
cd src/financial_data_agent
uv run alembic upgrade head
```

Check what is applied, and the full revision history:

```bash
uv run alembic current
uv run alembic history
```

Roll back one revision:

```bash
uv run alembic downgrade -1
```

## Create a migration

```bash
uv run alembic revision --autogenerate -m "migration name"
```

Add any new model to [../db/models/__init__.py](../db/models/__init__.py) first, otherwise `--autogenerate` will not see it. Review the generated file in [versions/](versions/) before applying it.

## Further reading

[docs/database.md](../../../docs/database.md) — what `--autogenerate` compares, the deployed environments and their secrets, and the state of pgvector.
