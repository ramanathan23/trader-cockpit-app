# Backend Architecture — DDD Layered Design

**Project:** Trader Cockpit App
**Pattern:** Domain-Driven Design (DDD) + CQRS
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [Layer Responsibilities](#layer-responsibilities)
2. [Dependency Rule](#dependency-rule)
3. [Full Folder Structure](#full-folder-structure)
4. [Layer Deep-Dive](#layer-deep-dive)
   - [Domain Layer](#domain-layer)
   - [Application Layer](#application-layer)
   - [Infrastructure Layer](#infrastructure-layer)
   - [API Layer](#api-layer)
5. [Dependency Injection Pattern](#dependency-injection-pattern)
6. [Async Concurrency Model](#async-concurrency-model)
7. [CQRS Flow Diagram](#cqrs-flow-diagram)
8. [Domain Boundaries and Ownership](#domain-boundaries-and-ownership)
9. [Inter-Domain Communication](#inter-domain-communication)

---

## Layer Responsibilities

### Domain Layer
- **Pure Python** — zero imports from FastAPI, SQLAlchemy, Redis, or any framework.
- Contains: **Entities**, **Aggregates**, **Value Objects**, **Domain Services**, **Domain Events**, **Repository Interfaces** (abstract base classes, not implementations).
- All business invariants enforced here. If a rule about position sizing, SL validation, or CSL triggering exists — it lives in the domain.
- Unit-testable without spinning up any infrastructure.
- Sub-domains: `market_data`, `signals`, `equity`, `orders`, `risk`, `options`, `portfolio`, `alerts`, `shared`.

### Application Layer
- **Use cases** — one handler per command or query.
- **Commands**: mutate state (place order, convert position, trigger CSL).
- **Queries**: return projections (get watchlist, calculate position size, get active strategies).
- Orchestrates domain objects and calls infrastructure via **Port interfaces** (abstract classes defined here, implemented in infrastructure).
- No direct DB or Redis calls — uses injected repository and cache ports.
- Contains DTOs (data transfer objects) for command/query payloads and results.

### Infrastructure Layer
- **Implements all ports** defined in the application layer.
- Contains: Dhan broker adapter, repository implementations, Redis cache implementations, TimescaleDB setup, background job workers, internal event bus.
- Only layer that imports `dhanhq`, `sqlalchemy`, `asyncpg`, `redis`, `APScheduler`.
- Translates external data (Dhan API responses) into domain models via a Mapper.

### API Layer
- **FastAPI thin routers** — one router per domain.
- Receives HTTP requests, validates with Pydantic schemas, calls application layer command/query handlers.
- Returns serialized Pydantic response models.
- Contains **WebSocket endpoints** that forward domain events and market data to the frontend.
- **Zero business logic** — no if/else trading decisions here.

---

## Dependency Rule

```
API  →  Application  →  Domain
              ↑
       Infrastructure
```

- API depends on Application (imports handlers and DTOs).
- Application depends on Domain (imports entities, aggregates, port interfaces).
- Infrastructure depends on Domain and Application (implements domain repository interfaces and application ports).
- Domain depends on **nothing** except Python stdlib.
- The rule: **imports never point inward**. Domain has no knowledge of FastAPI, SQLAlchemy, or Dhan SDK.

---

## Full Folder Structure

```
backend/
├── domains/
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── money.py              # Money value object (amount, currency)
│   │   ├── symbol.py             # Symbol value object (ticker, exchange)
│   │   ├── price.py              # Price value object (validated positive Decimal)
│   │   ├── quantity.py           # Quantity value object (validated positive int)
│   │   ├── timestamp.py          # Timestamp helpers (IST-aware)
│   │   ├── domain_event.py       # DomainEvent base class
│   │   └── result.py             # Result[T] monad (Ok / Err)
│   │
│   ├── market_data/
│   │   ├── __init__.py
│   │   ├── entities.py           # Quote, OHLCV entities
│   │   ├── value_objects.py      # Tick, MarketSession
│   │   ├── instrument.py         # Instrument aggregate
│   │   ├── enums.py              # CandleInterval, Exchange
│   │   └── ports.py              # IMarketDataRepository (abstract)
│   │
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── signal.py             # Signal entity
│   │   ├── score.py              # ScoreFactors value object, SignalGrade enum
│   │   ├── watchlist.py          # Watchlist aggregate, WatchlistEntry
│   │   ├── signal_engine.py      # Domain service: score_symbol, grade_signal
│   │   └── ports.py              # ISignalRepository, IWatchlistRepository
│   │
│   ├── equity/
│   │   ├── __init__.py
│   │   ├── positions.py          # IntradayPosition, CNCPosition entities
│   │   ├── conversion.py         # ConversionCandidate value object, conversion rules
│   │   ├── enums.py              # PositionMode (INTRADAY, CNC)
│   │   ├── events.py             # PositionOpened, PositionConverted, PositionClosed
│   │   └── ports.py              # IPositionRepository
│   │
│   ├── orders/
│   │   ├── __init__.py
│   │   ├── order.py              # Order aggregate
│   │   ├── enums.py              # OrderStatus, OrderType, ProductType, Side
│   │   ├── events.py             # OrderPlaced, OrderFilled, OrderCancelled
│   │   └── ports.py              # IOrderRepository, IBrokerOrderPort
│   │
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── profile.py            # RiskProfile entity, DailyRiskState
│   │   ├── sizer.py              # PositionSizer domain service
│   │   ├── atr_validator.py      # ATRValidator domain service
│   │   ├── events.py             # DailyLimitBreached, RiskStateUpdated
│   │   └── ports.py              # IRiskRepository
│   │
│   ├── options/
│   │   ├── __init__.py
│   │   ├── leg.py                # OptionLeg entity
│   │   ├── strategy.py           # OptionStrategy aggregate
│   │   ├── basket.py             # Basket aggregate
│   │   ├── csl_engine.py         # LSLCSLEngine domain service
│   │   ├── enums.py              # StrategyType, LegSide, OptionType
│   │   ├── events.py             # StrategyPlaced, CSLTriggered, LegFilled
│   │   └── ports.py              # IStrategyRepository, IBasketRepository
│   │
│   ├── portfolio/
│   │   ├── __init__.py
│   │   ├── portfolio.py          # Portfolio aggregate
│   │   ├── allocation.py         # Allocation value object
│   │   ├── pnl.py                # DailyPnL value object
│   │   └── ports.py              # IPortfolioRepository
│   │
│   └── alerts/
│       ├── __init__.py
│       ├── alert.py              # Alert entity, AlertRule entity
│       ├── notification.py       # Notification value object
│       ├── enums.py              # AlertType, AlertChannel
│       └── ports.py              # IAlertRepository, INotificationPort
│
├── application/
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── command.py            # BaseCommand, CommandHandler[C, R]
│   │   ├── query.py              # BaseQuery, QueryHandler[Q, R]
│   │   └── mediator.py           # Mediator: dispatch commands and queries
│   │
│   ├── market_data/
│   │   ├── queries/
│   │   │   ├── get_quote.py          # GetQuoteQuery → Quote
│   │   │   ├── get_ohlcv.py          # GetOHLCVQuery → List[OHLCV]
│   │   │   └── search_instruments.py # SearchInstrumentsQuery → List[Instrument]
│   │   └── commands/
│   │       └── subscribe_ticker.py   # SubscribeTickerCommand
│   │
│   ├── signals/
│   │   ├── queries/
│   │   │   ├── get_watchlist.py      # GetWatchlistQuery → Watchlist
│   │   │   └── get_signal.py         # GetSignalQuery → Signal | None
│   │   └── commands/
│   │       ├── run_eod_scan.py       # RunEODScanCommand → WatchlistResult
│   │       └── evaluate_candle.py    # EvaluateCandleCommand → Signal | None
│   │
│   ├── equity/
│   │   ├── queries/
│   │   │   ├── get_positions.py          # GetPositionsQuery → PositionsResult
│   │   │   └── get_conversion_candidates.py  # GetConversionCandidatesQuery
│   │   └── commands/
│   │       ├── place_intra_trade.py      # PlaceIntradayTradeCommand
│   │       ├── convert_to_delivery.py    # ConvertToDeliveryCommand
│   │       └── add_pyramid.py            # AddPyramidCommand
│   │
│   ├── orders/
│   │   ├── queries/
│   │   │   ├── get_orders.py             # GetOrdersQuery → List[Order]
│   │   │   └── get_order_history.py      # GetOrderHistoryQuery
│   │   └── commands/
│   │       ├── place_order.py            # PlaceOrderCommand
│   │       ├── cancel_order.py           # CancelOrderCommand
│   │       └── modify_order.py           # ModifyOrderCommand
│   │
│   ├── risk/
│   │   ├── queries/
│   │   │   ├── get_risk_profile.py       # GetRiskProfileQuery
│   │   │   ├── get_daily_limit.py        # GetDailyLimitQuery → DailyRiskState
│   │   │   └── get_position_size.py      # GetPositionSizeQuery → PositionSizeResult
│   │   └── commands/
│   │       ├── update_daily_limit.py     # UpdateDailyLimitCommand
│   │       └── set_pnl_exit.py           # SetPnLExitCommand
│   │
│   └── options/
│       ├── queries/
│       │   ├── get_strategies.py         # GetActiveStrategiesQuery
│       │   ├── get_baskets.py            # GetBasketsQuery
│       │   └── get_greeks.py             # GetGreeksQuery → GreeksResult
│       └── commands/
│           ├── place_strategy.py         # PlaceOptionStrategyCommand
│           ├── close_strategy.py         # CloseStrategyCommand
│           └── trigger_csl.py            # TriggerCSLCommand
│
├── infrastructure/
│   ├── dhan/
│   │   ├── __init__.py
│   │   ├── client.py             # DhanClient — wraps dhanhq SDK, async methods
│   │   ├── market_feed.py        # Binary WebSocket handler and parser
│   │   ├── order_feed.py         # Order update WebSocket handler (JSON)
│   │   ├── mapper.py             # Dhan response dicts → Domain model instances
│   │   ├── option_chain.py       # Option chain polling (rate-limited: 1 req/3s)
│   │   ├── position_poll.py      # Position poll service (3-5s interval)
│   │   └── token_store.py        # Token read/write from Redis
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── candle_repo.py        # CandleRepository — TimescaleDB
│   │   ├── watchlist_repo.py     # WatchlistRepository — PostgreSQL
│   │   ├── order_repo.py         # OrderRepository — PostgreSQL
│   │   ├── position_repo.py      # PositionRepository — PostgreSQL
│   │   └── strategy_repo.py      # StrategyRepository — PostgreSQL
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── quote_cache.py        # Redis quote store (TTL: 5s)
│   │   ├── candle_cache.py       # Redis live candle builder
│   │   ├── option_chain_cache.py # Option chain cache (TTL: 3s)
│   │   └── session_cache.py      # Daily limits, token (TTL: 24h)
│   │
│   ├── timeseries/
│   │   ├── __init__.py
│   │   └── timescale.py          # Hypertable creation, retention policies
│   │
│   ├── messaging/
│   │   ├── __init__.py
│   │   └── event_bus.py          # asyncio-based domain event pub/sub
│   │
│   └── jobs/
│       ├── __init__.py
│       ├── eod_scan.py           # Nightly EOD signal scan (4 PM IST)
│       ├── candle_agg.py         # Candle aggregation worker (tick consumer)
│       ├── token_renewal.py      # Daily token renewal (9 PM IST)
│       └── csl_monitor.py        # CSL monitor task (every 3s, market hours)
│
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── deps.py               # Shared FastAPI Depends() factories
│       ├── market_data/
│       │   └── router.py
│       ├── signals/
│       │   └── router.py
│       ├── equity/
│       │   └── router.py
│       ├── orders/
│       │   └── router.py
│       ├── risk/
│       │   └── router.py
│       ├── options/
│       │   └── router.py
│       ├── portfolio/
│       │   └── router.py
│       └── ws/
│           ├── market_feed.py    # WS /ws/market-feed — tick stream to frontend
│           └── cockpit_feed.py   # WS /ws/cockpit — signals, alerts, positions
│
├── config/
│   ├── __init__.py
│   ├── settings.py               # Pydantic BaseSettings — all env vars
│   └── database.py               # SQLAlchemy async engine and session factory
│
├── main.py                       # FastAPI app factory, router registration
└── lifespan.py                   # Startup/shutdown: DB, Redis, Dhan WS, Jobs
```

---

## Layer Deep-Dive

### Domain Layer

The domain layer contains no constructors that accept ORM models, no async methods, and no external service calls. It is a model of the trading business.

**Naming conventions:**
- Entities: classes with an `id` field and identity-based equality.
- Aggregates: entities that own a consistency boundary (e.g., `OptionStrategy` owns its `OptionLeg` list).
- Value Objects: immutable, equality by value (e.g., `Money`, `Symbol`, `ScoreFactors`).
- Domain Services: stateless functions that span multiple aggregates (e.g., `PositionSizer`, `ATRValidator`).
- Domain Events: emitted by aggregates to signal that something happened (e.g., `PositionConverted`).
- Ports: abstract base classes for repository and external service interfaces. Defined in the domain (or application), implemented in infrastructure.

**Example — Order aggregate:**
```python
# domains/orders/order.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from domains.shared.symbol import Symbol
from domains.shared.quantity import Quantity
from domains.shared.price import Price
from domains.orders.enums import OrderStatus, OrderType, ProductType, Side
from domains.orders.events import OrderPlaced, OrderFilled

@dataclass
class Order:
    id: UUID
    symbol: Symbol
    side: Side
    qty: Quantity
    price: Price
    order_type: OrderType
    product_type: ProductType
    status: OrderStatus = OrderStatus.PENDING
    dhan_order_id: str | None = None
    filled_qty: int = 0
    fill_price: Price | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    _events: list = field(default_factory=list, repr=False)

    @classmethod
    def create(cls, symbol, side, qty, price, order_type, product_type) -> "Order":
        order = cls(
            id=uuid4(),
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            order_type=order_type,
            product_type=product_type,
        )
        order._events.append(OrderPlaced(order_id=order.id, symbol=symbol))
        return order

    def mark_filled(self, fill_price: Price, filled_qty: int) -> None:
        self.fill_price = fill_price
        self.filled_qty = filled_qty
        self.status = OrderStatus.FILLED
        self._events.append(OrderFilled(order_id=self.id, fill_price=fill_price))

    def pop_events(self) -> list:
        events, self._events = self._events, []
        return events
```

### Application Layer

Each use case is a handler class with a single `handle(command_or_query)` async method.

**Command handler structure:**
```python
# application/equity/commands/convert_to_delivery.py
from dataclasses import dataclass
from application.shared.command import BaseCommand, CommandHandler
from domains.equity.conversion import ConversionCandidate
from domains.equity.ports import IPositionRepository
from domains.orders.ports import IBrokerOrderPort, IOrderRepository
from domains.risk.ports import IRiskRepository

@dataclass(frozen=True)
class ConvertToDeliveryCommand(BaseCommand):
    position_id: str
    cnc_qty: int
    swing_sl: float
    user_id: str

@dataclass
class ConvertToDeliveryResult:
    success: bool
    cnc_position_id: str | None
    closed_intra_qty: int
    message: str

class ConvertToDeliveryHandler(CommandHandler[ConvertToDeliveryCommand, ConvertToDeliveryResult]):
    def __init__(
        self,
        position_repo: IPositionRepository,
        order_repo: IOrderRepository,
        broker: IBrokerOrderPort,
        risk_repo: IRiskRepository,
    ):
        self._position_repo = position_repo
        self._order_repo = order_repo
        self._broker = broker
        self._risk_repo = risk_repo

    async def handle(self, cmd: ConvertToDeliveryCommand) -> ConvertToDeliveryResult:
        # Full orchestration shown in 03-application-layer.md
        ...
```

### Infrastructure Layer

The infrastructure layer is the only place that:
- Opens DB sessions (`async with async_session() as session`)
- Calls Dhan SDK methods
- Reads/writes Redis keys
- Schedules background tasks

All implementations satisfy abstract interfaces, making the application layer testable by swapping in fakes.

**Repository implementation pattern:**
```python
# infrastructure/repositories/order_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domains.orders.ports import IOrderRepository
from domains.orders.order import Order
from infrastructure.repositories.models import OrderORM

class OrderRepository(IOrderRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, order: Order) -> None:
        orm = OrderORM.from_domain(order)
        self._session.add(orm)
        await self._session.flush()

    async def get_by_dhan_id(self, dhan_id: str) -> Order | None:
        result = await self._session.execute(
            select(OrderORM).where(OrderORM.dhan_order_id == dhan_id)
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None
```

### API Layer

FastAPI routers receive validated Pydantic request bodies, call the appropriate command or query handler via `Depends()`, and return serialized response models.

```python
# api/v1/equity/router.py
from fastapi import APIRouter, Depends
from api.v1.deps import get_convert_handler
from application.equity.commands.convert_to_delivery import (
    ConvertToDeliveryCommand,
    ConvertToDeliveryHandler,
    ConvertToDeliveryResult,
)

router = APIRouter(prefix="/equity", tags=["equity"])

class ConvertRequest(BaseModel):
    position_id: str
    cnc_qty: int
    swing_sl: float

@router.post("/convert", response_model=ConvertToDeliveryResult)
async def convert_to_delivery(
    body: ConvertRequest,
    handler: ConvertToDeliveryHandler = Depends(get_convert_handler),
    current_user: User = Depends(get_current_user),
):
    cmd = ConvertToDeliveryCommand(
        position_id=body.position_id,
        cnc_qty=body.cnc_qty,
        swing_sl=body.swing_sl,
        user_id=current_user.id,
    )
    return await handler.handle(cmd)
```

---

## Dependency Injection Pattern

FastAPI's `Depends()` is used to wire all application-layer handlers with their infrastructure dependencies. A central `deps.py` file per API version provides factory functions.

```python
# api/v1/deps.py
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db_session
from infrastructure.dhan.client import DhanClient
from infrastructure.repositories.order_repo import OrderRepository
from infrastructure.repositories.position_repo import PositionRepository
from infrastructure.cache.session_cache import SessionCache
from application.equity.commands.convert_to_delivery import ConvertToDeliveryHandler

def get_dhan_client() -> DhanClient:
    # Singleton-like: app-level instance, not per-request
    from main import dhan_client
    return dhan_client

async def get_convert_handler(
    session: AsyncSession = Depends(get_db_session),
    dhan: DhanClient = Depends(get_dhan_client),
) -> ConvertToDeliveryHandler:
    return ConvertToDeliveryHandler(
        position_repo=PositionRepository(session),
        order_repo=OrderRepository(session),
        broker=dhan,
        risk_repo=RiskRepository(session),
    )
```

**Scoping rules:**
- `AsyncSession` — per-request scope (new session per HTTP request).
- `DhanClient` — application scope (single instance, holds WebSocket connection).
- `Redis` connection pool — application scope.
- `APScheduler` — application scope (started in lifespan).

---

## Async Concurrency Model

The backend runs on a **single asyncio event loop** managed by uvicorn.

```
┌─────────────────────────────────────────────────────────────┐
│                     asyncio Event Loop                       │
│                                                             │
│  HTTP Requests ──── FastAPI handlers ──── DB / Redis I/O    │
│                                                             │
│  Market Feed WS ─── Binary parser ──── Quote cache update   │
│                                                             │
│  Order Feed WS ──── JSON parser ──── Order status update    │
│                                                             │
│  Position Poll ──── GET /positions (every 3-5s) ───────────  │
│                                                             │
│  CSL Monitor ────── Check strategies (every 3s) ───────────  │
│                                                             │
│  Background Jobs ── APScheduler tasks (EOD, token renewal)  │
│                                                             │
│  CPU Work (numpy) ── run_in_executor ──── ThreadPoolExecutor │
└─────────────────────────────────────────────────────────────┘
```

**Key rules:**
- No blocking calls on the event loop. Any synchronous operation (numpy heavy computation, file I/O) runs in `asyncio.run_in_executor`.
- WebSocket connections to Dhan run as persistent `asyncio.Task` instances, started during app lifespan startup.
- Background jobs (APScheduler) run async job functions directly on the event loop.

---

## CQRS Flow Diagram

### Command Flow (Write Path)

```
HTTP POST /api/v1/equity/convert
        │
        ▼
[FastAPI Router] ── validate request body (Pydantic)
        │
        ▼
[ConvertToDeliveryCommand] ── frozen dataclass
        │
        ▼
[ConvertToDeliveryHandler.handle()]
        │
        ├── IPositionRepository.get(position_id) ──────────── PostgreSQL
        │
        ├── Domain logic: ConversionCandidate.validate()
        │       ↓ raises DomainError if not eligible
        │
        ├── IBrokerOrderPort.place_order(close_intra_leg) ─── Dhan API
        │
        ├── IBrokerOrderPort.place_order(new_cnc_order) ───── Dhan API
        │
        ├── IPositionRepository.save(cnc_position) ─────────── PostgreSQL
        │
        ├── IOrderRepository.save(orders) ───────────────────── PostgreSQL
        │
        └── EventBus.publish(PositionConverted) ─────────────── internal
                │
                ▼
        [Event Handlers]
          - JournalHandler: create journal entry
          - AlertHandler: notify user via cockpit WS
```

### Query Flow (Read Path)

```
HTTP GET /api/v1/equity/conversion-candidates
        │
        ▼
[FastAPI Router] ── validate query params
        │
        ▼
[GetConversionCandidatesQuery]
        │
        ▼
[GetConversionCandidatesHandler.handle()]
        │
        ├── Redis SessionCache.get_positions() ── cache hit → return
        │        ↓ cache miss
        ├── PositionRepository.get_intraday_positions()
        │
        ├── For each position:
        │     ConversionCandidate.evaluate(position, market_close_time)
        │
        └── Return List[ConversionCandidate] ── serialized by router
```

---

## Domain Boundaries and Ownership

| Domain | Owns | Consults (read-only) |
|---|---|---|
| `market_data` | Quotes, OHLCV candles, instrument master | — |
| `signals` | Signal scoring, watchlist | `market_data` (for candles) |
| `equity` | Intraday + CNC positions, conversion logic | `risk` (for sizing), `orders` (for SL order IDs) |
| `orders` | Order lifecycle (placed → filled → cancelled) | `market_data` (for current price) |
| `risk` | Daily limits, position sizing, ATR validation | `market_data` (for ATR candles), `equity` (for open positions) |
| `options` | Option legs, strategies, baskets, CSL/LSL | `market_data` (for Greeks), `orders` (for leg orders) |
| `portfolio` | Aggregated P&L, allocations across equity + options | `equity`, `options` |
| `alerts` | Alert rules, notification dispatch | All domains (subscribes to events) |

---

## Inter-Domain Communication

Domains do **not** call each other directly. All cross-domain communication happens via:

1. **Domain Events** through the internal async event bus.
   - Example: `orders` domain emits `OrderFilled`. The `equity` domain handler listens and updates position state.

2. **Application layer orchestration** — the command handler reaches into multiple domain repositories and services explicitly. The application layer is the legitimate place for cross-domain coordination.

3. **Shared value objects** — `Symbol`, `Money`, `Price`, `Quantity` are defined in `domains/shared/` and imported freely by all other domains without coupling.

```python
# domains/equity/events.py
from domains.shared.domain_event import DomainEvent
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class PositionConverted(DomainEvent):
    position_id: UUID
    symbol: str
    intra_qty_closed: int
    cnc_qty_created: int
    occurred_at: datetime

# infrastructure/messaging/event_bus.py registers handlers:
# event_bus.subscribe(PositionConverted, journal_handler.on_position_converted)
# event_bus.subscribe(PositionConverted, alert_handler.on_position_converted)
```
