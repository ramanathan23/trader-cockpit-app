# Orchestration & Operations

## Docker Compose Service Graph

```mermaid
flowchart TD
    redis["redis:7-alpine\n:6379"]
    dbinit["db-init\npostgres:16-alpine\nruns init.sql"]

    datasync["data-sync\n:8001"]
    indicators["indicators\n:8005"]
    ranking["ranking\n:8002"]
    livefeed["live-feed\n:8003\nhealthcheck: /api/v1/status"]
    modeling["modeling\n:8004\nvol: /models"]
    notebooks["notebooks\n:8888"]
    ui["cockpit-ui\n:3000"]

    redis --> dbinit
    dbinit --> datasync & indicators & ranking & livefeed & modeling & notebooks
    livefeed -->|"healthcheck pass"| ui
    datasync --> ui
    ranking --> ui
    modeling --> ui
```

### Service Definitions Summary

```yaml
redis:
  image: redis:7-alpine
  volumes: [d:/docker-data/redis:/data]
  ports: [6379:6379]

db-init:
  image: postgres:16-alpine
  # Runs infra/db/setup.sh — creates DB + runs init.sql

data-sync:
  build: DataSyncService/
  ports: [8001:8000]
  env: [DATABASE_URL, REDIS_URL, DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN]

indicators:
  build: IndicatorsService/
  ports: [8005:8000]
  env: [DATABASE_URL, REDIS_URL, INDICATORS_CONCURRENCY]

ranking:
  build: RankingService/
  ports: [8002:8000]
  env: [DATABASE_URL, REDIS_URL]

live-feed:
  build: LiveFeedService/
  ports: [8003:8000]
  env: [DATABASE_URL, REDIS_URL, DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN]
  healthcheck: GET /api/v1/status

modeling:
  build: ModelingService/
  ports: [8004:8000]
  volumes: [./ModelingService/models:/models]
  env: [DATABASE_URL, REDIS_URL, MODEL_BASE_PATH, AUTO_RETRAIN_ENABLED]

cockpit-ui:
  build: CockpitUI/
  ports: [3000:3000]
  args:
    LIVE_FEED_URL: http://live-feed:8000
    NEXT_PUBLIC_LIVE_FEED_URL: http://localhost:8003

notebooks:
  build: notebooks/
  ports: [8888:8888]
  env: [DATABASE_URL]
```

---

## Daily Post-Market Pipeline

```mermaid
flowchart LR
    close["15:30 IST\nMarket close"]

    subgraph step1["Step 1 — Ingest"]
        sync_daily["POST /datasync/sync/run\nDaily OHLCV — yfinance\n~3–5 min"]
        sync_1min["POST /datasync/sync/run-1min\nF&O 1-min — Dhan API\n~10–15 min"]
    end

    subgraph step2["Step 2 — Indicators"]
        compute["POST /indicators/compute-sse\nAll symbols concurrent\n~5–10 min"]
    end

    subgraph step3["Step 3 — Score"]
        score["POST /scorer/scores/compute-sse\nRank + select watchlist\n~2–3 min"]
    end

    subgraph step4["Step 4 — ML (optional)"]
        ml["POST /modeling/models/\ncomfort_scorer/score-all\n~1–2 min"]
    end

    subgraph step5["Step 5 — Feed refresh"]
        refresh["LiveFeedService reads\nnew watchlist from service_config\nautomatically on next cycle"]
    end

    close --> step1 --> step2 --> step3 --> step4 --> step5
```

---

## Makefile Commands

```bash
make up                  # docker compose up --build (all services)
make down                # docker compose down

make sync                # POST /datasync/sync/run  (daily OHLCV)
make sync-1min           # POST /datasync/sync/run-1min  (F&O 1-min)
make scores-compute      # POST /indicators/compute + /scorer/scores/compute
make scores-dashboard    # GET  /scorer/dashboard  (print top ranked)
make comfort-score       # POST /modeling/models/comfort_scorer/score-all

make test-python         # pytest across all services
make coverage-python     # combined coverage report
make ui                  # open http://localhost:3000 (Windows)
```

---

## Full Pipeline via Admin UI

```mermaid
sequenceDiagram
    participant U as User
    participant UI as CockpitUI Admin
    participant DS as DataSyncService
    participant IS as IndicatorsService
    participant RS as RankingService
    participant MS as ModelingService

    U->>UI: Click Full Sync
    UI->>DS: POST /datasync/sync/run-sse
    DS-->>UI: SSE progress stream
    DS-->>UI: {status: "done"}

    UI->>IS: POST /indicators/compute-sse
    IS-->>UI: SSE progress stream
    IS-->>UI: {status: "done"}

    UI->>RS: POST /scorer/scores/compute-sse
    RS-->>UI: SSE progress stream
    RS-->>UI: {status: "done", watchlist_updated: true}

    UI->>MS: POST /modeling/models/comfort_scorer/score-all
    MS-->>UI: {stored_count: 487}

    UI-->>U: Pipeline complete
```

