# CockpitUI — Frontend Instructions

## STACK
Next.js 15 (App Router), React 19, TypeScript strict, Tailwind CSS v3, `uv` not used (Node/npm).

---

## COMPONENT RULES

- **100-line hard limit** per `.tsx` component file. Hooks (`useXxx.ts`) are exempt.
- **Decomposition pattern**: atom → composition layer → orchestrator.
  - Atoms: single-responsibility, no business logic, props only.
  - Hooks: all imperative/async/state logic extracted to `useXxx.ts`.
  - Orchestrators: thin — call hooks, assemble atoms, no logic.
- Prefer editing existing files. Never create a new file when an atom/hook already exists.
- `memo()` on every component. Always set `.displayName`.
- React 19: `useRef<T>(null)` returns `RefObject<T | null>`. Prop types must be `React.RefObject<T | null>` not `React.RefObject<T>`.

---

## TAILWIND COLOR TOKENS

All defined in `tailwind.config.ts` and support opacity modifier (`text-accent/50`, `border-violet/35`, etc).

| Token    | Semantic use                          |
|----------|---------------------------------------|
| `accent` | Primary interactive / cyan-teal       |
| `bull`   | Positive / green                      |
| `bear`   | Negative / red                        |
| `amber`  | Warning / neutral momentum / yellow   |
| `violet` | F&O / derivatives / purple            |
| `sky`    | Secondary info / blue                 |
| `fg`     | Primary text                          |
| `dim`    | Secondary text                        |
| `ghost`  | Tertiary / muted text                 |
| `base`   | Page background                       |
| `panel`  | Sidebar / toolbar background          |
| `card`   | Card surface                          |
| `lift`   | Hover state surface                   |
| `border` | Default border                        |
| `rim`    | Stronger border / thumb               |

Usage: `text-accent`, `bg-bull/10`, `border-violet/35`, `text-ghost`, etc.

---

## COLOR RULES — CRITICAL

### Static colors → ALWAYS Tailwind class
Never `style={{ color: 'rgb(var(--X))' }}` for static semantic colors.

```tsx
// WRONG
<span style={{ color: 'rgb(var(--accent))' }}>text</span>
<span style={{ color: activeView === v ? 'rgb(var(--accent))' : undefined }}>text</span>

// RIGHT
<span className="text-accent">text</span>
<span className={cn('seg-btn', isActive && 'active text-accent')}>text</span>
```

### Dynamic/computed colors → inline style (cannot avoid)
Colors returned by runtime functions must remain inline:
- `signalColor(type)` — signal type color
- `comfortColor(score)` — comfort score gradient
- `rsiColor(rsi)` — RSI-based color
- `dotColor(sym)` — cluster dot color
- `stageColor(stage)` / `screenerStageColor(stage)` — Weinstein stage color
- `pctColor(price, ref)` — distance-from-ref color
- `advColor(cr)` — ADV tier color
- `dirColor(direction)` — bull/bear direction color

### SVG attributes → rgb(var(--X)) strings (Tailwind classes not valid)
SVG `fill`, `stroke`, `color` attributes must use `'rgb(var(--X))'` string literals.

---

## cn() UTILITY

```ts
import { cn } from '@/lib/cn';
// clsx + tailwind-merge — resolves class conflicts correctly
```

Pattern for conditional active-color buttons (replaces old style= + className= split):
```tsx
className={cn('seg-btn', isActive && 'active text-accent')}
className={cn('seg-btn', isActive && `active ${tokenClass}`)}
className={cn('seg-btn border border-border', fnoOnly && 'active text-violet')}
```

---

## CSS UTILITY CLASSES (globals.css @layer components)

| Class            | Description                                              |
|------------------|----------------------------------------------------------|
| `.num`           | Monospace tabular numerics (JetBrains Mono)              |
| `.chip`          | Pill badge — 22px height, border, rounded-full           |
| `.badge-sm`      | chip + h-4 min-h-0 px-1 (tiny inline badge)             |
| `.badge-md`      | chip + h-5 min-h-0 px-1.5 (standard inline badge)       |
| `.seg-group`     | Segmented button container (border, rounded-lg, gap-0.5) |
| `.seg-btn`       | Segmented button (11px, dim color, 28px min-height)     |
| `.seg-btn.active`| Active seg-btn (card bg + rim shadow)                   |
| `.icon-btn`      | 32×32 icon button (border, dim, transitions)            |
| `.field`         | Input/textarea (32px, border, accent focus ring)        |
| `.surface-card`  | Floating card (card bg, border, border-radius 8px, shadow)|
| `.glass-panel`   | Translucent panel (panel/88, border, inner highlight)   |
| `.modal-backdrop`| Fixed overlay (z-50, blur, dark overlay)                |
| `.table-wrap`    | Scrollable table container (overflow-auto, base bg)     |
| `.data-table`    | Full-width bordered table with sticky header             |
| `.signal-grid`   | Auto-fill card grid (minmax 260px)                      |
| `.metric-card`   | Small metric tile (144px min, border, card bg)          |
| `.label-xs`      | 9px black uppercase ghost label                         |
| `.label-sm`      | 10px black uppercase ghost label                        |
| `.stat-pair`     | num text-ghost (for label+value stat pairs)             |
| `.app-shell`     | Full-height page wrapper with gradient                  |
| `.pulse-new`     | 1100ms accent pulse animation (new signal indicator)    |

