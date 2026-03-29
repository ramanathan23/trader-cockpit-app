# Trader Cockpit — Business Document Index

> Primary broker: **Dhan (DhanHQ v2)**. Market: India NSE/BSE.
> Decision-first cockpit. Zero context switching.

---

## Documents

| # | Document | What It Covers |
|---|----------|---------------|
| 01 | [Overview & Vision](01-overview.md) | Problem, solution, differentiators, scope |
| 02 | [Equity Trading Workflow](02-equity-workflow.md) | EOD scan → intraday → INTRADAY/CNC conversion → swing → pyramid |
| 03 | [Signal Quality Engine](03-signal-engine.md) | Scoring, two timeframes, candle alignment, confluence zones |
| 04 | [Risk Management](04-risk-management.md) | SL philosophy (tight vs wide), sizing, limits, pre-trade overlay |
| 05 | [Options Trading](05-options-trading.md) | Strategies, baskets, LSL/CSL engine, Dhan gaps |
| 06 | [Cockpit UX & Layout](06-cockpit-ux.md) | Zones, adaptive behaviour, portfolio views, keyboard |
| 07 | [Dhan Broker Integration](07-dhan-integration.md) | Dhan API specifics, gaps, workarounds, constraints |
| 08 | [Data Architecture](08-data-architecture.md) | Streaming, candle aggregation, storage, Dhan limits |
| 09 | [Roadmap & Metrics](09-roadmap.md) | Phased build plan, success metrics |

---

## Dhan API — Terminology Map

| Our Term | Dhan Term | Notes |
|----------|----------|-------|
| MIS / Intraday | `INTRADAY` | Auto square-off 3:20 PM |
| Delivery / Swing equity | `CNC` | Cash & Carry, no leverage |
| F&O carry-forward | `MARGIN` | Options/futures overnight |
| MIS→NRML convert | `POST /positions/convert` | Programmatic, supported |
| Stop loss order | `SL` or `SL-M` order type | Placed at exchange |
| Target + stop together | Forever Order (OCO) | One-cancels-other |
| Entry + SL + target | Super Order | Single leg only |

---

## Critical Dhan Constraints

| Constraint | Impact |
|-----------|--------|
| No basket/multi-leg orders | Options legs placed individually; coordination is our responsibility |
| No F&O conditional triggers | No Dhan-side automation for options; cockpit signals only |
| No real-time position WebSocket | Poll `GET /positions` every 3–5s; order WS triggers refresh |
| Binary WebSocket market feed | Custom binary parser required |
| Option chain: 1 req/3s | Cache Greeks; refresh every 30s per underlying |
| Available candle timeframes | 1min, 5min, 15min, 25min, 60min, 1D only |
| Static IP mandatory for orders | Fixed IP deployment; no dynamic cloud IPs |
| 24-hour token validity | Daily renewal job required before expiry |
| 90-day max per historical call | Paginate to build multi-year candle history |
| 5,000 orders/day cap | CSL flatten + LSL stops count toward this |
| No historical Greeks | Options backtesting limited |

---

## The SL Philosophy — Core Sizing Principle

```
INTRADAY (Dhan: INTRADAY product)
  SL = MINIMUM viable — tightest technical level (swing low, ATR-based)
  Small SL → many shares within risk budget
  INTRADAY margin (~5x) makes large quantity affordable
  ₹10,000 risk ÷ ₹15 SL = 666 shares → ~₹19,000 margin needed

SWING (Dhan: CNC product)
  SL = MAXIMUM viable — widest key level (support/resistance zone)
  Large SL → few shares within same risk budget
  No leverage on CNC delivery (full capital required)
  ₹10,000 risk ÷ ₹50 SL = 200 shares → ₹5,80,000 capital needed

CONVERSION MATH (same stock, same ₹10k risk budget):
  Held intraday:    666 shares (₹19k margin, leveraged)
  Can convert:      200 shares (₹5.8L capital, no leverage)
  Must close:       466 shares before 3:20 PM
```

Conversion ALWAYS results in holding far fewer shares than the intraday position. This is not a preference — it is a structural consequence of leverage.

---

## Daily Session Checklist

```
Before 9:10 AM   [ ] System running, token valid
                 [ ] Data WebSocket connected (green indicator)
                 [ ] EOD watchlist loaded (from previous evening)
                 [ ] Overnight gaps reviewed

9:15 AM          [ ] Market open — candle streaming begins
                 [ ] Partial candle check (if late start)

9:15–3:00 PM     [ ] Monitor intraday signals on watchlist
                 [ ] Options entry at time gate (if configured)

2:45 PM          [ ] Conversion panel available (early review)
3:00 PM          [ ] Conversion panel prominent — finalize decisions
3:10 PM          [ ] Urgent: 10 min to auto square-off

After 3:30 PM    [ ] EOD scan runs automatically
                 [ ] Review new watchlist
                 [ ] Schedule token renewal
```
