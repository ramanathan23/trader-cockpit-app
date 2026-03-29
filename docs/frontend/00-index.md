# Frontend Documentation Index
## Trader Cockpit App — Frontend Technical Design

**Last Updated:** 2026-03-29
**Status:** Design Phase
**Broker:** Dhan (India NSE/BSE)
**Backend:** FastAPI (Python) with WebSocket endpoints

---

## Overview

The Trader Cockpit is a single-page, zero-tab, decision-first trading interface. It is purpose-built for active intraday and swing traders operating on NSE/BSE via the Dhan broker API. The entire UI is visible simultaneously — there are no modal workflows for core trading decisions, no tabs to switch between, and no information hidden behind clicks during market hours.

The frontend is a React 18 single-page application that communicates with a FastAPI backend over both REST (TanStack Query) and WebSocket (two persistent connections). All five permanent zones of the cockpit update in response to a single shared state: the active symbol.

---

## Tech Stack Summary

| Layer | Technology | Version | Role |
|---|---|---|---|
| Component framework | React | 18.3 | UI rendering, component model |
| Type system | TypeScript | 5.5 | End-to-end type safety |
| Build tool | Vite | 5.x | Dev server, HMR, production build |
| Client-side routing | TanStack Router | v1 | Type-safe routing, minimal routes |
| Global state | Zustand | 4.x | Active symbol, risk state, session |
| Server state / cache | TanStack Query | v5 | REST data fetching, cache, mutations |
| Charting | Apache ECharts + echarts-for-react | 5.x / 3.x | Candlestick chart, heatmap, payoff |
| Styling | Tailwind CSS | v4 | Utility-first, design tokens |
| Component primitives | shadcn/ui | latest | Accessible unstyled primitives |
| Panel layout | React Grid Layout | 1.4.x | Draggable/resizable cockpit zones |
| Data tables | TanStack Table | v8 | Positions strip, watchlist |
| Date handling | date-fns | 3.x | Candle timestamps, session windows |
| Forms + validation | React Hook Form + Zod | 7.x / 3.x | Order entry forms |
| Unit / component tests | Vitest + Testing Library | 2.x / 16.x | Component and hook tests |
| E2E tests | Playwright | 1.x | Full workflow tests |

### Why This Stack

This stack was chosen for a single high-density real-time page. It has no server-side rendering concerns (trading UI is behind auth, not SEO-indexed), so Vite SPA is the right build model. Zustand is chosen over Redux for minimal boilerplate — the cockpit has only 3 stores. TanStack Query v5 handles the REST/cache layer so WebSocket only carries true push data. ECharts is chosen over Lightweight Charts specifically because it supports custom mark areas for confluence zones, brush synchronization between price and volume, and imperative dataset updates without full component re-render.

---

## Module and Feature Structure Overview

```
frontend/src/
├── core/                    # Framework-level infrastructure — never feature-specific
│   ├── symbol-context/      # Active symbol Zustand slice + subscription hook
│   ├── websocket/           # WebSocket manager: market-feed + cockpit connections
│   ├── data-bus/            # Message routing from WS to stores/query cache
│   └── layout-engine/       # React Grid Layout wrapper, panel size persistence
│
├── features/                # Self-contained feature modules
│   ├── risk-bar/            # Zone 1: always-on single-line risk bar
│   ├── signal-panel/        # Zone 2: signal score + sizing panel
│   ├── canvas/              # Zone 3: primary canvas (multi-mode)
│   │   ├── chart/           # Candlestick chart with confluence bands
│   │   ├── eod-scan/        # EOD watchlist scan grid
│   │   ├── heatmap/         # Sector heatmap
│   │   ├── portfolio/       # Capital allocation view
│   │   └── options-builder/ # Options strategy builder + payoff
│   ├── market-context/      # Zone 4: index + sector + peers + history
│   ├── positions/           # Zone 5: positions strip (INTRA/CNC/Options)
│   ├── conversion/          # EOD conversion panel (activates at 2:45 PM)
│   ├── watchlist/           # Collapsible watchlist sidebar
│   ├── orders/              # Order entry + pre-trade overlay
│   └── options/             # Options strategy management
│
├── datasources/             # Backend API adapter layer
│   ├── rest/                # TanStack Query hooks (queries + mutations)
│   └── ws/                  # WebSocket subscription hooks
│
├── adapters/                # Domain-to-UI transform functions
│   ├── signal.adapter.ts    # Backend signal DTO → SignalViewModel
│   ├── position.adapter.ts  # Backend position DTO → PositionViewModel
│   ├── options.adapter.ts   # Options leg DTOs → StrategyViewModel
│   └── risk.adapter.ts      # Risk metrics DTO → RiskViewModel
│
├── store/                   # Zustand stores (3 total)
│   ├── cockpit.store.ts     # activeSymbol, canvasMode, selectedInterval, layout
│   ├── risk.store.ts        # Daily P&L, limits consumed, connection status
│   └── session.store.ts     # Auth token, userId, isAuthenticated
│
└── shared/
    ├── components/          # Reusable design system components
    ├── hooks/               # Shared hooks (useSymbol, useInterval, useConnectionStatus)
    ├── types/               # Domain type definitions (mirror backend schemas)
    └── theme/               # Tailwind config, design tokens
```

