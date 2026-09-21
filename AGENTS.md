# Agents.md

## Overview
This markdown file defines the overall project structure and code style used in the project.

### Code repository
When asked to update the code repository structure, only include the folders, do not include individual files. Next to the folder name, give a short summary of its contents.

```text
.
├── .agents/ - Agent-specific project resources.
├── data/ - Generated datasets organized by ticker, year, and quarter.
├── docs/ - Project documentation and reference material.
├── filings/ - Downloaded source financial filings.
├── src/ - Python source code for the application package.
│   └── financial_data_agent/ - Main application package.
│       ├── api/ - API endpoints, request models, and response models.
│       │   ├── requests/ - API request schemas.
│       │   ├── responses/ - API response schemas.
│       │   └── v1/ - Version 1 API routes.
│       ├── db/ - Database access, models, repositories, and schemas.
│       │   ├── DTO/ - Data-transfer objects.
│       │   ├── models/ - Database models.
│       │   ├── repositories/ - Data persistence operations.
│       │   └── schemas/ - Database-related schemas.
│       ├── ingestion/ - Data ingestion and acquisition workflows.
│       ├── migrations/ - Database migration definitions.
│       │   └── versions/ - Individual migration revisions.
│       └── services/ - Application business services.
└── tests/ - Unit tests.
```


### Code style 
Follow the standards defined in the `pyproject.toml` file.
- Avoid writing unnecessary comments inline.
- Avoid defining functions within functions.
- Avoid implementing "fallbacks" unless explicitly prompted.
- Every function should include type hints for inputs and outputs.
- Docstring format: Follow the autoDocstring extension format.

### Project
AI assistant for analysing S&P 500 earnings reports. `docs/architecture.md` describes the target design: a FastAPI backend, an agent orchestrator choosing between a SQL tool (structured metrics), a RAG tool (pgvector embeddings) and an SEC acquisition tool, all on one PostgreSQL+pgvector instance. Currently only the ingestion/import side (companies, filings, metrics model) is implemented; the agent/RAG layers are not. `src/financial_data_agent/main.py` is just an Ollama scratch script.

### Architecture
Layered, with strict one-way dependencies: **api/v1 route → services → repositories → models**, plus **ingestion** for external data sources.

- `api/v1/*` - Thin FastAPI routes. They take a `Session` via `Depends(get_session)`, call a service, and translate service exceptions (e.g. `CompanyNotFoundError`, `FilingNotFoundError`) into `HTTPException`. Request/response pydantic models live in `api/requests/` and `api/responses/`. New routers must be registered in `api/router.py`.
- `services/` - Business logic (`company_import`, `filing_import`, `financial_metrics_import`). Services build their own repositories from the session and take an optional injected fetcher (`SP500Fetcher`, `FilingsFetcher`) for testability. Each service defines its own domain exceptions.
- `ingestion/` - External I/O only: `sp500.py` scrapes the S&P 500 list from Wikipedia (Polars DataFrame, cached to `data/s&p500.parquet`); `filings.py` uses `edgartools` to download 10-Q/10-K filings as markdown under `data/ticker=<T>/...` and also has a CLI-style bulk backfill (threaded, by year/quarter).
- `db/` - SQLAlchemy 2.0 models (`Company`, `Document`, `FinancialMetric`, with `TimestampMixin`), repositories (session-based CRUD; they `commit()` per operation), pydantic `schemas/` for API payloads, and **DTOs** (`db/DTO/`) that sit between schemas/services and models. DTOs carry a `supplied_fields` frozenset so updates only touch fields that were explicitly provided (partial-update semantics); `to_model_kwargs()` produces the model constructor args. When building a DTO in a service, set `supplied_fields` to every field you want written.
- `migrations/` - Alembic; `env.py` imports `financial_data_agent.db.models` so autogenerate sees all models. Add new models to `db/models/__init__.py`.

### Tests
Unit tests are placed in `tests/` and the name convention is to use `test_` prefix.

They use `TestClient(app)` and `monkeypatch` to replace repositories/fetchers with fakes on the `services.*` modules, so no DB or network is needed. Follow that pattern (patch the name in the service module, not the origin module).

### Common commands
Uses `uv` (Python >=3.11).
- Install: `uv sync`
- Run all tests: `uv run pytest`; a single test: `uv run pytest tests/test_import_filings.py::test_import_filings_downloads_filing`
- Lint and format (ruff): `uv run ruff check .` and `uv run ruff format .`
- Type check (pyrefly): `uv run pyrefly check`
- Postgres (pgvector): `docker compose up -d` (reads `POSTGRES_USER/PASSWORD/DB` from `.env`)
- Migrations (run from `src/financial_data_agent/`, where the working `alembic.ini` and `migrations/` live): `alembic revision --autogenerate -m "name"` then `alembic upgrade head`
- API: `uv run fastapi dev src/financial_data_agent/api/main.py`

`.env` must define `DATABASE_URL` (used by both `db/database.py` and `migrations/env.py`).

### Agent guardrails
- Keep test updates close to behavior changes and use explicit test names describing what is validated.
- Avoid broad refactors unless requested; prioritize minimal, verifiable changes.
