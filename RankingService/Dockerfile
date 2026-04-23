FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared/pyproject.toml shared/pyproject.toml
COPY shared/shared/ shared/shared/

COPY RankingService/pyproject.toml .
RUN uv pip install --system --no-cache ./shared .

COPY RankingService/src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
