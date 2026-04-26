# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared/pyproject.toml shared/pyproject.toml
COPY shared/shared/ shared/shared/

COPY LiveFeedService/pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system ./shared .

COPY LiveFeedService/src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
