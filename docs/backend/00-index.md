# Backend Technical Design — Index

**Project:** Trader Cockpit App
**Backend:** Python / FastAPI (DDD)
**Primary Broker:** Dhan (DhanHQ v2 API)
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [Tech Stack Summary](#tech-stack-summary)
2. [DDD Layer Overview](#ddd-layer-overview)
3. [Package List with Fitness Ratings](#package-list-with-fitness-ratings)
4. [Folder Structure Overview](#folder-structure-overview)
5. [Key Architectural Decisions](#key-architectural-decisions)
6. [Document Map](#document-map)

---

## Tech Stack Summary

| Layer | Technology | Version | Role |
|---|---|---|---|
| API Framework | FastAPI | 0.115+ | HTTP + WebSocket server, thin routers |
| Language | Python | 3.12 | All backend logic |
| Data Validation | Pydantic v2 | 2.7+ | Domain models, settings, request/response schemas |
| ORM | SQLAlchemy | 2.0 (async) | Repository pattern, async DB access |
| DB Driver | asyncpg | 0.29+ | Native async PostgreSQL driver |
| Primary DB | PostgreSQL | 16+ | Order book, watchlist, strategies, positions |
| Time Series DB | TimescaleDB | 2.x | OHLCV candles as hypertables |
| Cache / Pub-Sub | Redis | 7.x (with hiredis) | Live quotes, candle builder, session state |
| Broker SDK | dhanhq | 2.0.2 stable | Dhan order/data API wrapper |
| Async HTTP | httpx | 0.27+ | REST calls to Dhan API |
| WebSocket | websockets | 12+ | Binary market feed, order feed |
| Background Jobs | APScheduler | 3.10+ | EOD scan, token renewal, candle aggregation |
| Logging | structlog | 24+ | Structured JSON logs |
| ASGI Server | uvicorn | 0.29+ | Production ASGI server |
| Auth (frontend) | PyJWT | 2.8+ | JWT tokens for UI sessions |
| Retry Logic | tenacity | 8.x | Retry Dhan API calls on transient failures |
| Numerics | numpy | 1.26+ | ATR, EMA, signal scoring calculations |
| Migrations | alembic | 1.13+ | DB schema versioning |
| Testing | pytest + pytest-asyncio + respx | latest | Async test suite, HTTP mocking |

---

## DDD Layer Overview

The backend is structured into four strict layers. Dependencies flow **inward only** — outer layers may depend on inner layers, never the reverse.

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (FastAPI routers, WebSocket endpoints)           │
│  — Thin HTTP/WS adapters, no business logic                 │
├─────────────────────────────────────────────────────────────┤
│  Application Layer (Use Cases — CQRS)                       │
│  — Commands (mutations), Queries (projections)              │
│  — Orchestrates domain objects and infrastructure           │
├─────────────────────────────────────────────────────────────┤
│  Domain Layer (Pure Python)                                 │
│  — Entities, Aggregates, Value Objects, Domain Services     │
│  — Business rules, invariants — zero framework imports      │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                       │
│  — Dhan adapter, repositories, Redis, TimescaleDB           │
│  — Implements interfaces defined by domain/application      │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities at a Glance

| Layer | Contains | Imports Allowed |
|---|---|---|
| **Domain** | Entities, Aggregates, Value Objects, Domain Services, Domain Events | stdlib only, no frameworks |
| **Application** | Commands, Queries, Handlers, DTOs, Port interfaces | Domain layer only |
| **Infrastructure** | Dhan adapter, Repos, Redis, DB, Jobs | Domain + Application (implements ports) |
| **API** | FastAPI routers, WebSocket handlers, Pydantic schemas | Application layer (via DI) |

---

## Package List with Fitness Ratings

| Package | Version | Fitness | Purpose |
|---|---|---|---|
| fastapi | 0.115+ | ★★★★★ | Core API framework |
| pydantic | 2.7+ | ★★★★★ | Validation, settings, schemas |
| sqlalchemy | 2.0+ async | ★★★★★ | Repository ORM layer |
| asyncpg | 0.29+ | ★★★★★ | Async PostgreSQL driver |
| alembic | 1.13+ | ★★★★★ | DB migrations |
| redis[hiredis] | 5.x | ★★★★★ | Cache and pub/sub |
| dhanhq | 2.0.2 | ★★★★☆ | Dhan broker SDK (v2.2.0rc1 available but pre-release) |
| httpx | 0.27+ | ★★★★★ | Async REST client |
| websockets | 12+ | ★★★★★ | Binary WebSocket for market feed |
| APScheduler | 3.10+ | ★★★★☆ | Background job scheduling |
| structlog | 24+ | ★★★★★ | Structured logging |
| uvicorn | 0.29+ | ★★★★★ | ASGI server |
| PyJWT | 2.8+ | ★★★★★ | Frontend JWT auth |
| tenacity | 8.x | ★★★★★ | Retry logic |
| numpy | 1.26+ | ★★★★★ | ATR / EMA / signal math |
| pytest + pytest-asyncio | latest | ★★★★★ | Async test suite |
| respx | 0.21+ | ★★★★★ | Mock httpx in tests |

Full evaluation with rationale in [06-packages.md](./06-packages.md).

---

## Folder Structure Overview

```
backend/
├── domains/            # Pure domain model — 8 sub-domains
├── application/        # CQRS handlers — commands + queries per domain
├── infrastructure/     # Dhan adapter, repos, Redis cache, jobs, event bus
├── api/
│   └── v1/             # FastAPI thin routers + WebSocket endpoints
└── config/             # Settings (Pydantic), DB engine setup
```

Full annotated structure in [01-architecture.md](./01-architecture.md).

---

## Key Architectural Decisions

### ADR-001: Domain-Driven Design with Strict Layering
**Decision:** Full DDD layering — Domain, Application, Infrastructure, API.
**Rationale:** The trading domain is complex with multiple sub-domains (equity intraday, CNC delivery, options, risk, signals). DDD enforces clear ownership of business rules in the domain layer, preventing logic from leaking into infrastructure or API code.
**Consequence:** Higher initial setup cost, but business logic is testable without database or broker SDK.

### ADR-002: CQRS (Command Query Responsibility Segregation)
**Decision:** Separate command handlers (mutations) from query handlers (reads/projections).
**Rationale:** Trading workflows are predominantly write-heavy commands (place order, convert position, trigger CSL) while the UI is read-heavy (live positions, watchlist, Greeks). Separating these allows independent optimization and prevents read-model complexity from polluting business logic.
**Consequence:** More boilerplate per feature, but read models can be Redis-cached independently.

### ADR-003: Async-First Throughout
**Decision:** All I/O (database, Redis, Dhan API, WebSocket) uses async/await.
**Rationale:** The trading cockpit has multiple concurrent concerns — live market feed, position polling, order updates, and user API requests — all running simultaneously. Synchronous blocking I/O would require threads; async handles all these on a single event loop efficiently.
**Consequence:** Care required with CPU-bound signal calculations — offload heavy numpy work with `asyncio.run_in_executor` to avoid blocking the event loop.

### ADR-004: Two Broker Ports — Data and Orders are Separate
**Decision:** Two independent interfaces: `IMarketDataPort` (data source) and `IOrderBrokerPort` (order execution). Both have Dhan implementations today; either can be replaced independently.
**Rationale:** Data source and order execution are distinct concerns. Market data may come from a different provider than where orders are placed. Paper mode requires replacing only `IOrderBrokerPort` (with `PaperOrderBrokerAdapter`) while keeping real market data flowing through `IMarketDataPort`.
**Consequence:** Application handlers check `broker.capabilities` flags rather than broker name. `PaperOrderBrokerAdapter` simulates all features (has_basket_orders=True, has_realtime_positions=True) regardless of Dhan constraints.

### ADR-005: No Basket Orders — Sequential Leg Placement
**Decision:** Option strategy legs are placed one by one via Dhan API.
**Rationale:** Dhan v2 does not support basket order API. Legs must be placed sequentially.
**Consequence:** Partial fill risk on multi-leg strategies. The infrastructure layer includes a sequential leg placement engine with abort-and-flatten logic if an intermediate leg fails.

### ADR-006: Position Polling Instead of WebSocket for Positions
**Decision:** Poll `GET /positions` every 3-5 seconds during market hours.
**Rationale:** Dhan does not provide a real-time position WebSocket. Polling is the only option.
**Consequence:** Up to 5-second position staleness. The UI cockpit feed WebSocket broadcasts position updates whenever the poll detects a change. The CSL monitor also consumes the polled position state.

### ADR-007: TimescaleDB for OHLCV Candles
**Decision:** OHLCV candles stored in TimescaleDB hypertables (not plain PostgreSQL).
**Rationale:** Candle queries for signal scoring (e.g., last 50 candles across 200 symbols) are time-series range queries. TimescaleDB's hypertable compression and time-bucketing queries run 10-50x faster than plain PostgreSQL for these access patterns.
**Consequence:** Requires TimescaleDB extension. Docker compose includes the timescale/timescaledb image.

### ADR-008: Static IP Mandatory
**Decision:** Backend must deploy on a server with a static IP (VPS or cloud VM).
**Rationale:** Dhan's order placement APIs mandate a registered static IP. Local development uses a VPN or dedicated static IP service.
**Consequence:** No serverless deployment. Always-on VPS deployment required.

### ADR-009: Token Validity and Renewal
**Decision:** Dhan access token has 24-hour validity. A nightly job (9 PM) calls the renewal endpoint and stores the new token in Redis (keyed `dhan:access_token`).
**Rationale:** Automated renewal prevents market-open failures. Redis provides fast token lookup without DB round-trip.
**Consequence:** Token renewal job failure must alert immediately (PagerDuty or Telegram notification).

### ADR-010: SL Philosophy Encoded in Domain
**Decision:** PositionSizer domain service encodes the tight-SL/many-shares rule for INTRADAY and wide-SL/few-shares rule for CNC as explicit domain logic — not configuration.
**Rationale:** This is core business logic. Encoding it in config YAML would allow silent bugs. The domain service validates that stop distance and calculated quantity are consistent with the product type's leverage profile.
**Consequence:** PositionSizer is a pure domain service with no framework dependencies, fully unit-testable.

---

## Document Map

| File | Contents |
|---|---|
| [00-index.md](./00-index.md) | This file — tech stack, overview, ADRs |
| [01-architecture.md](./01-architecture.md) | DDD layer design, full folder structure, DI patterns |
| [02-domains.md](./02-domains.md) | All domain models — entities, aggregates, value objects, services |
| [03-application-layer.md](./03-application-layer.md) | CQRS commands, queries, handlers, use case examples |
| [04-infrastructure.md](./04-infrastructure.md) | Dhan adapter, repositories, Redis, background jobs, event bus |
| [05-api-design.md](./05-api-design.md) | REST endpoints, WebSocket design, auth, error format |
| [06-packages.md](./06-packages.md) | Full package evaluation with fitness ratings and risks |
| [07-broker-abstraction.md](./07-broker-abstraction.md) | `IMarketDataPort` + `IOrderBrokerPort`, `BrokerCapabilities`, Dhan and Paper adapters |
| [08-paper-mode.md](./08-paper-mode.md) | Paper trading — PostgreSQL schema, `PaperFillMonitor`, fill simulation, analytics |

---

## Broker Capability Matrix

| Capability | Dhan v2 | Paper | Notes |
|-----------|---------|-------|-------|
| Super Order (entry+SL+target) | Yes | Simulated | Dhan native |
| Basket / multi-leg atomic | **No** | Simulated | Sequential placement in domain layer |
| OCO / Forever Order | Yes | Simulated | |
| Product conversion (INTRADAY→CNC) | Yes | Simulated | `POST /positions/convert` |
| Real-time position WebSocket | **No** | Yes (immediate) | Poll every 3s for Dhan |
| Historical Greeks | **No** | No | Options backtesting limited |
| Static IP required | **Yes** | No | |
| Token expiry | 24 hours | Never | Nightly renewal job |
| Orders/day cap | 5,000 | Unlimited | CSL flatten counts toward cap |
| Option chain rate limit | 1 req/3s | None | Cache Greeks; 30s refresh |
