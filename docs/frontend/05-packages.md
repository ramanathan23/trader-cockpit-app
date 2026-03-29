# 05 — Package Evaluation

Every package decision for the frontend, with rationale and alternatives considered.

---

## Selection Criteria

1. **Bundle size** — tree-shakeable? Does it add dead weight?
2. **TypeScript quality** — first-class types, not bolted-on `@types/`
3. **React 18 compatibility** — concurrent mode, Suspense, transitions
4. **Active maintenance** — last release within 6 months
5. **Trading domain fit** — does it solve a real problem in this app?

---

## Core Stack (Locked In)

| Package | Version | Role |
|---------|---------|------|
| `react` + `react-dom` | 18.3.x | UI runtime — concurrent features |
| `typescript` | 5.5.x | Strict mode, discriminated unions for WS messages |
| `vite` | 5.x | Build tool — HMR, ESM-native, fast cold start |
| `@tanstack/react-query` | 5.x | Server state — polling, background refetch, stale-while-revalidate |
| `zustand` | 4.5.x | Client state — minimal boilerplate, selector subscriptions |
| `echarts` | 5.5.x | Charts — native candlestick, in-place dataset updates |
| `echarts-for-react` | 3.0.x | React wrapper — exposes ECharts instance ref |
| `tailwindcss` | 4.x | Styling — CSS variables, dark mode, no runtime |
| `@shadcn/ui` | latest | Component primitives — Radix-based, unstyled, accessible |
| `react-router-dom` | 6.x | Routing — minimal; cockpit is a single SPA |

---

## Chart Library: Why ECharts

Candlestick chart performance is the most critical frontend constraint. At 60fps tick updates, any library that triggers a full React re-render is disqualifying.

| Library | Tick Update Strategy | React Integration | Candlestick Native | Decision |
|---------|---------------------|-------------------|-------------------|----------|
| **ECharts** | `dataset.source` replace-merge — redraws only changed data, bypasses VDOM | `echarts-for-react` exposes instance ref | Yes | **Selected** |
| Recharts | Controlled component — full re-render on every data prop change | Native React | Via ComposedChart | Rejected |
| Lightweight Charts (TradingView) | Direct API (`update()` / `setData()`) — no React | Third-party wrappers only, no ref control | Yes | Viable but poor cross-chart linking |
| D3 | Imperative DOM — full control | Manual SVG manipulation | No (manual) | Overkill, massive implementation cost |
| Highcharts | Direct API | Official wrapper | Yes | Commercial licence required |

### ECharts In-Place Update Pattern

```typescript
// No React re-render on tick — ECharts redraws only changed dataset
instance.setOption(
  { dataset: [{ source: updatedCandleArray }] },
  { replaceMerge: ['dataset'] },
)
```

This is why ECharts + Zustand `subscribe()` is the combination: Zustand selector subscriptions trigger without React's VDOM, and ECharts updates the canvas directly.

---

## State Management: Why Zustand

| Library | Selector Subscriptions Outside React | Boilerplate | Re-render Control |
|---------|-------------------------------------|-------------|-------------------|
| **Zustand** | `store.subscribe(selector, cb)` — yes, bypasses VDOM | Minimal | Full |
| Redux Toolkit | No — must use React hooks, goes through VDOM | High | Needs `reselect` |
| Jotai | No `subscribeWithSelector` equivalent | Low | Limited |
| Context API | No — triggers full subtree re-render | None | Poor |

The `subscribe(selector, callback)` API is what makes the ECharts tick update pattern possible without React re-renders. This is a hard requirement.

Three Zustand stores:
- `cockpitStore` — active symbol, active interval, live candle state
- `riskStore` — daily loss consumed, ordering blocked flag
- `sessionStore` — WS connection status, staleness state, market session phase

---

## TanStack Query (React Query v5)

Used exclusively for server state — anything that comes from REST endpoints.

