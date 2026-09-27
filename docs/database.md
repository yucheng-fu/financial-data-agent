# Financial Data Agent - Database

Design notes for the PostgreSQL layer. For the commands that start Postgres and run migrations, see [db/README.md](../src/financial_data_agent/db/README.md).

## 1. Overview

Local development runs Postgres in Docker. `test` and `prod` run on Supabase, one project per environment, created by Terraform rather than by hand.

`migrations/versions/` is the single source of truth for the schema in every environment. Nothing creates tables by hand, and Terraform owns no table definitions.

`.env` lives at the repository root, is gitignored, and is local development only. `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` configure the local container; `DATABASE_URL` is read by `db/database.py` and `migrations/env.py` and must match them. Deployed environments get `DATABASE_URL` from Terraform instead.

## 2. Local Postgres

`--env-file` is required and not optional. Compose resolves `.env` relative to the compose file's own directory, not the shell's working directory, so without it `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` all interpolate to empty strings and the container refuses to initialize. Passing `-f` from the repository root does not help either, for the same reason.

The same flag is needed for any other Compose command that interpolates those variables, such as `config` or `down -v`.

Once the `postgres_data` volume is initialized, a plain `docker compose up -d` will appear to work, because Postgres only reads those variables on first initialization. That makes a missing `--env-file` easy to miss until the volume is recreated.

The image is `pgvector/pgvector:pg18`, so the pgvector extension is available but not yet enabled — see [section 6](#6-pgvector).

## 3. Migrations

Alembic runs from `src/financial_data_agent/`, where the working `alembic.ini` and `migrations/` live.

Any new model must be added to `db/models/__init__.py`, otherwise `--autogenerate` will not see it: `migrations/env.py` builds `target_metadata` from that package.

`--autogenerate` only compares the `public` schema, because Alembic's `include_schemas` defaults to false. That is what keeps it from proposing to drop Supabase's own `auth` and `storage` schemas when run against a deployed database.

## 4. Deployed environments and secrets

Each environment has its own Supabase project, created by `modules/supabase-postgres`. The pipeline's `Migrate database (<env>)` job then runs `alembic upgrade head` against it, and the app deploy is gated on that job so a new image never reaches a database that is behind it.

Two secrets per GitHub environment, and they have different origins:

| Secret | Where it comes from |
| --- | --- |
| `SUPABASE_ACCESS_TOKEN` | Generated in the Supabase dashboard under *Account preferences* → *Access Tokens*. Account-level, so the same value serves both environments. Use a **classic** token, not a project-scoped one. |
| `SUPABASE_DB_PASSWORD` | You choose it. Terraform **sets** this as the new project's password rather than reading it back, so it is an input, not something to look up. |

Add both **before** the first deploy. Neither is produced by the deployment, so there is no ordering problem — without them `terraform plan` fails immediately on provider authentication and on the missing required variable, before anything is created.

Do not create the projects in the dashboard first. Terraform creates them as `fda-test` and `fda-prod`, and a free organization allows only two active projects.

[infrastructure.md](infrastructure.md) covers the full bootstrap, why the token must be a classic one, and the character set the password is restricted to.

## 5. The connection string

`DATABASE_URL` is not the direct `db.<ref>.supabase.co` host. It points at the Supavisor **session pooler** on port 5432. Two Supabase constraints force this:

- **The pooler is mandatory, not a tuning choice.** Supabase's direct host is IPv6 only on the free tier, and GitHub hosted runners are IPv4 only, so Alembic could never reach it.
- **Session mode, not transaction mode.** Alembic's DDL uses prepared statements, which transaction mode (port 6543) does not support. The module takes the session pooler URL, on port 5432 of the same host.

`modules/supabase-postgres` rewrites the `postgres://` scheme to `postgresql+psycopg://` for SQLAlchemy, substitutes the password that the Management API redacts, and appends `sslmode=require`. The `database_url` output carries a precondition that fails the apply if no substitution happened, so a passwordless URL can never reach the container app. If bring-up fails there, inspect the modes the API actually returned with `terraform output -json pooler_urls`.

The container app receives it as a container app **secret** with a secret-backed env var, not a plaintext env var, so Terraform owns the value and `az containerapp update` never competes with it.

To inspect an environment ad hoc, read the URL out of Terraform state rather than reconstructing it:

```bash
cd iac/environments/test
terraform output -raw database_url
```

That value is marked sensitive, so it is redacted in plan and apply output and has to be asked for by name.

`migrations/env.py` requires `DATABASE_URL` and calls `load_dotenv()` first, but `.env` is gitignored and local only, so on a runner the value the job exports is the single source. `load_dotenv()` also does not override an already set variable, so a `.env` appearing in the build context later would still not take precedence.

## 6. pgvector

No model uses a `Vector` column and no migration runs `CREATE EXTENSION vector`, so the extension is currently unused in every environment despite being present in the local image. [architecture.md](architecture.md) targets pgvector for document embeddings; enabling it is a migration to write when that lands, not infrastructure to provision, since Supabase already ships the extension as an available one.
