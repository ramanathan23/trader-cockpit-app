# 04 — Real-Time Data

How the frontend handles live market data: WebSocket management, tick processing, live candle building, and position polling.

---

## Two WebSocket Channels

The backend exposes two separate WebSocket endpoints. Each has a distinct concern.

### `/ws/market-feed` — Market Data

Carries ticks, candle updates, and option chain snapshots.

```typescript
type MarketFeedMessage =
  | { type: 'TICK';                symbol: string; price: number; volume: number; timestamp: string }
  | { type: 'CANDLE_CLOSE';        symbol: string; interval: string; candle: Candle }
  | { type: 'CANDLE_LIVE';         symbol: string; interval: string; candle: Candle }
  | { type: 'OPTION_CHAIN_UPDATE'; underlying: string; data: OptionChainSnapshot }
  | { type: 'CONNECTION_STATUS';   status: 'connected' | 'reconnecting' | 'degraded' }
  | { type: 'DATA_STALE';          source: string; seconds_since_last: number }

// Outbound (subscribe/unsubscribe)
type MarketFeedCommand =
  | { type: 'SUBSCRIBE';   symbols: string[] }
  | { type: 'UNSUBSCRIBE'; symbols: string[] }
```

### `/ws/cockpit` — Application Events

Carries signals, order updates, position updates, and risk alerts.

```typescript
type CockpitMessage =
  | { type: 'SIGNAL_FIRED';       signal: Signal }
  | { type: 'ORDER_UPDATE';       order: Order }
  | { type: 'POSITION_UPDATE';    positions: Position[] }
  | { type: 'ALERT_FIRED';        alert: Alert }
  | { type: 'CSL_BREACH';         strategy_id: string; combined_pnl: number }
  | { type: 'CONVERSION_ELIGIBLE'; symbol: string; suggestion: ConversionSuggestion }
  | { type: 'RISK_LIMIT_WARN';    kind: 'DAILY_LOSS' | 'POSITION_COUNT'; pct_consumed: number }
  | { type: 'DAILY_LOSS_BLOCKED'; message: string }
  | { type: 'AUTO_SQUARE_OFF_WARN'; minutes_remaining: number }
```

---

## WebSocketManager

Single class manages one WebSocket connection with typed message routing and automatic reconnection.

```typescript
// src/lib/websocket/WebSocketManager.ts

type MessageHandler<T = unknown> = (msg: T) => void

class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 10
  private readonly baseDelayMs = 1000
  private readonly handlers = new Map<string, Set<MessageHandler>>()
  private disposed = false

  connect(url: string): void {
    this.url = url
    this.disposed = false
    this._open()
  }

  disconnect(): void {
    this.disposed = true
    this.ws?.close(1000, 'client disconnect')
    this.ws = null
  }

  /** Subscribe to a message type. Returns an unsubscribe function. */
  on<T>(type: string, handler: MessageHandler<T>): () => void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler as MessageHandler)
    return () => this.handlers.get(type)?.delete(handler as MessageHandler)
  }

  send(payload: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload))
    }
  }

  get connectionState(): 'connected' | 'connecting' | 'reconnecting' | 'disconnected' {
    if (!this.ws) return 'disconnected'
    if (this.ws.readyState === WebSocket.OPEN) return 'connected'
    if (this.reconnectAttempts > 0) return 'reconnecting'
    return 'connecting'
  }

  private _open(): void {
    this.ws = new WebSocket(this.url)
    this.ws.onopen    = () => { this.reconnectAttempts = 0 }
    this.ws.onmessage = (e) => this._dispatch(e)
    this.ws.onclose   = () => { if (!this.disposed) this._reconnect() }
    this.ws.onerror   = () => { this.ws?.close() }
  }

  private _dispatch(event: MessageEvent): void {
    const msg = JSON.parse(event.data as string)
    const type: string = msg.type
    this.handlers.get(type)?.forEach(h => h(msg))
    this.handlers.get('*')?.forEach(h => h(msg))   // wildcard listeners
  }

  private _reconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      sessionStore.getState().setWsStatus('failed')
      return
    }
    const delay = Math.min(
      this.baseDelayMs * Math.pow(2, this.reconnectAttempts),
      30_000,
    )
    this.reconnectAttempts++
    sessionStore.getState().setWsStatus('reconnecting')
    setTimeout(() => this._open(), delay)
  }
}

export const marketFeedWS = new WebSocketManager()
export const cockpitWS = new WebSocketManager()
```