```typescript
// Polling positions every 3s (Dhan has no WS for positions)
const { data: positions } = useQuery({
  queryKey: ['positions'],
  queryFn: () => apiClient.get('/positions'),
  refetchInterval: 3_000,
  refetchIntervalInBackground: true,
  staleTime: 2_500,
})
```

Key features used:
- `refetchInterval` — position polling without manual `setInterval`
- `queryClient.setQueryData` — push candle data from WS without a REST call
- `queryClient.invalidateQueries` — force immediate refresh on position update event
- `staleTime` — prevent redundant requests within the same render cycle

---

## Date/Time: date-fns + date-fns-tz

**Not moment.js** (deprecated, 67KB gzipped, poor tree-shaking). **Not dayjs** (lightweight but timezone support relies on plugins that are harder to compose).

`date-fns` is tree-shakeable — import only what the code uses.

```typescript
import { isWithinInterval, set } from 'date-fns'
import { toZonedTime, formatInTimeZone } from 'date-fns-tz'

const IST = 'Asia/Kolkata'

function isMarketHours(): boolean {
  const now = toZonedTime(new Date(), IST)
  const open  = set(now, { hours: 9,  minutes: 15, seconds: 0, milliseconds: 0 })
  const close = set(now, { hours: 15, minutes: 30, seconds: 0, milliseconds: 0 })
  return isWithinInterval(now, { start: open, end: close })
}

function isAutoSquareOffWindow(): boolean {
  const now = toZonedTime(new Date(), IST)
  const cutoff = set(now, { hours: 15, minutes: 20, seconds: 0, milliseconds: 0 })
  return now >= cutoff
}

// Display format for candle timestamps
formatInTimeZone(candle.timestamp, IST, 'HH:mm')  // "09:15"
```

All candle timestamps stored and displayed in IST (UTC+5:30). Never convert to local time.

---

## Number Formatting (Indian Markets)

Use the browser's `Intl.NumberFormat` with `en-IN` locale — no library needed.

```typescript
// src/lib/format.ts

const inrFmt = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export const formatINR = (v: number) => inrFmt.format(v)
// ₹2,891.45  (Indian comma grouping: 2,891 not 2,891)

export function formatINRCompact(v: number): string {
  if (v >= 10_000_000) return `₹${(v / 10_000_000).toFixed(2)}Cr`
  if (v >= 100_000)    return `₹${(v / 100_000).toFixed(2)}L`
  if (v >= 1_000)      return `₹${(v / 1_000).toFixed(1)}K`
  return inrFmt.format(v)
}
// 2,89,100 → ₹2.89L
// 2,89,10,000 → ₹28.91Cr

export const formatPnl = (v: number) =>
  `${v >= 0 ? '+' : ''}${formatINR(v)}`
// +₹1,234.50 / -₹567.00
```

---

## Forms: react-hook-form + zod

```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const orderSchema = z.object({
  qty:        z.number().int().positive('Quantity must be positive'),
  limitPrice: z.number().positive().optional(),
  stopLoss:   z.number().positive('Stop loss required'),
}).refine(
  (d) => !d.limitPrice || d.stopLoss < d.limitPrice,
  { message: 'Stop loss must be below entry for a long', path: ['stopLoss'] },
)

type OrderFormData = z.infer<typeof orderSchema>
```

- `react-hook-form` uses uncontrolled inputs — no re-render per keystroke in the order panel
- `zod` schemas shared with backend (via `@repo/shared` in a monorepo setup, or copied)
- `@hookform/resolvers/zod` — bridge between the two

---

## Tables: TanStack Table v8

Used for:
- **Watchlist panel** — sortable by score, direction, change %
- **Positions strip** — sortable by unrealised P&L, symbol, product type
- **Trade journal** — filterable, paginated

```typescript
import { useReactTable, getCoreRowModel, getSortedRowModel } from '@tanstack/react-table'

const table = useReactTable({
  data: watchlist,
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  state: { sorting },
  onSortingChange: setSorting,
})
```

