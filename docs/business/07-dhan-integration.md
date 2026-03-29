# 07 — Dhan Broker Integration

Dhan (DhanHQ v2) API specifics, constraints, workarounds, and integration patterns.

---

## Why Dhan

- India's fastest-growing discount broker with a documented, versioned REST + WebSocket API
- Python SDK (`dhanhq`) officially maintained
- Supports all required product types: INTRADAY, CNC, MARGIN
- Programmatic position conversion (INTRADAY → CNC) supported
- Super Orders, Forever Orders (OCO), P&L Exit, Exit All — useful safety tools
- Sandbox environment for testing without real capital or KYC
- Option chain with Greeks available (limited rate)

---

## Authentication

| Type | Method | Validity |
|------|--------|----------|
| Direct Token | web.dhan.co → My Profile | 24 hours |
| OAuth flow | API key + secret → browser + 2FA → token | 24 hours |
| Token renewal | POST /v2/RenewToken | Extends 24 hours |

**Critical**: Token MUST be renewed before expiry. Expired tokens cannot be renewed — require full re-auth.

### Daily Renewal Strategy

- Scheduled job: 9:00 PM daily (well before 24hr expiry of morning token)
- Job: POST /v2/RenewToken with valid current token
- If renewal fails (network error): retry 3x, then alert operator
- If token expires during market hours: operator alert immediately; manual re-auth required
- Store token encrypted at rest; inject at runtime

---

## Static IP Requirement

SEBI mandate enforced by Dhan: order placement, modification, and cancellation APIs require whitelisted static IP.

**Implication**: The server component placing orders must run on a fixed IP address.

**Deployment constraint**:
- Cloud VM with static IP (AWS Elastic IP, GCP static IP, etc.)
- Or VPS with fixed IP
- IP change allowed only once per 7 days — plan any migration carefully
- Development: use a fixed VPN endpoint or a small cloud instance for order testing

---

## Product Types

| Our Term | Dhan API Value | Exchange Segments |
|----------|---------------|------------------|
| Intraday equity | `INTRADAY` | NSE_EQ, BSE_EQ |
| Delivery equity | `CNC` | NSE_EQ, BSE_EQ |
| F&O carry-forward | `MARGIN` | NSE_FNO, BSE_FNO |
| Intraday F&O | `INTRADAY` | NSE_FNO, BSE_FNO |
| Leveraged delivery | `MTF` | NSE_EQ, BSE_EQ |
| Cover / Bracket | `CO/BO` | Intraday only |

---

## Market Data

### WebSocket (Live Feed)
- Up to 5 connections per user
- Subscribe up to 5,000 instruments per connection
- Three packet modes: Ticker (LTP only), Quote (LTP+OI+bid/ask), Full (Quote + depth)
- **Binary format — custom parser required**
- Server pings every 10s; client must respond to keep alive
- Order update WebSocket is separate (JSON — easier to parse)

### Historical OHLCV
- Available timeframes: **1min, 5min, 15min, 25min, 60min, Daily**
- Intraday depth: last 5 years
- Daily depth: from stock inception
- Max 90 days per API call (paginate for longer periods)
- No rate limit for minute/hourly data
- Data includes OI (open interest) for F&O instruments

### Option Chain
- Full chain: all strikes, all expiries for any underlying
- Fields: LTP, OI, Volume, IV, Delta, Theta, Gamma, Vega, bid/ask
- Rate limit: **1 request per 3 seconds**
- Strategy: cache per underlying. For each active basket underlying, poll every 30s on a staggered schedule

### Historical Expired Options
- OHLCV, IV, OI for expired contracts
- Useful for backtesting entry/exit timing
- Not useful for Greeks backtesting (Greeks not in historical)

---

## Order Management

### Order Types Used in This App

| Purpose | Dhan Order Type | Notes |
|---------|----------------|-------|
| Intraday equity entry | LIMIT order, INTRADAY | Super Order preferred |
| Intraday SL | SL-M (Stop Loss Market) | Market fill ensures execution |
| Swing entry | LIMIT order, CNC | |
| Swing SL | SL-M, CNC | |
| Options leg entry | LIMIT order, MARGIN | |
| Options LSL | SL-M, MARGIN | Market stop for options |
| Options target + SL | Forever Order OCO | Single leg; one-cancels-other |
| Entry + SL + target | Super Order | Single leg equity/options |
| Emergency exit | MARKET order | Used for CSL flatten |

