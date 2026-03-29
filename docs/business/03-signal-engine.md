# 03 — Signal Quality Engine

Multi-factor scoring for both EOD swing scan and intraday signal generation.

---

## Devil's Advocate: Problems with a Simple Total Score

**Problem 1: All-mediocre score**
A score of 60 (B grade) can be: Trend 12/20 + Volume 12/20 + Sector 12/20 + Market 12/20 + R:R 12/20.
This is 4 factors at 60% — nothing compelling. A truly good setup should have at least 2-3 factors at near-full score.

**Solution**: Per-factor minimum scores enforced. If any factor falls below its minimum, the grade is capped at C regardless of total.

**Problem 2: Volume at 9:30 AM vs 11 AM**
Raw volume at 9:30 AM is always lower than 11 AM. Comparing to a 20-day daily average is misleading for intraday candles.

**Solution**: Time-of-day volume normalization. Compare the 9:30–9:45 candle volume to the historical average volume for the 9:30–9:45 window over the last 20 trading days.

**Problem 3: R:R depends on where you put the stop**
The score can be gamed by placing an unrealistically tight stop to get a good R:R ratio. A ₹2/share stop gives great R:R but will be hit constantly.

**Solution**: Stop must be placed at a real technical level (swing high/low, support/resistance). The R:R score penalizes stops that are tighter than the ATR-based minimum.

**Problem 4: Sector score for diverse conglomerates**
RELIANCE is in energy, retail, telecom. Which sector index? ITC is FMCG, cigarettes, hotels.

**Solution**: Use the stock's primary NSE sector classification. Flag multi-sector stocks with a note. Weight sector score lower (15%) for known conglomerates.

---

## Two Timeframes, One Framework

| Mode | When | Data | Candle Intervals |
|------|------|------|-----------------|
| **EOD scan** | After 3:30 PM | 1D + 60min (Dhan historical) | Daily + 60min |
| **Intraday** | 9:15 AM – 3:30 PM | Live WebSocket → OHLCV candles | 5min, 15min, 25min, 60min |

Dhan does not provide 10min or 30min historical data. These intervals are excluded.

---

## Score Factors

| Factor | Base Weight | EOD Weight | Intraday Weight | Per-Factor Minimum |
|--------|------------|-----------|----------------|-------------------|
| Trend Alignment | 20% | 22% | 18% | 10/20 |
| Volume Confirmation | 20% | 18% | 22% | 8/20 |
| Sector Momentum | 20% | 20% | 18% | 6/20 |
| Market Context | 20% | 18% | 22% | 8/20 |
| Risk/Reward Ratio | 20% | 22% | 20% | 12/20 (hard floor) |

EOD scan weights trend more (multi-week structure matters). Intraday weights volume and market context more (real-time conditions matter).

**Per-factor minimum**: If R:R < 12/20 (R:R below 1:1.5), the setup is NOT surfaced regardless of total score. If any other factor below its minimum, grade capped at C.

---

## Grade Scale

| Grade | Score Range | Action |
|-------|------------|--------|
| A | 80–100 | High conviction — alert trader prominently |
| B | 60–79 | Good setup — alert trader |
| C | 40–59 | Marginal — shown but not alerted |
| D | Below 40 | Not shown |

Configurable minimum for watchlist inclusion (default: B = 60+). Intraday alerts only for B+.

---

## Factor Specifications

### 1. Trend Alignment (20%)

**Bullish (for long candidates)**:
- Price above 20 EMA: +4
- Price above 50 EMA: +4
- 20 EMA above 50 EMA: +3
- Recent swing: higher high AND higher low vs prior: +5
- Price in upper 40% of 20-day range: +4

**Bearish (for short candidates)**: Mirror criteria, same scoring.

**Minimum**: 10/20. Below this = no trend conviction. Grade capped at C.

### 2. Volume Confirmation (20%)

**Time-of-day normalized comparison** (intraday):
- Compare current candle volume to historical average volume for same time slot over last 20 days
- 1.5x average = full score; 1.0x = partial; < 0.7x = low score

