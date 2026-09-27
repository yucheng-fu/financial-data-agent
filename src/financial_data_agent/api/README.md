# FastAPI backend

The ASGI application is `financial_data_agent.api.main:app`.

### Run locally

From the repository root, so the absolute `financial_data_agent.*` imports resolve:

```bash
uv run fastapi dev src/financial_data_agent/api/main.py
```

Interactive docs are then on <http://127.0.0.1:8000/docs>.

### Run in a container

Same command the deployed image uses, minus the reload and the loopback bind:

```bash
docker build -t fda-api:local .
docker run --rm -p 8000:8000 fda-api:local
```

`DATABASE_URL` is read lazily, so the app starts without a database. `/docs` and `/api/v1/cow` work; the import endpoints return 500 until one is configured.
