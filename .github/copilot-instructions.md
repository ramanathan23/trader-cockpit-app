# trader-cockpit: Project Instructions

**CRITICAL:** Always use caveman skill for all responses. Token efficiency = top priority.

---

## Architecture

Microservices platform. TimescaleDB backend, FastAPI services, Docker deployment.

**Services:**
- `DataSyncService` (8001) — OHLCV ingestion from yfinance + Dhan
- `MomentumScorerService` (8002) — Compute/serve momentum scores  
- `LiveFeedService` (8003) — Real-time tick processing, signal generation
- `CockpitUI` — Trading dashboard
- `shared/` — Cross-service utilities, base configs, constants

---

## Project Structure

```
<ServiceName>/
├── src/
│   ├── main.py                 # FastAPI app + lifespan
│   ├── config.py               # Subclass BaseServiceSettings
│   ├── db/
│   │   └── connection.py       # Pool creation + migrations
│   ├── api/
│   │   ├── routes.py           # FastAPI router
│   │   ├── deps.py             # Dependency injection
│   │   └── schemas/            # Pydantic request/response models
│   ├── domain/                 # Pure business logic (no I/O)
│   ├── services/               # Orchestration (calls repos + infra)
│   ├── repositories/           # DB queries (asyncpg)
│   ├── infrastructure/         # External integrations (APIs, fetchers)
│   └── signals/                # Stateless signal/indicator logic
├── tests/
│   ├── conftest.py             # Fixtures
│   └── test_*.py               # Pytest files
├── pyproject.toml              # Dependencies (hatchling + uv)
├── pytest.ini                  # asyncio_mode=auto
├── Dockerfile
└── README.md
```

**Shared:**
```
shared/
├── shared/
│   ├── base_config.py          # BaseServiceSettings
│   ├── constants.py            # IST, market hours, etc
│   ├── db.py                   # Shared DB utilities
│   └── utils.py                # ensure_utc, parse_pg_command_result
└── pyproject.toml
```

---

## Coding Principles

### Layer Separation (Strict)

1. **Domain** — pure functions, no async, no I/O. Testable in isolation.
   ```python
   # domain/daily_action.py
   def classify_daily(last_ts: datetime | None, now_ist: datetime) -> DailyAction:
       """Pure logic. No database, no API calls."""
   ```

2. **Repositories** — database queries only. Thin wrappers over asyncpg.
   ```python
   class PriceRepository:
       def __init__(self, pool: asyncpg.Pool):
           self._pool = pool
       
       async def fetch_ohlcv(self, symbol: str, ...) -> pd.DataFrame:
           """Single responsibility: fetch data."""
   ```

3. **Services** — orchestrate repos + domain + infra. Business workflows.
   ```python
   class SyncService:
       def __init__(self, pool: asyncpg.Pool):
           self._symbols = SymbolRepository(pool)
           self._fetcher = DailyFetcher(...)
       
       async def run_daily_sync(self):
           """Coordinate: load symbols, classify, fetch, persist."""
   ```

4. **Infrastructure** — external APIs, fetchers, WebSocket clients.
   ```python
   class YFinanceFetcher:
       async def fetch_daily(self, symbol: str, ...) -> pd.DataFrame:
           """Fetch from yfinance. Return normalized DataFrame."""
   ```

5. **API** — FastAPI routes, dependency injection, schemas.
   ```python
   @router.post("/sync/run")
   async def run_sync(request: Request) -> SyncResponse:
       svc = request.app.state.sync_service
       return await svc.run_daily_sync()
   ```

### Dependency Injection

