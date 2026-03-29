# 08 — Data Architecture

How data flows from Dhan's feed to the cockpit. Storage, streaming, candle aggregation, and Dhan-specific constraints.

---

## Data Flow Overview

```
DHAN WEBSOCKET (binary)
    │
    ▼
BINARY PARSER (broker adapter layer)
  → Normalized tick: { symbol, price, volume, timestamp, bid, ask }
    │
    ├─────────────────────────────────────────┐
    │                                         │
    ▼                                         ▼
CANDLE AGGREGATOR                       QUOTE CACHE (Redis)
  • Market-hour anchored boundaries       • Latest quote per symbol
  • 5/15/25/60min intervals               • Sub-ms read for risk bar
  • Partial candle detection              • 5s TTL (auto-stale)
  • Emit on candle close                  • Positions P&L calc
  • Store to TimescaleDB
    │
    ▼
SIGNAL ENGINE
  • Score on completed candle
  • Watchlist stocks only
  • Multi-factor scoring
    │
    ▼
EVENT BUS (internal)
  • Signal events
  • Alert events
  • CSL breach events
    │
    ▼
API / WEBSOCKET TO FRONTEND
  • REST for queries
  • WebSocket for live updates
```

---

## Dhan WebSocket — Binary Feed

Dhan's market feed WebSocket sends responses in **binary format**. This requires a custom parser in the broker adapter.

### Binary Packet Structure (Dhan v2)

Dhan publishes the binary packet spec in their docs. The parser:
1. Reads the packet header (feed type, instrument token)
2. Decodes fields based on packet type (Ticker/Quote/Full)
3. Converts to our domain Tick model

The Python SDK (`dhanhq`) includes a WebSocket handler but the parsing logic must be verified against the live binary format — the SDK may not expose raw tick granularity.

### Subscription Strategy

| Instrument Type | Packet Mode | Notes |
|----------------|------------|-------|
| Watchlist stocks (up to 50) | Quote | LTP + OI + bid/ask — sufficient for candle building |
| Index instruments (Nifty, BankNifty, VIX) | Quote | Context panel + market context factor |
| Options legs (active strategies) | Quote | For Greeks estimation (bid-ask) and P&L |
| 20-level depth (key stocks) | Full | Optional — for order book widget |

Up to 5,000 instruments per WebSocket connection, 5 connections available. Ample for typical watchlist size.

---

## Candle Aggregation — Market-Hour Alignment

### The Rule

All candle intervals anchor to 9:15 AM NSE market open. Not clock time.

```
25min: 9:15, 9:40, 10:05, 10:30, 10:55, 11:20 ...
15min: 9:15, 9:30, 9:45, 10:00, 10:15 ...
5min:  9:15, 9:20, 9:25, 9:30, 9:35 ...
60min: 9:15, 10:15, 11:15, 12:15, 1:15, 2:15 ...
```

The 60min candle closes at 10:15, not 10:00. The last candle of the day (3:15–3:30 or similar) is a partial — marked as such but included (it contains closing auction data).

### Partial Candle Policy

| State | Detection | Action |
|-------|-----------|--------|
| System starts before 9:10 | All candles complete | Normal operation |
| System starts between 9:15 and next boundary | First candle partial | Discard for signals; show greyed on chart |
| Any candle after system start | Complete | Normal signals |
| Last candle of day (after 3:15) | Usually partial | Show on chart; mark as closing candle; no next-day signals |

### Live Candle → TimescaleDB

```
On tick received:
  1. Find active candle bucket for this symbol + interval
  2. Update OHLCV in Redis (live candle store)
  3. On boundary time:
     a. Emit CANDLE_CLOSE event to signal engine
     b. Write completed candle to TimescaleDB
     c. Start new bucket in Redis
```

---

## Historical Data — Dhan Constraints

### Available Timeframes

| Timeframe | Available | Depth | Per-Call Limit |
|-----------|----------|-------|---------------|
| 1min | Yes | 5 years | 90 days |
| 5min | Yes | 5 years | 90 days |
| 15min | Yes | 5 years | 90 days |
| 25min | Yes | 5 years | 90 days |
| 60min | Yes | 5 years | 90 days |
| Daily | Yes | Inception | 90 days |

