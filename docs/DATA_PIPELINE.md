# Data Pipeline — End to End

## Full Pipeline Overview

```mermaid
flowchart TD
    yfinance["yfinance API"]
    dhan_rest["Dhan REST API"]
    dhan_ws["Dhan WebSocket"]
    zerodha["Zerodha OAuth API"]

    subgraph DSS["DataSyncService :8001"]
        daily_sync["Daily OHLCV Sync"]
        min_sync["1-min F&O Sync"]
        z_sync["Zerodha Broker Sync"]
    end

    subgraph DB["TimescaleDB"]
        pdd["price_data_daily"]
        pd1["price_data_1min"]
        c5m["candles_5min"]
        sm["symbol_metrics"]
        si["symbol_indicators"]
        sp["symbol_patterns"]
        ds["daily_scores"]
        mp["model_predictions"]
        sc["service_config watchlist"]
    end

    subgraph IS["IndicatorsService :8005"]
        struct_metrics["Structural Metrics"]
        tech_ind["Technical Indicators"]
        patterns["Pattern Detection"]
    end

    subgraph RS["RankingService :8002"]
        scorer["Unified Scorer"]
        watchlist["Watchlist Selector"]
    end

    subgraph LFS["LiveFeedService :8003"]
        tick_router["TickRouter"]
        candle_builder["CandleBuilder"]
        signal_engine["SignalEngine"]
        publisher["SignalPublisher"]
    end

    subgraph MS["ModelingService :8004"]
        model["ComfortScorer"]
    end

    REDIS[("Redis")]
    UI["CockpitUI :3000"]

    yfinance --> daily_sync --> pdd
    dhan_rest --> min_sync --> pd1
    zerodha --> z_sync
    dhan_ws --> tick_router --> candle_builder --> c5m
    candle_builder --> signal_engine

    pdd --> struct_metrics --> sm
    pdd --> tech_ind --> si
    pdd --> patterns --> sp

    sm --> scorer
    si --> scorer
    sp --> scorer
    scorer --> ds
    scorer --> watchlist --> sc

    ds --> model --> mp

    sc -->|watchlist symbols| signal_engine
    sm -->|prev day OHLC + ATR| signal_engine
    si -->|weekly_bias| signal_engine

    signal_engine --> publisher --> REDIS --> UI
    ds --> UI
    sm --> UI
    si --> UI
    sp --> UI
```

---

## Stage 1: Ingestion (DataSyncService)

### Daily OHLCV — yfinance

```mermaid
flowchart TD
    trigger["POST /api/v1/sync/run"]
    symbols["Load all symbols from DB"]
    classify{"Classify gap"}
    no_data["no_data\nFull history fetch"]
    gap_small["gap_small < 5 days\nIncremental append"]
    gap_medium["gap_medium 5–20 days\nIncremental + warning"]
    gap_large["gap_large > 20 days\nFull re-fetch"]
    yf["yfinance fetch"]
    upsert["Batch upsert → price_data_daily"]
    state["Update sync_state\nsymbol / 1d / last_synced_at"]

    trigger --> symbols --> classify
    classify -->|never synced| no_data --> yf
    classify -->|gap < 5d| gap_small --> yf
    classify -->|gap 5–20d| gap_medium --> yf
    classify -->|gap > 20d| gap_large --> yf
    yf --> upsert --> state
```

**Gap classification thresholds:**

| Class | Condition | Action |
|---|---|---|
| `no_data` | Never synced | Full history fetch |
| `gap_small` | < 5 trading days | Incremental append |
| `gap_medium` | 5–20 days | Incremental with warning |
| `gap_large` | > 20 days | Full re-fetch from last good date |

### 1-Minute OHLCV — Dhan API

```mermaid
flowchart LR
    trigger["POST /api/v1/sync/run-1min"]
    filter["Filter: is_fno=true\ndhan_security_id NOT NULL"]
    batch["Batch 10 concurrent symbols"]
    dhan["Dhan REST API\nlookback: SYNC_1M_HISTORY_DAYS"]
    upsert["Batch upsert → price_data_1min\nweekly chunks"]
    state["Update sync_state\nsymbol / 1m"]

    trigger --> filter --> batch --> dhan --> upsert --> state
```

### Zerodha Broker Sync

