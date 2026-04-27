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
| RankingService | 8002 | Python 3.12, FastAPI, pandas | Rankings, scoring, watchlist, dashboard |
| LiveFeedService | 8003 | Python 3.12, FastAPI, dhanhq WS | Real-time tick feed + SSE + intraday signals |
| IndicatorsService | 8005 | Python 3.12, FastAPI, pandas-ta | All metrics, indicators, pattern detection |

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
DataSyncService (8001) → TimescaleDB (price_data_daily, price_data_1min)
      ↓
IndicatorsService (8005) — reads price_data_daily → writes symbol_metrics, symbol_indicators, symbol_patterns
                         — reads price_data_1min (90d) → writes symbol_intraday_profile (ISS)
      ↓
RankingService (8002) — reads symbol_indicators → writes daily_scores
LiveFeedService (8003) — WS ticks → 5-min candles → signal engine + regime detector → SSE to UI
      ↓
CockpitUI (3000) — dashboard shows: daily scores + execution/setup behavior profile
                 — signal tape shows: live signals + regime badge (TRENDING_UP/CHOPPY/SQUEEZE)
```

---

## DB SCHEMA (key tables)
- `symbols` — NSE registry
- `price_data_1min` — Hypertable, 1-min OHLCV
- `price_data_daily` — Hypertable, daily OHLCV
- `symbol_metrics` — structural metrics: week52, ATR, ADV, EMAs, OHLC periods (owned by IndicatorsService)
- `symbol_indicators` — technical indicators: RSI, MACD, ADX, stage, BB, ATR ratio, RS vs Nifty (owned by IndicatorsService)
- `symbol_patterns` — VCP + rectangle breakout detection (owned by IndicatorsService)
- `symbol_intraday_profile` — ISS + intraday features from 90d 1-min: choppiness, stop_hunt_rate, orb_followthrough, pullback_depth, volatility_compression, iss_score (owned by IndicatorsService)
- `daily_scores` — composite scores + rank + watchlist flag (owned by RankingService)
- `sync_state` — per-symbol last sync + status (owned by DataSyncService)

---

## SCORING LOGIC
- RankingService reads pre-computed symbol_indicators (no raw OHLCV)
- Component weights (equal 25%): Momentum, Trend, Volatility, Structure
- Watchlist: top 25 per segment (FNO/equity) per stage (STAGE_2/STAGE_4)

## REGIME DETECTOR
- Rule-based, runs in LiveFeedService on 20-bar rolling window of live 5-min candles
- States: TRENDING_UP / TRENDING_DOWN / CHOPPY / SQUEEZE / NEUTRAL
- Pushed via SSE as `regime_update` events every 5 min

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
- UI data: fetched from service APIs (no direct DB from UI)

---

## SECURITY NOTES
- Dhan tokens + DB passwords in `.env` — never commit `.env`
- No CI/CD pipeline exists
- No auth on internal service APIs (trusted `trader-bridge` network only)
