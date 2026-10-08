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

The image is `pgvector/pgvector:pg18`, so the pgvector extension is available for the migration that enables it — see [section 6](#6-pgvector).

## 3. Migrations

Alembic runs from `src/financial_data_agent/`, where the working `alembic.ini` and `migrations/` live.

Any new model must be added to `db/models/__init__.py`, otherwise `--autogenerate` will not see it: `migrations/env.py` builds `target_metadata` from that package.

`--autogenerate` only compares the `public` schema, because Alembic's `include_schemas` defaults to false. That is what keeps it from proposing to drop Supabase's own `auth` and `storage` schemas when run against a deployed database.

## 4. Deployed environments and secrets

Each environment has its own Supabase project, created by `modules/supabase-postgres`. The pipeline's `Migrate database (<env>)` job then runs `alembic upgrade head` against it, and the app deploy is gated on that job so a new image never reaches a database that is behind it.

Three secrets per GitHub environment, and they have different origins:

| Secret | Where it comes from |
| --- | --- |
| `SUPABASE_ACCESS_TOKEN` | Generated in the Supabase dashboard under *Account preferences* → *Access Tokens*. Account-level, so the same value serves both environments. Use a **classic** token, not a project-scoped one. |
| `SUPABASE_DB_PASSWORD` | You choose it. Terraform **sets** this as the new project's password rather than reading it back, so it is an input, not something to look up. |
| `LLM_READER_DB_PASSWORD` | You choose it. Terraform composes it into `LLM_READER_DATABASE_URL` for the container app and the migrate job, and migration `b3c7e1d9a4f2` sets it on the `llm_reader` role. Locally the same URL comes from `.env`. |

Add all three **before** the first deploy. None is produced by the deployment, so there is no ordering problem — without them `terraform plan` fails immediately on provider authentication and on the missing required variables, before anything is created.

The migration sets the `llm_reader` password once. Changing `LLM_READER_DB_PASSWORD` later needs `alembic downgrade -1` and `alembic upgrade head` against that environment after the apply.

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

`document_chunks` stores one row per chunk of filing markdown, with a 384-dimension `Vector` column holding its embedding. The `document_chunks` migration enables the extension with `CREATE EXTENSION IF NOT EXISTS vector` before creating the table, because Postgres rejects the unknown `VECTOR` type otherwise. No `SCHEMA` clause is given: Supabase already ships the extension, and naming a schema would conflict with where it put it. The downgrade drops the table and its indexes but leaves the extension, because dropping one that another object may depend on is not this migration's business.

The vector migration is written by hand rather than autogenerated. `--autogenerate` emits the `Vector` type without importing it, never emits `CREATE EXTENSION`, and produces a file that fails on the first run.

The dimension is fixed in the DDL rather than read from configuration. pgvector needs a literal dimension for an index to be creatable at all, and a migration that resolved `EMBEDDING_MODEL` at apply time would produce a different schema per environment. `EMBEDDING_MODEL` therefore selects among models that produce 384 dimensions; anything else is a schema change. `DocumentChunkImportService` checks the length of every embedding before writing, so a 768-dimension model fails at import with a clear error rather than at query time with a silent recall collapse. Each row also records the model that produced it in `embedding_model`, which is what makes a half-re-embedded table detectable.

384 comes from `BAAI/bge-small-en-v1.5`, which `fastembed` runs in process on onnxruntime. That is what keeps corpus and query vectors comparable: the offline chunk import and the deployed agent load the same quantized ONNX weights, so there is no drift of the kind that appears when one side uses a locally quantized model and the other a hosted full-precision copy of nominally the same model. A larger model is a legitimate trade to make later — it is a new migration and a full re-embed, and the evaluation harness is what should decide it.

## 7. The vector index

The embedding column carries an HNSW index using `vector_cosine_ops`, declared in the model with `postgresql_using`, `postgresql_with` and `postgresql_ops` so it lives in the metadata rather than only in a migration.

HNSW rather than IVFFlat, because IVFFlat's lists are k-means centroids computed over whatever is in the table when the index is built. Building one in a migration, against an empty table, produces a degenerate index that has to be dropped and rebuilt after data lands — so the migration would claim a working index that does not exist, and recall would stay poor until someone remembered to reindex. HNSW is correct on an empty table and stays correct as filings are chunked one at a time.

Two consequences worth knowing:

- `migrations/env.py` excludes the index from autogenerate through `include_object`. Alembic cannot model the operator class, so every later autogenerate run would otherwise emit a spurious drop.
- Building HNSW needs the vectors to fit in `maintenance_work_mem`. A full S&P 500 backfill is on the order of 400MB of vectors and will exceed a small Supabase instance's default. The index is created on an empty table here, so the migration itself is instant; a bulk backfill should either raise `maintenance_work_mem` for the session or drop the index, load, and recreate it.

Queries must use the `<=>` operator, which is what `DocumentChunk.embedding.cosine_distance(...)` compiles to. The `cosine_distance()` SQL function is not the same thing and does not use the index, so a query written that way silently degrades into a sequential scan over every chunk.
