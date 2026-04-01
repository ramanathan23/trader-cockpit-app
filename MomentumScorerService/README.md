# MomentumScorerService

Reads OHLCV price data from TimescaleDB (written by DataSyncService), computes composite momentum scores for all synced NSE symbols, and exposes a ranking API. Runs on port 8002 (host) / 8000 (container).

## Responsibilities

- Batch-score all synced symbols on demand (daily or 1-min timeframe)
- Persist score breakdowns to `momentum_scores` table
- Expose endpoints to query top-N ranked symbols, per-symbol breakdown, and distribution histogram

## Service layout

```
MomentumScorerService/src/
├── main.py                        # FastAPI app + lifespan startup
├── config.py                      # Settings (pydantic-settings, reads .env)
├── api/routes.py                  # HTTP endpoints
├── db/
│   ├── connection.py              # asyncpg pool factory
│   └── migrations/001_schema.sql # DB schema (momentum_scores)
├── domain/models.py               # ScoreBreakdown value object
├── repositories/
│   ├── price_repository.py        # fetch_synced_symbols, fetch_ohlcv_batch
│   └── score_repository.py        # upsert, get_top, get_distribution
├── services/score_service.py      # Orchestrates batch scoring
└── signals/
    ├── indicators.py              # RSI, MACD, ROC, volume_ratio (pandas/numpy)
    └── scorer.py                  # Composite score computation (CPU-bound, pure)
```

## Scoring model

Each symbol receives a composite score from 0–100 built from four indicators:

| Component | Weight | Indicator | Notes |
|---|---|---|---|
| RSI | 30% | 14-period RSI | Penalises overbought (>80) and oversold (<20) extremes |
| MACD | 30% | MACD histogram z-score | `hist / hist.std() * 15 + 50`, clipped 0–100 |
| ROC | 25% | 10-bar Rate of Change | `50 + roc * 5`, clipped 0–100 |
| Volume ratio | 15% | Current vol / 20-bar avg | Confirms price move with volume |

Minimum 30 bars required to compute a score; symbols with insufficient data are skipped.

Scoring is CPU-bound (pure pandas/numpy). The service offloads it via `asyncio.to_thread` per symbol and upserts results in a single DB connection.

## Compute flow

### `POST /api/v1/scores/compute?timeframe=1d`

```
fetch_synced_symbols()           → symbols with price data in DB
fetch_ohlcv_batch(symbols, tf)   → single batched query, no N+1
  ↓ for each symbol
  asyncio.to_thread(compute_score, df)   → RSI, MACD, ROC, volume
  score_repository.upsert()      → insert or update momentum_scores
```

## REST API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/scores/compute` | Trigger batch scoring (background). Param: `timeframe=1d\|1m` |
| `GET` | `/api/v1/scores` | Top-N symbols ranked by score. Params: `timeframe`, `limit`, `min_score` |
| `GET` | `/api/v1/scores/{symbol}` | Full breakdown (RSI, MACD, ROC, volume) for one symbol |
| `GET` | `/api/v1/scores/summary/distribution` | Histogram of score distribution. Params: `timeframe`, `buckets` |

### Example responses

**Top scores** (`GET /api/v1/scores?limit=5&min_score=70`)
```json
[
  {"symbol": "RELIANCE", "score": 82.4, "rsi": 78.1, "macd_score": 87.0, "roc_score": 81.2, "vol_score": 74.5},
  ...
]
```

**Distribution** (`GET /api/v1/scores/summary/distribution?buckets=5`)
```json
[
  {"bucket": "0-20",  "count": 12},
  {"bucket": "20-40", "count": 89},
  {"bucket": "40-60", "count": 201},
  {"bucket": "60-80", "count": 143},
  {"bucket": "80-100","count": 31}
]
```

## Database schema

| Table | Description |
|---|---|
| `momentum_scores` | Composite score + component breakdown per symbol + timeframe, timestamped |

Reads from `price_data_daily` and `price_data_1m` (owned by DataSyncService).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | required | asyncpg DSN |
| `SCORE_LOOKBACK_BARS` | `100` | Number of bars fetched per symbol for scoring |
