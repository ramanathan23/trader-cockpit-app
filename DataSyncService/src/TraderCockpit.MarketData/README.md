# TraderCockpit.MarketData

Handles symbol seeding, Dhan API integration, and OHLCV data ingestion into TimescaleDB.

## Project Layout

```
TraderCockpit.MarketData/
├── Database/
│   ├── DatabaseInitializer.cs   # Runs schema.sql on startup (idempotent)
│   └── schema.sql               # DDL: symbols, price_data_1m, sync_runs, aggregates
├── Dhan/
│   ├── DhanClient.cs            # HTTP wrapper — rate limiting + retry (429 / 5xx)
│   ├── DhanModels.cs            # Request/response DTOs
│   ├── DhanNoDataException.cs   # Thrown on DH-905 (no data for range)
│   └── DhanOptions.cs           # Config: credentials, concurrency, rate limit
├── Domain/
│   ├── MarketSymbol.cs          # NSE equity symbol
│   ├── OhlcvBar.cs              # 1-minute OHLCV bar
│   └── SyncRun.cs               # One row = one full-universe sync trigger
├── Repositories/
│   ├── ISymbolRepository / SymbolRepository
│   ├── IPriceDataRepository / PriceDataRepository
│   └── ISyncRunRepository / SyncRunRepository
└── Services/
    ├── DhanSecurityIdSeeder.cs  # Maps dhan_security_id from Dhan's scrip-master CSV
    ├── SymbolSeeder.cs          # Upserts NSE equities from embedded symbols.csv
    └── SyncManager.cs           # Orchestrates full-universe sync runs
```

## How a Sync Run Works

```
POST /sync
  → SyncManager.TriggerAsync()
      → guard: reject 409 if InProgress
      → create sync_runs row (status = InProgress)
      → fire background Task
      → return 202 with runId

Background Task (Parallel.ForEachAsync, MaxConcurrency workers):
  for each syncable symbol:
    1. Read latest bar time from price_data_1m
    2. If no data          → backfill from 5 years ago
    3. If age < 15 minutes → skip (already current)
    4. Otherwise           → fetch from (latest + 1 min) to now
    5. Insert bars (bulk COPY, ON CONFLICT DO NOTHING)
    6. Update sync_runs counters (updated / skipped / failed)

Completion → sync_runs.status = Completed | Failed
```

### 15-Minute Threshold

If the most recent stored bar is less than 15 minutes old the symbol is skipped —
already current, no Dhan API call needed.

### Batch Windows

Dhan caps each intraday request at ~90 days. `SyncManager` iterates in 90-day windows.
If the first window returns DH-905 (no data yet), a binary search locates the listing
date in O(log n) calls (~4–5 for a 5-year range).

### Error Handling

- Per-symbol errors are caught, logged, and counted as `symbols_failed` — the run continues.
- The whole run only fails on unrecoverable exceptions (e.g. DB unreachable).
- On restart, any InProgress run left by a crashed process is reconciled to Failed;
  the next `POST /sync` resumes each symbol incrementally from its last stored bar.
