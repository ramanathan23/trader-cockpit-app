# 05 — Options Trading

Full options workflow accounting for Dhan API constraints. Strategies, baskets, LSL/CSL engine, delta rules, time gates.

---

## Dhan-Specific Constraints on Options

Before designing, acknowledge what Dhan cannot do:

| Capability | Dhan Support | Design Impact |
|-----------|-------------|--------------|
| Multi-leg basket order | ❌ Not available | Each leg placed as individual order |
| F&O conditional triggers | ❌ Equities only | No automated options entry via Dhan triggers |
| Real-time position WebSocket | ❌ Not available | Poll positions every 3-5s; order WS triggers refresh |
| Option chain Greeks | ✅ Available | Delta, Theta, Gamma, Vega, IV in chain response |
| Historical Greeks | ❌ Not available | Cannot backtest Greeks behaviour |
| Option chain rate | ⚠️ 1 req/3s | Cache per underlying; max refresh every 30s |
| Super Order for options | ✅ Single leg | Use for single-leg entries with built-in SL |
| Forever Order (OCO) | ✅ Single leg | Use for SL + target on individual legs |
| Position conversion | ✅ INTRADAY→MARGIN | F&O positions can be made carry-forward |

---

## Devil's Advocate Checks

| Assumption | Challenge | Mitigation |
|-----------|-----------|-----------|
| LSL placed at exchange will fill | Fast market, gap, illiquidity in OTM options | Use SL-M (market stop) not SL-L (limit stop) for options LSL |
| CSL fires quickly on breach | Position polling has 3-5s lag | Accept lag; set CSL slightly inside real limit to account for it |
| Individual leg orders placed atomically | Network failure mid-strategy entry | Track placement state per leg; retry failed legs; if partial entry: alert trader to manually complete or cancel |
| Greeks from option chain are accurate | 30s refresh lag means stale Greeks | Accept for monitoring; flag when delta is near hedge threshold (don't wait for exact threshold) |
| Exit All closes options legs | Legs may expire worthless vs getting closed | Exit All sends market sell/buy orders; near-expiry OTM legs may have no buyers — handle gracefully |
| CSL cancel orphaned exchange LSL orders | When CSL fires and closes all legs, exchange LSL orders for those legs must be cancelled | After CSL flatten: immediately cancel all pending SL orders for that strategy |

---

## Daily Options Workflow

```
PRE-MARKET    Review IV Rank on basket instruments (option chain API)
              Check open strategies: DTE, P&L, delta drift

9:15 AM       Market opens. Live Greeks begin updating (30s refresh).
              Overnight P&L change visible immediately.

TIME GATE     Configured entry time (e.g. 10:00 AM)
              System checks: IV Rank, signal score, delta availability
              If ready → strategy shown as actionable. Trader confirms.
              Individual leg orders placed sequentially.

INTRADAY      Delta monitoring (from cached option chain, 30s refresh)
              CSL internal monitor (real-time P&L calc from polled positions)
              LSL exchange orders already live (placed at entry)

3:00 PM       Options review alongside equity conversion review
              Adjust, roll, or close as needed before close

ONGOING       Manage DTE. Roll at 21 DTE. Close at 7 DTE or % target.
```

---

## Time-Gated Entry

Single entry window per day per basket (configurable time, e.g. 10:00 AM).

### Entry Gate Conditions

| Condition | Source | Notes |
|-----------|--------|-------|
| Time gate open | System clock | After configured entry time |
| IV Rank threshold | Option chain API | e.g. IV Rank > 30 for selling strategies |
| Signal quality | Score engine | Underlying instrument score ≥ threshold |
| Delta available | Option chain | Target delta exists at current strikes |
| No existing strategy | Internal DB | Same basket, same instrument — no double entry |
| Order budget | Daily counter | Enough remaining orders for all legs + LSL |

When all met → strategy builder shows "READY". Trader still manually confirms.

---

## Strategy Environment Detection

| IV Rank | Market Condition | Suggested Strategy |
|---------|-----------------|-------------------|
| > 50, range-bound | Nifty in defined range | Iron Condor |
| > 50, bullish | Nifty uptrending | Bull Put Spread |
| > 50, bearish | Nifty downtrending | Bear Call Spread |
| > 65, neutral | Wide range expected | Strangle |
| < 20, directional | Strong trending market | Debit Spread |
| Event-driven | Earnings/event nearby | Calendar or Iron Fly |

Suggestion is a starting point. Trader can override.

---

## Supported Strategies

All strategies execute as individual orders (no basket API). Our execution engine places legs sequentially and tracks state.

### Defined Risk Sells
| Strategy | Legs | Max Loss Known |
|----------|------|---------------|
| Bull Put Spread | Sell OTM put + Buy further OTM put | Yes — spread width - credit |
| Bear Call Spread | Sell OTM call + Buy further OTM call | Yes |
| Iron Condor | Bull put spread + Bear call spread | Yes |
| Iron Butterfly | Sell ATM put + Sell ATM call + Buy wings | Yes |

### Undefined Risk Sells
| Strategy | Legs | Notes |
|----------|------|-------|
| Naked Put | Sell OTM put | Requires MARGIN product, higher margin |
| Covered Call | Sell OTM call (own underlying CNC) | Lower margin — covered by holding |
| Strangle | Sell OTM put + Sell OTM call | Two individual orders |
| Straddle | Sell ATM put + Sell ATM call | Two individual orders |

### Debit Buys
| Strategy | Legs | Notes |
|----------|------|-------|
| Long Call / Put | Buy single option | Low margin, defined risk |
| Debit Spread | Buy closer strike + Sell further strike | Net debit |
| LEAP | Deep ITM long-dated call | Stock replacement, long-term |

### Multi-Leg Complex
| Strategy | Notes |
|----------|-------|
| Calendar Spread | Different expiries, same strike |
| Diagonal | Different expiries AND strikes |
| Jade Lizard | Bear call spread + Naked put |

---

## LSL / CSL Safety Engine — Dhan-Constrained Design

### The Fundamental Constraint

Dhan has no basket order API. This means:
- We cannot place a single "close this strategy" order
- We must fire individual close orders for each leg
- Between CSL breach detection and all legs closing: there is a gap of seconds
- This gap is irreducible — it is a hard constraint of using Dhan

Design response: set CSL slightly inside your true maximum loss to provide a buffer for the closing lag.

### LSL — Leg Stop Loss

**Definition**: Maximum loss on a single option leg.

**Mechanism**:
1. Calculate LSL price = entry price + LSL amount (for short legs) or entry price - LSL amount (for long/hedge legs)
2. Place a **SL-M order (Stop Loss Market)** at the exchange immediately on entry
3. Use SL-M (not SL-L) because OTM options can have wide bid-ask spreads; limit orders may not fill

**Why SL-M for options**: In a fast market, an OTM option that's going against you can gap through a limit stop. Market stop ensures closure even in gapped conditions (though at worse price).

**Order tracking**: Store the Dhan order ID of each LSL order. When CSL fires and closes all legs, immediately cancel any pending LSL orders for that strategy via Dhan cancel API. Orphaned LSL orders can re-trigger on price recovery.

### CSL — Combined Stop Loss

**Definition**: Maximum combined loss across all legs of one strategy.

**Mechanism**:
- Calculate combined P&L from polled position data (every 3-5s)
- If combined P&L ≤ -CSL amount: trigger flatten sequence
- Flatten sequence: place market close orders for all legs simultaneously (separate API calls in rapid succession)
- After flatten confirmed: cancel all pending LSL exchange orders for this strategy

**The 3-5s lag**: Accept it. Set CSL at 85-90% of your true maximum loss threshold to account for:
- Polling lag (3-5s)
- Order placement latency
- Market movement during flatten

### Safety Fallback — Auto-LSL

If CSL is defined but LSL is not set for a leg:

```
Auto-LSL = CSL × configurable% (default 50%) per leg
Placed as SL-M exchange order immediately on entry
```

Ensures exchange-level protection even when trader skips per-leg LSL configuration.

### Leg Placement State Machine

```
STRATEGY: Iron Condor (4 legs)

State transitions:
IDLE → PLACING_LEG_1 → LEG_1_PLACED → PLACING_LEG_2 → ...
    → ALL_LEGS_PLACED → PLACING_LSL_1 → LSL_1_PLACED → ...
    → ACTIVE (all legs + all LSL orders live)

On failure at any leg:
    → PARTIAL_ENTRY (alert trader immediately)
    → Options: complete remaining legs OR cancel placed legs
    → Trader decision required — cockpit shows exact state
```

Partial entry is a real risk with sequential individual orders. The cockpit must track exact state and alert immediately.

### Strategy Example (NIFTY Iron Condor)

```
Strategy: Iron Condor NIFTY  21 DTE

Orders placed (8 total):
1. Sell 22500 CE  MARGIN  → Order ID: D001
2. Buy  22600 CE  MARGIN  → Order ID: D002  (hedge)
3. Sell 22000 PE  MARGIN  → Order ID: D003
4. Buy  21900 PE  MARGIN  → Order ID: D004  (hedge)

LSL orders (SL-M, exchange):
5. Buy  22500 CE  SL-M trigger ₹240  → Order ID: D005  (covers D001)
6. Buy  22000 PE  SL-M trigger ₹220  → Order ID: D006  (covers D003)

(Hedge legs D002, D004 have no LSL — they protect the position)

CSL: -₹15,000 combined internal monitor active
Auto-LSL applied: D005 = 50% of CSL = ₹7,500 max per leg

If CSL breached:
→ Market sell D001 (close short CE)
→ Market sell D003 (close short PE)
→ Market buy D002 (close long CE hedge) — optional if near zero
→ Market buy D004 (close long PE hedge) — optional if near zero
→ Cancel D005, D006 (pending LSL orders)
```

---

## Basket Management

A basket = named group of strategies managed together.

### Basket Configuration

```
Basket: Weekly Income

Instruments:      NIFTY, BANKNIFTY
Default strategy: Iron Condor
Entry time gate:  10:00 AM
DTE on entry:     21–45 DTE
Delta to sell:    0.25–0.30 delta range
Delta to hedge:   0.50 (breach triggers alert)
IV Rank min:      30

LSL per leg:      ₹20/lot (or auto from CSL)
CSL combined:     ₹15,000
Auto-LSL %:       50%

Profit target:    50% of premium received
DTE milestones:   21 DTE (review), 7 DTE (close or roll)
```

### Basket P&L View

```
BASKET: Weekly Income
┌────────────┬──────┬─────┬─────────┬──────────┬────────┐
│ Instrument │ Str  │ DTE │ Credit  │ P&L      │ Theta  │
├────────────┼──────┼─────┼─────────┼──────────┼────────┤
│ NIFTY      │ IC   │ 18  │ ₹8,400  │ +₹4,200  │ +₹380 │
│ BANKNIFTY  │ IC   │ 18  │ ₹6,200  │ -₹1,100  │ +₹290 │
├────────────┼──────┼─────┼─────────┼──────────┼────────┤
│ TOTAL      │      │     │ ₹14,600 │ +₹3,100  │ +₹670 │
└────────────┴──────┴─────┴─────────┴──────────┴────────┘
```

### Portfolio Greeks View (switchable)

Greeks sourced from Dhan option chain API (cached 30s refresh).

```
PORTFOLIO GREEKS — All Baskets

Net Delta:  +0.08  (near neutral)
Net Theta:  +₹670/day
Net Vega:   -₹2,100  (short volatility)
Net Gamma:  -0.09

STRESS (approximate, not from Dhan — calculated internally):
India VIX +20%: estimated P&L ~ -₹420
Nifty -2%:      estimated P&L ~ -₹1,100
```

Note: Greeks are approximate due to 30s cache lag. Not suitable for precise hedging — use as directional awareness only.

---

## Delta Monitoring

Source: Dhan option chain API. Refresh: every 30 seconds (1 req/3s rate limit, multiple underlyings staggered).

| Parameter | Description |
|-----------|-------------|
| Delta to sell | Target delta at entry (e.g. 0.30). Verified against option chain before placing. |
| Delta to hedge | Breach threshold (e.g. 0.50). If position delta reaches this, alert fires. |
| Alert buffer | Alert at hedge_delta - 0.05 to give early warning (e.g. alert at 0.45) |

Delta breach alert:
```
BANKNIFTY BCS  Δ 0.47 → approaching hedge threshold (0.50)
[HEDGE NOW]  [DISMISS — monitor]  [CLOSE STRATEGY]
```

---

## Automated Alerts

| Alert | Trigger | Dhan mechanism |
|-------|---------|---------------|
| Profit target hit | P&L = configured % of max credit | Internal monitor |
| DTE milestone 21 | DTE = 21 | Internal date calc |
| DTE milestone 7 | DTE = 7 | Internal date calc |
| Delta breach | Leg delta ≥ hedge_delta | From option chain poll |
| CSL approaching | Combined P&L at 80% of CSL | Internal monitor |
| LSL hit | Exchange SL-M triggered | Detected via order WS |
| Partial entry | Any leg order failed | Order placement engine |
| IV Rank opportunity | New instrument crosses IV Rank threshold | Option chain poll |
