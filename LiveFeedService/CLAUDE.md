# LiveFeedService — Port 8003

Real-time Dhan WebSocket tick feed → SSE signals to UI. Also serves instrument metrics, screener data, charts, and option chains.

## Key files
```
src/main.py                           # FastAPI app + lifespan + pool + WS connect
src/api/routes/signals.py             # SSE signal stream + history endpoints
src/api/routes/instruments.py         # Metrics, screener, chart OHLCV endpoints
src/api/routes/option_chain.py        # Option chain + expiries endpoints
src/api/routes/status.py              # Health, feed status, token endpoints
src/api/routes/config.py              # Runtime config GET/PATCH
src/signals/                          # Intraday signal detection (open drive, spikes, patterns)
src/infrastructure/dhan/              # Dhan WS client + tick normalization
src/infrastructure/redis/             # Redis pub/sub for tick distribution
src/services/                         # Feed orchestration, tick aggregation
src/core/                             # Shared feed state, aggregators
```

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET    | /health | Liveness check |
| GET    | /status | Feed health + index bias (Nifty/BankNifty direction) |
| GET    | /token/status | Dhan access token presence + expiry |
| POST   | /token | Update Dhan token + reconnect WS feeds |
| GET    | /signals/stream | SSE stream of intraday trading signals |
| GET    | /signals/history | All signals for a given IST date (query: date) |
| GET    | /signals/history/dates | IST dates that have saved signal history |
| POST   | /instruments/metrics | Batch instrument metrics for multiple symbols |
| GET    | /instrument/{symbol}/metrics | Single symbol metrics (52w, ATR, today range) |
| GET    | /screener | All symbols with pre-computed daily metrics for screener UI |
| GET    | /chart/{symbol}/daily | Daily OHLCV for chart (proxied from price_data_daily) |
| GET    | /chart/{symbol}/intraday | Intraday OHLCV with optional resampling (query: interval) |
| POST   | /optionchain/expiries | Available expiry dates for a symbol |
| POST   | /optionchain | Full option chain for symbol + expiry |
| GET    | /config | Current tunable config |
| PATCH  | /config | Update config (persists + applies immediately) |

## DB tables read (not owned)
- `price_data_daily` — daily OHLCV for charts
- `price_data_1min` — intraday OHLCV for charts + tick baseline
- `symbol_metrics` — instrument metrics for screener + /instrument endpoint
- `symbol_indicators` — stage, RS, etc. for screener
- `symbols` — symbol list

## DB tables owned (writes)
- `intraday_signals` (or equivalent) — persisted signal history

## Architecture notes
- Dhan WS → Redis pub/sub → signal detection workers → SSE broadcast
- SSE /signals/stream: each client gets EventSource; signals broadcast to all connected clients
- Option chain: on-demand fetch from Dhan API (no caching)
- Screener endpoint aggregates symbol_metrics + symbol_indicators — heavy query, should not be called per-tick
- Token hot-swap: POST /token replaces token in memory + reconnects WS without restart
