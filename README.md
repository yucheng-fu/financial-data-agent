# Financial Data Agent

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql&logoColor=white)
![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)

AI assistant for analysing earnings reports of S&P 500 companies. It combines structured financial data (SQL), semantic search over filings (RAG with pgvector) and on-demand SEC filing acquisition behind a FastAPI backend.

> **Status:** early development. The ingestion and import side (companies, filings, financial metrics) is implemented. The agent orchestrator and RAG layers described in [docs/architecture.md](docs/architecture.md) are not built yet.

## Features

- Import the S&P 500 company list and store it in PostgreSQL
- Download 10-Q and 10-K filings from SEC EDGAR as markdown, with bulk backfill by year and quarter
- Store financial metrics per company, filing and period
- Versioned REST API built with FastAPI
- Target design: an agent that chooses between a SQL tool, a RAG tool and an SEC acquisition tool. See the [architecture](docs/architecture.md).

## Getting started

### Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) for the local PostgreSQL + pgvector instance

### Installation

```bash
git clone https://github.com/yucheng-fu/financial-data-agent.git
cd financial-data-agent
uv sync
```

### Configuration

Copy [.env.example](.env.example) to `.env` and set your own password:

```bash
cp .env.example .env
```

| Variable | Used by |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | the local Postgres container in [db/docker-compose.yaml](src/financial_data_agent/db/docker-compose.yaml) |
| `DATABASE_URL` | [db/database.py](src/financial_data_agent/db/database.py) and [migrations/env.py](src/financial_data_agent/migrations/env.py); must match the three above |

`.env` is gitignored and is local development only. In `test` and `prod`, Terraform provisions the Supabase project and passes `DATABASE_URL` to the container app as a secret — see [iac/README.md](iac/README.md).

### Database

```bash
docker compose up -d
cd src/financial_data_agent
alembic upgrade head
```

### Run the API

```bash
uv run fastapi dev src/financial_data_agent/api/main.py
```

Interactive API docs are then available at <http://127.0.0.1:8000/docs>.

## Development

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pyrefly check     # type check
```

To create a migration after changing a model, run this from `src/financial_data_agent/`:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Project structure

```text
.
├── data/ - Generated datasets organized by ticker, year, and quarter
├── docs/ - Project documentation and reference material
├── iac/ - Terraform for the Azure infrastructure (test and prod environments)
├── src/financial_data_agent/
│   ├── api/ - API routes, request models and response models
│   ├── db/ - Database models, repositories, DTOs and schemas
│   ├── ingestion/ - S&P 500 and SEC filing acquisition
│   ├── migrations/ - Alembic migrations
│   └── services/ - Application business services
└── tests/ - Unit tests
```

The code is layered with one-way dependencies: API route → service → repository → model.

## Deployment

The API is deployed to Azure Container Apps, with Postgres on Supabase. CI runs lint, type checks and tests on every pull request. On merge to `main`, the pipeline walks `test` then `prod`, with three jobs per environment and an approval on each GitHub environment:

**Deploy iac** — `terraform apply` for [iac/environments](iac/environments): container registry, the app's managed identity and its role assignments, the `filings` blob container, the Supabase Postgres project, and the container app itself. The registry, app and FQDN names are published as job outputs.

**Migrate database** — reads the connection string out of Terraform state and runs `alembic upgrade head` against that environment's Supabase project. The app deploy is gated on it, so a new image never reaches a database that is behind it.

**Deploy app** — `az acr build` builds the [Dockerfile](Dockerfile) in the registry and tags it with the commit SHA, `az containerapp update` points the app at that tag to create a new revision, then a smoke check requests `/api/v1/cow` over the public FQDN.

`Migrate database (test)` and `Deploy iac (prod)` both follow the test iac job and run in parallel. Prod is gated by its GitHub environment approval.

Terraform owns the infrastructure, the pipeline owns the image tag, and `migrations/versions/` owns the schema. See [iac/README.md](iac/README.md) for the split, the naming conventions and the one-off bootstrap, which includes two Supabase secrets per environment.

### Run the container locally

```bash
docker build -t fda-api:local .
docker run --rm -p 8000:8000 fda-api:local
```

The API is then on <http://127.0.0.1:8000/docs>. Pass `-e DATABASE_URL=...` to reach a database; on Windows and macOS use `host.docker.internal` instead of `localhost` to reach the Compose Postgres.

## Documentation

- [Architecture](docs/architecture.md)
