# Frontend Architecture
## Trader Cockpit App

**Last Updated:** 2026-03-29
**Document:** 01 of 06

---

## Table of Contents

1. [Module Structure](#1-module-structure)
2. [Symbol-Driven Context Pattern](#2-symbol-driven-context-pattern)
3. [Canvas Mode State Machine](#3-canvas-mode-state-machine)
4. [Zero Prop Drilling Strategy](#4-zero-prop-drilling-strategy)
5. [Cockpit Layout and Zone Boundaries](#5-cockpit-layout-and-zone-boundaries)
6. [Core Infrastructure Layer](#6-core-infrastructure-layer)
7. [Feature Module Contracts](#7-feature-module-contracts)
8. [Adapter Layer](#8-adapter-layer)
9. [Routing](#9-routing)
10. [Error Boundaries and Fallback Strategy](#10-error-boundaries-and-fallback-strategy)

---

## 1. Module Structure

The source tree is organized by feature, not by technical layer. Each feature module is self-contained: it owns its components, local hooks, and local types. Cross-cutting infrastructure lives in `core/` and `shared/`. The `datasources/` layer is the only place allowed to import fetch or WebSocket primitives.

```
frontend/src/
├── core/                          # Framework infrastructure — never feature-specific
│   ├── symbol-context/
│   │   ├── index.ts               # Re-exports useActiveSymbol, setActiveSymbol
│   │   └── symbol-context.ts      # Thin wrapper over cockpitStore.activeSymbol
│   ├── websocket/
│   │   ├── index.ts
│   │   ├── ws-manager.ts          # Manages both WS connections
│   │   ├── ws-market-feed.ts      # /ws/market-feed connection handler
│   │   └── ws-cockpit-feed.ts     # /ws/cockpit connection handler
│   ├── data-bus/
│   │   ├── index.ts
│   │   ├── data-bus.ts            # Message type → handler registry
│   │   └── handlers/
│   │       ├── tick.handler.ts
│   │       ├── candle.handler.ts
│   │       ├── signal.handler.ts
│   │       ├── position.handler.ts
│   │       ├── risk.handler.ts
│   │       └── conversion.handler.ts
│   └── layout-engine/
│       ├── index.ts
│       ├── cockpit-grid.tsx        # React Grid Layout root
│       ├── widget-registry.ts      # Panel ID → component + size config
│       └── layout-persistence.ts  # Save/restore layout to localStorage
│
├── features/
│   ├── risk-bar/
│   │   ├── index.ts
│   │   ├── risk-bar.tsx            # Root component (always rendered)
│   │   ├── risk-bar.hooks.ts       # useRiskBarData — reads riskStore
│   │   └── components/
│   │       ├── metric-block.tsx
│   │       ├── intra-exposure-bar.tsx
│   │       └── connection-indicator.tsx
│   │
│   ├── signal-panel/
│   │   ├── index.ts
│   │   ├── signal-panel.tsx        # Root component
│   │   ├── signal-panel.hooks.ts   # useSignalPanel — symbol + signal query
│   │   └── components/
│   │       ├── score-display.tsx
│   │       ├── factor-breakdown.tsx
│   │       ├── key-levels.tsx
│   │       └── sizing-panel.tsx
│   │
│   ├── canvas/
│   │   ├── index.ts
│   │   ├── canvas.tsx              # Mode-switching root
│   │   ├── canvas-tab-bar.tsx      # Mode selector (CHART / EOD / HEAT / PORT / OPT)
│   │   ├── canvas.hooks.ts
│   │   ├── chart/
│   │   │   ├── chart-view.tsx
│   │   │   ├── chart.hooks.ts      # useChartData(symbol, interval)
│   │   │   ├── interval-selector.tsx
│   │   │   ├── candle-dataset.ts   # In-place candle update logic
│   │   │   └── components/
│   │   │       ├── price-chart.tsx
│   │   │       ├── volume-chart.tsx
│   │   │       ├── confluence-bands.ts  # ECharts markArea config builder
│   │   │       ├── trade-markers.ts     # ECharts markPoint config builder
│   │   │       └── indicator-panel.tsx
│   │   ├── eod-scan/
│   │   │   ├── eod-scan-view.tsx
│   │   │   └── eod-scan.hooks.ts
│   │   ├── heatmap/
│   │   │   ├── heatmap-view.tsx
│   │   │   └── heatmap.hooks.ts
│   │   ├── portfolio/
│   │   │   ├── portfolio-view.tsx
│   │   │   └── portfolio.hooks.ts
│   │   └── options-builder/
│   │       ├── options-builder-view.tsx
│   │       ├── options-builder.hooks.ts
│   │       └── components/
│   │           ├── leg-configurator.tsx
│   │           └── payoff-diagram.tsx
│   │
│   ├── market-context/
│   │   ├── index.ts
│   │   ├── market-context-panel.tsx
│   │   ├── market-context.hooks.ts
│   │   └── components/
│   │       ├── index-block.tsx
│   │       ├── sector-block.tsx
│   │       ├── peers-block.tsx
│   │       └── trade-history.tsx
│   │
│   ├── positions/
│   │   ├── index.ts
│   │   ├── positions-strip.tsx
│   │   ├── positions.hooks.ts
│   │   └── components/
│   │       ├── intraday-section.tsx
│   │       ├── cnc-section.tsx
│   │       ├── options-section.tsx
│   │       └── position-row.tsx
│   │
│   ├── conversion/
│   │   ├── index.ts
│   │   ├── conversion-panel.tsx    # Renders when conversion candidates arrive
│   │   └── conversion.hooks.ts
│   │
│   ├── watchlist/
│   │   ├── index.ts
│   │   ├── watchlist-sidebar.tsx
│   │   └── watchlist.hooks.ts
│   │
│   ├── orders/
│   │   ├── index.ts
│   │   ├── order-entry.tsx
│   │   ├── pre-trade-overlay.tsx
│   │   └── orders.hooks.ts
│   │
│   └── options/
│       ├── index.ts
│       ├── options-manager.tsx
│       └── options.hooks.ts
│
├── datasources/
│   ├── rest/
│   │   ├── index.ts
│   │   ├── queries/
│   │   │   ├── use-watchlist.ts
│   │   │   ├── use-signal.ts
│   │   │   ├── use-positions.ts
│   │   │   ├── use-candles.ts
│   │   │   ├── use-conversion-candidates.ts
│   │   │   └── use-option-strategies.ts
│   │   └── mutations/
│   │       ├── use-place-order.ts
│   │       ├── use-convert-position.ts
│   │       └── use-place-option-strategy.ts
│   └── ws/
│       ├── index.ts
│       ├── use-market-feed.ts      # Subscribe/unsubscribe symbol ticks
│       └── use-cockpit-feed.ts     # Receive signals, alerts, P&L
│
├── adapters/
│   ├── signal.adapter.ts
│   ├── position.adapter.ts
│   ├── options.adapter.ts
│   └── risk.adapter.ts
│
├── store/
│   ├── cockpit.store.ts
│   ├── risk.store.ts
│   └── session.store.ts
│
└── shared/
    ├── components/
    │   ├── badge.tsx
    │   ├── number-cell.tsx          # Coloured +/- number display
    │   ├── spark-line.tsx
    │   ├── status-dot.tsx
    │   └── timer.tsx
    ├── hooks/
    │   ├── use-active-symbol.ts
    │   ├── use-interval.ts
    │   ├── use-connection-status.ts
    │   └── use-market-session.ts    # Is market open? Time to close? etc.
    ├── types/
    │   ├── symbol.types.ts
    │   ├── candle.types.ts
    │   ├── signal.types.ts
    │   ├── position.types.ts
    │   ├── order.types.ts
    │   ├── options.types.ts
    │   └── risk.types.ts
    └── theme/
        ├── tailwind.config.ts
        └── design-tokens.ts
```

---

## 2. Symbol-Driven Context Pattern

### Concept

The active symbol is the central organizing variable of the cockpit. Every zone reads it. When a trader clicks a symbol in the watchlist, the symbol changes once in the Zustand store, and all five zones respond independently without any parent component orchestrating the cascade.

### Implementation

**The store slice (cockpit.store.ts):**

```typescript
interface CockpitState {
  activeSymbol: string;           // e.g. "RELIANCE", "NIFTY50"
  activeExchange: 'NSE' | 'BSE';
  canvasMode: CanvasMode;
  selectedInterval: CandleInterval;
  layoutConfig: ReactGridLayout.Layout[];
  isEditMode: boolean;
  setActiveSymbol: (symbol: string, exchange: 'NSE' | 'BSE') => void;
  setCanvasMode: (mode: CanvasMode) => void;
  setSelectedInterval: (interval: CandleInterval) => void;
}

export type CandleInterval = '5min' | '15min' | '25min' | '60min' | '1D';
export type CanvasMode = 'CHART' | 'EOD_SCAN' | 'HEATMAP' | 'PORTFOLIO' | 'OPTIONS_BUILDER';
```

**The shared hook (shared/hooks/use-active-symbol.ts):**

```typescript
export function useActiveSymbol() {
  return useCockpitStore((state) => ({
    symbol: state.activeSymbol,
    exchange: state.activeExchange,
    setSymbol: state.setActiveSymbol,
  }));
}
```

**Each zone consuming the symbol:**

```typescript
// Inside signal-panel/signal-panel.hooks.ts
export function useSignalPanelData() {
  const { symbol } = useActiveSymbol();
  const { data: signal } = useSignal(symbol);       // TanStack Query
  const liveScore = useSignalFromFeed(symbol);       // WS data bus
  return { symbol, signal: liveScore ?? signal };
}

// Inside market-context/market-context.hooks.ts
export function useMarketContextData() {
  const { symbol } = useActiveSymbol();
  const { data: context } = useMarketContext(symbol); // TanStack Query
  return context;
}
```

### Why No Prop Drilling

The application layout is flat. `CockpitGrid` renders the five zones as direct children:

```
CockpitGrid
├── RiskBar          (reads riskStore directly)
├── SignalPanel      (reads cockpitStore.activeSymbol via hook)
├── PrimaryCanvas    (reads cockpitStore.activeSymbol + canvasMode)
├── MarketContextPanel (reads cockpitStore.activeSymbol)
└── PositionsStrip   (reads positions from riskStore / TanStack Query)
```

There is no shared props object passed down. There is no context provider wrapping the grid. Each zone imports its own hook, which internally calls `useActiveSymbol()`. Symbol change propagation is handled entirely by Zustand's selector-based subscription system.

### Symbol Change Flow

When a user clicks "RELIANCE" in the watchlist:

1. `watchlist-sidebar.tsx` calls `setActiveSymbol("RELIANCE", "NSE")`
2. `cockpitStore.activeSymbol` updates to `"RELIANCE"`
3. Zustand notifies all subscribers that selected this slice
4. `SignalPanel` re-renders → `useSignal("RELIANCE")` fires (TanStack Query cache hit or fresh fetch)
5. `PrimaryCanvas` re-renders → chart switches to RELIANCE candles
6. `MarketContextPanel` re-renders → loads RELIANCE context (index correlation, sector, peers)
7. `WebSocket manager` receives symbol change event → unsubscribes old symbol → subscribes RELIANCE
8. `RiskBar` does not re-render (reads riskStore, not activeSymbol)
9. `PositionsStrip` does not re-render (reads positions by product, not active symbol)

Steps 4–7 happen in parallel due to independent Zustand subscriptions.

---

## 3. Canvas Mode State Machine

### States

The Primary Canvas renders one of five views determined by `cockpitStore.canvasMode`:

```
                    ┌─────────────────────────────┐
                    │                             │
              ┌─────▼──────┐               ┌─────▼──────┐
              │  EOD_SCAN  │               │  HEATMAP   │
              └─────┬──────┘               └─────┬──────┘
                    │                             │
     ┌──────────────▼─────────────────────────────▼──────────────┐
     │                      CHART (default)                       │
     └──────────────┬─────────────────────────────┬──────────────┘
                    │                             │
              ┌─────▼──────┐               ┌─────▼──────────┐
              │ PORTFOLIO  │               │OPTIONS_BUILDER │
              └────────────┘               └────────────────┘
```

Any mode can transition to any other mode. `CHART` is the default on startup and after symbol change (symbol change resets canvas to CHART mode).

### Canvas Root Component

```typescript
// features/canvas/canvas.tsx
export function PrimaryCanvas() {
  const { canvasMode, activeSymbol } = useCockpitStore(
    (s) => ({ canvasMode: s.canvasMode, activeSymbol: s.activeSymbol })
  );

  // Reset to CHART on symbol change
  const prevSymbol = useRef(activeSymbol);
  useEffect(() => {
    if (prevSymbol.current !== activeSymbol) {
      useCockpitStore.getState().setCanvasMode('CHART');
      prevSymbol.current = activeSymbol;
    }
  }, [activeSymbol]);

  return (
    <div className="canvas-root">
      <CanvasTabBar currentMode={canvasMode} />
      <CanvasView mode={canvasMode} />
    </div>
  );
}

function CanvasView({ mode }: { mode: CanvasMode }) {
  switch (mode) {
    case 'CHART':           return <ChartView />;
    case 'EOD_SCAN':        return <EodScanView />;
    case 'HEATMAP':         return <HeatmapView />;
    case 'PORTFOLIO':       return <PortfolioView />;
    case 'OPTIONS_BUILDER': return <OptionsBuilderView />;
  }
}
```

### Mode Transition Rules

| From | To | Trigger |
|---|---|---|
| Any | CHART | Symbol changes in watchlist |
| Any | EOD_SCAN | User clicks "SCAN" tab |
| CHART | OPTIONS_BUILDER | User clicks "Build Strategy" in SignalPanel |
| Any | HEATMAP | User clicks "HEAT" tab |
| Any | PORTFOLIO | User clicks "PORT" tab |
| OPTIONS_BUILDER | CHART | User clicks "Back to Chart" |

Tabs are disabled during market session for EOD_SCAN (EOD data only available post 3:30 PM). The CanvasTabBar renders tabs as disabled with a tooltip when outside allowed time window.

---

## 4. Zero Prop Drilling Strategy

### Rule

No component passes trading domain data as props beyond one level deep. Components receive only display-ready values (strings, numbers, booleans) as props. All domain state is fetched via hooks inside the component that needs it.

### Pattern by Layer

**Zone roots** — read from stores and queries via hooks:

```typescript
// CORRECT: zone root fetches its own data
function SignalPanel() {
  const { signal, sizing, symbol } = useSignalPanelData(); // hook reads store + query
  return <SignalPanelLayout signal={signal} sizing={sizing} symbol={symbol} />;
}
```

**Layout components** — receive only display-ready values:

```typescript
// CORRECT: layout component receives primitives
function SignalPanelLayout({ signal, sizing, symbol }: SignalPanelProps) {
  return (
    <>
      <ScoreDisplay grade={signal.grade} score={signal.score} />
      <SizingPanel qty={sizing.suggestedQty} product={sizing.product} />
    </>
  );
}
```

**Leaf components** — receive only what they display:

```typescript
// CORRECT: leaf component has no knowledge of Zustand or TanStack Query
function ScoreDisplay({ grade, score }: { grade: SignalGrade; score: number }) {
  return <div className={gradeColorClass(grade)}>{score}</div>;
}
```

### Cross-Zone Communication

When Zone A needs to trigger an action in Zone B, it writes to a store — never calls a function on Zone B directly:

```typescript
// Signal panel "Trade" button → pre-trade overlay in orders feature
// CORRECT approach:
function SizingPanel() {
  const openOverlay = useOrdersStore((s) => s.openPreTradeOverlay);
  return <Button onClick={() => openOverlay(orderParams)}>Trade</Button>;
}
```

---

## 5. Cockpit Layout and Zone Boundaries

### Fixed Zone Assignments

The cockpit has five permanent zones. Their position and minimum sizes are fixed in the widget registry. Users can resize within constraints but cannot remove zones.

```
┌─────────────────────────────────────────────────────────────┐
│ RISK BAR (always 1 line, full width, not resizable)         │
├────────────────────┬────────────────────────────────────────┤
│                    │                                        │
│  SIGNAL PANEL      │         PRIMARY CANVAS                 │
│  (fixed width      │         (flexible, takes remaining)    │
│   ~280px)          │                                        │
│                    │                                        │
├────────────────────┴─────────────────┬─────────────────────┤
│                                      │                      │
│  (Signal panel bottom continues)     │  MARKET CONTEXT      │
│                                      │  PANEL               │
│                                      │                      │
├──────────────────────────────────────┴─────────────────────┤
│ POSITIONS STRIP (always 1-4 lines depending on positions)   │
└─────────────────────────────────────────────────────────────┘
```

### Widget Registry

```typescript
// core/layout-engine/widget-registry.ts
export const WIDGET_REGISTRY: Record<WidgetId, WidgetConfig> = {
  'risk-bar': {
    component: RiskBar,
    defaultLayout: { x: 0, y: 0, w: 24, h: 1 },
    minW: 24, maxW: 24, minH: 1, maxH: 1,  // not resizable
    isDraggable: false,
    isResizable: false,
  },
  'signal-panel': {
    component: SignalPanel,
    defaultLayout: { x: 0, y: 1, w: 6, h: 14 },
    minW: 5, maxW: 8, minH: 10, maxH: 20,
  },
  'primary-canvas': {
    component: PrimaryCanvas,
    defaultLayout: { x: 6, y: 1, w: 18, h: 14 },
    minW: 12, minH: 8,
  },
  'market-context': {
    component: MarketContextPanel,
    defaultLayout: { x: 14, y: 15, w: 10, h: 8 },
    minW: 8, minH: 6,
  },
  'positions-strip': {
    component: PositionsStrip,
    defaultLayout: { x: 0, y: 23, w: 24, h: 4 },
    minW: 24, maxW: 24, minH: 2, maxH: 6,
    isDraggable: false,
  },
};
```

---

## 6. Core Infrastructure Layer

### WebSocket Manager

The manager owns two WebSocket connections. It is instantiated once at app startup and persisted for the session. It is not a React component — it is a plain class instantiated in `core/websocket/ws-manager.ts` and referenced via a module-level singleton.

```typescript
class WebSocketManager {
  private marketFeed: WebSocketConnection;
  private cockpitFeed: WebSocketConnection;

  constructor(baseUrl: string, token: string) {
    this.marketFeed = new WebSocketConnection(`${baseUrl}/ws/market-feed`, token);
    this.cockpitFeed = new WebSocketConnection(`${baseUrl}/ws/cockpit`, token);
  }

  subscribeSymbol(symbol: string, interval: CandleInterval): void;
  unsubscribeSymbol(symbol: string): void;
  getConnectionStatus(): { marketFeed: WsStatus; cockpitFeed: WsStatus };
}
```

Full reconnection and message routing design is in `04-realtime.md`.

### Data Bus

The Data Bus is a typed event dispatcher. WS handlers parse raw messages and emit typed events. React hooks subscribe to events relevant to their component.

```typescript
// core/data-bus/data-bus.ts
type DataBusEventMap = {
  'tick': TickEvent;
  'candle:update': CandleUpdateEvent;
  'candle:close': CandleCloseEvent;
  'signal': SignalEvent;
  'position:update': PositionUpdateEvent;
  'risk:update': RiskUpdateEvent;
  'conversion:candidates': ConversionCandidatesEvent;
  'alert': AlertEvent;
};

export const dataBus = new TypedEventEmitter<DataBusEventMap>();
```

### Layout Persistence

Panel layout is saved to `localStorage` under key `cockpit-layout-v1`. On startup, the layout engine loads the saved layout and merges it with the widget registry defaults. If a widget is missing from the saved layout, its registry default is used.

---

## 7. Feature Module Contracts

Each feature module must satisfy this contract:

1. **Public API via `index.ts`** — the feature exports only what other features need. Internal components are not exported.
2. **No direct store writes from leaf components** — only hooks may write to stores.
3. **No direct backend calls from components** — only hooks from `datasources/` may initiate fetches.
4. **Self-contained types** — if a type is only used within one feature, it lives in that feature. Shared domain types live in `shared/types/`.
5. **One root component** — each feature has one root component that is the entry point for the layout engine.

---

## 8. Adapter Layer

Adapters transform backend response DTOs into UI view models. They live in `adapters/` and are pure functions — no side effects.

```typescript
// adapters/signal.adapter.ts
export function adaptSignal(dto: SignalResponseDTO): SignalViewModel {
  return {
    symbol: dto.symbol,
    score: dto.composite_score,
    grade: scoreToGrade(dto.composite_score),       // 0-100 → A/B/C/D
    direction: dto.direction,
    factors: dto.factors.map(adaptSignalFactor),
    keyLevels: {
      sl: dto.stop_loss,
      target1: dto.target_1,
      target2: dto.target_2,
      confluence: dto.confluence_zones,
    },
    sizing: adaptSizing(dto.sizing, dto.direction),
    computedAt: new Date(dto.computed_at),
  };
}
```

Adapters are called in TanStack Query `select` functions, so the query cache stores already-adapted view models:

```typescript
export function useSignal(symbol: string) {
  return useQuery({
    queryKey: ['signal', symbol],
    queryFn: () => fetchSignal(symbol),
    select: adaptSignal,                 // transform on the way into cache
    staleTime: 30_000,
  });
}
```

---

## 9. Routing

The cockpit is a single-page application with minimal routing. TanStack Router manages three routes:

```typescript
const routeTree = rootRoute.addChildren([
  indexRoute,    // / → redirect to /cockpit if authenticated
  authRoute,     // /auth → login page
  cockpitRoute,  // /cockpit → main cockpit (protected)
]);
```

Deep-linking is supported for the active symbol via a search parameter:

```
/cockpit?symbol=RELIANCE&exchange=NSE
```

On load, the cockpit reads `symbol` and `exchange` from the URL and sets them as the initial `activeSymbol` in the store. On symbol change, the URL is updated via `router.navigate` with `replace: true` (no history entry per symbol click).

---

## 10. Error Boundaries and Fallback Strategy

Each zone is wrapped in an independent ErrorBoundary. A crash in the SignalPanel does not take down the Chart or Positions strip.

```typescript
// For each zone in CockpitGrid:
<ErrorBoundary
  fallback={<ZoneFallback zoneId="signal-panel" />}
  onError={(error) => reportError(error, { zone: 'signal-panel' })}
>
  <SignalPanel />
</ErrorBoundary>
```

**Fallback behavior by zone:**

| Zone | Fallback when crashed |
|---|---|
| RiskBar | Shows static "Risk data unavailable" — trading is blocked until resolved |
| SignalPanel | Shows "Signal unavailable" — user can still trade manually |
| PrimaryCanvas | Shows "Chart unavailable" with reload button |
| MarketContextPanel | Shows "Context unavailable" — collapsible panel hides |
| PositionsStrip | Shows last known positions with stale indicator — no new data |

WebSocket connection errors are handled by the WS Manager (reconnection), not by ErrorBoundary. ErrorBoundary is only for render-time JavaScript errors.
