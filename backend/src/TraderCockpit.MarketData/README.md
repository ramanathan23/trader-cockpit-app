# TraderCockpit.MarketData

Class library that owns the entire market-data ingestion pipeline: fetching 1-minute OHLCV bars from the Dhan API, storing them in TimescaleDB, and serving them back via repository interfaces.

---

## Directory layout

```
TraderCockpit.MarketData/
├── Domain/                  # Pure domain objects — no I/O dependencies
│   ├── MarketSymbol.cs      # NSE equity symbol entity
│   ├── OhlcvBar.cs          # Immutable 1-minute candle record
│   └── SyncJob.cs           # Ingestion job aggregate + SyncRequest channel message
│
├── Dhan/                    # Dhan API client (infrastructure, not domain)
│   ├── DhanClient.cs        # HTTP client with rate-limiting and retry logic
│   ├── DhanModels.cs        # Internal request/response DTOs
│   ├── DhanOptions.cs       # Configuration bound from appsettings "DhanApi" section
│   └── DhanNoDataException.cs  # DH-905 typed exception
│
├── Repositories/            # Data access — depend on domain, not services
│   ├── ISymbolRepository    # CRUD for symbols table
│   ├── SymbolRepository     # Dapper + Npgsql implementation
│   ├── IPriceDataRepository # OHLCV read/write for price_data_1m hypertable
│   ├── PriceDataRepository  # Binary COPY bulk insert + continuous-aggregate query
│   ├── ISyncJobRepository   # Job lifecycle persistence
│   └── SyncJobRepository    # Dapper implementation
│
├── Services/                # Application services — orchestrate domain + repositories
│   ├── SyncManager.cs       # Calculates sync windows, creates jobs, enqueues requests
│   ├── IngestionBackgroundService.cs  # Workers: drains channel, calls Dhan, bulk-inserts
│   ├── SymbolSeeder.cs      # Startup: upserts NSE symbols from embedded CSV
│   └── DhanSecurityIdSeeder.cs  # Startup: maps dhan_security_id from Dhan scrip master
│
├── Database/
│   ├── schema.sql           # Idempotent DDL: tables, hypertables, continuous aggregates
│   └── DatabaseInitializer.cs  # Runs schema.sql on startup
│
└── DependencyInjection.cs   # AddMarketData() extension — wires everything together
```

---

## Domain model

### `MarketSymbol`
Represents an NSE-listed equity. `CanBeSynced` encodes the rule that a symbol needs both `IsActive = true` and a non-null `DhanSecurityId` before ingestion can proceed.

### `SyncJob`
Tracks the lifecycle of a single ingestion run (Pending → InProgress → Completed | Failed). State transitions are expressed as domain methods (`MarkInProgress`, `MarkCompleted`, `MarkFailed`) rather than raw property sets, so the valid lifecycle is enforced at compile time.

### `SyncRequest`
Immutable value object written to `Channel<SyncRequest>` by `SyncManager` and consumed by `IngestionBackgroundService` workers. Contains everything a worker needs — no extra DB queries required.

### `OhlcvBar`
Immutable record for a single 1-minute candle. Used both as the output of `DhanClient` and as the input to `IPriceDataRepository.BulkInsertAsync`.

---

## Ingestion pipeline

```
POST /api/market-data/sync
        │
        ▼
  SyncManager
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Guard: reject if any job is Pending/InProgress       │
  │ 2. Load syncable symbols (IsActive + DhanSecurityId ≠∅) │
  │ 3. Per symbol: calculate incremental or backfill window  │
  │ 4. INSERT sync_jobs row (Pending)                       │
  │ 5. Write SyncRequest → Channel                          │
  └─────────────────────────────────────────────────────────┘
        │  Channel<SyncRequest>
        ▼
  IngestionBackgroundService  (MaxConcurrency parallel workers)
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Mark job InProgress                                  │
  │ 2. Split window into 90-day batches                     │
  │ 3. Per batch → DhanClient.GetIntradayAsync              │
  │    • DH-905, no bars yet → jump 6 months (seek listing) │
  │    • DH-905, bars exist  → stop (end of history)        │
  │ 4. BulkInsertAsync (COPY binary → temp → hypertable)    │
  │ 5. Mark job Completed or Failed                         │
  └─────────────────────────────────────────────────────────┘
```

**Rate limiting:** A global `TokenBucketRateLimiter` (default: 3 req/s) is shared across all workers inside `DhanClient`. Each worker also waits `DelayBetweenCallsMs` between batches as a secondary courtesy delay.

**Retry on 429:** `DhanClient` retries up to `MaxRetries` times with exponential backoff (`RetryBackoffMs * 2^attempt`).

---

## Configuration (`appsettings.json` → `DhanApi` section)

| Key | Default | Description |
|-----|---------|-------------|
| `BaseUrl` | `https://api.dhan.co` | Dhan API base URL |
| `ClientId` | *(required)* | Dhan client ID header |
| `AccessToken` | *(required)* | Dhan access-token header |
| `MaxConcurrency` | `2` | Parallel ingestion workers |
| `DelayBetweenCallsMs` | `500` | Per-worker inter-batch delay (ms) |
| `RateLimitPerSecond` | `3` | Global token-bucket refill rate |
| `MaxRetries` | `5` | 429-retry attempts before failure |
| `RetryBackoffMs` | `10000` | Base backoff on 429 (doubles each retry) |

---

## Database schema overview

| Object | Type | Purpose |
|--------|------|---------|
| `symbols` | Table | NSE equity master; `dhan_security_id` nullable |
| `price_data_1m` | Hypertable | 1-minute OHLCV bars; chunk per day; compressed after 7 days |
| `price_data_5m` | Continuous Aggregate | Auto-aggregated from `price_data_1m` |
| `price_data_15m` | Continuous Aggregate | Auto-aggregated from `price_data_1m` |
| `price_data_daily` | Continuous Aggregate | Auto-aggregated from `price_data_1m` |
| `sync_jobs` | Table | Client-pollable job tracker |

See [Database/schema.sql](Database/schema.sql) for the full DDL.