- **NO global singletons**. Everything injected via constructor or FastAPI `Depends()`.
- `main.py` wires dependencies in lifespan context:
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      pool = await create_pool(...)
      app.state.pool        = pool
      app.state.price_repo  = PriceRepository(pool)
      app.state.sync_svc    = SyncService(pool)
      yield
  ```

### Configuration

- All services subclass `BaseServiceSettings` from `shared/base_config.py`
- Use Pydantic Settings with `.env` file
- Structure:
  ```python
  # config.py
  from shared.base_config import BaseServiceSettings
  from pydantic import Field

  class Settings(BaseServiceSettings):
      # Service-specific fields
      score_concurrency: int = Field(default=10)
      yfinance_lookback_years: int = Field(default=5)
  
  settings = Settings()
  ```

### Async Patterns

- Use `asyncpg.Pool` everywhere (no sync wrappers)
- Concurrency via `asyncio.Semaphore` for batch operations
- Always set timeouts:
  ```python
  pool = await asyncio.wait_for(
      create_pool(...),
      timeout=30,
  )
  ```

### Database

- **TimescaleDB** (PostgreSQL + hypertables)
- Bulk insert pattern:
  ```python
  # 1. COPY into temp table (fastest)
  # 2. INSERT ... ON CONFLICT DO NOTHING (idempotent)
  await conn.copy_records_to_table("tmp_price_data", records=records)
  result = await conn.execute("""
      INSERT INTO price_data_daily SELECT * FROM tmp_price_data
      ON CONFLICT (symbol, time) DO NOTHING
  """)
  ```
- Use `asyncpg.Pool.acquire()` for transactions
- Parse command results: `parse_pg_command_result(result)`

### Error Handling

- Services catch + log exceptions, return structured responses
- Domain functions raise `ValueError` for invalid inputs
- API routes use FastAPI exception handlers
- Critical failures log at `logger.critical()` with recovery hints

### Testing

- Pytest + pytest-asyncio
- `pytest.ini` sets `asyncio_mode = auto`
- Mock asyncpg connections with `AsyncMock`:
  ```python
  class AcquireContext:
      def __init__(self, conn):
          self._conn = conn
      async def __aenter__(self):
          return self._conn
      async def __aexit__(self, *args):
          return False

  conn = AsyncMock()
  pool = Mock()
  pool.acquire.return_value = AcquireContext(conn)
  ```
- Run: `make test-python` (runs all services, combines coverage)
- Test pure domain functions directly (no fixtures needed)

### Naming Conventions

- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/vars:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`
- Repo methods: `fetch_*`, `upsert_*`, `load_*`, `save_*`
- Service methods: `run_*`, `compute_*`, `process_*`

### Type Hints

- All function signatures have type hints
- Use `typing.Literal` for enums: `DailyAction = Literal["INITIAL", "SKIP", "FETCH_TODAY", "FETCH_GAP"]`
- Use `| None` (modern union syntax, Python 3.12+)
- Domain models use `@dataclass` or Pydantic `BaseModel`

### Logging

- Use module-level logger: `logger = logging.getLogger(__name__)`
- Format: `%(asctime)s %(levelname)-8s %(name)s: %(message)s`
- Levels:
  - `logger.debug()` — verbose diagnostics
  - `logger.info()` — progress milestones
  - `logger.warning()` — recoverable issues
  - `logger.error()` — failures that continue
  - `logger.critical()` — failures that abort startup

### Documentation

- Docstrings for **services** and **domain functions** (explain why, not what)
- Top-of-file module docstring for complex logic
- Example:
  ```python
  """
  SpikeDetector: identifies price-volume anomalies.
  
  Stateless — pure function: (candle, history, thresholds) → SpikeState | None.
  """
  ```
- NO docstrings for trivial getters, setters, or self-explanatory code

### Code Organization

- Keep files < 300 lines (split if needed)
- Group related functions in modules (e.g., `signals/indicators.py`)
- Constants at top of file
- Helper functions prefixed with `_` if internal
- Main logic at bottom

### DataFrame Usage

- Use pandas for OHLCV data (industry standard)
- **Always** normalize timezones to UTC:
  ```python
  if hasattr(ts, "tzinfo"):
      ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
  ```
