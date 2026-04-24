# RankingService — Port 8002

Reads pre-computed `symbol_indicators` → computes composite scores → writes to `daily_scores`. Owns the watchlist (top 25 per segment per stage).

## Key files
```
src/main.py                      # FastAPI app + lifespan + pool
src/api/routes.py                # scores/compute, dashboard, watchlist endpoints
src/services/score_service.py    # Scoring orchestration
src/services/                    # Component scorers (momentum, trend, volatility, structure)
src/repositories/                # asyncpg reads (symbol_indicators) + writes (daily_scores)
src/signals/                     # Watchlist signal helpers
```

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST   | /scores/compute | Trigger scoring for all symbols (background) |
| POST   | /scores/compute-sse | Scoring with SSE progress stream (pipeline UI) |
| GET    | /dashboard | Stats + scored symbols (query params: limit, watchlist_only, segment, stage) |
| GET    | /dashboard/watchlist | Watchlist symbols for live feed subscription |
| GET    | /watchlist/stage | Stage 2 (bull) + Stage 4 (bear) watchlist ranked by total score |

## DB tables owned (writes)
- `daily_scores` — composite score + component scores + rank + watchlist flag per symbol per date

## DB tables read (not owned)
- `symbol_indicators` — technical indicators (owned by IndicatorsService)
- `symbol_metrics` — structural metrics (owned by IndicatorsService)

## Scoring logic
- 4 components, equal 25% weight each: Momentum, Trend, Volatility, Structure
- Reads only pre-computed `symbol_indicators` — never raw OHLCV
- Watchlist: top 25 per segment (FNO / equity) per stage (STAGE_2 / STAGE_4)
- Must run AFTER IndicatorsService compute completes (pipeline dependency)

## Pattern notes
- Pipeline order: DataSync → IndicatorsService → RankingService → ModelingService
- No raw OHLCV access — all inputs from symbol_indicators / symbol_metrics
