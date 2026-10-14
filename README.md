# Financial Data Agent

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-1C3C3C)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql&logoColor=white)
![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)

AI assistant for analysing earnings reports of S&P 500 companies. It combines structured financial data (SQL), semantic search over filings (RAG with pgvector) and on-demand SEC filing acquisition behind a FastAPI backend.

> **Status:** in development.
> - **Ingestion is done:** companies, filings, financial metrics, and chunked and embedded filing text.
> - **The chat endpoint answers questions with read-only SQL.**
> - **The TableRAG subgraph is built but not yet a chat tool.**
> - **Not built yet:** filing acquisition and the web front end.
>
> See [docs/architecture.md](docs/architecture.md) for the target design.

## Features

- Import the S&P 500 company list and store it in PostgreSQL
- Download 10-Q and 10-K filings from SEC EDGAR as markdown, with bulk backfill by year and quarter
- Store financial metrics per company, filing and period
- Chunk filings with a table-aware markdown splitter and embed them in process with `fastembed` into pgvector
- `POST /api/v1/chat`: a LangGraph agent on Gemini that writes SQL, runs it as a read-only `llm_reader` role, and returns the answer, the SQL steps and the tokens used
- TableRAG subgraph: query decomposition, filtered vector search, BM25 reranking and selective SQL. See [docs/RAG.md](docs/RAG.md).

## Getting started

### Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) for the local PostgreSQL + pgvector instance
- A [Gemini API key](https://aistudio.google.com/apikey) (free tier) for the chat endpoint

### Installation

```bash
git clone https://github.com/yucheng-fu/financial-data-agent.git
cd financial-data-agent
uv sync
```

### Configuration

Copy [.env.example](.env.example) to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Used by |
| --- | --- |
| `ENVIRONMENT` | filings storage: `local` writes to `data/`; `test` and `prod` use Azure Blob |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | the local Postgres container in [db/docker-compose.yaml](src/financial_data_agent/db/docker-compose.yaml) |
| `DATABASE_URL` | [db/database.py](src/financial_data_agent/db/database.py) and [migrations/env.py](src/financial_data_agent/migrations/env.py); must match the three above |
| `LLM_READER_DATABASE_URL` | the read-only login that model-generated SQL runs as |
| `EMBEDDING_MODEL`, `EMBEDDING_CACHE_DIR` | the in-process embedding model (must produce 384 dimensions) and where it is cached |
| `LLM_MODEL`, `GOOGLE_API_KEY` | the Gemini chat model; not in `.env.example`, so add both yourself |

`.env` is gitignored and is for local development only. In `test` and `prod`, Terraform passes the values to the container app. See [docs/database.md](docs/database.md).

### Database

```bash
cd src/financial_data_agent/db
docker compose --env-file ../../../.env up -d
cd ..
alembic upgrade head
```

`--env-file` is required, and `alembic upgrade` sets the `llm_reader` password from `LLM_READER_DATABASE_URL`. See [db/README.md](src/financial_data_agent/db/README.md).

### Run the API

From the repository root:

```bash
uv run fastapi dev src/financial_data_agent/api/main.py
```

Interactive API docs are then available at <http://127.0.0.1:8000/docs>. To load data and ask a question, call the endpoints in this order:

1. `POST /api/v1/companies/sp500/import`
2. `POST /api/v1/filings/import`
3. `POST /api/v1/financial-metrics/import`
4. `POST /api/v1/document-chunks/import`
5. `POST /api/v1/chat`

## Development

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pyrefly check     # type check
```

Tests need no database or network. The `llm_reader` permission tests skip unless `LLM_READER_DATABASE_URL` is reachable.

To create a migration after changing a model, run this from `src/financial_data_agent/`:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Write migrations for `Vector` columns by hand, because autogenerate gets them wrong. See [docs/database.md](docs/database.md#6-pgvector).

## Project structure

```text
.
├── data/ - Generated datasets organized by ticker, year, and quarter
├── docs/ - Design documents
├── iac/ - Terraform for the Azure infrastructure (test and prod environments)
├── src/financial_data_agent/
│   ├── agent/ - LangGraph chat graph, schema prompt and the TableRAG subgraph
│   ├── api/ - API routes, agent tools, request models and response models
│   ├── db/ - Database models, repositories, DTOs and schemas
│   ├── ingestion/ - S&P 500 and SEC acquisition, storage, chunking, embeddings and the chat model
│   ├── migrations/ - Alembic migrations
│   └── services/ - Application business services
└── tests/ - Unit tests
```

The code is layered with one-way dependencies: API route or tool → agent → service → repository → model.

## Deployment

The API is deployed to Azure Container Apps, with Postgres on Supabase. CI runs lint, type checks, tests and an image build on every pull request. On merge to `main`, the pipeline deploys to `test` and then `prod`. Each stage applies the infrastructure, migrates the database and deploys the image, and each GitHub environment requires an approval.

Terraform owns the infrastructure, the pipeline owns the image tag, and `migrations/versions/` owns the schema. See [iac/README.md](iac/README.md) to provision an environment and [docs/infrastructure.md](docs/infrastructure.md) for the pipeline and the ownership split.

### Run the container locally

```bash
docker build -t fda-api:local .
docker run --rm -p 8000:8000 --env-file .env fda-api:local
```

The API is then on <http://127.0.0.1:8000/docs>. On Windows and macOS, use `host.docker.internal` instead of `localhost` in the database URLs to reach the Compose Postgres.

## Documentation

- [Architecture](docs/architecture.md): target design, the chat agent, tools, MCP and deployment
- [TableRAG](docs/RAG.md): components, control flow and contracts of the TableRAG subgraph
- [Infrastructure](docs/infrastructure.md): Azure resources, resource ownership and the deployment pipeline
- [Database](docs/database.md): local and deployed Postgres, migrations and the Supabase connection string
