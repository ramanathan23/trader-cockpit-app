# Python Package Evaluation

**Project:** Trader Cockpit App
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [Core Framework](#core-framework)
2. [Data Validation and Settings](#data-validation-and-settings)
3. [Database Layer](#database-layer)
4. [Broker Integration](#broker-integration)
5. [Async HTTP and WebSocket](#async-http-and-websocket)
6. [Background Jobs](#background-jobs)
7. [Logging and Observability](#logging-and-observability)
8. [Authentication](#authentication)
9. [Resilience](#resilience)
10. [Numerics and Signal Calculations](#numerics-and-signal-calculations)
11. [Testing](#testing)
12. [ASGI Server](#asgi-server)
13. [Packages to Avoid](#packages-to-avoid)

---

## Core Framework

### FastAPI

| Attribute | Value |
|---|---|
| Package | `fastapi` |
| Version | 0.115+ |
| Fitness | ★★★★★ |
| Why Chosen | Modern async-first Python web framework. Native Pydantic v2 support. WebSocket support built-in. Automatic OpenAPI docs. Dependency injection via `Depends()`. Fastest Python web framework for async workloads. |
| Alternatives Considered | Django REST Framework (see Packages to Avoid), Flask (see Avoid), Litestar (0.x maturity), Starlette (too low-level). |
| Risks | None for this use case. API stability is excellent post-0.100. |

**Notes for this project:**
- FastAPI's `Depends()` is used heavily for all handler injection (DDD application layer wiring).
- Background tasks via `asyncio.create_task` and `lifespan` (not FastAPI `BackgroundTasks` which is per-request and too limited).
- WebSocket support covers both market feed and cockpit feed.

---

## Data Validation and Settings

### Pydantic v2

| Attribute | Value |
|---|---|
| Package | `pydantic` + `pydantic-settings` |
| Version | 2.7+ |
| Fitness | ★★★★★ |
| Why Chosen | v2 is a complete rewrite in Rust — 5-17x faster than v1. `BaseSettings` handles all environment variable loading with type coercion. `model_validator` and `field_validator` provide rich validation logic. Deeply integrated with FastAPI. |
| Alternatives Considered | `attrs` (no settings support), `marshmallow` (verbose, slower), `dataclasses` (no validation). |
| Risks | v2 breaking changes from v1. Ensure no v1 library pulls in an old Pydantic. Use `pydantic>=2.7,<3.0` pin. |

**Usage in this project:**
- **API layer:** Request and response Pydantic models for all endpoints.
- **Settings:** `BaseSettings` loads `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` from environment.
- **NOT used in domain layer:** Domain value objects are plain `@dataclass(frozen=True)`. Pydantic is only in the API layer and settings.

```python
# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Dhan
    dhan_client_id: str
    dhan_access_token: str       # Seed token; renewed nightly by TokenRenewalJob

    # Database
    database_url: str            # postgresql+asyncpg://user:pass@host/db
    redis_url: str               # redis://localhost:6379

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 12

    # App
    debug: bool = False
    environment: str = "production"
    static_ip: str               # Registered IP for Dhan API

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Database Layer

### SQLAlchemy 2.0 (Async)

| Attribute | Value |
|---|---|
| Package | `sqlalchemy[asyncio]` |
| Version | 2.0+ |
| Fitness | ★★★★★ |
| Why Chosen | Industry-standard Python ORM. v2.0 async API is first-class (not bolt-on). `AsyncSession` with `asyncpg` provides full async PostgreSQL access. Repository pattern maps cleanly onto SQLAlchemy. Well-tested, stable, excellent docs. |
| Alternatives Considered | `tortoise-orm` (immature, smaller community), `databases` (query-only, no ORM), `encode/orm` (abandoned). |
| Risks | SQLAlchemy 2.0 async has different session management from 1.x. All sessions must use `async with`. Never use `Session.execute()` without `await`. |

**Usage:**
- `AsyncSession` per HTTP request, scoped via `Depends(get_db_session)`.
- `AsyncSession` per background job task, scoped manually.
- Raw SQL (`text()`) preferred over ORM models for complex queries (TimescaleDB time-series queries don't map well to ORM).

```python
# config/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,     # Detect stale connections
    echo=settings.debug,
)

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Critical for async — prevents lazy load after commit
)

async def get_db_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session

async def init_db() -> None:
    async with engine.begin() as conn:
        # TimescaleDB hypertable setup is handled by Alembic migrations
        pass
```

### asyncpg

| Attribute | Value |
|---|---|
| Package | `asyncpg` |
| Version | 0.29+ |
| Fitness | ★★★★★ |
| Why Chosen | The fastest async PostgreSQL driver for Python. Used by SQLAlchemy as the async backend. Pure Python protocol implementation with native type codecs. Handles Decimal, UUID, datetime with PostgreSQL native types. |
| Alternatives Considered | `psycopg3` (async) — excellent alternative, slightly newer, good TimescaleDB support. Either works; asyncpg is more battle-tested in async FastAPI stacks. |
| Risks | None significant. Well-maintained, widely deployed. |

### Alembic

| Attribute | Value |
|---|---|
| Package | `alembic` |
| Version | 1.13+ |
| Fitness | ★★★★★ |
| Why Chosen | The standard SQLAlchemy migration tool. Supports async migrations. Version-controlled DB schema changes for the full lifecycle (candles hypertable, orders, positions, watchlists). |
| Alternatives Considered | Manual SQL scripts (no version tracking), `yoyo-migrations` (less popular). |
| Risks | Initial setup with async engine requires `alembic.ini` + `env.py` customization. Well-documented. |

**TimescaleDB hypertable creation in Alembic:**
```python
# alembic/versions/001_create_candles_hypertable.py
def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT NOT NULL,
            exchange TEXT NOT NULL,
            interval TEXT NOT NULL,
            open_time TIMESTAMPTZ NOT NULL,
            open NUMERIC(12,4),
            high NUMERIC(12,4),
            low NUMERIC(12,4),
            close NUMERIC(12,4),
            volume BIGINT,
            oi BIGINT,
            PRIMARY KEY (symbol, exchange, interval, open_time)
        )
    """)
    op.execute("SELECT create_hypertable('candles', 'open_time')")
    op.execute("""
        SELECT add_retention_policy('candles', INTERVAL '5 years')
    """)
```

### redis[hiredis]

| Attribute | Value |
|---|---|
| Package | `redis[hiredis]` |
| Version | 5.x |
| Fitness | ★★★★★ |
| Why Chosen | `redis-py` 5.x has first-class async support (`redis.asyncio`). `hiredis` is a C extension parser for Redis protocol — 3-10x faster response parsing than pure Python. Used for: live quote cache (TTL 5s), live candle builder state, option chain cache, Dhan token storage, daily risk state. |
| Alternatives Considered | `aioredis` (merged into redis-py 4.2+, no longer separate), `valkey` (Redis fork, fully compatible). |
| Risks | `hiredis` requires a C compiler at build time. Alpine Linux Docker images need `musl-dev`. Use `pip install redis[hiredis]` — the extra handles this. |

---

## Broker Integration

### dhanhq

| Attribute | Value |
|---|---|
| Package | `dhanhq` |
| Version | 2.0.2 stable (2.2.0rc1 pre-release available) |
| Fitness | ★★★★☆ |
| Why Chosen | Official Dhan SDK. The only Python library supporting DhanHQ v2 API. Covers orders, positions, market data, historical candles, option chain, Kill Switch, Super Order, Forever Order. |
| Alternatives Considered | Direct httpx calls to Dhan REST API (possible but duplicates SDK work, more maintenance). |
| Risks | **SDK is synchronous** — all calls block. Must run in `asyncio.run_in_executor` to avoid blocking the async event loop. The `DhanClient` wrapper handles this transparently. v2.2.0rc1 is pre-release — do not use in production until stable. Pin to `dhanhq==2.0.2` in production. |

**Known SDK limitations:**
- No async support (see above).
- Binary WebSocket (market feed) not handled by the SDK — must implement custom binary parser (documented in `04-infrastructure.md`).
- Option chain rate limit (1 req/3s) must be managed manually — the SDK does not enforce this.
- No basket orders — each leg must be placed individually.

**Version strategy:**
```
# requirements.txt
dhanhq==2.0.2          # Pin to stable
# dhanhq==2.2.0rc1    # Watch for stable release; evaluate before upgrading
```

---

## Async HTTP and WebSocket

### httpx

| Attribute | Value |
|---|---|
| Package | `httpx` |
| Version | 0.27+ |
| Fitness | ★★★★★ |
| Why Chosen | Modern async HTTP client. Drop-in replacement for `requests` with full async support. Used where the dhanhq SDK is insufficient (e.g., direct REST calls for token renewal, instrument master download). Supports HTTP/2. Works with `respx` for mocking in tests. |
| Alternatives Considered | `aiohttp` (heavier, client + server framework), `requests` (synchronous — not acceptable). |
| Risks | None. `httpx` is now the standard async HTTP client for FastAPI ecosystem. |

### websockets

| Attribute | Value |
|---|---|
| Package | `websockets` |
| Version | 12+ |
| Fitness | ★★★★★ |
| Why Chosen | Pure-Python, asyncio-native WebSocket library. Used for both Dhan market feed connection (binary) and Dhan order feed connection (JSON). Full control over connection lifecycle, ping/pong, reconnect. |
| Alternatives Considered | `aiohttp` WebSocket (requires using aiohttp as HTTP client too — overkill), `websocket-client` (synchronous — not acceptable). |
| Risks | v12+ changed some connection API. Use `async with websockets.connect(...)` pattern. |

---

## Background Jobs

### APScheduler

| Attribute | Value |
|---|---|
| Package | `apscheduler` |
| Version | 3.10+ |
| Fitness | ★★★★☆ |
| Why Chosen | In-process async job scheduler. `AsyncIOScheduler` runs jobs directly on the FastAPI event loop. Cron triggers support IST timezone. Supports job persistence (for missed runs). Simple to set up — no separate worker process. |
| Alternatives Considered | `rocketry` (interesting Python-native scheduler, but less mature), `Celery` (see Avoid), `arq` (requires separate worker process + Redis queue for every job, overkill for 3 scheduled tasks), `fastapi-utils` repeat_task (too simple). |
| Risks | APScheduler 4.0 is in development with breaking changes. Pin to `apscheduler>=3.10,<4.0`. Jobs run in the same process — a crash in a job does not kill the app, but does block the event loop if async is not used properly. All APScheduler jobs must be `async def`. |

**Why not Celery:**
The app has only 3 scheduled jobs (EOD scan at 4 PM, candle aggregation as event-driven, token renewal at 9 PM). Celery's overhead (broker, workers, beat scheduler) is disproportionate. APScheduler runs in-process with zero infrastructure additions.

---

## Logging and Observability

### structlog

| Attribute | Value |
|---|---|
| Package | `structlog` |
| Version | 24+ |
| Fitness | ★★★★★ |
| Why Chosen | Structured JSON logging — every log entry has typed key-value pairs instead of free-text strings. Enables log aggregation (Loki, CloudWatch, Datadog) with field-based queries. Context-binding (bind `symbol`, `order_id`, `strategy_id`) produces consistent log correlation. Works with Python's stdlib `logging` for library output. |
| Alternatives Considered | `loguru` (prettier but less structured), stdlib `logging` (no structured output). |
| Risks | None. structlog is the gold standard for structured Python logging. |

```python
# config/logging.py
import structlog

def configure_logging(debug: bool = False) -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if not debug
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            10 if debug else 20  # DEBUG vs INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

---

## Authentication

### PyJWT

| Attribute | Value |
|---|---|
| Package | `PyJWT` |
| Version | 2.8+ |
| Fitness | ★★★★★ |
| Why Chosen | Minimal, fast JWT encode/decode. No extra dependencies. HS256 signing for single-server deployment. RS256 can be added later if needed. |
| Alternatives Considered | `python-jose` (supports JWK and JOSE standards — adds complexity not needed here; also has known security advisory history). |
| Risks | Ensure `algorithms=["HS256"]` is always passed to `jwt.decode()` — omitting it allows algorithm confusion attacks. |

---

## Resilience

### tenacity

| Attribute | Value |
|---|---|
| Package | `tenacity` |
| Version | 8.x |
| Fitness | ★★★★★ |
| Why Chosen | Elegant Python retry library. Decorator-based `@retry`. Supports async functions natively. Configurable: stop after N attempts, exponential backoff, jitter, retry only on specific exception types. Critical for Dhan API calls that may fail transiently (network issues, Dhan 5xx). |
| Alternatives Considered | `backoff` (also good, less feature-rich), manual retry loops (error-prone). |
| Risks | None. tenacity is stable and widely used. |

**Usage pattern:**
```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import structlog

log = structlog.get_logger()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(DhanNetworkError),
    before_sleep=before_sleep_log(log, "WARNING"),
    reraise=True,
)
async def place_order_with_retry(...):
    ...
```

---

## Numerics and Signal Calculations

### numpy

| Attribute | Value |
|---|---|
| Package | `numpy` |
| Version | 1.26+ (or 2.0+ when ecosystem catches up) |
| Fitness | ★★★★★ |
| Why Chosen | ATR (Average True Range), EMA, SMA, RSI, Bollinger Bands calculations are array operations. numpy vectorized operations run at C speed — processing 50 candles for ATR takes microseconds. No need for pandas overhead for these calculations. |
| Alternatives Considered | Pure Python math (acceptable for 14-period ATR, but ugly and slower), pandas (evaluated below). |
| Risks | numpy arrays are not thread-safe for concurrent writes. All signal calculations happen in a single logical flow (event-driven, per-symbol) — no concurrent write risk. Heavy numpy computation blocks the event loop — wrap in `asyncio.run_in_executor`. |

**Usage:**
```python
# domains/risk/atr_validator.py (simplified — actual uses numpy)
import asyncio
import numpy as np
from decimal import Decimal

async def calculate_atr_async(candles: list, period: int = 14) -> Decimal:
    """Run numpy ATR calculation in thread executor to avoid event loop blocking."""
    def _compute():
        highs  = np.array([float(c.high)  for c in candles])
        lows   = np.array([float(c.low)   for c in candles])
        closes = np.array([float(c.close) for c in candles])
        prev_closes = np.roll(closes, 1)
        prev_closes[0] = closes[0]
        tr = np.maximum(
            highs - lows,
            np.maximum(
                np.abs(highs - prev_closes),
                np.abs(lows - prev_closes)
            )
        )
        atr = np.mean(tr[-period:])
        return float(atr)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _compute)
    return Decimal(str(round(result, 2)))
```

### pandas — Evaluated but Not Used in Real-Time Path

| Attribute | Value |
|---|---|
| Package | `pandas` |
| Version | 2.x (if used) |
| Fitness | ★★★☆☆ (for this project's real-time path) |
| Use Case | Pandas is acceptable for offline batch processing — EOD scan, historical backtest reports, journal export. NOT acceptable for real-time candle processing. |
| Why Not in Real-Time | `pd.DataFrame` construction per tick is expensive (30-50µs overhead vs 0.5µs numpy array). Importing pandas adds 200-400ms to startup time. `DataFrame` is mutable — not safe to pass through the domain layer. Memory overhead: a pandas DataFrame of 50 candles uses ~100x more memory than a numpy array. |
| Decision | Install pandas only in the `requirements-analysis.txt` extras file, not in production `requirements.txt`. Use numpy arrays directly for all signal calculations. |

---

## Testing

### pytest + pytest-asyncio + respx

| Package | Version | Fitness | Purpose |
|---|---|---|---|
| `pytest` | 8.x | ★★★★★ | Test runner, fixtures, parametrize |
| `pytest-asyncio` | 0.23+ | ★★★★★ | Async test function support (`@pytest.mark.asyncio`) |
| `respx` | 0.21+ | ★★★★★ | Mock `httpx` HTTP calls (Dhan REST API mocking) |
| `pytest-cov` | 4.x | ★★★★★ | Coverage reporting |
| `factory-boy` | 3.x | ★★★★☆ | Test data factories for domain objects |

**Testing strategy:**
- **Domain layer:** Pure unit tests. No mocks. Pass domain objects directly.
- **Application layer:** Unit tests with fake/stub implementations of all ports. No real DB or Redis.
- **Infrastructure layer:** Integration tests with a test PostgreSQL and Redis (via Docker `pytest` fixture).
- **API layer:** `TestClient` (sync) or `AsyncClient` from `httpx` for async tests.

```python
# conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import create_app

@pytest_asyncio.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

# Example async API test
@pytest.mark.asyncio
async def test_get_watchlist_empty(client: AsyncClient, mock_jwt):
    response = await client.get(
        "/api/v1/signals/watchlist",
        headers={"Authorization": f"Bearer {mock_jwt}"},
    )
    assert response.status_code == 200
    assert "entries" in response.json()
```

---

## ASGI Server

### uvicorn

| Attribute | Value |
|---|---|
| Package | `uvicorn[standard]` |
| Version | 0.29+ |
| Fitness | ★★★★★ |
| Why Chosen | The standard ASGI server for FastAPI. `[standard]` extra includes `uvloop` (faster event loop on Linux) and `httptools` (faster HTTP parser). Single-worker for this app (trading cockpit is single-user, no horizontal scaling needed). `uvloop` gives 20-30% throughput improvement over standard asyncio event loop. |
| Alternatives Considered | `hypercorn` (supports HTTP/2 and HTTP/3 — not needed here), `daphne` (Django-origin). |
| Risks | `uvloop` not available on Windows — development on Windows uses standard asyncio. Production on Linux server gets `uvloop` automatically. |

**Production startup:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop
```

**Single worker is intentional:**
- The Dhan WebSocket connections (market feed, order feed) are application-level singletons.
- Multiple workers would each try to open duplicate WebSocket connections to Dhan.
- The app is single-user (one trader). Single worker handles all concurrency via asyncio.

---

## Packages to Avoid

### Django / Django REST Framework

**Reason:** Django is a synchronous WSGI framework at its core. Even with Django Channels (async), it carries enormous overhead for a trading cockpit use case. Django's ORM is synchronous — async support is partial and slow. The admin, templating, and session middleware are all irrelevant to this project. DRF adds serializers that compete with Pydantic for data validation, creating two validation paths. Django's "batteries included" philosophy is a liability when you need tight control over async I/O, domain isolation, and broker integration. Use FastAPI.

### Flask

**Reason:** Flask is synchronous by default. Flask-ASGI adapters exist but are not production-ready. Flask has no native Pydantic or dependency injection. The trading cockpit requires concurrent handling of market feed WebSocket, position polling, and HTTP requests — Flask's threading model cannot handle this efficiently. Use FastAPI.

### Synchronous SQLAlchemy (1.x or 2.0 sync API)

**Reason:** Using the synchronous SQLAlchemy API (`Session`, `engine.connect()`) blocks the asyncio event loop, making the entire application single-threaded for the duration of every DB query. In a trading app where position polling, order feed, and HTTP requests all run concurrently, any DB blocking call would introduce 50-200ms stalls into the event loop. All SQLAlchemy usage must use `AsyncSession` and `async with`.

### requests library

**Reason:** `requests` is synchronous and blocks the event loop. In an async FastAPI application, calling `requests.get(...)` in an async function blocks the entire event loop until the HTTP call returns — pausing market feed processing, position polling, and all other concurrent operations. Use `httpx` with `async with httpx.AsyncClient() as client: await client.get(...)`.

### Celery

**Reason:** Celery requires a message broker (Redis or RabbitMQ), a separate beat scheduler process, and one or more worker processes. For this project's three scheduled jobs (EOD scan, token renewal, candle aggregation), this adds 3 running processes and a complex deployment for zero additional capability over APScheduler. Celery is appropriate for distributed task queues at scale. APScheduler running in-process is the right tool for a small number of scheduled jobs in a single-server async application.

**When to reconsider Celery:** If the EOD scan grows to scan 5000+ symbols and takes > 10 minutes, or if you add a second trading server, Celery's distributed task queue becomes justified.

### pandas (in real-time signal path)

**Reason:** As detailed above — `DataFrame` construction overhead, memory bloat, startup time cost, and mutable state make pandas unsuitable for the real-time tick processing and candle evaluation path. numpy is sufficient and significantly faster for the calculations needed (ATR, EMA, simple statistical indicators). pandas is acceptable in offline/batch contexts such as the EOD scan where it runs once per day and performance is not critical.

### synchronous websocket-client

**Reason:** `websocket-client` is a synchronous WebSocket library. Using it in an async application requires running it in a thread, which adds complexity and loses the performance benefits of async I/O. Use `websockets` (the async library) for all WebSocket connections.

### SQLite

**Reason:** SQLite has no TimescaleDB extension and poor concurrent write performance. The trading cockpit writes candle ticks at high frequency from the market feed. SQLite's file-level write locking would become a bottleneck. PostgreSQL 16+ with TimescaleDB is required.

---

## Dependency Summary

```
# requirements.txt (production)
fastapi==0.115.6
pydantic==2.7.4
pydantic-settings==2.3.4
sqlalchemy[asyncio]==2.0.32
asyncpg==0.29.0
alembic==1.13.2
redis[hiredis]==5.0.8
dhanhq==2.0.2
httpx==0.27.2
websockets==12.0
apscheduler==3.10.4
structlog==24.4.0
PyJWT==2.8.0
tenacity==8.5.0
numpy==1.26.4
uvicorn[standard]==0.29.0
slowapi==0.1.9        # Rate limiting

# requirements-dev.txt
pytest==8.3.2
pytest-asyncio==0.23.8
pytest-cov==5.0.0
respx==0.21.1
factory-boy==3.3.1
httpx==0.27.2         # Also in dev for test client

# requirements-analysis.txt (offline tooling only, not deployed)
pandas==2.2.2
```

**Total production dependencies: 16 packages (plus transitive).**
Lean and purpose-built — no unused framework baggage.
