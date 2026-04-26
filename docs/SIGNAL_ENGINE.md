# Signal Engine — LiveFeedService Deep Dive

## Overview

Each watchlist symbol gets a dedicated `SignalEngine` instance. Engine receives completed 5-min candles and decides whether a tradeable signal has occurred.

---

## Signal Detection Flow

```mermaid
flowchart TD
    candle["5-min candle completed"]

    subgraph engine["SignalEngine.on_candle(candle)"]
        update["Update 5-min candle stack"]
        agg15["Recompute 15-min candle\naggregate 3 × 5-min"]
        agg1h["Recompute 1-hour candle\naggregate 12 × 5-min"]
        bias["Compute intraday bias\nbias_15m + bias_1h"]
        range_det["_range_detector.check()\n→ RANGE_BREAKOUT / RANGE_BREAKDOWN"]
        cam_det["_cam_detector.check()\n→ CAM_* signals"]
    end

    subgraph checks["Signal Checks"]
        confluence{"Index bias\nconfluence?"}
        wl_check["Check watchlist_conflict\nweekly_bias vs signal direction"]
        levels["Compute trade levels\nentry / stop / target / trail_stop"]
        cluster{"Cluster filter\ncooldown?"}
    end

    emit["_on_signal(signal)"]

    subgraph publish["Publish"]
        redis_bc["PUBLISH signals"]
        redis_sym["PUBLISH signals:symbol"]
        redis_hist["LPUSH signals:history"]
        redis_day["LPUSH signals:daily:DATE"]
        ws["Broadcast SSE + WebSocket"]
    end

    candle --> update --> agg15 & agg1h --> bias
    bias --> range_det & cam_det
    range_det & cam_det --> confluence
    confluence -->|aligned| wl_check --> levels --> cluster
    confluence -->|counter-trend| suppress["downgrade score\nor suppress"]
    cluster -->|allowed| emit
    cluster -->|cooldown active| drop["drop signal"]
    emit --> redis_bc & redis_sym & redis_hist & redis_day --> ws
```

---

## Range Breakout Detection

```mermaid
flowchart TD
    lookback["Look back 12–20 candles\n(configurable)"]
    find["Find range_high = max(high)\nrange_low = min(low)"]
    pct["range_pct = (range_high - range_low) / range_low × 100"]
    consol{"range_pct ≤\nconsolidation_threshold\n(default ~3–5%)?"}
    no_signal["No consolidation\nSkip detection"]

    close_above{"close > range_high\nvol_ratio > 1.2?"}
    close_below{"close < range_low\nvol_ratio > 1.2?"}

    breakout["RANGE_BREAKOUT BULLISH\nentry_low = range_high\nentry_high = candle.close"]
    breakdown["RANGE_BREAKDOWN BEARISH\nentry_high = range_low\nentry_low = candle.close"]

    lookback --> find --> pct --> consol
    consol -->|no| no_signal
    consol -->|yes| close_above & close_below
    close_above -->|yes| breakout
    close_below -->|yes| breakdown
```

---

## Camarilla Signal Detection

### Pivot Level Calculation

```mermaid
flowchart LR
    prev["prev_day_close C\nprev_day_high H\nprev_day_low L"]
    range["r = H - L"]
    levels["H4 = C + 1.1/12 × r  ← breakout level
H3 = C + 1.1/6  × r  ← reversal level
L3 = C - 1.1/6  × r  ← reversal level
L4 = C - 1.1/12 × r  ← breakdown level"]
    tolerance["tolerance = cam_median_range_pct\n× prev_close × 0.2\n(adaptive per symbol volatility)"]

    prev --> range --> levels
    prev --> tolerance
```

### Signal Conditions

```mermaid
flowchart TD
    price["Current candle close/action"]

    above_H4{"close > H4\nvol confirmed?"}
    near_H4{"price near H4\n± tolerance?"}
    near_H3{"price near H3\n± tolerance?"}
    near_L3{"price near L3\n± tolerance?"}
    near_L4{"price near L4\n± tolerance?"}
    below_L4{"close < L4\nvol confirmed?"}

    bearish_candle{"Bearish candle pattern?\nclose < open or\npin bar upper shadow"}
    bullish_candle{"Bullish candle pattern?\nclose > open or\npin bar lower shadow"}

    H4_breakout["CAM_H4_BREAKOUT BULLISH"]
    H4_reversal["CAM_H4_REVERSAL BEARISH"]
    H3_reversal["CAM_H3_REVERSAL BEARISH"]
    L3_reversal["CAM_L3_REVERSAL BULLISH"]
    L4_reversal["CAM_L4_REVERSAL BULLISH"]
    L4_breakdown["CAM_L4_BREAKDOWN BEARISH"]

    price --> above_H4 -->|yes| H4_breakout
    price --> near_H4 --> bearish_candle -->|yes| H4_reversal
    price --> near_H3 --> bearish_candle
    bearish_candle -->|yes at H3| H3_reversal
    price --> near_L3 --> bullish_candle -->|yes at L3| L3_reversal
    price --> near_L4 --> bullish_candle -->|yes| L4_reversal
    price --> below_L4 -->|yes| L4_breakdown
```

