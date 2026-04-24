# DataSyncService — Port 8001

Fetches OHLCV from yfinance/Dhan and persists to TimescaleDB. Owns `price_data_daily`, `price_data_1min`, `sync_state`, `symbols`.

## Key files
```
src/main.py                       # FastAPI app + lifespan + pool
src/api/_sync_routes.py           # Sync trigger endpoints
src/api/_symbol_routes.py         # Symbol registry endpoints
src/api/_data_routes.py           # OHLCV query + quality check endpoints
src/api/_config_routes.py         # Runtime config GET/PATCH
src/services/sync_service.py      # Core sync orchestration
src/infrastructure/fetchers/      # yfinance + Dhan fetcher impls
src/repositories/                 # asyncpg DB writes (price_data_daily, 1min, sync_state)
```

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET    | /health | Liveness |
| POST   | /sync/run | Trigger daily OHLCV sync (background) |
| POST   | /sync/run-sse | Daily sync with SSE progress stream |
| POST   | /sync/run-1min | Trigger 1-min OHLCV sync |
| POST   | /sync/run-1min-sse | 1-min sync with SSE progress stream |
| POST   | /sync/run-all | Sync all intervals |
| GET    | /sync/status | Per-symbol sync status summary |
| GET    | /sync/status/{symbol} | Sync status for one symbol |
| GET    | /sync/gaps | Symbols with data gaps |
| POST   | /sync/reset-1min | Reset 1-min sync state |
| GET    | /symbols | List all symbols |
| POST   | /symbols/load | Load/refresh symbols from CSV |
| POST   | /symbols/refresh-master | Refresh master symbol list |
| GET    | /symbols/dhan-status | Dhan security ID mapping coverage |
| GET    | /prices/{symbol}/daily | Query daily OHLCV for a symbol |
| GET    | /data-quality/1min | 1-min staleness check |
| GET    | /config | Current tunable config |
| PATCH  | /config | Update config (persists to DB, applies immediately) |

## DB tables owned
- `symbols` — NSE symbol registry
- `price_data_daily` — Hypertable, daily OHLCV
- `price_data_1min` — Hypertable, 1-min OHLCV
- `sync_state` — per-symbol last sync timestamp + status

## Pattern notes
- Uses `shared/db.py` asyncpg pool. Never use SQLAlchemy.
- Batch upserts in repositories — never row-by-row inserts.
- SSE endpoints yield `data: {...}\n\n` lines; use `EventSourceResponse` from sse-starlette.
- Config stored in `service_config` DB table, loaded at startup, hot-patched via PATCH /config.