---

## Service Config Tuning (Runtime)

All services expose `/config` GET+POST. Config stored in `service_config` DB table.  
Changes apply without restart via `config_store.apply_overrides()` on each request cycle.

### LiveFeedService Tunable Config

```json
{
  "consolidation_lookback": 15,
  "consolidation_threshold_pct": 4.0,
  "volume_confirm_ratio": 1.2,
  "signal_cooldown_seconds": 300,
  "index_confluence_required": true,
  "candle_buffer_size": 100,
  "candle_flush_interval": 5
}
```

### RankingService Tunable Config

```json
{
  "watchlist_size_fno": 25,
  "watchlist_size_equity": 25,
  "score_date_lookback": 0,
  "balanced_response": true
}
```

### IndicatorsService Tunable Config

```json
{
  "concurrency": 10,
  "atr_period": 14,
  "rsi_period": 14,
  "squeeze_threshold": 0.02,
  "vcp_max_contraction_ratio": 0.80,
  "rect_max_range_pct": 10.0,
  "rect_min_bars": 20,
  "rect_max_bars": 40
}
```

---

## Monitoring & Health Checks

| Service | Health URL |
|---|---|
| DataSyncService | `GET http://localhost:8001/api/v1/health` |
| IndicatorsService | `GET http://localhost:8005/health` |
| RankingService | `GET http://localhost:8002/health` |
| LiveFeedService | `GET http://localhost:8003/api/v1/status` |
| ModelingService | `GET http://localhost:8004/health` |

LiveFeedService `/api/v1/status` returns richer state:
```json
{
  "status": "running",
  "dhan_ws_connected": true,
  "subscribed_symbols": 87,
  "signals_today": 142,
  "last_tick_at": "2026-04-26T09:47:33Z"
}
```

### Redis Key Inspection

```bash
redis-cli LLEN signals:history
redis-cli LRANGE signals:history 0 9
redis-cli LLEN "signals:daily:2026-04-26"
redis-cli GET dhan:access_token
```

---

## Common Failure Modes

```mermaid
flowchart LR
    s1["No live signals"]
    s2["Scores stale"]
    s3["Screener empty"]
    s4["1-min data missing"]
    s5["UI can't reach services"]
    s6["DB pool exhausted"]

    c1["Dhan WS disconnected"]
    c2["Indicators not run"]
    c3["symbol_metrics not populated"]
    c4["Dhan token expired"]
    c5["Docker network issue"]
    c6["INDICATORS_CONCURRENCY too high"]

    f1["Check /api/v1/status\nrestart live-feed"]
    f2["Run indicators → scoring"]
    f3["Run make scores-compute"]
    f4["Update DHAN_ACCESS_TOKEN in .env\nrestart"]
    f5["make down && make up"]
    f6["Lower INDICATORS_CONCURRENCY"]

    s1 --> c1 --> f1
    s2 --> c2 --> f2
    s3 --> c3 --> f3
    s4 --> c4 --> f4
    s5 --> c5 --> f5
    s6 --> c6 --> f6
```

---

## Adding a New Symbol

```mermaid
flowchart LR
    master["POST /datasync/symbols/refresh-master\nRefresh Dhan security master"]
    load["POST /datasync/symbols/load\nRe-load from CSV"]
    sync["POST /datasync/sync/run\nFetch OHLCV history"]
    compute["POST /indicators/compute-sse\nCompute indicators"]
    score["POST /scorer/scores/compute-sse\nScore + watchlist check"]
    wl["If qualifies for watchlist:\nLiveFeedService subscribes\non next refresh"]

    master --> load --> sync --> compute --> score --> wl
```

---

## Adding a New Indicator

```mermaid
flowchart TD
    calc["1. Add computation to\nIndicatorsService/src/services/_calculator.py"]
    col_si["2. Add column to symbol_indicators\nvia migration in infra/db/migrations/"]
    col_ds["3. Add column to daily_scores\nif embedding in score snapshot"]
    scorer["4. Update unified_scorer.py\nif used in scoring"]
    ts["5. Update CockpitUI/src/domain/screener.ts\nif surfaced in screener"]

    calc --> col_si --> col_ds --> scorer --> ts
```

---

## Security Notes

- `.env` contains Dhan tokens + DB passwords — **never commit**
- No auth on internal service APIs — trusted `trader-bridge` Docker network only
- Zerodha OAuth tokens stored per-account in DB — encrypted at rest (DB-level)
- `DHAN_ACCESS_TOKEN` seeded into Redis by LiveFeedService on startup (from env)
- No CI/CD pipeline — all deploys are manual `make up`