---

## Index Bias Integration

```mermaid
flowchart TD
    ticks["Ticks from NIFTY\nBANKNIFTY · SENSEX"]
    candles["index_future_candles_5min\n(per index)"]
    direction["direction = BULLISH if close > open\nelse BEARISH"]
    tracker["IndexBiasTracker\nin-memory Dict[symbol → direction]"]
    vote["get_market_bias()\nmajority vote across 3 indices"]

    signal_dir{"signal.direction\nvs market_bias?"}
    confluence["Confluence ✓\nfull score"]
    counter["Counter-trend\nlower score or suppress\n(config: index_confluence_required)"]

    ticks --> candles --> direction --> tracker --> vote --> signal_dir
    signal_dir -->|aligned| confluence
    signal_dir -->|opposed| counter
```

---

## Cluster Filter (Deduplication)

```mermaid
flowchart TD
    signal["Signal detected\n(symbol, signal_type)"]
    key["key = (symbol, signal_type)"]
    seen{"key in _last_seen?"}
    elapsed{"elapsed > cooldown_seconds\n(default: 300s = 5 candles)?"}
    allow["Allow signal\nupdate _last_seen[key] = now"]
    suppress["Suppress signal\n(spam prevention)"]

    signal --> key --> seen
    seen -->|no| allow
    seen -->|yes| elapsed
    elapsed -->|yes| allow
    elapsed -->|no| suppress
```

---

## Trade Level Computation

```mermaid
flowchart LR
    atr["atr_14 from symbol_metrics"]

    subgraph bull["BULLISH signal"]
        b_entry_low["entry_low = candle.low"]
        b_entry_high["entry_high = candle.close"]
        b_stop["stop = entry_low - 1.0 × atr"]
        b_target["target_1 = entry_high + 2.0 × atr"]
        b_trail["trail_stop = entry_high - 0.5 × atr"]
    end

    subgraph bear["BEARISH signal"]
        s_entry_high["entry_high = candle.high"]
        s_entry_low["entry_low = candle.close"]
        s_stop["stop = entry_high + 1.0 × atr"]
        s_target["target_1 = entry_low - 2.0 × atr"]
        s_trail["trail_stop = entry_low + 0.5 × atr"]
    end

    atr --> bull
    atr --> bear
```

---

## Signal Score Factors

```mermaid
pie title signal.score (0–10) Composition
    "Volume ratio at signal" : 30
    "Index bias confluence" : 25
    "Candle body/range ratio" : 20
    "Distance from pivot/range" : 15
    "Time of day (EXECUTION phase bonus)" : 10
```

---

## Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Startup

    Startup --> Idle : pool connect\nRedis connect\nwarm-start candles\nload watchlist

    Idle --> Trading : 09:15 IST\nmarket open

    state Trading {
        [*] --> Subscribing
        Subscribing --> Receiving : Dhan WS connected
        Receiving --> Aggregating : tick arrives
        Aggregating --> Detecting : 5-min candle complete
        Detecting --> Publishing : signal detected
        Publishing --> Receiving
        Aggregating --> Receiving : no signal
    }

    Trading --> AfterHours : 15:30 IST\nSessionManager blocks new ticks

    AfterHours --> Reset : midnight IST
    Reset --> Idle : clear bias state\nreset candle stacks\nclear cluster filter\nreload watchlist from service_config
```

---

## Watchlist Subscription Lifecycle

```mermaid
sequenceDiagram
    participant RS as RankingService
    participant DB as TimescaleDB service_config
    participant LF as LiveFeedService
    participant DW as Dhan WebSocket

    Note over RS,DB: After scoring run
    RS->>DB: UPSERT service_config\n(ranking, watchlist, [...symbols])

    Note over LF,DW: On startup or scheduled refresh
    LF->>DB: SELECT value FROM service_config\nWHERE service='ranking' AND key='watchlist'
    DB-->>LF: {symbols: ["RELIANCE", "TCS", ...]}

    loop for each new symbol
        LF->>LF: create SignalEngine(symbol)
        LF->>LF: load metrics from MetricsService
    end

    LF->>DW: subscribe(watchlist + INDEX_FUTURES)
    Note over LF,DW: Delta subscription — no reconnect needed
```

---

## Redis Signal Payload

Full JSON structure of a published signal:

```json
{
  "id": "3f8a1bc2-...",
  "symbol": "RELIANCE",
  "signal_type": "RANGE_BREAKOUT",
  "direction": "BULLISH",
  "price": 1423.50,
  "volume_ratio": 2.34,
  "score": 7.8,
  "timestamp": "2026-04-26T06:45:00Z",
  "message": "Range breakout above 1418.00 with 2.3× volume",
  "bias_15m": "BULLISH",
  "bias_1h": "BULLISH",
  "entry_low": 1418.00,
  "entry_high": 1423.50,
  "stop": 1402.30,
  "target_1": 1455.70,
  "trail_stop": 1415.25,
  "watchlist_conflict": false
}
```