```mermaid
flowchart LR
    trigger["POST /api/v1/zerodha/sync"]
    oauth["OAuth session\naccount_id → access token"]
    fetch["Fetch orders / trades\npositions / holdings"]
    reconstruct["Reconstruct trade legs\nmulti-leg options"]
    pnl["Compute PnL\nper-trade + per-symbol"]
    persist["Persist to DB\nper-account isolation"]

    trigger --> oauth --> fetch --> reconstruct --> pnl --> persist
```

---

## Stage 2: Indicator Computation (IndicatorsService)

```mermaid
flowchart TD
    trigger["POST /api/v1/compute-sse"]
    symbols["All symbols — N concurrent workers"]

    subgraph metrics["Structural Metrics — _calculator.py"]
        m1["week52_high/low · atr_14 · adv_20_cr"]
        m2["ema_20/50/200"]
        m3["prev_day/week/month OHLC"]
        m4["week_return_pct · cam_median_range_pct"]
    end

    subgraph tech["Technical Indicators — _calculator.py"]
        t1["rsi_14 · macd_hist · macd_hist_std"]
        t2["roc_5/20/60 · vol_ratio_20"]
        t3["adx_14 · plus_di · minus_di · weekly_bias"]
        t4["bb_width/squeeze/squeeze_days · kc_width"]
        t5["atr_ratio · atr_5 · nr7"]
        t6["rs_vs_nifty = symbol_roc60 − nifty500_roc60"]
        t7["stage classification"]
    end

    subgraph patt["Pattern Detection — _pattern_detector.py"]
        p1["VCP: close > ema_50\n2–3 contractions ≤80% each\nvolume declining"]
        p2["Rectangle: 20–40 bar range ≤10%\nclose > range_high + vol spike"]
    end

    sm_out["→ symbol_metrics"]
    si_out["→ symbol_indicators"]
    sp_out["→ symbol_patterns"]

    trigger --> symbols
    symbols --> metrics --> sm_out
    symbols --> tech --> si_out
    symbols --> patt --> sp_out
```

---

## Stage 3: Scoring (RankingService)

```mermaid
flowchart TD
    trigger["POST /api/v1/scores/compute-sse"]
    join["JOIN symbol_indicators\n+ symbol_metrics\n+ symbol_patterns"]

    subgraph score["unified_scorer.compute_score_from_indicators()"]
        mom["Momentum 25%\nRSI + MACD + ROC + volume"]
        trend["Trend 25%\nADX + EMA stack + weekly_bias + DI"]
        vol["Volatility 25%\nBB squeeze + ATR contraction + NR7"]
        struct["Structure 25%\n52wk proximity + RS vs Nifty"]
        total["total = 0.25 × each component"]
    end

    rank["Dense rank by total_score DESC"]

    subgraph watchlist["Watchlist Selection"]
        stage2["STAGE_2 bull candidates"]
        stage4["STAGE_4 bear candidates"]
        top25["Top 25 per segment per stage\n(fno + equity × bull + bear)"]
    end

    upsert["Upsert → daily_scores\nwith embedded indicator snapshot"]
    publish["Publish watchlist → service_config"]

    trigger --> join
    join --> mom & trend & vol & struct --> total
    total --> rank --> stage2 & stage4 --> top25
    top25 --> upsert --> publish
```

### Stage Classification

| Stage | Condition |
|---|---|
| `STAGE_1` | Below EMA-200, EMA-50 flat or declining |
| `STAGE_2` | Above EMA-200, EMA-50 rising, positive momentum |
| `STAGE_3` | Topping — below EMA-50, above EMA-200 but weakening |
| `STAGE_4` | Below EMA-200 and EMA-50, negative momentum |
| `UNKNOWN` | Insufficient data |

### Scoring Component Weights

```mermaid
pie title Unified Score Components
    "Momentum" : 25
    "Trend" : 25
    "Volatility" : 25
    "Structure" : 25
```

---

## Stage 4: ML Predictions (ModelingService)

```mermaid
flowchart LR
    trigger["POST /models/comfort_scorer/score-all\n?score_date=YYYY-MM-DD"]
    fetch["Fetch all symbols from\ndaily_scores for score_date"]
    features["Extract feature vector\nfrom score row + price_data_daily"]
    load["Load versioned model\n/models/comfort_scorer/vN.pkl"]
    infer["sklearn inference"]
    out["predictions JSONB\n+ confidence REAL"]
    store["Upsert → model_predictions"]

    trigger --> fetch --> features --> load --> infer --> out --> store
```

---

## Stage 5: Real-Time Feed (LiveFeedService)

