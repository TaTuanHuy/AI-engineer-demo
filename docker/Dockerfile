FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:3.12-slim AS base

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy


# Development includes dev dependencies and starts Uvicorn with auto-reload.
FROM base AS development

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY app ./app

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000} --reload"]


# Production only includes runtime dependencies and uses multiple workers.
FROM base AS production

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000} --workers 4"]

