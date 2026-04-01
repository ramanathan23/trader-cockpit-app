FROM python:3.12-slim

WORKDIR /app

# Copy the uv binary from the official image — faster than pip-installing uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies before copying source so Docker can cache this layer.
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
