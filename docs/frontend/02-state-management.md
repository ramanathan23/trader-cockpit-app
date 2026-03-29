# State Management Design
## Trader Cockpit App

**Last Updated:** 2026-03-29
**Document:** 02 of 06

---

## Table of Contents

1. [State Architecture Overview](#1-state-architecture-overview)
2. [Zustand Stores](#2-zustand-stores)
3. [TanStack Query v5 — Server State](#3-tanstack-query-v5--server-state)
4. [WebSocket Integration](#4-websocket-integration)
5. [Data Flow Walkthrough](#5-data-flow-walkthrough)
6. [Cache Invalidation Strategy](#6-cache-invalidation-strategy)
7. [Derived State and Selectors](#7-derived-state-and-selectors)

---

## 1. State Architecture Overview

State in the cockpit is divided into three categories, each managed by a different layer:

| Category | Manager | Examples |
|---|---|---|
| UI state | Zustand (3 stores) | Active symbol, canvas mode, daily P&L limits |
| Server state | TanStack Query v5 | Candle history, signal scores, positions, watchlist |
| Real-time push | WebSocket + Data Bus | Live ticks, candle updates, P&L changes |

**Rule:** TanStack Query owns all REST data. Zustand owns UI state and the in-session aggregates (risk counters, connection status). WebSocket data flows through the Data Bus and writes either into Zustand stores or into TanStack Query's cache via `queryClient.setQueryData`.

There is no Redux. There is no React context for trading domain state. There are no local `useState` calls for state that needs to be shared across zones.

---

## 2. Zustand Stores

### 2.1 cockpitStore

Owns the active symbol and all UI navigation state. This is the most-subscribed store in the application — all five zones read from it.

```typescript
// store/cockpit.store.ts
import { create } from 'zustand';
import { persist, subscribeWithSelector } from 'zustand/middleware';

export type CandleInterval = '5min' | '15min' | '25min' | '60min' | '1D';
export type CanvasMode = 'CHART' | 'EOD_SCAN' | 'HEATMAP' | 'PORTFOLIO' | 'OPTIONS_BUILDER';

interface CockpitState {
  // Active symbol
  activeSymbol: string;
  activeExchange: 'NSE' | 'BSE';

  // Canvas
  canvasMode: CanvasMode;
  selectedInterval: CandleInterval;

  // Layout
  layoutConfig: ReactGridLayout.Layout[];
  isEditMode: boolean;

  // Actions
  setActiveSymbol: (symbol: string, exchange: 'NSE' | 'BSE') => void;
  setCanvasMode: (mode: CanvasMode) => void;
  setSelectedInterval: (interval: CandleInterval) => void;
  setLayoutConfig: (config: ReactGridLayout.Layout[]) => void;
  toggleEditMode: () => void;
}

export const useCockpitStore = create<CockpitState>()(
  subscribeWithSelector(
    persist(
      (set) => ({
        activeSymbol: 'NIFTY50',
        activeExchange: 'NSE',
        canvasMode: 'CHART',
        selectedInterval: '15min',
        layoutConfig: DEFAULT_LAYOUT,
        isEditMode: false,

        setActiveSymbol: (symbol, exchange) =>
          set({
            activeSymbol: symbol,
            activeExchange: exchange,
            canvasMode: 'CHART',  // always reset canvas on symbol change
          }),

        setCanvasMode: (mode) => set({ canvasMode: mode }),
        setSelectedInterval: (interval) => set({ selectedInterval: interval }),
        setLayoutConfig: (config) => set({ layoutConfig: config }),
        toggleEditMode: () => set((s) => ({ isEditMode: !s.isEditMode })),
      }),
      {
        name: 'cockpit-store-v1',
        partialize: (s) => ({
          activeSymbol: s.activeSymbol,
          activeExchange: s.activeExchange,
          selectedInterval: s.selectedInterval,
          layoutConfig: s.layoutConfig,
        }),
      }
    )
  )
);
```

**What is persisted:** Active symbol, exchange, selected interval, and layout config survive page refresh. Canvas mode is not persisted — always starts on CHART.

**Subscriptions used outside React:** The WebSocket manager subscribes to `activeSymbol` changes via Zustand's `subscribeWithSelector` middleware to manage market feed subscriptions without needing a React component:

```typescript
// core/websocket/ws-manager.ts
useCockpitStore.subscribe(
  (state) => state.activeSymbol,
  (newSymbol, prevSymbol) => {
    wsManager.unsubscribeSymbol(prevSymbol);
    wsManager.subscribeSymbol(newSymbol, useCockpitStore.getState().selectedInterval);
  }
);
```

---

### 2.2 riskStore

Owns in-session risk tracking. Updated by the Data Bus when `RISK_UPDATE` or `POSITION_UPDATE` messages arrive from the cockpit WebSocket feed.

```typescript
// store/risk.store.ts
import { create } from 'zustand';

export type ConnectionStatus = 'CONNECTED' | 'RECONNECTING' | 'FAILED' | 'STALE';
export type RiskLevel = 'NORMAL' | 'CAUTION' | 'WARNING' | 'BLOCKED';

interface RiskState {
  // P&L tracking
  dailyPnl: number;
  dailyLimitConsumed: number;      // 0–1 fraction of daily loss limit
  dailyLimitAmount: number;        // absolute limit in INR

  // Position tracking
  intradayPositionCount: number;
  cncDeployed: number;             // INR deployed in CNC positions
  openIntradayExposure: number;    // INR gross exposure

  // Risk level (derived, but stored for RiskBar color)
  riskLevel: RiskLevel;

  // Connection status
  marketFeedStatus: ConnectionStatus;
  cockpitFeedStatus: ConnectionStatus;
  lastMarketFeedAt: number | null;   // epoch ms
  lastCockpitFeedAt: number | null;

  // Actions
  applyRiskUpdate: (update: RiskUpdatePayload) => void;
  setConnectionStatus: (feed: 'market' | 'cockpit', status: ConnectionStatus) => void;
  setLastFeedTime: (feed: 'market' | 'cockpit', ts: number) => void;
}

export const useRiskStore = create<RiskState>()((set, get) => ({
  dailyPnl: 0,
  dailyLimitConsumed: 0,
  dailyLimitAmount: 0,
  intradayPositionCount: 0,
  cncDeployed: 0,
  openIntradayExposure: 0,
  riskLevel: 'NORMAL',
  marketFeedStatus: 'CONNECTING' as ConnectionStatus,
  cockpitFeedStatus: 'CONNECTING' as ConnectionStatus,
  lastMarketFeedAt: null,
  lastCockpitFeedAt: null,

  applyRiskUpdate: (update) => {
    const consumed = update.daily_loss / update.daily_limit;
    set({
      dailyPnl: update.daily_pnl,
      dailyLimitConsumed: consumed,
      dailyLimitAmount: update.daily_limit,
      intradayPositionCount: update.intra_position_count,
      cncDeployed: update.cnc_deployed,
      openIntradayExposure: update.intra_exposure,
      riskLevel: deriveRiskLevel(consumed),
    });
  },

  setConnectionStatus: (feed, status) =>
    set(feed === 'market'
      ? { marketFeedStatus: status }
      : { cockpitFeedStatus: status }),

  setLastFeedTime: (feed, ts) =>
    set(feed === 'market'
      ? { lastMarketFeedAt: ts }
      : { lastCockpitFeedAt: ts }),
}));

function deriveRiskLevel(consumed: number): RiskLevel {
  if (consumed >= 1.0)  return 'BLOCKED';
  if (consumed >= 0.8)  return 'WARNING';
  if (consumed >= 0.6)  return 'CAUTION';
  return 'NORMAL';
}
```

**riskStore is never persisted.** It rebuilds from WebSocket on every session start. This prevents stale risk state from the previous day from appearing.

---

### 2.3 sessionStore

Owns auth state. Written to by the login flow and cleared on logout.

```typescript
// store/session.store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SessionState {
  userId: string | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (userId: string, token: string) => void;
  logout: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      userId: null,
      token: null,
      isAuthenticated: false,
      login: (userId, token) => set({ userId, token, isAuthenticated: true }),
      logout: () => set({ userId: null, token: null, isAuthenticated: false }),
    }),
    { name: 'session-store-v1' }
  )
);
```

---

## 3. TanStack Query v5 — Server State

### Query Client Configuration

```typescript
// main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,           // 30s default — most data is fairly stable
      gcTime: 5 * 60_000,          // 5 min cache retention after unmount
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
      refetchOnWindowFocus: false, // trading app, not a blog
    },
  },
});
```

### Query Keys Convention

All query keys follow a consistent hierarchy for precise invalidation:

```typescript
// shared/query-keys.ts
export const queryKeys = {
  watchlist:            () => ['watchlist'] as const,
  signal:    (symbol: string) => ['signal', symbol] as const,
  candles:   (symbol: string, interval: CandleInterval) =>
                              ['candles', symbol, interval] as const,
  positions:            () => ['positions'] as const,
  conversionCandidates: () => ['conversion-candidates'] as const,
  optionStrategies:     () => ['option-strategies'] as const,
  optionStrategy: (id: string) => ['option-strategies', id] as const,
  marketContext: (symbol: string) => ['market-context', symbol] as const,
  tradeHistory:  (symbol: string) => ['trade-history', symbol] as const,
};
```

### Core Query Hooks

**useWatchlist**
```typescript
// datasources/rest/queries/use-watchlist.ts
export function useWatchlist() {
  return useQuery({
    queryKey: queryKeys.watchlist(),
    queryFn: () => apiFetch<WatchlistDTO>('/api/watchlist'),
    staleTime: 24 * 60 * 60_000,   // watchlist changes rarely — cache all day
    select: (dto) => dto.symbols.map(adaptWatchlistItem),
  });
}
```

**useSignal**
```typescript
// datasources/rest/queries/use-signal.ts
export function useSignal(symbol: string) {
  return useQuery({
    queryKey: queryKeys.signal(symbol),
    queryFn: () => apiFetch<SignalDTO>(`/api/signal/${symbol}`),
    staleTime: 30_000,              // signal valid for 30s, refresh on next candle close
    enabled: !!symbol,
    select: adaptSignal,
  });
}
```

**useCandles**
```typescript
// datasources/rest/queries/use-candles.ts
export function useCandles(symbol: string, interval: CandleInterval) {
  return useQuery({
    queryKey: queryKeys.candles(symbol, interval),
    queryFn: () => apiFetch<CandleDTO[]>(
      `/api/candles/${symbol}?interval=${interval}&limit=300`
    ),
    staleTime: intervalToMs(interval),  // stale after one candle period
    enabled: !!symbol,
    select: (dtos) => dtos.map(adaptCandle),
    placeholderData: keepPreviousData,  // keep old chart while loading new symbol
  });
}
```

**usePositions**
```typescript
// datasources/rest/queries/use-positions.ts
export function usePositions() {
  return useQuery({
    queryKey: queryKeys.positions(),
    queryFn: () => apiFetch<PositionDTO[]>('/api/positions'),
    staleTime: 3_000,               // positions from REST are backup — WS is primary
    refetchInterval: 3_000,         // poll every 3s matching backend poll cycle
    select: (dtos) => dtos.map(adaptPosition),
  });
}
```

**useConversionCandidates**
```typescript
export function useConversionCandidates() {
  const { isConversionWindow } = useMarketSession();
  return useQuery({
    queryKey: queryKeys.conversionCandidates(),
    queryFn: () => apiFetch<ConversionCandidateDTO[]>('/api/positions/conversion-candidates'),
    enabled: isConversionWindow,   // only active after 2:45 PM
    staleTime: 30_000,
    select: (dtos) => dtos.map(adaptConversionCandidate),
  });
}
```

**useOptionStrategies**
```typescript
export function useOptionStrategies() {
  return useQuery({
    queryKey: queryKeys.optionStrategies(),
    queryFn: () => apiFetch<OptionStrategyDTO[]>('/api/options/strategies'),
    staleTime: 10_000,
    select: (dtos) => dtos.map(adaptOptionStrategy),
  });
}
```

### Mutation Hooks

**usePlaceOrder**
```typescript
// datasources/rest/mutations/use-place-order.ts
export function usePlaceOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: PlaceOrderParams) =>
      apiFetch<OrderResponseDTO>('/api/orders', {
        method: 'POST',
        body: JSON.stringify(adaptOrderParams(params)),
      }),
    onSuccess: (response) => {
      // Optimistically assume position will update — backend confirms via WS
      queryClient.invalidateQueries({ queryKey: queryKeys.positions() });
    },
    onError: (error) => {
      useRiskStore.getState().addAlert({
        type: 'ORDER_FAILED',
        message: extractErrorMessage(error),
        severity: 'ERROR',
      });
    },
  });
}
```

**useConvertPosition**
```typescript
export function useConvertPosition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: ConversionParams) =>
      apiFetch<void>('/api/positions/convert', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.positions() });
      queryClient.invalidateQueries({ queryKey: queryKeys.conversionCandidates() });
    },
  });
}
```

**usePlaceOptionStrategy**
```typescript
export function usePlaceOptionStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategy: OptionStrategyParams) =>
      apiFetch<OptionStrategyResponseDTO>('/api/options/strategies', {
        method: 'POST',
        body: JSON.stringify(strategy),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.optionStrategies() });
      queryClient.invalidateQueries({ queryKey: queryKeys.positions() });
    },
  });
}
```

### Refetch Strategy Summary

| Query | staleTime | refetchInterval | Trigger |
|---|---|---|---|
| watchlist | 24 hours | — | Session start only |
| signal | 30s | — | On candle close (via WS event → invalidate) |
| candles | 1 candle period | — | On symbol/interval change |
| positions | 3s | 3s | Continuous poll + WS invalidation |
| conversionCandidates | 30s | — | 2:45–3:20 PM window only |
| optionStrategies | 10s | — | On strategy order fill |
| marketContext | 60s | — | On symbol change |

---

## 4. WebSocket Integration

### Architecture

Two WebSocket connections are maintained. They are managed outside React by the `WebSocketManager` singleton. React components never interact with WebSocket directly — they consume state from Zustand or TanStack Query.

```
Backend FastAPI
    │
    ├── /ws/market-feed ─────────────────────────────────────────┐
    │   (TICK, CANDLE_UPDATE, CANDLE_CLOSE)                      │
    │                                                            ▼
    └── /ws/cockpit ─────────────────────────────────────────────┤
        (SIGNAL, ALERT, POSITION_UPDATE, RISK_UPDATE,            │
         STRATEGY_UPDATE, CONVERSION_CANDIDATES)                 │
                                                                 │
                                              WebSocketManager   │
                                                     │           │
                                                Data Bus         │
                                                     │           │
                         ┌───────────────────────────┼───────────┘
                         │                           │
                    riskStore               TanStack Query
                    cockpitStore            queryClient.setQueryData
                    (alerts, status)        (candles, positions, signal)
```

### useMarketFeed Hook

Components subscribe to the market feed via this hook. The hook manages symbol subscription lifecycle.

```typescript
// datasources/ws/use-market-feed.ts
export function useMarketFeed(symbols: string[]) {
  const interval = useCockpitStore((s) => s.selectedInterval);

  useEffect(() => {
    const manager = getWsManager();
    symbols.forEach((sym) => manager.subscribeSymbol(sym, interval));

    return () => {
      symbols.forEach((sym) => manager.unsubscribeSymbol(sym));
    };
  }, [symbols, interval]);
}
```

**Usage in ChartView:**
```typescript
function ChartView() {
  const { activeSymbol } = useActiveSymbol();
  useMarketFeed([activeSymbol]);  // subscribe current symbol to get live candles
  // ...
}
```

**Usage in PositionsStrip:**
```typescript
function PositionsStrip() {
  const { data: positions } = usePositions();
  const positionSymbols = positions?.map((p) => p.symbol) ?? [];
  useMarketFeed(positionSymbols);  // subscribe all open position symbols
}
```

### useCockpitFeed Hook

The cockpit feed carries non-price data. Components call this hook to confirm they want the feed active. The feed itself runs continuously regardless — this hook is mainly for lifecycle management and optional per-component filtering.

```typescript
// datasources/ws/use-cockpit-feed.ts
export function useCockpitFeed() {
  const status = useRiskStore((s) => s.cockpitFeedStatus);

  // Returns feed status so components can show connection indicator
  return { status };
}
```

Signal and position updates from this feed write directly into TanStack Query's cache via `queryClient.setQueryData` in the Data Bus handlers — no polling needed for real-time data.

### Reconnection Logic

```typescript
// core/websocket/ws-connection.ts
class WebSocketConnection {
  private attempts = 0;
  private maxAttempts = 5;
  private backoffMs = [1000, 2000, 4000, 8000, 16000, 30000];

  private reconnect(): void {
    if (this.attempts >= this.maxAttempts) {
      useRiskStore.getState().setConnectionStatus(this.feedType, 'FAILED');
      // Show persistent alert — user must manually reconnect
      return;
    }
    const delay = this.backoffMs[Math.min(this.attempts, this.backoffMs.length - 1)];
    this.attempts++;
    useRiskStore.getState().setConnectionStatus(this.feedType, 'RECONNECTING');
    setTimeout(() => this.connect(), delay);
  }

  private onConnected(): void {
    this.attempts = 0;
    useRiskStore.getState().setConnectionStatus(this.feedType, 'CONNECTED');
    this.resubscribeAll();  // re-send all active subscriptions after reconnect
  }
}
```

### Stale Feed Indicator

The RiskBar connection indicator reads feed timestamps to compute staleness:

```typescript
// features/risk-bar/risk-bar.hooks.ts
export function useConnectionIndicator() {
  const { lastMarketFeedAt, marketFeedStatus } = useRiskStore();
  const [now, setNow] = useState(Date.now);

  // Update every second
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const silentMs = lastMarketFeedAt ? now - lastMarketFeedAt : Infinity;

  if (marketFeedStatus === 'FAILED') return 'RED';
  if (silentMs > 30_000) return 'RED';
  if (silentMs > 5_000) return 'AMBER';
  return 'GREEN';
}
```

### Heartbeat

The WebSocket manager sends a ping frame every 10 seconds on both connections. If a pong is not received within 5 seconds, the connection is considered dead and reconnection begins immediately (skipping the backoff for the first retry).

---

## 5. Data Flow Walkthrough

### Scenario: User clicks RELIANCE in the watchlist

This walkthrough traces the complete state and data changes triggered by a single symbol click.

**Step 1 — User interaction**
```
WatchlistSidebar → calls setActiveSymbol("RELIANCE", "NSE")
```

**Step 2 — Store update (synchronous)**
```
cockpitStore.activeSymbol = "RELIANCE"
cockpitStore.canvasMode   = "CHART"  (reset on symbol change)
```

**Step 3 — Zustand notifies subscribers (synchronous, parallel)**
```
SignalPanel subscriber fires       → useSignal("RELIANCE") becomes active query
PrimaryCanvas subscriber fires     → useCandles("RELIANCE", "15min") becomes active query
MarketContextPanel subscriber fires → useMarketContext("RELIANCE") becomes active query
URL router listener fires          → URL updates to /cockpit?symbol=RELIANCE&exchange=NSE
WebSocket subscriber fires         → unsubscribe("HDFC"), subscribe("RELIANCE", "15min")
```

**Step 4 — TanStack Query responses (async, parallel)**
```
useSignal("RELIANCE"):
  - If cache hit and not stale: renders immediately from cache
  - If cache miss: shows loading state, fetches /api/signal/RELIANCE
  - On response: adaptSignal(dto) → SignalPanel renders with RELIANCE signal

useCandles("RELIANCE", "15min"):
  - If previous symbol (HDFC) candles were cached: keepPreviousData shows HDFC
    chart temporarily while RELIANCE loads (no blank flash)
  - Fetches /api/candles/RELIANCE?interval=15min&limit=300
  - On response: ChartView rebuilds ECharts dataset

useMarketContext("RELIANCE"):
  - Fetches /api/market-context/RELIANCE
  - MarketContextPanel shows RELIANCE index correlation, sector, peers
```

**Step 5 — WebSocket subscription active**
```
Backend sends TICK events for RELIANCE:
  → Data Bus receives TICK
  → candle.handler.ts updates the live candle in TanStack Query cache
  → ChartView's ECharts instance updates last candle in-place (no re-render)

Backend sends CANDLE_CLOSE for RELIANCE 15min:
  → Data Bus receives CANDLE_CLOSE
  → candle.handler.ts appends completed candle to query cache
  → queryClient.invalidateQueries(['signal', 'RELIANCE'])
  → Fresh signal request fires → SignalPanel updates

Backend sends POSITION_UPDATE:
  → Data Bus receives POSITION_UPDATE
  → queryClient.setQueryData(['positions'], adapted positions)
  → PositionsStrip re-renders with latest P&L (was already subscribed)
```

**Step 6 — Panels that do NOT re-render on symbol change**
```
RiskBar: reads riskStore (daily limits) — unchanged by symbol click
PositionsStrip: reads positions query — unchanged by symbol click
  (positions for HDFC and RELIANCE are both in the positions array regardless of active symbol)
```

### Outcome

All five zones are updated within one render cycle (Zustand subscriptions) plus two async ticks (HTTP responses). The user sees RELIANCE data in the signal panel, chart, and context panel within the normal network round-trip time (~100–200ms on a local network, ~200–400ms on internet). The positions strip and risk bar are unaffected.

---

## 6. Cache Invalidation Strategy

### Invalidation Triggers

| Event | Query to invalidate | How triggered |
|---|---|---|
| Order fill (from WS POSITION_UPDATE) | `['positions']` | Data Bus position handler |
| Candle close (from WS CANDLE_CLOSE) | `['signal', symbol]` | Data Bus candle handler |
| Conversion complete (mutation success) | `['positions']`, `['conversion-candidates']` | useMutation onSuccess |
| Strategy placed (mutation success) | `['option-strategies']`, `['positions']` | useMutation onSuccess |
| Order failed | None (no state change) | Show alert only |
| Session start | All queries | `queryClient.clear()` on login |

### Real-time Writes vs Invalidation

For frequently updated data (positions, candles), the Data Bus writes directly into the query cache using `queryClient.setQueryData` rather than invalidating. This prevents unnecessary refetch network calls.

```typescript
// core/data-bus/handlers/position.handler.ts
export function handlePositionUpdate(event: PositionUpdateEvent) {
  const adapted = event.positions.map(adaptPosition);
  queryClient.setQueryData(queryKeys.positions(), adapted);
  // No HTTP refetch needed — data is fresh from the backend push
}
```

For less frequent data (signal on candle close), invalidation is used so the full calculation runs on the backend:

```typescript
// core/data-bus/handlers/candle.handler.ts
export function handleCandleClose(event: CandleCloseEvent) {
  // Append to candle cache
  const currentCandles = queryClient.getQueryData<Candle[]>(
    queryKeys.candles(event.symbol, event.interval)
  ) ?? [];
  queryClient.setQueryData(
    queryKeys.candles(event.symbol, event.interval),
    [...currentCandles, adaptCandle(event.candle)]
  );

  // Trigger signal refresh for active symbol only
  const activeSymbol = useCockpitStore.getState().activeSymbol;
  if (event.symbol === activeSymbol) {
    queryClient.invalidateQueries({ queryKey: queryKeys.signal(event.symbol) });
  }
}
```

---

## 7. Derived State and Selectors

Derived values that are computed from store state are computed in hooks or selectors — never stored as redundant state.

```typescript
// shared/hooks/use-risk-summary.ts
export function useRiskSummary() {
  return useRiskStore((state) => ({
    pnlDisplay: formatCurrency(state.dailyPnl),
    limitBar: state.dailyLimitConsumed,        // 0–1 for CSS width
    limitColor: riskLevelToColor(state.riskLevel),
    isBlocked: state.riskLevel === 'BLOCKED',
    intradayCount: state.intradayPositionCount,
    cncDisplay: formatCurrency(state.cncDeployed),
  }));
}
```

```typescript
// features/signal-panel/signal-panel.hooks.ts
export function useSizingRecommendation() {
  const { data: signal } = useSignal(useCockpitStore.getState().activeSymbol);
  const { isBlocked } = useRiskSummary();

  // Sizing is derived from signal + risk state — never stored separately
  return {
    suggestedQty: signal ? computeQty(signal, useRiskStore.getState()) : 0,
    isTradeAllowed: !isBlocked && !!signal && signal.grade !== 'D',
    product: inferProduct(signal),
  };
}
```

Memoization is used in selectors that compute expensive values (e.g., payoff curve data points for options strategies). These use `useMemo` inside the hook, keyed on the strategy parameters.
