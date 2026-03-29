# 02 — Equity Trading Workflow

Full lifecycle: EOD scan → intraday signal → entry (INTRADAY) → conversion (INTRADAY→CNC) → swing management → pyramid.

---

## Devil's Advocate Checks

Before the workflow, these are the assumptions that must hold — if they don't, the workflow breaks:

| Assumption | Challenge | Mitigation |
|-----------|-----------|-----------|
| Watchlist is fresh | Stock may gap badly since EOD scan | Gap check at market open: if gap > configurable % from key level, flag as stale |
| Signal score threshold is sufficient | Score of 60 can be 4 factors at 15/20 — mediocre across all | Minimum per-factor score enforced (e.g. Trend min 12/20, Volume min 10/20) |
| Intraday SL will hold | Gaps, circuit breakers, illiquidity | SL placed as exchange order immediately on entry. Cannot guarantee fill but reduces risk |
| Conversion API succeeds | Network failure, Dhan API error | Retry 3x with backoff. If fails: alert trader, offer manual fallback instruction |
| Position polling captures fills | 3-5s lag | Order WebSocket triggers immediate poll on fill — lag is < 5s in practice |
| EOD scan completes before market open | Data API slow or rate-limited | Run scan at 4 PM, not 3:30 PM. Store in DB. Use previous scan as fallback |

---

## Workflow Phases

```
PHASE 1: EOD SCAN (after 3:30 PM)
  ↓
PHASE 2: PRE-MARKET REVIEW (before 9:10 AM)
  ↓
PHASE 3: INTRADAY TRADING (9:15 AM – 3:00 PM)
  ↓
PHASE 4: CONVERSION DECISION (2:45 PM – 3:15 PM)
  ↓
PHASE 5: SWING MANAGEMENT (multi-day)
  ↓
PHASE 6: PYRAMID (manual, signal-triggered)
```

---

## Phase 1 — EOD Swing Scan

**Runs**: After 3:30 PM (target: 4:00 PM after data settles)
**Data**: Dhan historical API — 1D candles + 60min candles (last 90 days per call, paginate for more)

### What It Produces

| List | Criteria | Trading Direction |
|------|----------|-----------------|
| **Bull candidates** | Score ≥ threshold, uptrend structure, accumulation volume | INTRADAY long + CNC swing long |
| **Bear candidates** | Score ≥ threshold, downtrend structure, distribution volume | INTRADAY short only (equity) OR buy puts (F&O swing) |

**Bear candidates — clarification**: In India equity markets, overnight short selling is not permitted for delivery. Bear candidates serve two purposes:
1. Intraday short via INTRADAY product
2. Swing short via buying PUT options (MARGIN product) — this is a valid swing strategy

### Staleness Check at Market Open

Every watchlist stock is checked at 9:15 AM against its key levels:
- If gap up > 2% above entry zone → flag as "gapped away" → signal suspended until pullback
- If gap down > 1.5% below support (for bull candidates) → flag as "support broken" → remove from active list
- Configurable thresholds

### Watchlist Structure Per Candidate

```
Symbol:         RELIANCE
Score:          B  74/100  (factor minimums: all passed)
Direction:      Bull
Key support:    ₹2,820   (swing SL reference — WIDE)
Key resistance: ₹2,980   (first target)
Extended tgt:   ₹3,120
Entry zone:     ₹2,840–₹2,870
Intraday SL:    ₹2,848   (tight — recent 15min low, recalculated at signal time)
Sector:         Energy
Staleness:      Fresh (last scan: [date])
Gap status:     Normal (as of 9:15 AM check)
```

Note: Intraday SL is NOT stored in the EOD scan — it is calculated fresh when the signal fires, based on the live chart at that moment.

---

## Phase 2 — Intraday Signal Generation

**Runs**: 9:15 AM – 3:30 PM
**Data**: Dhan WebSocket (binary) → tick aggregation → OHLCV candles

### Available Candle Intervals (Dhan constraint)

Dhan historical API provides: **1min, 5min, 15min, 25min, 60min, 1D**.
The cockpit live candle intervals must match: **5min, 15min, 25min, 60min** for intraday use.

> **Why not 10min or 30min?** Dhan does not provide these timeframes historically. If we build live 10min candles but cannot validate them against historical 10min data, signal consistency breaks. We only offer Dhan-native intervals.

### Candle Boundary Alignment (Critical Rule)

Candles anchor to market open (9:15 AM IST), NOT clock boundaries.

```
25min intervals: 9:15, 9:40, 10:05, 10:30, 10:55 ...  (anchored to 9:15)
NOT:             9:00, 9:25, 9:50, 10:15 ...           (clock-anchored — wrong)

15min intervals: 9:15, 9:30, 9:45, 10:00 ...
5min intervals:  9:15, 9:20, 9:25, 9:30 ...
```

### Partial Candle Handling

System must start before 9:10 AM for complete first candle.

