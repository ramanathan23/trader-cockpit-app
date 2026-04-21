# CLAUDE.md — trader-cockpit-app

## COMMUNICATION MODE
**Always use caveman ultra mode.** Every response. No revert. Drop all articles/filler/hedging. Fragments OK. Code/commits/security blocks: write normal.

---

## REPO: NSE Trading Platform (Microservices)

### Services + Ports
| Service | Port | Tech | Purpose |
|---|---|---|---|
| CockpitUI | 3000 | Next.js 15, React 19, TS, Tailwind | Dashboard UI |
| DataSyncService | 8001 | Python 3.12, FastAPI, yfinance, dhanhq | OHLCV fetch + persist |
| MomentumScorerService | 8002 | Python 3.12, FastAPI, ta, pandas | Composite scores (0-100) |
| LiveFeedService | 8003 | Python 3.12, FastAPI, dhanhq WS | Real-time tick feed + SSE |
| ModelingService | 8004 | Python 3.12, FastAPI, sklearn | ML model registry |
| notebooks | 8888 | Jupyter + Python 3.12 | Research/backtesting |

### Shared Infra
- **DB**: External TimescaleDB/PostgreSQL via `POSTGRES_HOST:POSTGRES_PORT`
- **Cache**: Redis 7 (in-compose, `redis://redis:6379`)
- **Network**: `trader-bridge` Docker bridge — services reach each other by hostname
- **Package manager**: `uv` (all Python services)
- **Shared lib**: `/shared` — asyncpg pool, migrations, base config; installed editable in each service

---

## DATA FLOW
```
yfinance / Dhan API
      ↓
DataSyncService (8001) → TimescaleDB
      ↓
MomentumScorerService (8002) — reads price_data_1m/daily → writes momentum_scores
LiveFeedService (8003) — WS ticks → SSE to UI
ModelingService (8004) — reads DB → ComfortScorer predictions
      ↓
CockpitUI (3000) — polls 8001-8004 APIs
```

---

## DB SCHEMA (key tables)
- `symbols` — NSE registry
- `price_data_1m` — Hypertable, 1-min OHLCV
- `price_data_daily` — Hypertable, daily OHLCV
- `momentum_scores` — RSI(30%) + MACD(30%) + ROC(25%) + VolRatio(15%)
- `sync_state` — per-symbol last sync + status
- `price_1m_hourly` — continuous aggregate view

---

## SCORING LOGIC
- Min 30 bars required per symbol
- Timeframes: `1d`, `1m`
- Weights: RSI 0.30, MACD 0.30, ROC 0.25, VolumeRatio 0.15
- `is_new_watchlist` flag affects dashboard ranking

---

## KEY PATHS
```
shared/db.py               # asyncpg pool factory
shared/_migrations.py      # migration runner
shared/base_config.py      # pydantic Settings base
infra/db/init.sql          # full schema (~450 lines)
infra/db/setup.sh          # DB bootstrap
docker-compose.yml         # all services
Makefile                   # dev commands
.env / .env.example        # credentials
```

### Per-service pattern (all Python)
```
src/main.py                # FastAPI app + lifespan
src/api/routes.py          # HTTP endpoints
src/services/              # business logic
src/repositories/          # DB access (asyncpg)
src/infrastructure/        # external integrations
tests/                     # pytest
pyproject.toml             # deps (uv)
Dockerfile                 # Python 3.12 slim + uv
```

---

## ENV VARS (critical)
```
DB_USER / DB_PASSWORD / DB_NAME
POSTGRES_HOST / POSTGRES_PORT
REDIS_URL
DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN
DOCKER_DATA_PATH          # volume root (Windows: d:/docker-data)
```

---

## DEV COMMANDS (Makefile)
```
make up                   # compose up --build
make down                 # compose down
make sync                 # trigger DataSync
make sync-1min            # 1-min fetch
make scores-compute       # score all symbols
make scores-dashboard     # top ranked
make comfort-score        # ComfortScorer predict
make test-python          # all pytest
make coverage-python      # combined coverage
make ui                   # open dashboard (Windows)
```

---

## CODING RULES
- Python 3.12 + FastAPI pattern across all services
- asyncpg (not SQLAlchemy) for DB — use pool from `shared/db.py`
- No mocking DB in tests — integration tests hit real DB
- No comments unless WHY is non-obvious
- No abstractions beyond task scope
- No error handling for impossible scenarios
- Validate only at system boundaries (user input, external APIs)
- Prefer editing existing files over creating new ones

---

## ARCHITECTURE CONSTRAINTS
- Each service independently deployable
- New features: add endpoint to relevant service, reuse shared lib
- Schema changes: update `infra/db/init.sql` + run migration
- Model changes: go through ModelingService registry, not direct DB writes
- UI data: fetched from service APIs (no direct DB from UI)

---

## SECURITY NOTES
- Dhan tokens + DB passwords in `.env` — never commit `.env`
- No CI/CD pipeline exists
- No auth on internal service APIs (trusted `trader-bridge` network only)
