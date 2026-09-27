FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies resolve from the lock file alone, so this layer is only invalidated by uv.lock.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

FROM python:3.11-slim-bookworm

# /app is created owned by app rather than by WORKDIR, which would leave it
# root-owned: the ingestion layer writes its data directory relative to the CWD.
RUN useradd --create-home --uid 10001 app \
    && install -d -o app -g app /app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

CMD ["uvicorn", "financial_data_agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
