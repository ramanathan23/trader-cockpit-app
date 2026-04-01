# trader-cockpit

NSE trading analytics platform. Ingests OHLCV data for all NSE equities, computes momentum scores, and exposes REST APIs for downstream dashboards and alerting.

## Services

| Service | Port | Responsibility |
|---|---|---|
| `DataSyncService` | 8001 | Fetch and persist OHLCV data (yfinance daily + Dhan 1-min) |
| `MomentumScorerService` | 8002 | Compute and serve momentum scores |
| `notebooks` | 8888 | Jupyter environment for backtesting and research |
| `timescaledb` | 5432 | TimescaleDB (PostgreSQL + time-series extensions) |
| `redis` | 6379 | Cache layer (reserved for rate limiting / session state) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Data Sources                          │
│   yfinance (daily, 5yr backfill)   Dhan API (1-min, 90d)    │
└────────────────────────┬────────────────────────────────────┘
                         │
                ┌────────▼────────┐
                │ DataSyncService │  :8001
                │  - Fetchers     │  yfinance/ + dhan/
                │  - SyncService  │  initial + patch sync
                │  - Repositories │  price, symbol, sync_state
                └────────┬────────┘
                         │ TimescaleDB (price_data_1m, price_data_daily)
                ┌────────▼──────────────┐
                │ MomentumScorerService │  :8002
                │  - ScoreService       │  batch compute
                │  - Signals            │  RSI, MACD, ROC, Volume
                │  - ScoreRepository    │  upsert + query
                └───────────────────────┘
                         │
                ┌────────▼────────┐
                │   notebooks     │  :8888  (research / backtest)
                └─────────────────┘
```

## Quick start

```bash
# copy and fill in credentials
cp .env.example .env

# start all services
docker compose up -d

# seed symbols and run initial 5yr daily + 90d 1-min backfill
curl -X POST http://localhost:8001/api/v1/sync/initial

# compute momentum scores (after sync completes)
curl -X POST http://localhost:8002/api/v1/scores/compute

# top 50 by momentum score
curl http://localhost:8002/api/v1/scores
```

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL DSN |
| `REDIS_URL` | Redis DSN |
| `DHAN_CLIENT_ID` | Dhan brokerage client ID |
| `DHAN_ACCESS_TOKEN` | Dhan API access token |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` |

See `.env.example` for full list.

## Repo layout

```
trader-cockpit-app/
├── DataSyncService/        # OHLCV ingestion service
├── MomentumScorerService/  # Scoring and ranking service
├── notebooks/              # Jupyter backtesting
├── infra/db/init.sql       # Shared DB initialisation
├── docker-compose.yml
└── Makefile
```