- Convert to records for asyncpg:
  ```python
  def _to_records(symbol: str, df: pd.DataFrame) -> list[tuple]:
      records = []
      for row in df.itertuples():
          records.append((row.Index, symbol, row.Open, ...))
      return records
  ```

### Performance

- Batch DB operations (no loops of single inserts)
- Use `asyncio.gather()` for parallel I/O
- Semaphore to limit concurrency: `asyncio.Semaphore(10)`
- Chunk large datasets (50k rows per COPY)
- Profile before optimizing

---

## Common Patterns

### Service Initialization

```python
class SyncService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool    = pool
        self._symbols = SymbolRepository(pool)
        self._prices  = PriceRepository(pool)
```

### FastAPI Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(...)
    await run_migrations(pool)
    app.state.pool = pool
    app.state.repo = Repository(pool)
    logger.info("Service ready")
    yield
    await pool.close()

app = FastAPI(lifespan=lifespan)
```

### Repository Query

```python
async def fetch_symbols(self) -> list[str]:
    async with self._pool.acquire() as conn:
        rows = await conn.fetch("SELECT symbol FROM symbols WHERE enabled")
        return [row["symbol"] for row in rows]
```

### Pure Domain Function

```python
def classify_daily(last_ts: datetime | None, now_ist: datetime) -> DailyAction:
    """No I/O. Deterministic. Easy to test."""
    if last_ts is None:
        return "INITIAL"
    # ... classification logic
```

### Batch Processing with Semaphore

```python
async def _score_one(self, symbol: str) -> ScoreResult:
    async with self._semaphore:
        df = await self._prices.fetch_ohlcv(symbol, ...)
        return compute_unified_score(df)

results = await asyncio.gather(*[
    self._score_one(sym) for sym in symbols
])
```

---

## Development Workflow

### Local Setup

```bash
cp .env.example .env
# Fill in POSTGRES_HOST, DHAN_CLIENT_ID, etc
docker compose up -d
```

### Running Tests

```bash
make test-python          # All services
make coverage-python      # With coverage report
```

### Service Access

```bash
make sync                 # Trigger daily sync
make scores-compute       # Compute momentum scores
make scores-top           # View top 20
make feed-status          # LiveFeed health
make ui                   # Open dashboard
```

---

## File Templates

### Service pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "service-name"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "asyncpg>=0.30",
    "pydantic-settings>=2.6",
]

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.uv]
dev-dependencies = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
]
```

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
addopts = -ra
```

### Dockerfile (Service)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY src/ ./src/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## Anti-Patterns (Avoid)

❌ Global database connections  
❌ Sync wrappers around async code  
❌ Business logic in API routes  
❌ Hardcoded credentials  
❌ SQL strings without parameterization  
❌ Catching exceptions without logging  
❌ Loops of single-row inserts (use bulk COPY)  
❌ Mixing I/O and pure logic in same function  
❌ Import * (always explicit imports)  
❌ Mutable default arguments  

---

## Key Files

- `shared/base_config.py` — Base settings class
- `shared/constants.py` — IST timezone, market hours
- `shared/utils.py` — ensure_utc, parse_pg_command_result
- `Makefile` — Development shortcuts
- `docker-compose.yml` — Service orchestration
- `infra/db/init.sql` — DB schema + hypertables

---

## When Adding New Features

1. **Domain first** — pure functions, write tests
2. **Repository** — DB queries, use existing pool
3. **Service** — orchestrate domain + repo
4. **API** — expose via FastAPI route
5. **Wire in main.py** — inject dependencies in lifespan
6. **Test** — unit tests for domain, integration for service
7. **Update README** — document new endpoints

---

## LLM Collaboration Notes

- **Always use caveman skill** (token efficiency)
- Check existing patterns before suggesting new ones
- Respect layer boundaries (no I/O in domain)
- Follow async patterns (no sync wrappers)
- Test domain functions in isolation
- Use bulk operations for database writes
- Keep responses concise, code examples preferred over prose