```mermaid
flowchart TD
    startup["Service startup — lifespan()"]
    pool["asyncpg pool connect"]
    redis_conn["SignalPublisher → Redis connect"]
    token["TokenStore.load()\nRedis → env fallback"]
    warmstart["InstrumentLoader.warm_start()\nload recent candles_5min"]
    task["asyncio.create_task(feed_service.run())"]

    startup --> pool & redis_conn & token & warmstart --> task

    subgraph loop["feed_service.run() — continuous"]
        ws["Dhan WebSocket connect\nwatchlist + NIFTY/BANKNIFTY/SENSEX"]
        router["TickRouter.route(tick)"]
        index_bias["Update IndexBiasTracker\n(majority vote: NIFTY/BANKNIFTY/SENSEX)"]
        candle["CandleBuilder accumulate\nOHLCV + tick_count in 5-min window"]
        flush["BufferedCandleWriter\nbatch 100 candles / flush 5s"]
        db_write["Upsert → candles_5min"]
        engine["SignalEngine.on_candle(candle)\n5-min + 15-min + 1h stacks"]
        detect["Detect RANGE / CAM signals"]
        check["Check index confluence\nCheck watchlist_conflict"]
        levels["Compute trade levels\nentry/stop/target/trail_stop"]
        emit["_on_signal()"]
        redis_pub["PUBLISH to Redis\nsignals / signals:symbol\nsignals:history / signals:daily:DATE"]
        broadcast["Broadcast SSE + WebSocket\nto all subscribers"]
    end

    task --> ws --> router
    router --> index_bias
    router --> candle --> flush --> db_write
    candle -->|on window close| engine --> detect --> check --> levels --> emit
    emit --> redis_pub --> broadcast
```

---

## Stage 6: UI Consumption (CockpitUI)

```mermaid
sequenceDiagram
    participant B as Browser
    participant UI as CockpitUI Next.js
    participant LF as LiveFeedService
    participant RS as RankingService
    participant DS as DataSyncService

    Note over B,DS: Initial page load
    B->>UI: GET /
    UI->>RS: GET /scorer/dashboard
    UI->>LF: GET /api/v1/instruments/metrics
    UI->>RS: GET /scorer/config
    UI->>DS: GET /datasync/config
    UI->>LF: GET /api/v1/config
    UI->>LF: GET /api/v1/token/status
    RS-->>UI: DashboardStats + ScoredSymbol[]
    LF-->>UI: InstrumentMetrics[]

    Note over B,LF: Live signal subscription
    B->>LF: WS /api/v1/signals/ws
    B->>LF: GET /api/v1/signals/history (catchup)
    LF-->>B: historical Signal[]
    loop on each signal
        LF-->>B: Signal JSON via WebSocket
        B->>B: deduplicate by symbol:signal_type
    end

    Note over B,LF: Screener
    B->>LF: GET /api/v1/screener
    LF-->>B: ScreenerRow[]
    B->>B: apply preset filters client-side

    Note over B,LF: Symbol detail
    B->>LF: GET /api/v1/optionchain/expiries
    B->>LF: GET /api/v1/optionchain?symbol=X&expiry=Y
```

---

## Full Daily Pipeline (Ordered)

```mermaid
flowchart LR
    close["Market close\n~15:30 IST"]
    sync["make sync\nPOST /datasync/sync/run\n+ /sync/run-1min"]
    ind["POST /indicators/compute\nAll symbols concurrent"]
    score["POST /scorer/scores/compute\nRank + select watchlist"]
    ml["make comfort-score\nPOST /models/comfort_scorer/score-all"]
    refresh["LiveFeedService\nreads new watchlist\nfrom service_config"]

    close --> sync --> ind --> score --> ml --> refresh
```

---

## Data Freshness Contract

| Table | Written by | Frequency |
|---|---|---|
| `price_data_daily` | DataSyncService | Daily post-market |
| `price_data_1min` | DataSyncService | Daily (F&O symbols) |
| `candles_5min` | LiveFeedService | Continuous (trading hours) |
| `symbol_metrics` | IndicatorsService | Daily (after sync) |
| `symbol_indicators` | IndicatorsService | Daily (after sync) |
| `symbol_patterns` | IndicatorsService | Daily (after sync) |
| `daily_scores` | RankingService | Daily (after indicators) |
| `model_predictions` | ModelingService | Daily (after scoring) |
| `service_config` (watchlist) | RankingService | After each scoring run |
