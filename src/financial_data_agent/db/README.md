# PostgreSQL Database

Local development runs Postgres in Docker. `test` and `prod` run on Supabase, one project per environment, created by Terraform.

## Configuration

`.env` lives at the repository root and is gitignored. From there:

```bash
cp .env.example .env
```

`POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` configure the container below; `DATABASE_URL` is read by [database.py](database.py) and [../migrations/env.py](../migrations/env.py) and must match them.

## Start Postgres

Run from this directory, where [docker-compose.yaml](docker-compose.yaml) lives. `--env-file` is required, not optional.

```bash
docker compose --env-file ../../../.env up -d
```

Verify it is running

```bash
docker compose ps -a
```

## Stop Postgres

```bash
docker compose down
```

## Migrations

Run from `src/financial_data_agent/` (one level up), where the working `alembic.ini` and `migrations/` live — not from this directory.

```bash
alembic revision --autogenerate -m "migration name"
alembic upgrade head
```

Add any new model to [models/__init__.py](models/__init__.py), otherwise `--autogenerate` will not see it.

## Enable the llm_reader login

The migrations create `llm_reader` without a password. Once per database, from this directory, set the password used in `LLM_READER_DATABASE_URL`:

```bash
docker compose --env-file ../../../.env exec postgres psql -U postgres -d financial_data_agent -c "ALTER ROLE llm_reader LOGIN PASSWORD 'change-me'"
```

## Further reading

[docs/database.md](../../../docs/database.md) — why `--env-file` is mandatory, what `--autogenerate` compares, the deployed environments and their secrets, how the Supabase connection string is built, and the state of pgvector.
