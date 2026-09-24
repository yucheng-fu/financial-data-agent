# financial-data-agent

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

Create a `.env` file in the project root:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_DB=financial_data_agent
DATABASE_URL=postgresql+psycopg://postgres:change-me@localhost:5432/financial_data_agent
```

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

CI runs lint, type checks and tests on every pull request. On merge to `main`, the pipeline deploys the Terraform in [iac/environments](iac/environments) to `test` and then `production`, with an approval on each GitHub environment. The target platform is Azure Container Apps.

## Documentation

- [Architecture](docs/architecture.md)