| Scenario | Action |
|----------|--------|
| System starts before 9:10 | All candles complete from 9:15 — preferred |
| System starts 9:16–9:39 (for 25min) | First candle partial — discard for signals, show greyed on chart |
| System starts mid-session | All candles until next boundary are partial — discard for signals |

Pre-market readiness indicator shown in cockpit. Green = data pipeline live before 9:15.

### Signal Generation Rules

- Signals fire only on **completed candles** — never on forming candles
- Signals generated only for **watchlist stocks** — not market-wide
- Long signals from bull list only
- Short signals from bear list only
- Each signal carries: direction, score at signal time, intraday SL (calculated live from chart), estimated target, R:R

---

## Phase 3 — INTRADAY Trade Entry

All intraday equity orders: **Dhan INTRADAY product type**.

### The SL Philosophy Applied

This is where the tight SL → large quantity principle is executed:

```
Risk budget:    0.5% of capital = ₹5,000
Intraday SL:    ₹15/share (recent 15min candle low — TIGHT)
Quantity:       ₹5,000 ÷ ₹15 = 333 shares
INTRADAY margin (5x): 333 × ₹2,858 ÷ 5 = ₹1,90,564 margin needed
→ Affordable with INTRADAY leverage
```

**Why tight SL for intraday?**
- Intraday trades must be right quickly. If price moves against you by a small amount (the SL), the thesis is invalid — exit cleanly.
- Tight SL allows a large position for the same risk budget.
- Leverage makes the large position affordable on margin.
- This is not speculation — it is disciplined use of leverage within defined risk.

### Stop Loss Placement

Stop loss placed as **SL-M (Stop Loss Market) order at Dhan exchange** immediately on entry. This is separate from the entry order.

Alternative: Use Dhan **Super Order** which combines entry + SL + target in one call (single leg). Preferred when available.

### Pre-Trade Overlay (INTRADAY)

```
TRADE REVIEW — BUY INTRADAY  RELIANCE

Signal:           B  74/100  (all factor minimums passed)
Entry:            ₹2,858
Intraday SL:      ₹2,843   (₹15 distance, 0.52%) — TIGHT
Target:           ₹2,900   R:R 1:2.8
SL type:          SL-M order at exchange ✓

INTRADAY SIZING
Capital:          ₹10,00,000
Risk per trade:   0.5%  =  ₹5,000
SL distance:      ₹15
Shares:           333
Margin required:  ₹1,90,564  (INTRADAY 5x)
Available margin: ₹3,20,000  ✓

DAILY LIMIT
Used today:       ₹1,800  (36% of ₹5,000 daily limit)
This trade adds:  max ₹5,000 risk if SL hit → would use 100% ⚠

On swing list:    YES ★  (CNC conversion eligible if profitable)

[CONFIRM 333 INTRADAY]                    [CANCEL]
```

---

## Phase 4 — Conversion Decision (INTRADAY → CNC)

**Window**: 2:45 PM – 3:15 PM
**Trigger**: Cockpit surfaces conversion panel at 2:45 PM (early warning), prominent at 3:00 PM, urgent at 3:10 PM

### Why 2:45 PM, Not 3:00 PM?

3:00 PM gives 20 minutes but is psychologically compressed by market activity. 2:45 PM gives the trader a first look with low pressure. Conversion decision quality improves with more time.

### Eligibility Criteria

| Condition | Rule | Why |
|-----------|------|-----|
| Profitable | P&L > 0 on the INTRADAY position | Never average down into a swing |
| On swing watchlist | Stock is on current day's bull candidate list | Pre-validated setup, not random |
| Staleness check | Gap status still Normal | If gap invalidated setup, don't convert |
| Score still valid | Current intraday score ≥ minimum threshold | Setup hasn't degraded intraday |

Bear list stocks: never converted to CNC equity. May trigger put-buying separately.

### The Conversion Sizing Calculation

**The wide SL for swing = fewer shares than held intraday. Always.**

```
Step 1: Identify swing SL
        Use key support from EOD scan (WIDE — might be 2-4% from current price)
        Swing SL is NOT the intraday SL — it is much wider

Step 2: Calculate risk per share (swing)
        Risk per share = current price − swing SL price

Step 3: Apply swing risk budget
        Swing risk budget = capital × swing risk % (e.g. 1%)
        ₹10,00,000 × 1% = ₹10,000

Step 4: Max shares for CNC
        Max CNC shares = swing budget ÷ risk per share

Step 5: Compare to intraday position
        Convert: min(intraday qty, max CNC shares)
        Close:   intraday qty − converted qty (before 3:20 PM)

EXAMPLE:
  Intraday held:      333 shares RELIANCE @ INTRADAY
  Current price:      ₹2,891
  Swing SL (support): ₹2,820  (₹71 distance — WIDE)
  Swing risk budget:  ₹10,000
  Max CNC shares:     ₹10,000 ÷ ₹71 = 140 shares
  Convert:            140 → CNC
  Close:              193 → INTRADAY square-off (before 3:20 PM)
```