---

## CUSTOM TYPOGRAPHY VARIANTS (tailwind.config.ts)

| Class           | Size  | Weight | Use                            |
|-----------------|-------|--------|--------------------------------|
| `text-ticker`   | 17px  | 750    | Stock symbol display           |
| `text-price`    | 22px  | 780    | Large price display            |
| `text-signal-badge` | 10px | 800 | Signal type label text        |
| `text-meta`     | 10px  | 500    | Timestamp / secondary metadata |

---

## Badge COMPONENT

```tsx
import { Badge } from '@/components/ui/Badge';

// color: 'accent' | 'amber' | 'bull' | 'bear' | 'violet' | 'sky' | 'ghost' | 'dim'
// size: 'sm' | 'md' (default 'md')
<Badge color="violet">F&O</Badge>
<Badge color="amber" size="sm">{count}x</Badge>
<Badge color="accent" title="tooltip text">VCP</Badge>
```

Use Badge for all inline chip labels (F&O, WL, VCP, RECT, NEW, counts). Do NOT hand-roll chip+color inline spans when Badge covers it.

---

## ScoreBar COMPONENT

```tsx
import { ScoreBar } from '@/components/dashboard/ScoreBar';
// color: ScoreColor = 'accent' | 'amber' | 'bull' | 'bear' | 'violet' | 'sky' | 'ghost'
<ScoreBar value={75} color="bull" label="Momentum" />
```

ScoreBar builds `rgb(var(--${color}))` internally — pass token string, not CSS.

---

## LIB CATALOG (src/lib/)

| File                  | Exports / purpose                                              |
|-----------------------|----------------------------------------------------------------|
| `cn.ts`               | `cn(...ClassValue[])` — clsx + tailwind-merge                 |
| `fmt.ts`              | `fmt2`, `fmtAdv`, `spct`, `timeStr`, `screenerPctText`        |
| `scoreColors.ts`      | `comfortColor`, `rsiColor` — dynamic color functions          |
| `screenerDisplay.ts`  | `screenerPctColor`, `screenerStageColor`, `screenerStageLabel`, `screenerF52hColor`, `screenerF52lColor` |
| `stageUtils.ts`       | `stageColor`, stage label helpers                             |
| `chainAssessment.ts`  | `assessChain`, `AssessResult`, `fmtOI`, `fmtIV`, `fmtGreek`  |
| `clusterUtils.ts`     | `W`, `H`, `PAD`, `PW`, `PH`, `QUAD_TOTAL`, `QUAD_COMFORT`, `dotColor`, `dotRadius`, `axisTicks`, `mkToX`, `mkToY`, `ViewBounds` |
| `chartUtils.ts`       | Lightweight-charts helpers                                    |
| `headerUtils.ts`      | App header helpers                                            |
| `audio.ts`            | Alert sound                                                   |
| `api-config.ts`       | API base URL config                                           |

---

## DOMAIN CATALOG (src/domain/)

| File                   | Key types exported                                          |
|------------------------|-------------------------------------------------------------|
| `signal.ts`            | `Signal`, `SignalCategory`, `SignalType`, `dirColor`, `signalColor`, `pctColor`, `advColor`, `filterSignals` |
| `dashboard.ts`         | `ScoredSymbol`, `DashboardResponse`                         |
| `instrument_metrics.ts`| `InstrumentMetrics`                                         |
| `screener.ts`          | `ScreenerRow`, `ScreenerPreset`, `ScreenerRangeFilter`, `isRangeActive` |
| `option_chain.ts`      | `OptionChainResponse`, `ExpiryListResponse`, `Strike`       |
| `market.ts`            | `MarketPhase`                                               |
| `chart.ts`             | Chart domain types                                          |

---

## HOOKS CATALOG (src/hooks/)

| File                | Returns / purpose                                         |
|---------------------|-----------------------------------------------------------|
| `useDashboard.ts`   | `{ stats, scores, loading, fetched, loadDashboard }`      |
| `useSignals.ts`     | `{ signals, connState, metricsCache, … }`                 |
| `useHistory.ts`     | `{ historySignals, histDates, loadHistory, … }`           |
| `useNotes.ts`       | `{ notes, saveNote }`                                     |
| `useScreener.ts`    | `{ rows, loading, loadScreener }`                         |
| `useLivePrices.ts`  | `Record<string, LivePriceData>` from SSE                  |
| `useMarketStatus.ts`| `{ phase, marketOpen }`                                   |
| `useTokenStatus.ts` | `{ status, label }`                                       |

---

## API ROUTES

All proxied through Next.js at `/api/v1/...`:
- `POST /api/v1/optionchain/expiries` — `{ symbol }` → `ExpiryListResponse`
- `POST /api/v1/optionchain` — `{ symbol, expiry }` → `OptionChainResponse`
- Dashboard, signals, screener routes follow same `/api/v1/` prefix.
