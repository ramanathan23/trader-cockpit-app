# IndicatorsService — Port 8005

Reads OHLCV from DB → computes all technical indicators, metrics, and patterns → writes to DB. Owns `symbol_metrics`, `symbol_indicators`, `symbol_patterns`.

## Key files
```
src/main.py                      # FastAPI app + lifespan + pool
src/api/routes.py                # compute + compute-sse endpoints
src/services/                    # indicator computation logic (pandas-ta)
src/repositories/                # asyncpg reads (price_data_daily) + writes (symbol_metrics, symbol_indicators, symbol_patterns)
```

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST   | /compute | Compute all indicators for all symbols (background) |
| POST   | /compute-sse | Compute with SSE progress stream (pipeline UI) |

## DB tables owned (writes)
- `symbol_metrics` — structural metrics: week52_high/low, ATR-14, ADV-20, EMAs (50/200), OHLC periods
- `symbol_indicators` — technical indicators: RSI, MACD, ADX, Bollinger Bands, ATR ratio, RS vs Nifty, stage (Weinstein)
- `symbol_patterns` — pattern detection results: VCP, rectangle breakout

## DB tables read (not owned)
- `price_data_daily` — source OHLCV (owned by DataSyncService)
- `symbols` — symbol list

## Pattern notes
- Uses pandas-ta for indicator calculation — batch process all symbols in one pass.
- Stage detection: Weinstein method from 200-day SMA slope + price position.
- RS vs Nifty: relative strength ratio vs NIFTY 500 index.
- Must run AFTER DataSyncService sync completes (pipeline dependency).
- Results consumed by RankingService (symbol_indicators) and LiveFeedService (symbol_metrics for screener).
