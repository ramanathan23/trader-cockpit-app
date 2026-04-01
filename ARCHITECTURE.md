# Architecture — Trader Cockpit

High-level overview of the solution structure, technology choices, and data flow.

---

## Solution layout

```
DataSyncService/
├── TraderCockpit.sln
└── src/
    ├── TraderCockpit.Api/            # ASP.NET Core minimal-API host
    ├── TraderCockpit.Infrastructure/ # Placeholder for future cross-cutting services
    └── TraderCockpit.MarketData/     # All market-data ingestion and query logic
```

The solution deliberately keeps **one deployable** (the API project) thin.
All domain logic lives in `TraderCockpit.MarketData`, which has no dependency
on ASP.NET Core and can be tested in isolation.

---

## Layer responsibilities

```
┌──────────────────────────────────────────┐
│  TraderCockpit.Api (HTTP boundary)       │
│  • Minimal-API endpoint definitions      │
│  • Request/response DTOs                 │
│  • Startup sequencing                    │
└───────────────┬──────────────────────────┘
                │ depends on
┌───────────────▼──────────────────────────┐
│  TraderCockpit.MarketData                │
│  ┌────────────────────────────────────┐  │
│  │ Domain                             │  │
│  │  MarketSymbol · OhlcvBar · SyncJob │  │
│  └────────────┬───────────────────────┘  │
│               │                          │
│  ┌────────────▼───────────────────────┐  │
│  │ Services (application layer)       │  │
│  │  SyncManager                       │  │
│  │  IngestionBackgroundService        │  │
│  │  SymbolSeeder · DhanSecurityIdSeeder│ │
│  └────────────┬───────────────────────┘  │
│               │                          │
│  ┌────────────▼───────────────────────┐  │
│  │ Repositories (data access)         │  │
│  │  ISymbolRepository                 │  │
│  │  IPriceDataRepository              │  │
│  │  ISyncJobRepository                │  │
│  └────────────┬───────────────────────┘  │
│               │                          │
│  ┌────────────▼───────────────────────┐  │
│  │ Dhan (external API adapter)        │  │
│  │  DhanClient · DhanOptions          │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

Dependencies point strictly **inward**: Dhan adapters and repositories know about
the domain, but the domain knows about nothing else.

---

## Technology choices

| Concern | Choice | Reason |
|---------|--------|--------|
| Database | TimescaleDB (PostgreSQL) | Native time-series hypertables + continuous aggregates eliminate manual aggregation code |
| ORM | Dapper | Micro-ORM; zero magic, predictable SQL, minimal overhead for hot paths |
| Bulk insert | `NpgsqlBinaryImporter` (COPY) | Fastest possible write path — bypasses row-by-row parsing |
| Rate limiting | `System.Threading.RateLimiting.TokenBucketRateLimiter` | Built-in; shared across all workers via DI singleton |
| Work queue | `System.Threading.Channels.Channel<T>` | Back-pressure-free producer/consumer without an external broker |
| HTTP client | `IHttpClientFactory` | Connection pooling; separates lifetime from usage |
| Config | `IOptions<T>` | Strongly-typed; supports env-var overrides for Docker |

---

## Sync data flow

```
Client                 API             SyncManager          Channel
  │                     │                   │                  │
  │  POST /sync         │                   │                  │
  │────────────────────►│                   │                  │
  │                     │ EnqueueFullSync() │                  │
  │                     │──────────────────►│                  │
  │                     │                   │ HasActiveJobs?   │
  │                     │                   │──────────────────►  DB
  │                     │                   │◄─────────────────  false
  │                     │                   │                  │
  │                     │                   │ GetSyncable()    │
  │                     │                   │──────────────────►  DB
  │                     │                   │  [symbols]       │
  │                     │                   │ per symbol:      │
  │                     │                   │  GetLatestTime() │
  │                     │                   │  CreateJob()     │
  │                     │                   │  Write(request)──────►│
  │                     │  {enqueued: N}    │                  │
  │◄────────────────────│                   │                  │
  │  202 Accepted       │                   │                  │
  │                     │                   │                  │
  │                     │          IngestionBackgroundService  │
  │                     │                   │    Read()◄────────────│
  │                     │                   │    MarkInProgress     │
  │                     │                   │    [90-day batches]   │
  │                     │                   │    DhanClient.Get()   │
  │                     │                   │    BulkInsert()       │
  │                     │                   │    MarkCompleted      │
  │                     │                   │                  │
  │  GET /sync/{id}     │                   │                  │
  │────────────────────►│                   │                  │
  │  {status: Completed}│                   │                  │
  │◄────────────────────│                   │                  │
```

---

## Startup sequence

```
1. DatabaseInitializer.InitializeAsync()   — runs schema.sql (idempotent DDL)
2. SymbolSeeder.SeedAsync()                — upserts 2,278 NSE symbols from embedded CSV
3. DhanSecurityIdSeeder.SeedAsync()        — downloads Dhan scrip master, maps dhan_security_id
4. WebApplication.Run()                    — REST API + IngestionBackgroundService both start
```

Steps 1–3 run sequentially in a scoped DI scope before the app opens its port,
ensuring the DB is always ready before the first request is served.

---

## REST API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/market-data/symbols` | List all active symbols |
| `PUT` | `/api/market-data/symbols/{symbol}/security-id` | Map a Dhan security ID manually |
| `POST` | `/api/market-data/sync` | Trigger full or single-symbol sync |
| `GET` | `/api/market-data/sync` | List last 500 sync jobs |
| `GET` | `/api/market-data/sync/{id}` | Poll a specific sync job |
| `DELETE` | `/api/market-data/reset` | Wipe all price data and sync jobs |
| `GET` | `/api/market-data/{symbol}/ohlcv` | Query OHLCV bars (`timeframe`: 1m \| 5m \| 15m \| daily) |

Interactive docs available at `/swagger` when running in any environment.

---

## Running locally

```bash
# Start TimescaleDB
docker-compose up -d db

# Set secrets (or use appsettings.Development.json)
export DhanApi__ClientId=your_client_id
export DhanApi__AccessToken=your_token
export ConnectionStrings__TimescaleDb="Host=localhost;Port=5432;Database=tradercockpit;Username=postgres;Password=yourpassword"

# Run the API
dotnet run --project DataSyncService/src/TraderCockpit.Api
```

Or run the full stack:
```bash
docker-compose up --build
```
