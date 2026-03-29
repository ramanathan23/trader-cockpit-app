# Component Design
## Trader Cockpit App

**Last Updated:** 2026-03-29
**Document:** 03 of 06

---

## Table of Contents

1. [Design System](#1-design-system)
2. [Zone Components](#2-zone-components)
3. [Chart Component](#3-chart-component)
4. [PreTradeOverlay](#4-pretradeoverlay)
5. [ConversionPanel](#5-conversionpanel)
6. [OptionsPayoffDiagram](#6-optionspayoffdiagram)
7. [Shared Component Library](#7-shared-component-library)
8. [Accessibility Notes](#8-accessibility-notes)

---

## 1. Design System

### Tailwind CSS v4 and shadcn/ui

The design system uses Tailwind CSS v4 for all layout, spacing, and typography. shadcn/ui provides accessible, unstyled component primitives (dialogs, tooltips, popovers, select menus) that are styled entirely through Tailwind utility classes.

Dark theme is the only theme. There is no `dark:` variant usage — all tokens are defined for dark-background usage directly.

### Design Tokens

Tokens are defined in `shared/theme/design-tokens.ts` and registered as Tailwind CSS custom properties in `tailwind.config.ts`.

```typescript
// shared/theme/design-tokens.ts
export const tokens = {
  // Background layers
  'bg-base':       '#0a0a0f',   // deepest background
  'bg-panel':      '#111118',   // panel backgrounds
  'bg-elevated':   '#1a1a24',   // cards, rows
  'bg-hover':      '#222230',   // hover state
  'bg-selected':   '#2a2a3a',   // selected row / active state

  // Borders
  'border-subtle': '#2a2a3a',   // panel dividers
  'border-active': '#3a3a50',   // focused/active element borders

  // Text
  'text-primary':  '#e8e8f0',   // main content
  'text-secondary':'#8888a8',   // labels, secondary info
  'text-muted':    '#55556a',   // timestamps, disabled

  // Trading semantics — price direction
  'trading-green': '#26a65b',   // price up, profit, long
  'trading-red':   '#e84040',   // price down, loss, short
  'trading-green-bright': '#2ecc71',  // strong positive
  'trading-red-bright':   '#ff4444',  // strong negative
  'trading-neutral':      '#8888a8',  // unchanged

  // Signal grades
  'signal-a': '#26a65b',   // Grade A — high conviction
  'signal-b': '#3498db',   // Grade B — moderate conviction
  'signal-c': '#e67e22',   // Grade C — low conviction
  'signal-d': '#7f8c8d',   // Grade D — no trade

  // Risk states
  'risk-normal':  '#26a65b',   // < 60% limit consumed
  'risk-caution': '#e67e22',   // 60–80% consumed
  'risk-warning': '#e84040',   // 80–100% consumed
  'risk-blocked': '#7f1c1c',   // > 100% consumed (stop)

  // Product type badges
  'intra-accent':   '#3498db',   // INTRADAY positions
  'cnc-accent':     '#9b59b6',   // CNC/delivery positions
  'options-accent': '#e67e22',   // Options positions

  // Connection status
  'conn-green': '#26a65b',
  'conn-amber': '#e67e22',
  'conn-red':   '#e84040',
} as const;
```

**Tailwind CSS v4 registration:**
```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: Object.fromEntries(
        Object.entries(tokens).map(([k, v]) => [k, v])
      ),
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'trading-xs': ['10px', { lineHeight: '14px', letterSpacing: '0.02em' }],
        'trading-sm': ['11px', { lineHeight: '16px', letterSpacing: '0.01em' }],
        'trading-base': ['12px', { lineHeight: '18px' }],
        'trading-lg': ['14px', { lineHeight: '20px' }],
        'trading-xl': ['18px', { lineHeight: '24px', fontWeight: '600' }],
      },
    },
  },
};
```

### Typography Rules

- All price and numeric data use `font-mono` (JetBrains Mono). This ensures numbers align vertically in tables and digit widths are consistent.
- Labels and structural text use `font-sans` (Inter).
- Signal scores use `font-mono font-bold text-trading-xl`.
- Timestamps use `font-mono text-trading-xs text-text-muted`.

### Spacing System

The cockpit is information-dense. Standard Tailwind spacing is used but at the lower end:
- Panel padding: `p-2` (8px)
- Row internal padding: `py-1 px-2`
- Section gaps: `gap-2`
- Zone borders: `border border-border-subtle`

---

## 2. Zone Components

### 2.1 RiskBar

**Purpose:** Always-visible single line showing the four most critical session metrics. Never hidden, never collapses.

**Component tree:**
```
RiskBar
├── DailyPnlBlock          — formatted INR P&L with colour
├── IntraExposureBar        — horizontal bar showing % of intraday limit consumed
│   └── BarFill             — width = limitConsumed, colour = riskLevel
├── CncDeployedBlock       — INR deployed in CNC
├── IntradayCountBlock     — X of Y intraday positions open
└── ConnectionIndicator    — coloured dot: GREEN / AMBER / RED
```

**Layout:** Single `flex items-center` row, 1 grid unit tall (not resizable). All four metrics are always visible.

**Colour logic:**

| Metric | Condition | Colour |
|---|---|---|
| Daily P&L | > 0 | `trading-green` |
| Daily P&L | < 0 | `trading-red` |
| Daily P&L | = 0 | `text-secondary` |
| IntraExposureBar | < 60% consumed | `risk-normal` |
| IntraExposureBar | 60–80% | `risk-caution` |
| IntraExposureBar | > 80% | `risk-warning` |
| IntraExposureBar | >= 100% | `risk-blocked` (full bar, pulsing) |
| ConnectionIndicator | WS live < 5s ago | `conn-green` |
| ConnectionIndicator | WS silent 5–30s | `conn-amber` |
| ConnectionIndicator | WS silent > 30s | `conn-red` |

**BLOCKED state:** When `riskLevel === 'BLOCKED'`, the entire RiskBar background changes to `bg-[#1a0505]` and a "TRADING BLOCKED" text appears between the metrics. Order entry is disabled.

```typescript
// features/risk-bar/risk-bar.tsx
export function RiskBar() {
  const { pnlDisplay, limitBar, limitColor, isBlocked, intradayCount, cncDisplay }
    = useRiskSummary();
  const connectionColor = useConnectionIndicator();

  return (
    <div className={cn(
      'flex items-center gap-4 px-3 h-8 border-b border-border-subtle',
      isBlocked && 'bg-[#1a0505]'
    )}>
      <DailyPnlBlock value={pnlDisplay} isBlocked={isBlocked} />
      <IntraExposureBar fraction={limitBar} color={limitColor} />
      <CncDeployedBlock value={cncDisplay} />
      <IntradayCountBlock count={intradayCount} />
      <div className="ml-auto">
        <ConnectionIndicator color={connectionColor} />
      </div>
      {isBlocked && (
        <span className="text-trading-red font-bold text-trading-sm tracking-widest animate-pulse">
          TRADING BLOCKED
        </span>
      )}
    </div>
  );
}
```

---

### 2.2 SignalPanel

**Purpose:** Shows the signal for the active symbol — score, factor breakdown, key levels, and sizing recommendation. The primary decision-support panel.

**Component tree:**
```
SignalPanel
├── SymbolHeader            — symbol name + exchange badge + last price
├── ScoreDisplay            — large grade letter (A/B/C/D) + numeric score
│   └── GradeIndicator      — coloured ring/background around grade
├── FactorBreakdown         — list of scoring factors with bar indicators
│   └── FactorRow[]         — factor name + score bar + value
├── KeyLevels               — SL / Target1 / Target2 / confluence zone
│   ├── SlLevel             — stop-loss with distance % from current
│   ├── TargetLevel[]       — target levels with R:R ratio
│   └── ConfluenceNote      — key zone description
└── SizingPanel
    ├── ProductToggle       — [INTRADAY] [CNC] — defaults from signal
    ├── QtyDisplay          — suggested quantity with capital required
    ├── RiskPerTrade        — INR risk at SL
    └── TradeButton         — opens PreTradeOverlay
```

**ScoreDisplay design:**

The grade letter is the largest visual element in the panel — designed to be readable from arm's length. Grade A is `text-signal-a`, B is `text-signal-b`, etc. The numeric score (0–100) appears below the letter in `text-trading-sm text-text-secondary`.

**FactorBreakdown:**

Each factor shows a horizontal bar and a label. The bar width represents the factor's contribution to the total score. Positive factors use `trading-green`, negative factors use `trading-red`.

```typescript
// features/signal-panel/components/factor-breakdown.tsx
function FactorRow({ factor }: { factor: SignalFactor }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <span className="w-24 text-trading-xs text-text-secondary truncate">
        {factor.label}
      </span>
      <div className="flex-1 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300',
            factor.value >= 0 ? 'bg-trading-green' : 'bg-trading-red'
          )}
          style={{ width: `${Math.abs(factor.normalizedScore) * 100}%` }}
        />
      </div>
      <span className={cn(
        'w-8 text-right text-trading-xs font-mono',
        factor.value >= 0 ? 'text-trading-green' : 'text-trading-red'
      )}>
        {factor.value > 0 ? '+' : ''}{factor.value}
      </span>
    </div>
  );
}
```

**SizingPanel — MIS/CNC toggle:**

The product toggle defaults to the signal's recommended product. User can override:

```typescript
function SizingPanel() {
  const { suggestedQty, isTradeAllowed } = useSizingRecommendation();
  const [product, setProduct] = useState<'INTRADAY' | 'CNC'>('INTRADAY');
  const openOverlay = useOrdersStore((s) => s.openPreTradeOverlay);

  return (
    <div className="mt-auto border-t border-border-subtle pt-2">
      <div className="flex gap-1 mb-2">
        <button
          className={cn('px-3 py-1 text-trading-xs rounded',
            product === 'INTRADAY'
              ? 'bg-intra-accent text-white'
              : 'bg-bg-elevated text-text-secondary'
          )}
          onClick={() => setProduct('INTRADAY')}
        >
          INTRADAY
        </button>
        <button
          className={cn('px-3 py-1 text-trading-xs rounded',
            product === 'CNC'
              ? 'bg-cnc-accent text-white'
              : 'bg-bg-elevated text-text-secondary'
          )}
          onClick={() => setProduct('CNC')}
        >
          CNC
        </button>
      </div>
      <div className="flex justify-between text-trading-sm mb-2">
        <span className="text-text-secondary">Qty</span>
        <span className="font-mono text-text-primary">{suggestedQty}</span>
      </div>
      <button
        disabled={!isTradeAllowed}
        onClick={() => openOverlay({ qty: suggestedQty, product })}
        className={cn(
          'w-full py-1.5 rounded text-trading-sm font-bold',
          isTradeAllowed
            ? 'bg-trading-green text-white hover:bg-trading-green-bright'
            : 'bg-bg-elevated text-text-muted cursor-not-allowed'
        )}
      >
        {isTradeAllowed ? 'TRADE' : 'BLOCKED'}
      </button>
    </div>
  );
}
```

---

### 2.3 PrimaryCanvas

**Purpose:** The main content area. Displays one of five views based on `canvasMode`. The largest zone by screen area.

**Component tree:**
```
PrimaryCanvas
├── CanvasTabBar
│   ├── TabButton (CHART)           — always available
│   ├── TabButton (EOD_SCAN)        — disabled during market hours
│   ├── TabButton (HEATMAP)
│   ├── TabButton (PORTFOLIO)
│   └── TabButton (OPTIONS_BUILDER)
└── CanvasView                      — renders active mode
    ├── ChartView                   — see Section 3
    ├── EodScanView                 — table of signals (post-market)
    ├── HeatmapView                 — ECharts heatmap
    ├── PortfolioView               — capital allocation treemap
    └── OptionsBuilderView          — leg config + payoff diagram
```

**CanvasTabBar:** Six characters max per tab label, monospace, no icons. Uses shadcn/ui `Tabs` primitive for keyboard navigation. EOD_SCAN tab has a tooltip: "Available after 3:30 PM" when disabled.

---

### 2.4 MarketContextPanel

**Purpose:** Shows the market environment for the active symbol — index performance, sector position, peer comparison, and personal trade history on this symbol.

**Component tree:**
```
MarketContextPanel
├── IndexBlock
│   ├── IndexRow (NIFTY50)         — % change + spark line
│   ├── IndexRow (BANKNIFTY)       — % change + spark line
│   └── IndexRow (NIFTY_IT etc.)   — sector index relevant to symbol
├── SectorBlock
│   └── SectorHeatBar              — sector stocks sorted by % change
├── PeersBlock
│   └── PeerRow[]                  — symbol + % change + volume ratio
└── TradeHistory
    └── HistoryRow[]               — past trades on active symbol: date, P&L, type
```

**PeerRow:** Shows peer symbol name, price change %, and a volume-ratio indicator (current volume vs 20-day average). A volume ratio > 1.5x shows in `trading-green`, < 0.5x in `text-muted`.

---

### 2.5 PositionsStrip

**Purpose:** Always-visible strip showing all open positions. Organized by product type. Updates in real-time from WebSocket POSITION_UPDATE messages.

**Component tree:**
```
PositionsStrip
├── SectionHeader (INTRADAY | CNC | OPTIONS)
├── IntradaySection
│   └── PositionRow[]              — symbol, qty, entry, LTP, P&L, action
├── CNCSection
│   └── PositionRow[]
└── OptionsSection
    └── OptionPositionRow[]        — symbol, strike, expiry, qty, premium, P&L, delta
```

**PositionRow:** Designed for maximum data density at minimum height. One row = one position.

```typescript
function PositionRow({ position }: { position: PositionViewModel }) {
  const pnlColor = position.pnl >= 0 ? 'text-trading-green' : 'text-trading-red';

  return (
    <div className="flex items-center gap-3 px-2 py-1 hover:bg-bg-hover text-trading-xs font-mono">
      <span
        className="w-20 text-text-primary font-bold cursor-pointer hover:text-signal-b"
        onClick={() => setActiveSymbol(position.symbol, position.exchange)}
      >
        {position.symbol}
      </span>
      <span className={cn('w-8', position.product === 'INTRADAY' ? 'text-intra-accent' : 'text-cnc-accent')}>
        {position.product === 'INTRADAY' ? 'MIS' : 'CNC'}
      </span>
      <span className="w-10 text-right text-text-secondary">{position.qty}</span>
      <span className="w-16 text-right text-text-secondary">{formatPrice(position.avgPrice)}</span>
      <span className="w-16 text-right text-text-primary">{formatPrice(position.ltp)}</span>
      <span className={cn('w-20 text-right font-bold', pnlColor)}>
        {formatPnl(position.pnl)}
      </span>
      <span className={cn('w-12 text-right', pnlColor)}>
        {formatPercent(position.pnlPct)}
      </span>
      <PositionActions position={position} />
    </div>
  );
}
```

**Symbol clickable:** Clicking a symbol in the PositionsStrip sets it as the active symbol, switching the chart and signal panel to that position's symbol. This is the fastest way to navigate to a current position.

---

## 3. Chart Component

### Architecture

The chart is the most complex component in the cockpit. It uses ECharts via `echarts-for-react`. Two ECharts instances are rendered: one for the price chart (candlesticks + confluence bands + trade markers) and one for the volume chart. They share the same x-axis zoom state via ECharts' `dataZoom` linking.

**Component tree:**
```
ChartView
├── ChartToolbar
│   ├── IntervalSelector            — [5m][15m][25m][60m][1D]
│   └── IndicatorToggle             — toggle confluence bands, volume
├── PriceChart (ECharts instance 1)
│   ├── CandlestickSeries
│   ├── ConfluenceBandSeries        — markArea overlays
│   ├── TradeMarkerSeries           — markPoint for past entries/exits
│   └── DataZoom (shared group)
└── VolumeChart (ECharts instance 2)
    ├── BarSeries (volume bars)
    └── DataZoom (shared group — synced with PriceChart)
```

### Interval Selector

Only Dhan-native intervals are shown. The type system prevents any other value from being used.

```typescript
// features/canvas/chart/interval-selector.tsx
const INTERVALS: { label: string; value: CandleInterval }[] = [
  { label: '5m',  value: '5min' },
  { label: '15m', value: '15min' },
  { label: '25m', value: '25min' },
  { label: '60m', value: '60min' },
  { label: '1D',  value: '1D' },
];

export function IntervalSelector() {
  const { selectedInterval, setSelectedInterval } = useCockpitStore(
    (s) => ({ selectedInterval: s.selectedInterval, setSelectedInterval: s.setSelectedInterval })
  );

  return (
    <div className="flex gap-1">
      {INTERVALS.map(({ label, value }) => (
        <button
          key={value}
          onClick={() => setSelectedInterval(value)}
          className={cn(
            'px-2 py-0.5 text-trading-xs font-mono rounded',
            selectedInterval === value
              ? 'bg-bg-selected text-text-primary border border-border-active'
              : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
```

### ECharts Configuration — Price Chart

```typescript
// features/canvas/chart/components/price-chart.tsx
function buildPriceChartOption(
  candles: Candle[],
  confluenceZones: ConfluenceZone[],
  tradeMarkers: TradeMarker[],
  liveCandle: Candle | null
): EChartsOption {
  const dataset = buildCandleDataset(candles, liveCandle);

  return {
    backgroundColor: tokens['bg-panel'],
    animation: false,          // CRITICAL: disable animation for real-time updates
    grid: { left: 60, right: 60, top: 20, bottom: 50 },
    xAxis: {
      type: 'category',
      data: dataset.timestamps,
      axisLine: { lineStyle: { color: tokens['border-subtle'] } },
      axisLabel: { color: tokens['text-muted'], fontSize: 10, fontFamily: 'JetBrains Mono' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      position: 'right',
      axisLine: { lineStyle: { color: tokens['border-subtle'] } },
      axisLabel: {
        color: tokens['text-muted'], fontSize: 10, fontFamily: 'JetBrains Mono',
        formatter: (v: number) => formatPrice(v),
      },
      splitLine: { lineStyle: { color: tokens['border-subtle'], opacity: 0.3 } },
    },
    dataZoom: [
      { id: 'price-zoom', type: 'inside', xAxisIndex: 0, start: 70, end: 100 },
      { id: 'price-slider', type: 'slider', xAxisIndex: 0, height: 20, bottom: 10,
        fillerColor: tokens['bg-selected'], borderColor: tokens['border-subtle'] },
    ],
    series: [
      {
        type: 'candlestick',
        data: dataset.ohlc,
        itemStyle: {
          color: tokens['trading-green'],         // bullish candle fill
          color0: tokens['trading-red'],          // bearish candle fill
          borderColor: tokens['trading-green'],
          borderColor0: tokens['trading-red'],
        },
        // Live (partial) candle gets reduced opacity
        markPoint: buildTradeMarkPoints(tradeMarkers),
        markArea: buildConfluenceMarkAreas(confluenceZones),
      },
    ],
  };
}
```

**Animation disabled:** `animation: false` is critical for real-time performance. With animation enabled, every tick update triggers an animation frame. Disabled, ECharts updates the dataset imperatively with no visual latency.

### Live Candle Update — In-Place (No Re-Render)

When a `CANDLE_UPDATE` WebSocket event arrives, the chart updates without React re-rendering the component:

```typescript
// features/canvas/chart/candle-dataset.ts
export function updateLiveCandleInPlace(
  chartRef: React.RefObject<EChartsReact>,
  liveCandle: Candle,
  isPartial: boolean
): void {
  const chart = chartRef.current?.getEchartsInstance();
  if (!chart) return;

  // Get current options — do not rebuild, only patch the last data point
  const currentOption = chart.getOption() as EChartsOption;
  const series = currentOption.series as CandlestickSeriesOption[];

  const lastIndex = (series[0].data as CandleDataItem[]).length - 1;

  // Patch only the last data point
  chart.setOption({
    series: [{
      data: {
        [lastIndex]: {
          value: [liveCandle.open, liveCandle.close, liveCandle.low, liveCandle.high],
          itemStyle: {
            opacity: isPartial ? 0.4 : 1.0,  // grey out partial candle
          },
        },
      },
    }],
  }, { replaceMerge: ['series'] });
}
```

This uses ECharts' `replaceMerge` strategy to patch only the changed index. The React component does not re-render — only the ECharts canvas repaints. This is the key performance advantage of ECharts over React-based chart libraries.

### Confluence Zone Bands

Confluence zones are rendered as `markArea` overlays. They appear as semi-transparent horizontal bands across the price chart, representing key support/resistance areas from the signal scoring engine.

```typescript
// features/canvas/chart/components/confluence-bands.ts
export function buildConfluenceMarkAreas(zones: ConfluenceZone[]): MarkAreaOption {
  return {
    silent: true,    // not interactive
    data: zones.map((zone) => [
      {
        yAxis: zone.lower,
        itemStyle: {
          color: zone.type === 'SUPPORT'
            ? 'rgba(38, 166, 91, 0.08)'
            : 'rgba(232, 64, 64, 0.08)',
          borderColor: zone.type === 'SUPPORT'
            ? tokens['trading-green']
            : tokens['trading-red'],
          borderWidth: 0.5,
          borderType: 'dashed',
        },
        label: {
          show: true,
          position: 'insideTopLeft',
          formatter: zone.label,
          color: zone.type === 'SUPPORT' ? tokens['trading-green'] : tokens['trading-red'],
          fontSize: 9,
          fontFamily: 'JetBrains Mono',
        },
      },
      { yAxis: zone.upper },
    ]),
  };
}
```

### Trade Markers

Past entries and exits for the active symbol are shown as `markPoint` overlays on the candle where they occurred:

```typescript
// features/canvas/chart/components/trade-markers.ts
export function buildTradeMarkPoints(markers: TradeMarker[]): MarkPointOption {
  return {
    symbol: (marker) => marker.type === 'ENTRY' ? 'triangle' : 'pin',
    symbolSize: 10,
    data: markers.map((marker) => ({
      coord: [marker.timestamp, marker.price],
      itemStyle: {
        color: marker.direction === 'LONG'
          ? tokens['trading-green']
          : tokens['trading-red'],
      },
      label: {
        formatter: `${marker.type[0]}\n${formatPrice(marker.price)}`,
        fontSize: 8,
        color: tokens['text-secondary'],
      },
    })),
  };
}
```

### Volume Chart Sync

The volume chart is a separate ECharts instance with the same `dataZoom` group. ECharts built-in `dataZoom` group linking ensures both charts zoom and pan together.

```typescript
// Shared dataZoom configuration applied to both instances
const SHARED_DATA_ZOOM_CONFIG = {
  dataZoom: [
    {
      type: 'inside',
      xAxisIndex: 0,
      id: 'shared-zoom',
    },
  ],
};
// Both charts use the same dataZoom id — ECharts handles synchronization natively
```

---

## 4. PreTradeOverlay

**Purpose:** Modal overlay that appears before order placement. Shows full trade context — signal, sizing, risk impact, and warnings. The user must explicitly confirm before the order is placed.

**Two variants:**

- **Equity variant** — for INTRADAY and CNC stock orders
- **Options variant** — for multi-leg options strategies

### Equity Variant

```
PreTradeOverlay (Equity)
├── Header
│   ├── SymbolBadge                — "RELIANCE NSE"
│   ├── DirectionBadge             — "LONG INTRADAY" or "SHORT CNC"
│   └── SignalGrade                — Grade letter with colour
├── TradeParameters
│   ├── EntryPrice                 — current market price
│   ├── StopLoss                   — with distance % and INR risk
│   ├── Target1                    — with R:R ratio
│   └── Target2                    — with R:R ratio
├── RiskImpact
│   ├── CapitalRequired            — qty × price × margin factor
│   ├── RiskPerTrade               — INR at risk to stop-loss
│   ├── DailyLimitImpact           — "this trade would use X% of remaining limit"
│   └── NewPositionCount           — current count + 1
├── Warnings                       — shows only if relevant:
│   ├── NearDailyLimitWarning      — if > 70% limit would be consumed
│   ├── PositionConcentration      — if > 20% of capital in one stock
│   └── LowSignalWarning           — if grade is C
└── ActionButtons
    ├── CancelButton
    └── ConfirmButton              — disabled if BLOCKED, shows "PLACE ORDER"
```

The overlay is rendered using shadcn/ui `Dialog`. It is mounted at the root level (outside the grid) so it appears over all panels. It does not affect the underlying grid layout.

```typescript
// features/orders/pre-trade-overlay.tsx
export function PreTradeOverlay() {
  const { isOpen, params, close } = useOrdersStore();
  const { mutate: placeOrder, isPending } = usePlaceOrder();
  const { isBlocked } = useRiskSummary();

  if (!params) return null;

  return (
    <Dialog open={isOpen} onOpenChange={close}>
      <DialogContent className="bg-bg-panel border-border-subtle max-w-md">
        <PreTradeHeader params={params} />
        <TradeParameters params={params} />
        <RiskImpact params={params} />
        <Warnings params={params} />
        <div className="flex gap-2 mt-4">
          <Button variant="outline" onClick={close} className="flex-1">
            Cancel
          </Button>
          <Button
            disabled={isBlocked || isPending}
            onClick={() => placeOrder(params, { onSuccess: close })}
            className={cn(
              'flex-1 font-bold',
              params.direction === 'LONG'
                ? 'bg-trading-green hover:bg-trading-green-bright'
                : 'bg-trading-red hover:bg-trading-red-bright'
            )}
          >
            {isPending ? 'Placing...' : `PLACE ${params.direction}`}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Options Variant

The options variant adds a payoff diagram and shows all legs of the strategy:

```
PreTradeOverlay (Options)
├── Header                         — strategy name + underlying
├── LegTable
│   └── LegRow[]                   — strike, expiry, qty, premium, side (BUY/SELL)
├── StrategyMetrics
│   ├── MaxProfit                  — INR + condition
│   ├── MaxLoss                    — INR + condition
│   ├── BreakEven[]                — price points
│   └── NetPremium                 — credit or debit
├── PayoffDiagram (mini)           — compact OptionsPayoffDiagram
├── RiskImpact
└── ActionButtons
```

---

## 5. ConversionPanel

**Purpose:** Appears at 2:45 PM when the backend pushes CONVERSION_CANDIDATES. Allows the trader to decide for each INTRADAY position: convert to CNC, keep a partial qty as CNC, or let it square off.

**Activation condition:** `useConversionCandidates()` returns data AND current time is between 2:45 PM and 3:20 PM. The panel mounts as a floating overlay in the lower section of the canvas area.

```
ConversionPanel
├── Header
│   ├── Title                      — "EOD Conversion Decisions"
│   ├── SquareOffTimer             — "Sq-off in 35 min"
│   └── CloseButton
└── CandidateList
    └── CandidateRow[]
        ├── SymbolCell             — symbol + current P&L
        ├── QtyMath
        │   ├── IntradayQty        — full qty (e.g., "100 shares INTRADAY")
        │   ├── ConvertQty         — quantity to convert (editable)
        │   └── CloseQty           — derived: IntradayQty - ConvertQty
        ├── CapitalImpact          — "CNC would use ₹X of margin"
        └── ActionRow
            ├── ConvertAllButton   — convert full qty to CNC
            ├── ConvertPartial     — number input for partial qty
            └── CloseAllButton     — let square off (no action needed)
```

**Timer design:** The `SquareOffTimer` shows a live countdown. It counts down from 3:20 PM (Dhan auto square-off) in `MM:SS` format. When under 5 minutes, the background turns `risk-warning`. When under 1 minute, it pulses red.

**Maths visibility:** The panel shows all maths. For a 100-share position:

```
100 INTRADAY → convert: [___] → close: [auto]
Capital blocked: ₹1,24,500 (CNC margin)
CNC margin available: ₹3,20,000
```

The trader sees exactly what converting means for their capital before confirming.

```typescript
// features/conversion/conversion-panel.tsx
function CandidateRow({ candidate }: { candidate: ConversionCandidate }) {
  const [convertQty, setConvertQty] = useState(candidate.intradayQty);
  const { mutate: convert, isPending } = useConvertPosition();
  const closeQty = candidate.intradayQty - convertQty;

  return (
    <div className="border border-border-subtle rounded p-3 mb-2">
      <div className="flex justify-between mb-2">
        <span className="font-bold text-text-primary">{candidate.symbol}</span>
        <span className={candidate.pnl >= 0 ? 'text-trading-green' : 'text-trading-red'}>
          {formatPnl(candidate.pnl)}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-trading-xs mb-2">
        <div>
          <div className="text-text-muted">INTRADAY</div>
          <div className="font-mono text-intra-accent">{candidate.intradayQty}</div>
        </div>
        <div>
          <div className="text-text-muted">→ CNC</div>
          <input
            type="number"
            min={0}
            max={candidate.intradayQty}
            value={convertQty}
            onChange={(e) => setConvertQty(Math.min(+e.target.value, candidate.intradayQty))}
            className="w-full bg-bg-elevated border border-border-subtle rounded px-1 font-mono text-cnc-accent"
          />
        </div>
        <div>
          <div className="text-text-muted">CLOSE</div>
          <div className="font-mono text-text-secondary">{closeQty}</div>
        </div>
      </div>
      <CapitalImpact candidate={candidate} convertQty={convertQty} />
      <div className="flex gap-2 mt-2">
        <button
          onClick={() => convert({ symbol: candidate.symbol, qty: convertQty, toProduct: 'CNC' })}
          disabled={convertQty === 0 || isPending}
          className="flex-1 py-1 text-trading-xs bg-cnc-accent text-white rounded disabled:opacity-40"
        >
          Convert {convertQty > 0 && convertQty < candidate.intradayQty ? `${convertQty}` : 'All'} → CNC
        </button>
        <button className="px-3 py-1 text-trading-xs text-text-secondary border border-border-subtle rounded">
          Close All
        </button>
      </div>
    </div>
  );
}
```

---

## 6. OptionsPayoffDiagram

**Purpose:** ECharts line chart showing P&L of an options strategy at expiry across a range of underlying prices. Used in both the OptionsBuilderView (canvas mode) and the PreTradeOverlay (options variant, compact).

### Data

The payoff data is computed frontend-side from strategy leg parameters (strike, premium, qty, side) plus Black-Scholes for time-value approximation (if pre-expiry). The computation runs in a `useMemo` inside the hook.

```typescript
// features/canvas/options-builder/components/payoff-diagram.tsx
export function OptionsPayoffDiagram({ strategy, currentPrice }: Props) {
  const payoffData = useMemo(
    () => computePayoff(strategy, currentPrice),
    [strategy, currentPrice]
  );

  const option: EChartsOption = {
    backgroundColor: tokens['bg-panel'],
    animation: false,
    grid: { left: 70, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: payoffData.prices.map(formatPrice),
      axisLabel: { color: tokens['text-muted'], fontSize: 9, fontFamily: 'JetBrains Mono' },
    },
    yAxis: {
      type: 'value',
      position: 'left',
      axisLabel: { color: tokens['text-muted'], fontSize: 9, fontFamily: 'JetBrains Mono',
        formatter: (v: number) => formatPnl(v) },
      splitLine: { lineStyle: { color: tokens['border-subtle'], opacity: 0.3 } },
    },
    series: [
      {
        type: 'line',
        data: payoffData.pnl,
        smooth: false,
        lineStyle: { width: 2 },
        itemStyle: { opacity: 0 },     // hide data points, show only line
        // Colour the line based on profit (green) vs loss (red)
        visualMap: {
          show: false,
          dimension: 1,
          pieces: [
            { gte: 0, color: tokens['trading-green'] },
            { lt: 0, color: tokens['trading-red'] },
          ],
        },
      },
    ],
    markLine: {
      silent: true,
      data: [
        // Break-even lines
        ...payoffData.breakEvens.map((be) => ({
          xAxis: formatPrice(be),
          lineStyle: { color: tokens['trading-neutral'], type: 'dashed', width: 1 },
          label: { formatter: `BE: ${formatPrice(be)}`, color: tokens['text-secondary'], fontSize: 9 },
        })),
        // Current price marker
        {
          xAxis: formatPrice(currentPrice),
          lineStyle: { color: tokens['signal-b'], type: 'solid', width: 1.5 },
          label: { formatter: 'NOW', color: tokens['signal-b'], fontSize: 9 },
        },
      ],
    },
  };

  return <ReactECharts option={option} style={{ height: '200px', width: '100%' }} />;
}
```

**Live updates:** When the active symbol's price changes via WebSocket (TICK event), the diagram re-renders because `currentPrice` changes, which invalidates the `useMemo`. This is intentional — options P&L curves are computationally cheap to recalculate and the live price marker is important for decision-making.

---

## 7. Shared Component Library

### NumberCell

Used everywhere a price or P&L number appears. Applies colour based on value.

```typescript
// shared/components/number-cell.tsx
interface NumberCellProps {
  value: number;
  format: 'price' | 'pnl' | 'percent' | 'count';
  showSign?: boolean;
}

export function NumberCell({ value, format, showSign = false }: NumberCellProps) {
  const color = value > 0 ? 'text-trading-green'
               : value < 0 ? 'text-trading-red'
               : 'text-trading-neutral';

  return (
    <span className={cn('font-mono tabular-nums', color)}>
      {showSign && value > 0 ? '+' : ''}
      {formatByType(value, format)}
    </span>
  );
}
```

### StatusDot

Connection and status indicator. Always rendered as a circle, colour-only.

```typescript
export function StatusDot({ status }: { status: 'green' | 'amber' | 'red' | 'grey' }) {
  const colorMap = {
    green: 'bg-conn-green',
    amber: 'bg-conn-amber',
    red: 'bg-conn-red animate-pulse',
    grey: 'bg-text-muted',
  };
  return (
    <span className={cn('inline-block w-2 h-2 rounded-full', colorMap[status])} />
  );
}
```

### SparkLine

Mini ECharts line chart for index performance in the MarketContextPanel.

---

## 8. Accessibility Notes

The cockpit is a professional trading tool, not a public-facing consumer app. Accessibility targets are:

- All interactive elements (buttons, inputs) are keyboard reachable and have visible focus rings.
- The PreTradeOverlay and ConversionPanel trap focus while open (shadcn/ui Dialog handles this).
- Colour is never the sole differentiator — price up/down also shows +/- sign prefix.
- Font sizes use `trading-xs` minimum (10px) — suitable for desktop use at arm's length.
- Screen reader support is not a design priority for the trading panels, but form controls have labels.
- No animations that could trigger vestibular disorders in non-data components. Chart transitions are disabled entirely.
