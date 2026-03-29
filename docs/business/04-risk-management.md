# 04 — Risk Management

The SL philosophy, position sizing mechanics, daily limits, pre-trade overlay, and Dhan-native safety mechanisms.

---

## The Core SL Philosophy

This is the foundational principle that governs all position sizing.

### Intraday (INTRADAY product): MINIMUM SL

The stop loss for an intraday trade is placed at the **tightest technically valid level**.

Why minimum (tight)?
- Intraday thesis is either right quickly or it isn't. A small adverse move invalidates the setup — get out.
- Tight SL = small risk per share = MANY shares within fixed risk budget
- INTRADAY leverage (~5x) makes a large-share position affordable on margin
- This is deliberate, disciplined leverage — not speculation

```
Capital:          ₹10,00,000
Intraday risk %:  0.5%  →  ₹5,000 risk budget
Intraday SL:      ₹15/share (recent 15min candle low — tight)
Quantity:         ₹5,000 ÷ ₹15 = 333 shares
INTRADAY margin:  333 × ₹2,858 ÷ 5 = ₹1,90,532
→ 333 shares affordable with ₹1.9L margin on ₹10L account
```

**Minimum stop rule**: Stop must be at a real technical level AND ≥ 0.5× ATR. Cannot place stop ₹2 below entry for a ₹500 stock just to maximize quantity.

### Swing (CNC product): MAXIMUM SL

The stop loss for a swing trade is placed at the **widest technically valid level** — the key support or resistance zone that, if broken, invalidates the swing thesis entirely.

Why maximum (wide)?
- Swing trades need room to breathe — intraday noise should not stop out a valid swing
- Wide SL = large risk per share = FEW shares within fixed risk budget
- No leverage on CNC delivery — full capital required
- Fewer shares, properly sized for the wide stop, is the correct position

```
Capital:          ₹10,00,000
Swing risk %:     1%  →  ₹10,000 risk budget
Swing SL:         ₹71/share (key support zone — wide)
Quantity:         ₹10,000 ÷ ₹71 = 140 shares
CNC capital:      140 × ₹2,891 = ₹4,04,740  (full delivery capital)
→ 140 shares requires ₹4L capital — affordable, correctly sized
```

### The Inversion — Why This Matters for Conversion

The same ₹10,000 risk budget produces radically different quantities:
- INTRADAY (₹15 SL): 333 shares
- CNC (₹71 SL): 140 shares

When converting an INTRADAY position to CNC, the cockpit ALWAYS converts fewer shares. The 333-share intraday position cannot survive as a 333-share CNC position — the risk would be ₹71 × 333 = ₹23,643 (2.36% of capital — above swing risk budget).

**This is not optional. It is a hard constraint of the SL philosophy.**

---

## Risk Parameters (Configurable Per User)

| Parameter | INTRADAY | CNC | Notes |
|-----------|---------|-----|-------|
| Risk per trade % | 0.5% (default) | 1% (default) | Higher swing % to compensate for larger SL |
| Daily loss limit | ₹5,000 (configurable) | N/A | Per-session cap on intraday losses |
| Max simultaneous | 5 positions | 10 positions | Configurable |
| Min R:R required | 1:2 | 1:1.5 | Intraday needs better R:R for tight stops |
| ATR floor for SL | 0.5× ATR14 | 1.0× ATR14 | Swing needs at least 1 ATR for noise |
| Max sector exposure | 30% intraday book | 40% CNC book | Prevent sector concentration |

---

## Always-On Risk Bar

```
Day P&L: +₹4,200  │  INTRA: [██████░░░░] 58% ₹2,900/₹5,000  │  CNC: ₹4.0L  │  09:47 IST
```

| Element | What It Shows |
|---------|--------------|
| Day P&L | Real-time MTM — all open positions |
| INTRA % bar | Daily intraday loss limit consumed |
| CNC deployed | Total capital in CNC positions (not P&L — deployed amount) |
| Session time | Always visible — critical near 3:10 PM |

**Colour states**:

| State | Condition | Colour |
|-------|-----------|--------|
| Normal | INTRA risk < 60% | White |
| Caution | 60–79% | Amber |
| Warning | 80–99% | Orange |
| Blocked | 100% | Red — new INTRADAY orders blocked |

---

## Dhan-Native Safety Mechanisms

### Dhan P&L Exit API
`POST /pnlExit` — set a daily profit and/or loss threshold. Dhan auto-squares all positions when threshold is hit.