---

## Key Architectural Decisions

### 1. Widget Registry Pattern

Every panel in the cockpit is registered in a central widget registry. The registry maps a panel ID to its component, default size, minimum size, and resize constraints. React Grid Layout reads from this registry to render the cockpit grid. This allows future panels to be added without modifying the layout engine, and allows users to save/restore panel arrangements.

### 2. Symbol-Driven Context

There is one active symbol at any moment. It lives in `cockpitStore.activeSymbol`. All five zones subscribe to this value via a shared `useActiveSymbol()` hook. When the symbol changes, every zone re-queries or re-subscribes without any prop drilling. The symbol is the single source of truth that drives context coherence across all panels simultaneously.

### 3. WebSocket Data Bus

The application maintains two persistent WebSocket connections to the FastAPI backend:

- `/ws/market-feed` — real-time tick and candle data for subscribed symbols
- `/ws/cockpit` — signal updates, alerts, position updates, risk updates, and conversion candidates

The WebSocket Manager (in `core/websocket/`) owns both connections. It routes incoming messages to the Data Bus (`core/data-bus/`), which dispatches events to the appropriate Zustand store or TanStack Query cache based on message type. No component receives raw WebSocket messages directly — all components consume state from stores or queries.

### 4. Dhan-Native Intervals Only

The chart interval selector exposes exactly five intervals: 5min, 15min, 25min, 60min, 1D. These are the only intervals supported by the Dhan API. No other intervals appear anywhere in the UI. The type system enforces this via a union type: `type CandleInterval = '5min' | '15min' | '25min' | '60min' | '1D'`.

### 5. Feature-Based Module Structure

The source tree is organized by feature, not by technical layer. Each feature in `features/` owns its components, hooks, and local types. Shared infrastructure lives in `core/` and `shared/`. The `datasources/` layer is the only place that talks to the backend — no component imports fetch calls directly.

### 6. Dark Theme Only

The design system supports only dark theme. There is no theme toggle. All design tokens are defined against a dark background. This eliminates conditional theme logic throughout the codebase and ensures optimal contrast for high-density trading data at all times.

---

## Document Map

| File | Title | Contents |
|---|---|---|
| `00-index.md` | Index (this file) | Stack summary, module overview, key decisions |
| `01-architecture.md` | Architecture | Full module structure, symbol-driven context, canvas state machine, data flow |
| `02-state-management.md` | State Management | Zustand stores, TanStack Query hooks, WebSocket integration, data flow walkthrough |
| `03-components.md` | Components | Design system, zone components, chart design, overlays, panels |
| `04-realtime.md` | Real-time Data | WebSocket manager, message types, candle building, subscription management |
| `05-packages.md` | Package Evaluation | Per-package evaluation with ratings, alternatives, risks, and packages to avoid |

---

## Design Principles Reference

| Principle | Implementation |
|---|---|
| Zero context switching | All 5 zones visible simultaneously. No tabs for core workflow. Canvas modes switch content, not zones. |
| Symbol-driven context | `cockpitStore.activeSymbol` drives all zones. One state change, all panels update. |
| Decision-first | Signal scores, risk bar, and position P&L are always visible. Nothing critical is hidden. |
| Dhan-native intervals | UI exposes only 5/15/25/60min and 1D. Enforced at type level. |
| Dark theme only | Single color scheme. No toggle. Tokens defined for trading-specific semantics. |

---

## Constraints and Non-Goals

**Constraints:**
- Candle intervals are limited to Dhan API capabilities: 5min, 15min, 25min, 60min, 1D
- Products are limited to: INTRADAY (MIS equivalent) and CNC (delivery/swing)
- Exchange support: NSE and BSE only
- The app is a single-user desktop-sized web application — no mobile layout

**Non-Goals for this document set:**
- Backend API design (covered in backend docs)
- Deployment and infrastructure
- Authentication flow (handled by session store + FastAPI JWT)
- CI/CD pipeline