---

## Subscription Lifecycle

Symbols are subscribed when they appear in the active watchlist or chart. Unsubscribed on unmount.

```typescript
// src/hooks/useSymbolTick.ts

export function useSymbolTick(symbol: string | null): Tick | null {
  const [tick, setTick] = useState<Tick | null>(null)

  useEffect(() => {
    if (!symbol) return

    // Tell backend to include this symbol in the feed
    marketFeedWS.send({ type: 'SUBSCRIBE', symbols: [symbol] })

    const unsub = marketFeedWS.on<MarketFeedMessage>('TICK', (msg) => {
      if (msg.symbol === symbol) setTick(msg)
    })

    return () => {
      unsub()
      marketFeedWS.send({ type: 'UNSUBSCRIBE', symbols: [symbol] })
    }
  }, [symbol])

  return tick
}
```

---

## Live Candle Building

The frontend maintains the in-progress candle in Zustand. ECharts updates directly — no React re-render per tick.

### Zustand Store Update

```typescript
// In cockpitStore — set up during app init
marketFeedWS.on<MarketFeedMessage>('TICK', (msg) => {
  const { activeSymbol, activeInterval } = cockpitStore.getState()
  if (msg.symbol !== activeSymbol) return

  cockpitStore.setState((state) => {
    const live = state.liveCandle
    if (!live) return state
    return {
      liveCandle: {
        ...live,
        high:   Math.max(live.high, msg.price),
        low:    Math.min(live.low, msg.price),
        close:  msg.price,
        volume: live.volume + msg.volume,
      },
    }
  })
})

marketFeedWS.on<MarketFeedMessage>('CANDLE_CLOSE', (msg) => {
  const { activeSymbol, activeInterval } = cockpitStore.getState()
  if (msg.symbol !== activeSymbol || msg.interval !== activeInterval) return

  // Push closed candle into TanStack Query cache
  queryClient.setQueryData<Candle[]>(
    ['candles', msg.symbol, msg.interval],
    (old = []) => [...old, msg.candle],
  )

  // Reset live candle — next tick opens a new one
  cockpitStore.setState({ liveCandle: null })
})
```

### ECharts In-Place Update (bypass React VDOM)

```typescript
// src/components/chart/CandleChart.tsx

export function CandleChart() {
  const chartRef = useRef<EChartsReactCore>(null)
  const historicalCandles = useCandleData()   // TanStack Query

  // Subscribe to liveCandle changes — update ECharts directly
  useEffect(() => {
    return cockpitStore.subscribe(
      (state) => state.liveCandle,
      (liveCandle) => {
        const instance = chartRef.current?.getEchartsInstance()
        if (!instance || !liveCandle) return

        const data = liveCandle
          ? [...(historicalCandles ?? []), liveCandle]
          : (historicalCandles ?? [])

        instance.setOption(
          { dataset: [{ source: data }] },
          { replaceMerge: ['dataset'] },   // no full re-render
        )
      },
    )
  }, [historicalCandles])

  return (
    <ReactECharts
      ref={chartRef}
      option={buildChartOption(historicalCandles ?? [])}
      style={{ height: '100%' }}
      notMerge={false}
    />
  )
}
```

The `replaceMerge: ['dataset']` flag tells ECharts to replace only the dataset series — canvas redraws only changed data points, not the full chart.

---

## Position Polling

Dhan has no real-time position WebSocket. The backend polls `GET /positions` every 3 seconds and the frontend polls the backend.