Do not build manual tables. TanStack Table handles virtualisation, sorting, filtering, and column pinning.

---

## Virtual Scrolling: TanStack Virtual

For long lists that exceed the visible viewport:
- Watchlist with 50+ symbols
- Option chain table (100+ strikes)
- Trade journal (months of data)

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

const rowVirtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 36,  // row height in px
})
```

---

## Animation: framer-motion (limited)

Used only for:
- Conversion panel slide-in (appears at 2:45 PM)
- Alert pulse on signal fire
- Pre-trade overlay appear/dismiss

```typescript
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: 8 }}
  transition={{ duration: 0.15 }}
>
  <ConversionPanel />
</motion.div>
```

**Not used for**: candle chart (ECharts handles), positions strip rows (TanStack Table), any data that updates on every tick.

Keep transitions ≤ 200ms. Anything slower feels sluggish during trading hours.

---

## Packages to Avoid

| Package | Reason |
|---------|--------|
| `moment.js` | 67KB gzipped, deprecated, poor tree-shaking |
| `recharts` | Full React re-render on data update — unusable for tick data |
| `react-chartjs-2` | Same re-render issue, Chart.js not designed for financial data |
| `lodash` (full) | Import from `lodash-es` by function, or use native equivalents |
| `axios` | `fetch()` with TanStack Query is sufficient; saves 14KB |
| `react-table` v7 | Superseded by TanStack Table v8 — use v8 |
| `socket.io-client` | Backend uses native WebSocket (FastAPI); socket.io adds protocol overhead |
| `styled-components` | Runtime CSS-in-JS conflicts with Tailwind v4 approach |
| `redux` / `@reduxjs/toolkit` | Overkill for this state shape; Zustand achieves same with 90% less code |

---

## Complete package.json

```json
{
  "dependencies": {
    "react":                     "^18.3.0",
    "react-dom":                 "^18.3.0",
    "react-router-dom":          "^6.24.0",
    "@tanstack/react-query":     "^5.50.0",
    "@tanstack/react-table":     "^8.19.0",
    "@tanstack/react-virtual":   "^3.8.0",
    "zustand":                   "^4.5.4",
    "echarts":                   "^5.5.1",
    "echarts-for-react":         "^3.0.2",
    "react-hook-form":           "^7.52.0",
    "@hookform/resolvers":       "^3.9.0",
    "zod":                       "^3.23.0",
    "date-fns":                  "^3.6.0",
    "date-fns-tz":               "^3.1.3",
    "framer-motion":             "^11.3.0",
    "clsx":                      "^2.1.1",
    "tailwind-merge":            "^2.4.0"
  },
  "devDependencies": {
    "typescript":                "^5.5.0",
    "vite":                      "^5.3.0",
    "@vitejs/plugin-react":      "^4.3.0",
    "tailwindcss":               "^4.0.0",
    "@tailwindcss/vite":         "^4.0.0",
    "vitest":                    "^2.0.0",
    "@vitest/ui":                "^2.0.0",
    "@testing-library/react":    "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "msw":                       "^2.3.0",
    "@types/react":              "^18.3.0",
    "@types/react-dom":          "^18.3.0"
  }
}
```

Note: shadcn/ui components are added via CLI — not a direct dependency:
```bash
npx shadcn@latest add button dialog select table badge
```

---

## Testing Stack

| Tool | Role |
|------|------|
| Vitest | Test runner — Vite-native, same config, fast |
| @testing-library/react | Component tests with user-event simulation |
| MSW v2 | Mock REST and WebSocket for isolated tests |
| @vitest/ui | Browser-based test UI for debugging |

Pure functions (candle aggregation math, P&L calculation, SL sizing) are tested without React. WS message handlers tested with a mock `WebSocketManager`. Component tests use MSW to mock API responses and WS events.
