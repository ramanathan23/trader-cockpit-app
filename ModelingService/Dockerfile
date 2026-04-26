# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

WORKDIR /app

# Install OpenMP lib for LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared/pyproject.toml shared/pyproject.toml
COPY shared/shared/ shared/shared/

COPY ModelingService/pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system ./shared .

COPY ModelingService/src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
