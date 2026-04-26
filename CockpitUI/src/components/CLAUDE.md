# src/components — Component Catalog

All components: `memo()` + `.displayName`. 100-line limit per file. Hooks (useXxx.ts) exempt.

---

## ui/ — Shared primitives

| File              | What it does                                                      |
|-------------------|-------------------------------------------------------------------|
| `Badge.tsx`       | CVA chip badge — props: `color`, `size` (`sm`\|`md`), `className`, `title` |
| `LivePrice.tsx`   | Flashing live price + pct change — props: `ltp`, `prevClose`, `marketOpen`, `className` |
| `ConnectionDot.tsx`| Colored dot for SSE connection state                             |
| `BiasPill.tsx`    | Bull/bear/neutral pill for MTF bias display                      |
| `ViewToggle.tsx`  | Generic icon toggle button                                       |

---

## signals/

### Atoms
| File                  | What it does                                                  |
|-----------------------|---------------------------------------------------------------|
| `BiasTag.tsx`         | Small MTF bias label (`15m UP`, `1h DN`)                     |
| `MetricCell.tsx`      | Label + value cell for signal card metric grid                |
| `LevelRow.tsx`        | Entry/SL/target price row                                     |
| `NoteBar.tsx`         | Inline note preview bar                                       |
| `NoteModal.tsx`       | Note edit modal (backdrop + textarea + save)                  |
| `SignalTypeBadge.tsx`  | Colored signal type chip (BREAKOUT, REVERSAL, etc.)          |
| `SignalNoteCell.tsx`   | Table `<td>` with note icon + option chain button            |

### Composed
| File                      | What it does                                              |
|---------------------------|-----------------------------------------------------------|
| `SignalCardHeader.tsx`    | Top section of signal card: symbol, price, bias tags      |
| `SignalCardMetrics.tsx`   | Metric grid: 52H/L, ATR, ADV, CHG, O=H/O=L              |
| `SignalCard.tsx`          | Full signal card (header + levels + metrics + note bar)   |
| `SignalCardView.tsx`      | Card grid layout (signal-grid CSS class)                  |
| `SignalRow.tsx`           | Table row for signal (all cols + note cell)               |
| `SignalTableView.tsx`     | Virtualized table with search + sort header               |
| `SignalFeed.tsx`          | Root: picks CardView or TableView, handles note modal     |
| `SignalToolbar.tsx`       | Top toolbar: view nav, workspace controls, pause/clear    |
| `SignalWorkspaceControls.tsx` | Category tabs, subtypes, F&O toggle, ADV tiers       |

### Config/hooks
| File                  | What it does                                                  |
|-----------------------|---------------------------------------------------------------|
| `signalToolbarConfig.ts`| TABS, SUBTYPES_BY_CATEGORY, VALUE_TIERS, TAB_SIGNAL_TYPE  |
| `useSignalSort.ts`    | Sort state, TABLE_HEADERS const, sort logic                   |

---

## dashboard/

### Atoms / display
| File                  | What it does                                                  |
|-----------------------|---------------------------------------------------------------|
| `StatCard.tsx`        | Single stat tile (label + value + optional tone color)        |
| `ScoreBar.tsx`        | Horizontal score bar — props: `value`, `color: ScoreColor`, `label` |
| `ScoreCard.tsx`       | Full scored symbol card (score bars, badges, comfort)         |
| `ScoreRow.tsx`        | Table row for scored symbol                                   |
| `WatchlistItem.tsx`   | Watchlist entry row with mini metrics                         |
| `ExpirySelector.tsx`  | Option chain expiry date seg-group                            |
| `StageBadge.tsx`      | Weinstein stage colored badge                                 |
| `IndToggle.tsx`       | Chart indicator visibility toggle button                      |
| `ChartLegend.tsx`     | Crosshair OHLCV overlay + indicator legend strip             |
| `ClusterBackground.tsx`| SVG axes, ticks, quadrant lines/labels (renders `<g>` frags)|
| `ClusterDots.tsx`     | SVG dots with clip-path, symbol labels, hover/select         |
| `ClusterTooltip.tsx`  | HTML tooltip positioned relative to containerRef             |

### Composed / panels
| File                  | What it does                                                  |
|-----------------------|---------------------------------------------------------------|
| `DashboardFilters.tsx`| Filter toolbar: search, watchlist, segment, stage, view mode  |
| `DashboardTable.tsx`  | Virtualized scored-symbol table with sort header              |
| `DashboardPanel.tsx`  | Root dashboard: filters + stats + view switcher + detail modal|
| `ClusterChart.tsx`    | SVG pan-zoom scatter: total score vs comfort score            |
| `DailyChart.tsx`      | LightweightCharts OHLCV + indicators + VP canvas              |
| `OptionChainBody.tsx` | Assessment bar + OC strike table                              |
| `OptionChainPanel.tsx`| OC modal or embedded — fetches expiries + chain data          |
| `SymbolModal.tsx`     | Full-screen symbol modal: chart + option chain tabs           |
| `WatchlistSplitView.tsx`| Split view: watchlist items + per-symbol charts             |

### Hooks/types
| File                  | What it does                                                  |
|-----------------------|---------------------------------------------------------------|
| `useDailyChart.ts`    | All chart imperative logic: init, series, VP, resize, legends |
| `useClusterPanZoom.ts`| Cluster pan/zoom state: viewBounds, drag handlers             |
| `useDashboardState.ts`| Filter/sort/detail state for DashboardPanel                  |
| `dashboardTypes.ts`   | `Segment`, `StageFilter`, `SortKey`, `DASHBOARD_HEADERS`      |

---

## screener/

| File                    | What it does                                                |
|-------------------------|-------------------------------------------------------------|
| `ScreenerPresetGroups.tsx`| Preset filter button groups used by stock list filters     |

---

## admin/

| File                   | What it does                                                 |
|------------------------|--------------------------------------------------------------|
| `ConfigField.tsx`      | Single config key-value field (number/string/bool input)     |
| `WorkflowGraph.tsx`    | SVG workflow graph atoms: `WorkflowNode`, `MergeConnector`, `VLine` |
| `FullSyncPane.tsx`     | Pipeline runner with workflow graph + run button. Also exports `SectionHeader` |
| `ServiceConfigPane.tsx`| Config form for a microservice (grouped fields, save/reset)  |
| `TokenPane.tsx`        | API token status display                                     |
| `AdminNav.tsx`         | Admin section nav                                            |
| `AdminPanel.tsx`       | Root admin panel: nav + section switcher                     |
| `adminConstants.ts`    | `PIPELINE_STEPS`, `SERVICE_CONFIGS`                         |
| `adminTypes.ts`        | `AdminSection`, `FieldDef`, `StepStatus`                    |
| `sseUtils.ts`          | SSE helper for admin pipeline events                         |
| `useFullSync.ts`       | Pipeline run state machine                                   |

---

## Naming conventions

- `useXxx.ts` — hook (state + effects), no JSX
- `XxxConfig.ts` / `xxxTypes.ts` — pure data/types, no JSX
- `XxxPanel.tsx` — root of a view section (fetches data, owns layout)
- `XxxView.tsx` — sub-layout (receives data props, picks display mode)
- `XxxBody.tsx` — content area within a panel (no fetch, pure display)