**Note**: Held 333 intraday, can only keep 140 swing. The 333-share position was only viable because of 5x INTRADAY leverage. CNC delivery requires full capital for 333 shares (₹9.64L) — but swing risk only justifies 140 shares. The gap is structural, not optional.

### Conversion Panel UI

```
╔══════════════════════════════════════════════════════════════╗
║  CONVERSION REVIEW   2:45 PM   [35 min to square-off]       ║
╠══════════════════════════════════════════════════════════════╣
║  RELIANCE  INTRADAY  333sh  entry ₹2,858  curr ₹2,891       ║
║  P&L: +₹11,011  (+1.15%)  ✓ profitable                      ║
║  On swing list: YES ★  Score: B 74/100  Gap: Normal ✓       ║
╠══════════════════════════════════════════════════════════════╣
║  SWING ANALYSIS                                              ║
║  Swing SL:      ₹2,820  (key support — WIDE ₹71 distance)   ║
║  Swing target:  ₹2,980                                       ║
║  R:R:           1:2.4                                        ║
╠══════════════════════════════════════════════════════════════╣
║  SIZING COMPARISON                                           ║
║  Intraday held:    333 shares  (tight SL ₹15, 5x leverage)  ║
║  CNC can hold:     140 shares  (wide SL ₹71, no leverage)   ║
║  Must close:       193 shares  (INTRADAY square-off)         ║
╠══════════════════════════════════════════════════════════════╣
║  CONVERSION EXECUTION                                        ║
║  1. Convert 140 → CNC  (POST /positions/convert)            ║
║  2. Close 193 → INTRADAY  (sell order, before 3:20)         ║
║  3. Update SL: cancel old SL-M, place new at ₹2,820 CNC    ║
╠══════════════════════════════════════════════════════════════╣
║  [CONFIRM CONVERSION]          [CLOSE ALL INTRADAY]         ║
╚══════════════════════════════════════════════════════════════╝
```

### Conversion Failure Handling

Dhan API call may fail (network, rate limit, Dhan server). Protocol:
1. Retry 3x with exponential backoff (1s, 2s, 4s)
2. If still failing at 3:10 PM: alert trader immediately with manual instruction
3. Manual fallback: trader manually converts via Dhan app before 3:20 PM
4. Log failure for debugging
5. If 3:20 PM passes with unconverted position: Dhan auto-squares off INTRADAY portion — accept and log

---

## Phase 5 — Swing Position Management (CNC)

After conversion, position enters swing mode.

### Post-Conversion Actions (Automated)

1. Cancel old INTRADAY SL-M order (for the closed portion)
2. Place new SL order at swing SL price for CNC position
3. Position moves from INTRADAY book to CNC book in positions strip
4. Hold day counter starts: Day 1

### Daily Monitoring

Each CNC position re-evaluated in nightly EOD scan:
- Score updated nightly
- If score drops below warning threshold (< 40): flag for review next morning
- If price closes below swing SL: alert — stop may trigger on open next day
- Target tracking: show % of target achieved

### CNC Position Strip

```
[CNC] RELIANCE  140sh  avg ₹2,891  curr ₹2,935  +₹6,160 +1.52%
      SL: ₹2,820  T1: ₹2,980  Score: B 74  Day 3  Sector: ✓
```

---

## Phase 6 — Pyramid

Adding to an existing profitable CNC position.

### Pyramid Rules

| Rule | Value | Reasoning |
|------|-------|-----------|
| Position must be profitable | P&L > 0 | No adding to losers |
| Score maintained | Score ≥ 60 (B) | Setup still valid |
| Price at a key level | Breakout or pullback to support | Not buying blindly |
| Per-symbol max | Configurable (e.g. 3 adds maximum) | Prevent concentration risk |
| Budget check | Remaining CNC risk budget available | No overfitting the risk allocation |
| Manual only | Cockpit flags, trader decides | No automatic pyramid |

### Pyramid Sizing

```
Original entry:   140 shares  avg ₹2,891  SL ₹2,820
Original risk:    140 × ₹71 = ₹9,940  (≈ ₹10,000 budget — fully used)

New add scenario: Price pulled back to ₹2,920 (support), score still B
New SL:           ₹2,900 (raised trailing stop — narrower now)
New risk/share:   ₹2,920 − ₹2,900 = ₹20/share
Remaining budget: ₹10,000 − ₹9,940 = ₹60 (budget exhausted)

→ With original budget scheme, no room to add.

ALTERNATIVE: Use a separate pyramid budget (configurable)
Pyramid budget:   ₹5,000 per position (50% of original)
Pyramid shares:   ₹5,000 ÷ ₹20 = 250 shares
New combined:     140 + 250 = 390 shares  avg ₹2,901
Combined SL:      ₹2,820 (original — never move SL against you)
Combined risk:    390 × ₹81 = ₹31,590  (higher than original — trader must approve)
```

The cockpit shows the combined risk clearly in the pyramid overlay. Trader sees exactly what the full position risks before adding.

**Per-symbol cap**: Maximum 3 pyramids per position. After 3 adds, position is full — cockpit blocks further adds and shows "position full" on that symbol.