### Order Rate Limits
- 10 orders/second (regulatory cap per SEBI)
- 5,000 orders/day
- For CSL: flatten 4-leg strategy = 4 MARKET orders + 2 SL cancels = 6 order actions
- Budget: track daily order count; warn at 80% of limit

### Multi-Leg Options — Sequential Placement Protocol

Since Dhan has no basket order, we place each leg individually:

```
FOR each leg in strategy.legs:
  1. Place order via Dhan API
  2. Wait for order confirmation (via order update WebSocket)
  3. On TRADED status: proceed to next leg
  4. On REJECTED: alert trader, pause remaining legs
  5. After all legs placed: place LSL orders for each sell leg
  6. Track all order IDs in strategy state

FAILURE HANDLING:
  - If any leg fails: strategy enters PARTIAL_ENTRY state
  - Cockpit shows which legs are placed and which failed
  - Trader chooses: complete the strategy or cancel placed legs
  - Cancellation reverses legs in reverse order
```

---

## Position Management

### Polling Strategy
- No real-time position WebSocket from Dhan
- Poll `GET /positions` every 3-5 seconds
- Order update WebSocket → triggers immediate position poll on fill
- Net effect: position awareness with < 5s lag

### Position Conversion (INTRADAY → CNC)

```
POST /positions/convert

Body:
{
  "dhanClientId": "...",
  "fromProductType": "INTRADAY",
  "toProductType": "CNC",
  "exchangeSegment": "NSE_EQ",
  "positionType": "LONG",
  "securityId": "1333",
  "convertQty": 140,
  "tradingSymbol": "RELIANCE"
}
```

After successful conversion:
1. `GET /positions` → verify converted position appears in CNC book
2. Cancel old INTRADAY SL order (if standing)
3. Place new CNC SL order at swing SL price

Error handling: retry 3x. If failing at 3:10 PM, alert trader for manual action.

---

## Safety APIs

### P&L Exit (Global Kill Switch)
```
POST /pnlExit
{
  "dhanClientId": "...",
  "maxProfit": 50000,    // auto close all if daily profit hits ₹50k
  "maxLoss": -5000,      // auto close all if daily loss hits -₹5k
  "productType": "INTRADAY"  // or CNC or ALL
}
```
Set this at market open each day. Acts as a second-layer CSL for intraday positions.

### Exit All
```
DELETE /positions
```
Closes ALL open positions and cancels ALL pending orders. Use as last resort only. Counts toward 5k order limit.

### Kill Switch
```
POST /killswitch
{ "killSwitchStatus": "ACTIVATE" }
```
Requires all positions to be closed first. Disables all trading for the session.

---

## Sandbox Environment

- URL: sandbox.dhan.co
- No KYC, no real money
- Same API structure as live
- Limitations: market orders not supported in sandbox (use LIMIT orders for testing)
- Derivatives lot sizes still apply
- Recommended for: integration testing, order flow testing, UI testing

---

## Known Gaps and Workarounds

| Gap | Our Workaround |
|-----|---------------|
| No basket orders | Sequential individual leg placement with state machine |
| No F&O conditional triggers | App-level signal engine triggers entries |
| No real-time position WS | Poll every 3-5s; order WS triggers immediate refresh |
| Option chain 1 req/3s | 30s cache per underlying; stagger requests across underlyings |
| Binary WebSocket | Custom parser in broker adapter layer |
| No historical Greeks | Cannot backtest delta/theta behaviour; use entry rules only |
| No 10min/30min candles | Only offer 5min, 15min, 25min, 60min, 1D in UI |
| 24hr token | Scheduled renewal job at 9 PM daily |
| Static IP | Fixed IP cloud deployment; no dynamic IPs |
| Partial options entry | State machine tracks each leg; alert on partial; trader decides |
