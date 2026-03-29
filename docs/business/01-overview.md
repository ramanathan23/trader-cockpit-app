# 01 — Overview & Vision

---

## The Problem

Traders lose edge not because they lack knowledge — but because the tools force them to context-switch at the worst possible moment.

**What a trader must do today for one trade decision:**

| Step | Tool / Location | Time Pressure |
|------|----------------|--------------|
| Identify setup | Charting tool | None |
| Check signal quality | Manual judgment or another tool | None |
| Calculate position size | Spreadsheet or mental math | None |
| Check sector/index context | Another browser tab | None |
| Check own history on the symbol | Trade journal (if maintained) | None |
| Place order | Broker platform | Moderate |
| EOD: decide MIS → CNC conversion | Mental calculation under time pressure | HIGH — 3:20 PM deadline |
| EOD: calculate swing position size | Mental math (different risk %, different SL) | HIGH |

The EOD conversion decision is particularly brutal: the trader has minutes to decide whether to hold a position overnight, calculate a different risk-appropriate size, update the stop loss, and execute the conversion — all while managing other open positions.

**The result**: traders either skip conversions (miss swing opportunities built from intraday entries), convert the full intraday position (over-sized for swing risk), or make hasty decisions they later regret.

---

## The Solution

A single cockpit where:
1. **Signal quality is scored and displayed** — not subjectively judged
2. **Position sizing is auto-calculated** — for both INTRADAY and CNC modes
3. **Conversion sizing is pre-calculated** — by 2:45 PM, before time pressure peaks
4. **Risk impact is shown before every order** — not discovered after

The cockpit eliminates the cognitive load of information assembly. The trader focuses on judgment calls only.

### Core Principle

> Organize around the trade decision workflow, not around features.

```
EOD scan → Signal → Size → Risk check → Execute → [Convert or Close]
```

---

## Target Users

| Profile | Need | How Cockpit Serves |
|---------|------|-------------------|
| Intraday trader | Fast signals, clean execution, tight risk | Streaming candles, auto sizing, keyboard-first |
| Swing trader | Quality setups, EOD watchlist, multi-day management | EOD scan, conversion assistant, pyramid tracking |
| **Primary user: both** | Intraday entries that become swing positions | Unified cockpit, mode-aware sizing, seamless conversion |

---

## Key Differentiators

### 1. Conversion-First Design
Most platforms treat MIS and delivery as separate products. This cockpit treats them as a **continuous workflow** — intraday entry → evaluated for swing potential → converted with correct sizing automatically calculated.

### 2. SL-Driven Position Sizing
The cockpit enforces the core principle: **tight SL for intraday (many shares), wide SL for swing (few shares)**. The same ₹ risk budget produces radically different quantities depending on mode. This is auto-calculated — no mental math.

### 3. Decision at Point of Action
Signal score, position size, risk impact, and market context are all visible when the order is initiated — not on a separate screen.

### 4. Dhan-Native
Built specifically for Dhan's API v2. Uses Dhan's Super Orders, Forever Orders (OCO), P&L Exit, and position conversion natively. No generic broker abstractions that don't map cleanly.

---

## Scope — What This Is

- Technical and price/volume based trading tool
- India NSE/BSE markets (Dhan API)
- Equity intraday (INTRADAY) + delivery swing (CNC) + F&O options (MARGIN)
- Manual execution — cockpit assists decisions, human places orders

## Scope — What This Is NOT

| Not This | Why |
|----------|-----|
| Algo / automated execution | All orders require explicit human confirmation |
| Fundamental analysis tool | No earnings, valuations, or news aggregation |
| Screener | Signals only for pre-loaded watchlist stocks |
| Backtester | Shows your own trade history only |
| Social/copy trading | Single-user, private |
| Multi-broker | Dhan only (v1). Broker abstraction layer for future expansion |

---

## Dhan Platform Constraints That Shape Design

These are non-negotiable constraints from the broker API:

**No basket orders**: Options strategy legs must be placed as individual orders. Our LSL/CSL engine coordinates them — Dhan does not.

**No real-time position WebSocket**: Positions polled every 3-5 seconds. Order fill WebSocket triggers the poll. There is an inherent ~5s lag in position awareness.

**Available candle timeframes**: 1min, 5min, 15min, 25min, 60min, 1D. The cockpit UI exposes exactly these — no invented timeframes.

**Static IP required**: Order APIs require a whitelisted static IP. Deployment must use a fixed IP cloud instance or VPS.

**Token validity**: 24 hours. A scheduled job renews the token daily. Expired tokens cannot be renewed — must re-authenticate. This is a critical operational risk.

**Option chain rate limit**: 1 request per 3 seconds. Greeks are cached and refreshed at 30-second intervals, not real-time.

**5,000 orders/day cap**: A strategy with 4 legs + 4 LSL stop orders = 8 orders at entry alone. With 10 strategies/day = 80 orders. Flatten emergencies (CSL) add more. Budget carefully.
