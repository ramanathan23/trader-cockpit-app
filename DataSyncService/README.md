# DataSyncService

Fetches OHLCV data for all NSE equities and persists it to TimescaleDB. Runs as a FastAPI service on port 8001 (host) / 8000 (container).

## Responsibilities

- Load NSE symbol list from `data/symbols.csv`
- Full backfill: 5 years of daily bars (yfinance) + 90 days of 1-minute bars (Dhan)
- Incremental patch: sync only stale symbols since their last known timestamp
- Expose REST endpoints to trigger sync and query prices / sync state

## Data sources

| Source | Interval | Lookback | Library |
|---|---|---|---|
| yfinance | `1d` | 5 years (1825 days) | `yfinance` |
| Dhan API | `1m` | 90 days, chunked in 30-day windows | `dhanhq` SDK |

**Why two sources?** yfinance caps 1-minute history at 7 days. Dhan provides up to 90 days of intraday data via their broker API.

## Service layout

```
DataSyncService/src/
├── main.py                         # FastAPI app + lifespan startup
├── config.py                       # Settings (pydantic-settings, reads .env)
├── api/routes.py                   # HTTP endpoints
├── data/symbols.csv                # NSE symbol list
├── db/
│   ├── connection.py               # asyncpg pool factory
│   └── migrations/001_schema.sql  # DB schema
├── domain/models.py                # Price, Symbol value objects
├── infrastructure/
│   └── fetchers/
│       ├── protocol.py             # DataFetcher Protocol (interface)
│       ├── yfinance/
│       │   └── fetcher.py          # YFinanceFetcher — daily bars
│       └── dhan/
│           ├── fetcher.py          # DhanFetcher — 1-min bars
│           └── security_master.py  # Dhan symbol → security_id mapping (TTL cache)
├── repositories/
│   ├── price_repository.py         # bulk_ingest, OHLCV queries
│   ├── symbol_repository.py        # symbol list management
│   └── sync_state_repository.py   # per-symbol sync timestamps + status
└── services/sync_service.py        # Orchestration: initial + patch sync
```

## Fetcher architecture

```
DataFetcher (Protocol)
    ├── fetch_batch(symbols, days) → dict[symbol, DataFrame]
    └── fetch_since(symbol, since) → DataFrame

    Implementations:
    YFinanceFetcher          DhanFetcher
    ─────────────────        ─────────────────────────────────
    yfinance.download()      dhanhq.intraday_minute_data()
    Batches all symbols      Per-symbol, concurrent (semaphore)
    Single HTTP call         30-day chunk loop per symbol
    NSE suffix: .NS          Dhan security_id lookup required
```

`DhanSecurityMaster` downloads the Dhan security master CSV on first use and caches it for 24 hours in the system temp directory.

## Sync flow

### Initial sync (`POST /api/v1/sync/initial`)

```
bootstrap_symbols()          → upsert symbols.csv into DB
_sync_daily_initial()        → yfinance batch 50 symbols at a time, 1825d
_sync_1m_initial()           → Dhan concurrent fetch, 200 symbols at a time, 90d
```

### Patch sync (`POST /api/v1/sync/patch`)

```
get_stale_daily()            → symbols where last_data_ts is stale (>1d old)
get_stale_1m()               → symbols where last_data_ts is stale (>1h old)
fetch_since(symbol, since)   → incremental from last known timestamp
bulk_ingest()                → upsert new bars; update sync_state
```

Both intervals run concurrently via `asyncio.gather`.

## REST API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/symbols/load` | Upsert symbols from CSV |
| `POST` | `/api/v1/symbols/refresh-master` | Re-download Dhan security master |
| `GET` | `/api/v1/symbols` | List all symbols |
| `POST` | `/api/v1/sync/initial` | Start full backfill (background) |
| `POST` | `/api/v1/sync/patch` | Start incremental sync (background) |
| `GET` | `/api/v1/sync/status` | Overall sync status per interval |
| `GET` | `/api/v1/sync/status/{symbol}` | Sync state for one symbol |
| `GET` | `/api/v1/prices/{symbol}/1m` | 1-minute OHLCV (params: limit, from_ts, to_ts) |
| `GET` | `/api/v1/prices/{symbol}/daily` | Daily OHLCV (param: limit) |
| `GET` | `/api/v1/prices/{symbol}/hourly` | Hourly aggregate from TimescaleDB view |

## Database schema

Tables written by this service:

| Table | Hypertable | Description |
|---|---|---|
| `symbols` | No | NSE symbol registry |
| `price_data_1m` | Yes (time) | 1-minute OHLCV bars |
| `price_data_daily` | Yes (time) | Daily OHLCV bars |
| `sync_state` | No | Last sync timestamp + status per symbol+interval |

Continuous aggregate view: `price_1m_hourly` (hourly OHLCV rolled up from 1m).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | required | asyncpg DSN |
| `DHAN_CLIENT_ID` | required | Dhan brokerage client ID |
| `DHAN_ACCESS_TOKEN` | required | Dhan API token |
| `SYNC_BATCH_SIZE` | `50` | Symbols per yfinance batch |
| `SYNC_BATCH_DELAY_S` | `1.0` | Delay between batches (rate limiting) |
| `DHAN_MAX_CONCURRENCY` | `5` | Max concurrent Dhan symbol fetches |