**EOD scan (daily volume)**:
- Compare to 20-day daily average
- Accumulation pattern: up-day volume > down-day volume average (last 10 days)

**Minimum**: 8/20. Below this = price move not confirmed by participation.

### 3. Sector Momentum (20%)

- Score the sector index using simplified Trend Alignment on the same timeframe
- Full score if sector trend matches trade direction
- Half score if sector is neutral
- Low score (< 6) if sector is against the trade — warning flag shown

For multi-sector stocks: use primary NSE sector classification. Note in signal panel.

**Minimum**: 6/20. Can be below minimum if stock is showing independent strength (override available with warning).

### 4. Market Context (20%)

**Favourable for longs**:
- Nifty 50 above 50 EMA: +5
- Nifty 50 trending up (higher highs): +5
- India VIX below 15: +5
- BankNifty aligned with Nifty: +5

**Warning flags** (shown regardless of score):
- India VIX > 20: "Elevated volatility" warning
- Nifty near major resistance: "Index at resistance" note
- Global sell-off (ADR data if available): note

**Minimum**: 8/20. A bullish stock trade in a strongly bearish market day gets capped at C.

### 5. Risk/Reward Ratio (20%)

Calculated from:
- Entry: signal candle close or defined entry zone midpoint
- Stop: placed at nearest meaningful technical level (NOT tighter than 0.5× ATR)
- Target: next key resistance (long) or support (short)

| R:R | Score | Notes |
|-----|-------|-------|
| 1:3+ | 20/20 | Excellent |
| 1:2–1:3 | 16/20 | Good |
| 1:1.5–1:2 | 12/20 | Minimum acceptable |
| Below 1:1.5 | 0/20 | Trade not surfaced |

**ATR minimum stop rule**: Stop distance must be ≥ 0.5× 14-period ATR. This prevents unrealistically tight stops gaming the R:R score.

---

## Candle Boundary Alignment (Implementation Rule)

Live candle boundaries anchor to market open (9:15 AM), not clock time.

```
5min:  9:15, 9:20, 9:25, 9:30 ...
15min: 9:15, 9:30, 9:45, 10:00 ...
25min: 9:15, 9:40, 10:05, 10:30 ...
60min: 9:15, 10:15, 11:15, 12:15 ...
```

Partial candle (if system starts late): excluded from signal calculation. Shown greyed on chart. Pre-market start (before 9:10 AM) avoids this.

---

## Confluence Zones

A confluence zone is a price level where 2+ independent methods agree.

Contributors to a confluence zone:
- Prior swing high or low
- Round number (e.g. ₹2,900, ₹3,000)
- EMA value (20 or 50)
- Volume node (price with highest traded volume in recent range)
- Fibonacci retracement level

Zones drawn on chart as horizontal bands. Darker = more factors. These are reference levels for SL and target placement — if the signal's stop or target doesn't align with a zone, the score is penalized in R:R factor.

---

## Signal Panel Display

```
╔══════════════════════════════╗
║  RELIANCE   B  74/100        ║
║  ███████░░░░░                ║
╠══════════════════════════════╣
║  Trend     16/20  ✓ (min 10) ║
║  Volume    14/20  ✓ (norm'd) ║
║  Sector    16/20  ✓ Energy   ║
║  Mkt Ctx   12/20  ⚠ VIX 17  ║
║  R:R       16/20  1:2.8      ║
╠══════════════════════════════╣
║  SL:    ₹2,843  (0.52%, ATR✓)║
║  Entry: ₹2,858               ║
║  T1:    ₹2,900               ║
║  T2:    ₹2,980               ║
╠══════════════════════════════╣
║  Confluence:                 ║
║  ● ₹2,843 20EMA + swing low  ║
║  ● ₹2,900 prior high         ║
║  ● ₹2,980 resistance zone    ║
╚══════════════════════════════╝
```

`⚠` on Market Context: VIX is elevated. Not blocking — trader informed. Grade is B not A because of this.
