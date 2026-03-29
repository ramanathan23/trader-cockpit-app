# 06 — Cockpit UX & Layout

Spatial design, zone responsibilities, adaptive behaviour, portfolio views, keyboard shortcuts.

---

## Design Principles

| Principle | Rule |
|-----------|------|
| No tabs for core workflow | All critical info visible simultaneously |
| Symbol drives everything | Changing active symbol updates all panels |
| Colour = state | Green/red for P&L, amber/red for risk, intensity for magnitude |
| Latency is visible | Data freshness shown per feed; stale data is visible not hidden |
| Two-step on critical actions | Order confirm has 2s cancel window; conversion has explicit confirm |
| Dark theme only | Industry standard for trading; reduces eye strain |
| Dhan-native intervals only | 5min, 15min, 25min, 60min, 1D — no invented timeframes |

---

## Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  RISK BAR  Day P&L │ INTRA risk % │ CNC deployed │ [Options Θ] │ Time  │
├──────────────┬─────────────────────────────────────┬───────────────────┤
│              │                                     │                   │
│   SIGNAL     │          PRIMARY CANVAS             │  MARKET CONTEXT   │
│   PANEL      │                                     │                   │
│              │  [Chart/Heatmap/Portfolio/           │  Index + Sector   │
│  Score       │   Options Payoff/EOD Scan]           │  Peers            │
│  Factors     │                                     │  Correlation      │
│  SL / Entry  │  Candlestick+Volume+Confluence       │  Your history     │
│  Target      │  on Dhan-native intervals            │  on symbol        │
│  Sizing      │                                     │                   │
│  MIS/CNC     │                                     │  Auto sizing      │
│  toggle      │                                     │  (mode-aware)     │
│              ├─────────────────────────────────────┤                   │
│              │  POSITIONS STRIP (always visible)   │                   │
│              │  [INTRA] [CNC] [OPTIONS]            │                   │
└──────────────┴─────────────────────────────────────┴───────────────────┘
```

---

## Zone: Risk Bar

Always visible. Never hidden. Single line.

```
Day P&L: +₹4,200  │  INTRA: [██████░░░░] 58% ₹2,900/₹5,000  │  CNC: ₹4.0L  │  Θ+₹670  │  09:47 IST
```

Colour changes based on INTRA limit consumed (normal/amber/orange/red). See Risk Management doc.

**Dhan-specific**: P&L data sourced from `GET /positions` poll. Latency ~3-5s. This is acceptable for the risk bar — it is awareness, not real-time trading data.

---

## Zone: Signal Panel

Updates when active symbol changes. Always expanded — no hover required.

```
╔══════════════════════════════╗
║  RELIANCE   B  74/100        ║
║  ████████░░░░                ║
╠══════════════════════════════╣
║  Trend     16/20  ✓          ║
║  Volume    14/20  ✓ (norm'd) ║
║  Sector    16/20  ✓          ║
║  Mkt Ctx   12/20  ⚠ VIX 17  ║
║  R:R       16/20  1:2.8      ║
╠══════════════════════════════╣
║  SL:    ₹2,843  (ATR ✓)      ║
║  Entry: ₹2,858               ║
║  T1:    ₹2,900               ║
╠══════════════════════════════╣
║  MODE: [INTRADAY]  [CNC]     ║  ← toggle switches sizing
║  Qty:  333 shares  ←auto     ║
║  Risk: ₹4,995  (0.5%)        ║
╚══════════════════════════════╝
```

Mode toggle: switches between INTRADAY sizing (tight SL, many shares) and CNC sizing (wide SL, few shares). Qty recalculates instantly.

Manually adjusting Qty shows override in different colour. Risk % shown as override changes.

---

## Zone: Primary Canvas

Largest zone. Mode-switchable via keyboard or tab bar.

| Canvas Mode | Keyboard | Content |
|-------------|----------|---------|
| Chart | `C` (default) | Candlestick + volume + confluence + indicators |
| EOD Scan | `E` | Today's watchlist with scores and key levels |
| Heatmap | `H` | Sector performance heatmap |
| Portfolio | `P` | CNC positions treemap + CNC/INTRA/Options capital view |
| Options Builder | `O` | Strategy legs + live payoff diagram |

### Chart Mode

Candle intervals: **5min, 15min, 25min, 60min, 1D** (Dhan-native only).

Live candles built from Dhan WebSocket binary feed. Candle boundaries anchored to 9:15 AM, not clock.

Partial first candle: shown greyed. No signal generated. Pre-market start (before 9:10 AM) avoids this.

Confluence zones drawn as horizontal bands directly on chart. Darker = more factors aligning at that level.

Your own prior entries/exits shown as markers on the chart (from trade journal DB).

### Options Builder Mode

- Strategy type selector
- Legs table: strike, expiry, delta, premium, LSL
- Live payoff diagram (ECharts — updates as market moves)
- Entry conditions checklist
- Order budget impact shown (orders this strategy will consume)

---

## Zone: Market Context Panel

Auto-loads for the active symbol. No manual setup.

| Symbol Type | Context Loaded |
|-------------|---------------|
| Large cap NSE | Nifty 50, sector index, top 3 peers, India VIX |
| Bank/NBFC | Nifty 50, BankNifty, peer banks |
| IT stock | Nifty IT, USD/INR rate |
| Nifty index | BankNifty, MidCap, India VIX |

**Data source**: Dhan WebSocket (Quote packets) — same connection as main market feed. No extra API calls needed for context panel if already subscribed to index instruments.

**Correlation**: Calculated from 60-day daily returns using Dhan historical data. Refreshed nightly. Not real-time.

**Your history on this symbol**: From local trade journal DB. Win/loss, avg R:R, last trade outcome, last conversion result.

---

## Zone: Positions Strip

Always visible. Three sections, clearly separated.

```
[INTRA] RELIANCE 333sh  entry ₹2,858  curr ₹2,891  +₹11,011  SL ₹2,843  [Convert★] [Close]
[INTRA] HDFC     80sh   entry ₹1,640  curr ₹1,628  -₹960                           [Close]

[CNC]   TCS      140sh  entry ₹3,720  curr ₹3,698  -₹3,080   SL ₹3,680  Day 1      [Manage]
[CNC]   RELIANCE 140sh  entry ₹2,891  curr ₹2,935  +₹6,160   SL ₹2,820  Day 3  ★   [Add]

[OPT]   NIFTY IC  18DTE  cr ₹8,400  P&L +₹4,200 50% ⚡       Δ+0.04              [Close]
[OPT]   BFNK IC   18DTE  cr ₹6,200  P&L -₹1,100             Δ+0.18 ⚠ drift      [Hedge]
```

- `★` on INTRA row: eligible for CNC conversion at EOD
- `★` on CNC row: pyramid opportunity flagged
- `⚡` on OPT row: at or near profit target
- `⚠` on OPT row: delta drift alert

Clicking any row: canvas chart switches to that symbol, signal panel updates, context panel updates.

---

## EOD Conversion Panel

Appears at 2:45 PM if conversion candidates exist. Urgent styling at 3:10 PM.

```
╔═══════════════════════════════════════════════════════════════╗
║  CONVERSION REVIEW   3:05 PM  [15 min to square-off]  URGENT ║
╠═══════════════════════════════════════════════════════════════╣
║  RELIANCE  INTRA 333sh  +₹11,011  ★ swing list  B 74  ✓     ║
║  Hold INTRA: 333  Convert: 140 → CNC  Close: 193 INTRA       ║
║                                          [CONFIRM]  [SKIP]   ║
╠═══════════════════════════════════════════════════════════════╣
║  HDFC  INTRA -₹960  ✗ loss — will square-off at 3:20        ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Adaptive Behaviour

| Event | Cockpit Response |
|-------|-----------------|
| Before 9:10 AM | Pre-market readiness indicator (green/red) |
| System starts after 9:15 | First candle greyed, alerts suppressed until complete candle |
| Signal fires on watchlist | Row highlights with score and direction arrow |
| Order initiated | Pre-trade overlay fires automatically |
| INTRA position near SL | Row pulses amber in positions strip |
| INTRA daily limit at 80% | Risk bar turns orange, warning on INTRA orders |
| INTRA daily limit at 100% | Risk bar red, INTRA orders blocked |
| 2:45 PM | Conversion panel appears (if candidates exist) |
| 3:10 PM | Conversion panel goes urgent styling, timer prominent |
| Options delta breach (0.45) | Early warning in strip |
| Options delta breach (0.50) | Alert with inline hedge/close action |
| Options profit target | Alert with one-click close |
| Options 21 DTE | Review alert |
| Options 7 DTE | Close/roll urgent alert |
| CSL breach | Options strip row turns red, flatten in progress shown |
| Token expiry approaching (2hr) | Warning notification — renewal required |
| Dhan WebSocket disconnect | Data staleness shown; reconnect in progress |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus symbol search |
| `B` | Order: BUY |
| `S` | Order: SELL |
| `M` | Toggle mode: INTRADAY ↔ CNC |
| `Enter` | Confirm order (2s cancel window) |
| `Esc` | Cancel overlay / close panel |
| `1` | Chart: 5min |
| `2` | Chart: 15min |
| `3` | Chart: 25min |
| `4` | Chart: 60min |
| `5` | Chart: 1D |
| `C` | Canvas: Chart |
| `E` | Canvas: EOD Scan |
| `H` | Canvas: Heatmap |
| `P` | Canvas: Portfolio |
| `O` | Canvas: Options Builder |
| `V` | Canvas: Conversion Panel |
| `W` | Focus watchlist |
| `Tab` | Cycle positions strip |