```typescript
// src/hooks/usePositions.ts

export function usePositions() {
  return useQuery({
    queryKey: ['positions'],
    queryFn: () => apiClient.get<Position[]>('/positions'),
    refetchInterval: 3_000,
    refetchIntervalInBackground: true,
    staleTime: 2_500,
  })
}
```

On order fill, the cockpit WebSocket pushes `POSITION_UPDATE` — frontend invalidates immediately:

```typescript
// App initialisation
cockpitWS.on('POSITION_UPDATE', () => {
  queryClient.invalidateQueries({ queryKey: ['positions'] })
})
```

This gives instant position refresh on fill (via push) with 3s polling as fallback. The two mechanisms are complementary.

---

## Data Staleness Indicators

The backend emits `DATA_STALE` when any source gap exceeds 5 seconds. The risk bar reflects this immediately.

```typescript
// src/stores/sessionStore.ts
type StalenessState = {
  marketFeed: 'fresh' | 'stale' | 'disconnected'
  positions: 'fresh' | 'stale'
  optionChain: 'fresh' | 'stale'
}

marketFeedWS.on<MarketFeedMessage>('DATA_STALE', (msg) => {
  sessionStore.getState().setStale(msg.source, msg.seconds_since_last)
})

marketFeedWS.on<MarketFeedMessage>('CONNECTION_STATUS', (msg) => {
  sessionStore.getState().setWsStatus(msg.status)
})
```

Risk bar display:
- `● LIVE` — green, all sources fresh
- `⚠ STALE 8s` — amber, source delayed
- `✕ DISCONNECTED` — red, reconnecting

---

## Alert Routing

Alerts from the cockpit channel are routed to the relevant zone:

```typescript
cockpitWS.on<CockpitMessage>('SIGNAL_FIRED', (msg) => {
  // Highlight watchlist row
  watchlistStore.getState().markSignal(msg.signal.symbol)
  // Show toast in signal panel
  toastSignal(msg.signal)
})

cockpitWS.on<CockpitMessage>('CSL_BREACH', (msg) => {
  // Show urgent modal — CSL flatten is automatic, inform trader
  showCslBreachAlert(msg)
})

cockpitWS.on<CockpitMessage>('RISK_LIMIT_WARN', (msg) => {
  if (msg.pct_consumed >= 100) {
    riskStore.getState().setOrderingBlocked(true)
  }
  riskStore.getState().setDailyLossConsumed(msg.pct_consumed)
})

cockpitWS.on<CockpitMessage>('CONVERSION_ELIGIBLE', (msg) => {
  // Surface conversion panel — this fires around 2:45 PM
  conversionStore.getState().addEligible(msg.symbol, msg.suggestion)
})

cockpitWS.on<CockpitMessage>('AUTO_SQUARE_OFF_WARN', (msg) => {
  // Show countdown in positions strip if > 0 INTRADAY positions open
  sessionStore.getState().setSquareOffWarning(msg.minutes_remaining)
})
```

---

## Paper Mode

Market feed WebSocket: identical — always real Dhan data.

Cockpit WebSocket events: `ORDER_UPDATE` and `POSITION_UPDATE` are published by `PaperFillMonitor` after each simulated fill. The frontend receives them exactly as it would from a live fill. No frontend code changes required for paper mode.

The only visible difference: the risk bar `[PAPER]` badge (amber), and order confirmation dialogs skip the live-order warning countdown.

---

## App Initialisation

Both WebSocket connections open at app start, before any component mounts:

```typescript
// src/main.tsx
marketFeedWS.connect(`${WS_BASE_URL}/ws/market-feed`)
cockpitWS.connect(`${WS_BASE_URL}/ws/cockpit`)

// Register global handlers
registerMarketFeedHandlers(marketFeedWS, cockpitStore, sessionStore)
registerCockpitHandlers(cockpitWS, queryClient, sessionStore)
```

Components subscribe to Zustand selectors and TanStack Query — they never directly handle WebSocket events.
