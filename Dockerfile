FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

# Must match the EMBEDDING_MODEL the environment sets, or it downloads again at runtime.
ARG EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RUN uv run --no-dev python -c \
    "from fastembed import TextEmbedding; TextEmbedding(model_name='$EMBEDDING_MODEL', cache_dir='/app/.model-cache')"

FROM python:3.11-slim-bookworm

# WORKDIR would leave /app root-owned; ingestion writes relative to the CWD.
RUN useradd --create-home --uid 10001 app \
    && install -d -o app -g app /app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    EMBEDDING_CACHE_DIR=/app/.model-cache

USER app

CMD ["uvicorn", "financial_data_agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