**10min and 30min**: NOT available. Do not attempt to build these.

### Initial Load Strategy

For a fresh install, fetching 5 years of 5min data for 100 symbols:
- 5 years = 60 months = 20 calls per symbol (90-day chunks, ~18 chunks per year)
- 100 symbols × 18 chunks = 1,800 API calls
- No rate limit on minute/hourly data (as per Dhan docs)
- Run as background job during setup; store to TimescaleDB
- Subsequent days: incremental update (fetch last trading day's data)

### EOD Scan Data Pipeline

```
After 3:30 PM (run at 4:00 PM):
1. Fetch today's 60min + 1D candles for all watchlist stocks
   (Dhan historical API — day's data available after 3:30 PM)
2. Update TimescaleDB with today's candles
3. Run signal scoring engine (reads from TimescaleDB)
4. Write new watchlist to PostgreSQL
5. Notify cockpit: new watchlist ready for tomorrow
```

---

## Option Chain Data Pipeline

Source: Dhan option chain API. Rate: 1 req/3s.

### Caching Strategy

```
Per underlying instrument (e.g. NIFTY, BANKNIFTY, RELIANCE):
  Poll every 30 seconds
  Store in Redis with 35s TTL (5s buffer)

For multiple underlyings (stagger requests):
  t=0:   fetch NIFTY chain
  t=3:   fetch BANKNIFTY chain
  t=6:   fetch RELIANCE chain
  t=9:   (if more: fetch next)
  t=30:  repeat cycle
```

Greeks sourced from option chain response (Delta, Theta, Gamma, Vega, IV). Updated every 30s.

**Limitation**: 30s lag means delta monitoring is not real-time. For near-threshold positions (e.g. delta at 0.45 near 0.50 threshold), the cockpit alerts conservatively — warn at 0.45, not only at 0.50.

---

## Storage Architecture

### Redis (Real-Time Layer)

| Key Pattern | Content | TTL |
|-------------|---------|-----|
| `quote:{symbol}` | Latest tick from WebSocket | 5s |
| `candle:live:{symbol}:{interval}` | Current candle being built | Until boundary |
| `option_chain:{underlying}:{expiry}` | Full chain snapshot | 35s |
| `risk:session:{user}` | Daily INTRA loss consumed | Until market close |
| `csl:monitor:{strategy_id}` | Running P&L for CSL check | Until strategy closed |
| `order:state:{strategy_id}` | Leg placement state machine | Until strategy active |
| `token:dhan:{user}` | Current Dhan access token | 23hr (renewed before expiry) |

### TimescaleDB (Time-Series Layer)

| Table | Partitioning | Retention |
|-------|-------------|-----------|
| `candles_5min` | By day | 5 years |
| `candles_15min` | By day | 5 years |
| `candles_25min` | By day | 5 years |
| `candles_60min` | By month | 5 years |
| `candles_1day` | By year | 10 years |
| `option_chain_snapshots` | By day | 90 days |

### PostgreSQL (Business Layer)

| Table | Purpose |
|-------|---------|
| `watchlist` | Daily EOD scan results, versioned by date |
| `orders` | All placed orders with Dhan order IDs, audit trail |
| `positions` | Position snapshots (from polls), current + historical |
| `strategies` | Options strategies, leg details, LSL/CSL config |
| `baskets` | Basket configuration |
| `conversions` | INTRADAY→CNC conversion history |
| `trade_journal` | Closed trade history, P&L, tags |
| `signals` | Historical signal log per candle close |
| `user_settings` | Risk %, limits, layout, token config |

---

## Data Freshness Indicators

Shown in cockpit for each feed:

| Indicator | Meaning |
|-----------|---------|
| ● green | Live — data < 5s old |
| ● amber | Delayed — data 5-30s old |
| ● red | Stale — data > 30s or WebSocket disconnected |
| ✗ | Feed offline |

Token expiry warning shown 2 hours before expiry.
