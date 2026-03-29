# 09 — Roadmap & Success Metrics

Phased build plan and measurement criteria. Each phase produces a fully usable product before the next begins.

---

## Build Principles

1. **Phase 1 must be usable as a daily trading tool** before Phase 2 starts
2. **Dhan constraints are first-class requirements**, not afterthoughts
3. **Test in sandbox first** — every order flow validated in Dhan sandbox before live capital
4. **No invented candle timeframes** — match Dhan's available intervals exactly
5. **Static IP from day one** — deployment configured with fixed IP before any live order testing

---

## Phase 1 — Equity Cockpit (Foundation)

**Goal**: Full equity workflow from EOD scan to intraday trading to INTRADAY→CNC conversion. Usable daily.

### Data Layer
- [ ] Dhan WebSocket connection with binary parser (market feed)
- [ ] Order update WebSocket handler (JSON)
- [ ] Position polling service (GET /positions every 3-5s)
- [ ] Historical data fetcher with 90-day pagination
- [ ] Candle aggregator: market-hour aligned, 5/15/25/60min
- [ ] Partial candle detection and handling
- [ ] TimescaleDB schema: candles_5min through candles_1day
- [ ] Redis: quote cache, live candle store, session risk state
- [ ] PostgreSQL: watchlist, orders, positions, trade journal, settings
- [ ] Daily token renewal job (scheduled at 9 PM)
- [ ] Initial historical data load job (5 years for tracked symbols)

### Signal Engine
- [ ] EOD swing scan: 5-factor scoring on 1D + 60min data
- [ ] Per-factor minimum enforcement (not just total score)
- [ ] Bull/bear candidate classification
- [ ] Key level identification (support, resistance, target)
- [ ] Intraday signal generation on completed candles (watchlist stocks only)
- [ ] Time-of-day volume normalization for intraday volume factor
- [ ] ATR floor check for SL placement
- [ ] Confluence zone calculation
- [ ] Watchlist staleness check (gap check at 9:15 AM)

### Risk Engine
- [ ] INTRADAY risk parameters: risk %, daily loss limit, max positions
- [ ] CNC risk parameters: risk %, max positions
- [ ] Auto position sizing: separate formulas for INTRADAY (tight SL, high qty) and CNC (wide SL, low qty)
- [ ] Daily loss limit tracking and enforcement (amber/orange/red states)
- [ ] Pre-trade overlay: INTRADAY and CNC versions
- [ ] ATR minimum SL validation
- [ ] Dhan P&L Exit API setup at market open (daily loss threshold)
- [ ] SL placed as exchange SL-M order on entry (or via Super Order)

### Conversion Engine
- [ ] Conversion candidate identification at 2:45 PM
- [ ] Swing risk-based conversion sizing (CNC qty << INTRADAY qty)
- [ ] Conversion panel UI with full breakdown
- [ ] POST /positions/convert API integration with retry logic
- [ ] Post-conversion: cancel old INTRADAY SL, place new CNC SL
- [ ] Conversion failure handling and manual fallback instruction
- [ ] Conversion history logging

### Cockpit UI
- [ ] Layout shell: all 5 zones (risk bar, signal panel, canvas, context panel, positions strip)
- [ ] Chart canvas: candlestick + volume + confluence zones
- [ ] Candle interval selector: 5min, 15min, 25min, 60min, 1D only
- [ ] Watchlist panel: scores, direction, key levels, staleness flags
- [ ] Signal panel: score breakdown with per-factor display, mode toggle (INTRADAY/CNC), auto sizing
- [ ] Market context panel: index, sector, peers, your history on symbol
- [ ] Positions strip: INTRADAY and CNC separated, live P&L
- [ ] EOD conversion panel (surfaces at 2:45 PM, urgent at 3:10 PM)
- [ ] Pre-trade overlay for equity (both modes)
- [ ] Pre-market readiness indicator (green before 9:10 AM)
- [ ] Data freshness indicators per feed
- [ ] Keyboard shortcuts (full set)
- [ ] Token expiry warning (2 hours before expiry)

### Trade Journal
- [ ] Auto-log every order: entry price, qty, SL, target, product type
- [ ] Auto-log exits: exit price, P&L
- [ ] Log conversions: INTRADAY qty → CNC qty, reason
- [ ] Per-symbol history view: win/loss, avg R:R
- [ ] Conversion outcome tracking

---

## Phase 2 — Options Layer

**Goal**: Full options workflow with Dhan-constrained execution. LSL/CSL safety engine live.

### Options Data
- [ ] Option chain polling service (staggered, 30s per underlying, 1 req/3s rate)
- [ ] Greeks cache in Redis (35s TTL)
- [ ] Delta monitoring service (from cached Greeks)
- [ ] Historical expired options data (for pattern reference)