**How we use it**: As a coarse-level global kill switch backup.
- Set daily loss threshold = our configured daily loss limit (or 1.5× for buffer)
- If our app fails to block orders at 100% limit: Dhan P&L Exit provides a second layer
- Does NOT replace per-strategy CSL for options. It is a global blunt instrument.

### Dhan Kill Switch
`POST /killswitch` — disables all trading for the session. Requires all positions closed first.

**When we use it**: Only triggered by explicit trader action (emergency button in cockpit). Not automated.

### Dhan Exit All
`DELETE /positions` — closes all open positions and cancels all pending orders in one call.

**When we use it**: CSL breach on options (we send individual leg close orders first; Exit All as fallback if individual orders fail).

### Super Order for Entry + SL
Dhan Super Order: entry + SL + target in one API call (single leg). Reduces order count and ensures SL is placed atomically with entry.

**Limitation**: Single leg only. Cannot use for multi-leg options strategies.

### Forever Order (OCO) for SL + Target
After entry, place a Forever Order with SL price + target price. One-cancels-other: whichever hits first closes the position.

**Advantage**: Reduces our monitoring burden. Exchange manages the exit logic.

---

## Pre-Trade Overlay

Fires automatically on every order initiation. Cannot be skipped without 2-step confirmation.

### INTRADAY Equity Order

```
TRADE REVIEW — BUY INTRADAY  RELIANCE

SIGNAL                    B  74/100
Entry:                    ₹2,858
SL:                       ₹2,843  (₹15, tight, SL-M at exchange)
Target:                   ₹2,900  R:R 1:2.8
ATR check:                ₹15 > 0.5×ATR(₹22) — below minimum ⚠
                          → SL is tighter than ATR floor. Confirm?

INTRADAY SIZING
Risk budget:              ₹5,000  (0.5%)
Shares:                   333
Margin required:          ₹1,90,532
Available:                ₹3,20,000  ✓

DAILY LIMIT IMPACT
Used today:               ₹2,900  (58%)
After this trade max:     ₹7,900  (158%) if all stop ⚠ — would breach limit
Effective risk this trade: ₹2,100 remaining in limit (partial fill of budget)

On swing list:            YES ★

[CONFIRM 333 INTRADAY]    [RESIZE]    [CANCEL]
```

### CNC Equity Order (Direct Swing Entry)

```
TRADE REVIEW — BUY CNC  TCS

SIGNAL                    A  82/100
Entry:                    ₹3,720
SL:                       ₹3,680  (₹40 wide, key support)
Target:                   ₹3,900  R:R 1:4.5
ATR check:                ₹40 > 1.0×ATR(₹35) ✓

CNC SIZING
Risk budget:              ₹10,000  (1%)
Shares:                   250
Capital required:         ₹9,30,000
Available cash:           ₹9,50,000  ✓

PORTFOLIO IMPACT
CNC book before:          ₹4,00,000  (40%)
CNC book after:           ₹13,30,000  (133%) ⚠ EXCEEDS CASH
→ Not enough capital. Reduce to 162 shares (₹6,03,000 capital)

[RESIZE TO 162]    [OVERRIDE]    [CANCEL]
```

---

## Daily Loss Limit Mechanics

| Event | System Action |
|-------|--------------|
| Intraday loss hits 60% | Amber risk bar |
| Intraday loss hits 80% | Orange bar + warning on every new INTRADAY order |
| Intraday loss hits 100% | Red bar + new INTRADAY orders blocked |
| Intraday loss hits 100% | Dhan P&L Exit API already set — second layer |
| Reset | Every market open — daily limits reset |
| Manual reset | Not available — protects against fatigue-driven override |

**Important**: CNC positions are NOT subject to the daily intraday loss limit. A CNC position going against you on a given day does not consume the INTRADAY daily limit. They are fully independent.

---

## Order Budget Tracking

Dhan allows 5,000 orders/day. Each action consumes:

| Action | Orders Used |
|--------|-------------|
| INTRADAY entry (Super Order) | 1 |
| CNC entry + SL-M stop | 2 |
| Options strategy entry (4 legs + 4 LSL stops) | 8 |
| CSL flatten (4 legs market close) | 4 |
| Conversion: cancel old SL + place new CNC SL | 2 |
| Forever Order (OCO) | 1 |

With 10 options strategies + 5 equity trades: ~100–150 orders/day. Well within 5,000 limit for personal trading. At scale (many strategies), monitor order count.
