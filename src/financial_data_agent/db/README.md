# PostgreSQL Database

Local development runs Postgres in Docker. `test` and `prod` run on Supabase, one project per environment, created by Terraform — see [Deployed environments](#deployed-environments) below.

`migrations/versions/` is the single source of truth for the schema in every environment. Nothing creates tables by hand, and Terraform owns no table definitions.

### Configuration

`.env` lives at the **repository root**, is gitignored, and is local only. From there:

```bash
cp .env.example .env
```

`POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` configure the container below; `DATABASE_URL` is read by [database.py](database.py) and [../migrations/env.py](../migrations/env.py) and must match them. Deployed environments get `DATABASE_URL` from Terraform instead.

### Start Postgres

Run from this directory, where [docker-compose.yaml](docker-compose.yaml) lives. The image is `pgvector/pgvector:pg18`, so the pgvector extension is available but not yet enabled — see [pgvector](#pgvector).

`--env-file` is required and not optional. Compose resolves `.env` relative to the compose file's own directory, not the shell's working directory, so without it `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` all interpolate to empty strings and the container refuses to initialize. Passing `-f` from the repository root does not help either, for the same reason.

```bash
docker compose --env-file ../../../.env up -d
```

The same flag is needed for any other Compose command that interpolates those variables, such as `config` or `down -v`. Once the `postgres_data` volume is initialized, a plain `docker compose up -d` will appear to work, because Postgres only reads those variables on first initialization.

Verify it is running
```bash
docker compose ps -a
```

### Stop Postgres
```bash
docker compose down
```

### Migrations

Run from `src/financial_data_agent/` (one level up), where the working `alembic.ini` and `migrations/` live — not from this directory.

```bash
alembic revision --autogenerate -m "migration name"
alembic upgrade head
```

Add any new model to [models/__init__.py](models/__init__.py), otherwise `--autogenerate` will not see it: [../migrations/env.py](../migrations/env.py) builds `target_metadata` from that package.

`--autogenerate` only compares the `public` schema, because Alembic's `include_schemas` defaults to false. That is what keeps it from proposing to drop Supabase's own `auth` and `storage` schemas when run against a deployed database.

## Deployed environments

Each environment has its own Supabase project, created by `modules/supabase-postgres` rather than by hand. The pipeline's `Migrate database (<env>)` job then runs `alembic upgrade head` against it, and the app deploy is gated on that job so a new image never reaches a database that is behind it.

### Secrets

Two secrets per GitHub environment, and they have different origins:

| Secret | Where it comes from |
| --- | --- |
| `SUPABASE_ACCESS_TOKEN` | Generated in the Supabase dashboard under *Account preferences* → *Access Tokens*. Account-level, so the same value serves both environments. Use a **classic** token, not a project-scoped one — see [iac/README.md](../../../iac/README.md). |
| `SUPABASE_DB_PASSWORD` | You choose it. Terraform **sets** this as the new project's password rather than reading it back, so it is an input, not something to look up. |

Add both **before** the first deploy. Neither is produced by the deployment, so there is no ordering problem — without them `terraform plan` fails immediately on provider authentication and on the missing required variable, before anything is created.

Do not create the projects in the dashboard first. Terraform creates them as `fda-test` and `fda-prod`, and a free organization allows only two active projects. See [iac/README.md](../../../iac/README.md) for the full bootstrap, including the character set the password is restricted to.

### Connecting to a deployed database

`DATABASE_URL` is not the direct `db.<ref>.supabase.co` host. It points at the Supavisor **session pooler** on port 5432, for two reasons:

- The direct host is IPv6 only on the free tier, and GitHub hosted runners are IPv4 only, so migrations could never reach it.
- Session mode supports the prepared statements Alembic's DDL uses; transaction mode, on port 6543, does not.

To inspect an environment ad hoc, read the URL out of Terraform state rather than reconstructing it:

```bash
cd iac/environments/test
terraform output -raw database_url
```

That value is marked sensitive, so it is redacted in plan and apply output and has to be asked for by name.

### pgvector

No model uses a `Vector` column and no migration runs `CREATE EXTENSION vector`, so the extension is currently unused in every environment despite being present in the local image. [docs/architecture.md](../../../docs/architecture.md) targets pgvector for document embeddings; enabling it is a migration to write when that lands, not infrastructure to provision, since Supabase already ships the extension.