### Strategy Execution Engine
- [ ] Sequential leg placement state machine
- [ ] Partial entry detection and alerting
- [ ] Per-leg order ID tracking
- [ ] LSL order placement (SL-M for sell legs, immediately after entry)
- [ ] Auto-LSL calculation and placement (when LSL not configured)
- [ ] CSL internal monitor (from polled positions)
- [ ] CSL breach action: sequential market close orders + cancel pending LSL orders
- [ ] Forever Order (OCO) for entry + SL + target on single-leg strategies
- [ ] Super Order usage for simpler strategies

### Strategy Builder
- [ ] Strategy type selector with environment suggestion
- [ ] Live payoff diagram (ECharts, updates with market)
- [ ] Order budget impact display (orders this strategy consumes)
- [ ] All supported strategy types

### Basket Management
- [ ] Basket configuration CRUD
- [ ] Time gate enforcement
- [ ] Basket P&L aggregation
- [ ] Portfolio Greeks view (from cached option chain)
- [ ] Multiple baskets with independent CSL limits

### Active Strategies Strip
- [ ] DTE tracking and milestone alerts
- [ ] Profit target alerts (% of max credit)
- [ ] Delta breach alert (warn at threshold-0.05, alert at threshold)
- [ ] Inline action buttons (close, roll, hedge)
- [ ] CSL status indicator per strategy

---

## Phase 3 — Portfolio Analytics

**Goal**: Full capital view and performance analytics to improve strategy over time.

- [ ] Portfolio canvas: CNC positions treemap by sector
- [ ] Capital allocation view: INTRADAY / CNC / Options / Cash
- [ ] Performance metrics: win rate by signal grade (A/B/C), R:R achieved vs planned
- [ ] Conversion analytics: INTRADAY→CNC trade performance vs direct CNC entries
- [ ] Pyramid performance: do adds improve or hurt P&L?
- [ ] Options analytics: theta earned per ₹ margin, win rate by strategy type
- [ ] Daily P&L history chart

---

## Phase 4 — Hardening & Expansion

- [ ] Second broker adapter (Zerodha or Upstox) — validate broker abstraction layer
- [ ] Alert delivery: Telegram bot, push notifications
- [ ] Multi-device: same state across desktop and mobile view
- [ ] Performance: profile and optimize for low-latency rendering
- [ ] Monitoring: Dhan API health, WebSocket reconnect metrics, order fill rates

---

## Success Metrics

### Operational Reliability
| Metric | Target |
|--------|--------|
| Dhan WebSocket uptime during market hours | > 99% |
| Position poll lag | < 5s average |
| Token renewal success rate | 100% |
| Candle completeness (no missed candles) | > 99.9% |
| CSL breach to flatten complete | < 10 seconds |

### Trading Workflow
| Metric | Target / Measures |
|--------|------------------|
| Signal to order placed | < 10s (cockpit removes friction) |
| INTRADAY→CNC conversion rate | % of profitable INTRA positions converted |
| INTRA auto square-off rate | % closed by Dhan (not trader) — lower = better |
| Conversion sizing accuracy | CNC qty within 5% of optimal (risk budget math) |
| Daily loss limit adherence | Zero breaches via cockpit |

### Signal Quality
| Metric | What It Measures |
|--------|-----------------|
| Win rate by grade (A / B / C) | Does a higher score actually mean a better trade? |
| R:R achieved vs planned | Are targets realistic? |
| Conversion win rate vs direct CNC | Does INTRA entry improve CNC entry quality? |
| Volume-normalized signal performance | Is time-of-day normalization improving signal accuracy? |

### Options Safety
| Metric | What It Measures |
|--------|-----------------|
| Partial entry rate | How often does sequential leg placement fail mid-strategy? |
| CSL trigger rate | Are strategies sized correctly? |
| LSL vs CSL trigger frequency | Is CSL catching combined drift before individual legs hit LSL? |
| Orphaned LSL order rate | Are we successfully cancelling LSL orders after CSL flatten? |

---

## What "Done" Looks Like Per Phase

### Phase 1 Complete
Trader can:
1. Review EOD watchlist each morning
2. Monitor intraday signals on watchlist stocks
3. Place INTRADAY order with auto-calculated tight SL and large qty
4. At 2:45 PM: see conversion panel showing eligible positions with CNC sizing already calculated
5. Confirm conversion — cockpit places CNC order, closes excess INTRADAY, updates SL
6. End day with full trade journal entry, no manual logging

### Phase 2 Complete
Trader can additionally:
1. Build any supported options strategy in cockpit
2. Have LSL exchange orders placed atomically with strategy entry
3. Monitor delta and P&L in active strategies strip
4. CSL fires within 10s of breach — all legs closed, LSL orders cancelled

### Phase 3 Complete
Trader can additionally:
1. See full capital utilization at a glance
2. Review conversion effectiveness (were INTRA→CNC trades better than direct CNC?)
3. See options theta earned vs risk deployed over time
