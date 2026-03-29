# 07 — Broker Abstraction

How the cockpit connects to brokers and data sources without coupling domain logic to any specific API.

---

## Design Principle

> Data source and order execution are separate concerns. Tomorrow, market data may come from one provider and orders may go to a different broker.

Two independent ports:

| Port | Interface | Responsibility |
|------|-----------|---------------|
| `IMarketDataPort` | Data source | Quotes, candles, option chain, tick stream |
| `IOrderBrokerPort` | Order execution | Place/cancel/modify orders, positions, product conversion |

The cockpit domain and application layers never import broker SDKs. They only depend on these two interfaces.

---

## BrokerCapabilities

Every `IOrderBrokerPort` implementation declares its capabilities upfront. Application handlers check capabilities to decide execution strategy — not the broker name.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BrokerCapabilities:
    broker_id: str

    # Order features
    has_super_order: bool           # entry + SL + target in one call
    has_basket_orders: bool         # multi-leg atomic placement
    has_oco_order: bool             # forever order / OCO
    has_cover_order: bool           # CO with mandatory bracket SL
    has_product_conversion: bool    # MIS → CNC/NRML conversion API

    # Data features
    has_realtime_positions: bool    # WebSocket position updates
    has_historical_greeks: bool     # historical IV/Greeks data
    has_tick_data: bool             # tick-level historical

    # Constraints
    requires_static_ip: bool
    token_validity_hours: int       # 0 = never expires
    orders_per_day_cap: int         # 0 = unlimited
    option_chain_rate_limit_seconds: int
```

### Dhan Capabilities

```python
DHAN_CAPABILITIES = BrokerCapabilities(
    broker_id="dhan_v2",
    has_super_order=True,
    has_basket_orders=False,                # must place legs individually
    has_oco_order=True,                     # Forever Order supported
    has_cover_order=False,
    has_product_conversion=True,            # POST /positions/convert
    has_realtime_positions=False,           # must poll GET /positions every 3–5s
    has_historical_greeks=False,
    has_tick_data=False,
    requires_static_ip=True,
    token_validity_hours=24,
    orders_per_day_cap=5000,
    option_chain_rate_limit_seconds=3,
)
```

### Paper Capabilities

```python
PAPER_CAPABILITIES = BrokerCapabilities(
    broker_id="paper",
    has_super_order=True,                   # simulated
    has_basket_orders=True,                 # no real constraint in simulation
    has_oco_order=True,                     # simulated
    has_cover_order=True,                   # simulated
    has_product_conversion=True,            # row update in paper_positions
    has_realtime_positions=True,            # fills update positions immediately
    has_historical_greeks=False,
    has_tick_data=False,
    requires_static_ip=False,
    token_validity_hours=0,                 # never expires
    orders_per_day_cap=0,                   # unlimited
    option_chain_rate_limit_seconds=0,
)
```

---

## IMarketDataPort

```python
from typing import Protocol, Callable, Awaitable
from datetime import datetime, date

class IMarketDataPort(Protocol):
    async def get_quote(self, symbol: Symbol) -> Quote: ...

    async def get_quotes(self, symbols: list[Symbol]) -> dict[Symbol, Quote]: ...

    async def get_candles(
        self,
        symbol: Symbol,
        interval: CandleInterval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]: ...

    async def get_option_chain(
        self,
        underlying: Symbol,
        expiry: date,
    ) -> OptionChain: ...

    async def subscribe_ticks(
        self,
        symbols: list[Symbol],
        handler: Callable[[Tick], Awaitable[None]],
    ) -> str: ...  # returns subscription_id

    async def unsubscribe(self, subscription_id: str) -> None: ...

    @property
    def is_connected(self) -> bool: ...
```

---

## IOrderBrokerPort

```python
class IOrderBrokerPort(Protocol):
    @property
    def capabilities(self) -> BrokerCapabilities: ...

    async def place_order(self, cmd: PlaceOrderCommand) -> OrderId: ...

    async def cancel_order(self, order_id: OrderId) -> None: ...

    async def modify_order(
        self, order_id: OrderId, cmd: ModifyOrderCommand
    ) -> None: ...

    async def get_order_status(self, order_id: OrderId) -> OrderStatus: ...

    async def get_positions(self) -> list[Position]: ...

    async def convert_product(self, cmd: ConvertProductCommand) -> None: ...

    async def get_account_balance(self) -> AccountBalance: ...
```

---

## Product Type Abstraction

Domain uses canonical terms. Adapters translate to broker-specific values.

| Domain `ProductType` | Dhan | Zerodha (future) | Upstox (future) |
|---------------------|------|-----------------|-----------------|
| `INTRADAY` | `"INTRADAY"` | `"MIS"` | `"I"` |
| `DELIVERY` | `"CNC"` | `"NRML"` | `"D"` |
| `CARRY_FORWARD` | `"MARGIN"` | `"NRML"` | `"D"` |

```python
# In DhanOrderBrokerAdapter
_PRODUCT_MAP: dict[ProductType, str] = {
    ProductType.INTRADAY: "INTRADAY",
    ProductType.DELIVERY: "CNC",
    ProductType.CARRY_FORWARD: "MARGIN",
}
```

---

## DhanMarketDataAdapter

```python
class DhanMarketDataAdapter:
    def __init__(self, client: DhanClient) -> None:
        self._client = client
        self._last_option_chain_call: float = 0.0
        self._subscriptions: dict[str, set[Symbol]] = {}

    async def get_candles(
        self,
        symbol: Symbol,
        interval: CandleInterval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]:
        """Paginate Dhan's 90-day max per call limit."""
        all_candles: list[Candle] = []
        cursor = from_dt
        while cursor < to_dt:
            chunk_end = min(cursor + timedelta(days=90), to_dt)
            raw = await self._client.get_intraday_candles(
                symbol=symbol.dhan_id,
                interval=_INTERVAL_MAP[interval],
                from_date=cursor.date(),
                to_date=chunk_end.date(),
            )
            all_candles.extend(_parse_candles(raw))
            cursor = chunk_end + timedelta(days=1)
        return all_candles

    async def get_option_chain(
        self, underlying: Symbol, expiry: date
    ) -> OptionChain:
        """Respect Dhan's 1 request per 3 seconds rate limit."""
        elapsed = time.monotonic() - self._last_option_chain_call
        if elapsed < 3.0:
            await asyncio.sleep(3.0 - elapsed)
        raw = await self._client.get_option_chain(
            underlying_scrip=underlying.dhan_id,
            expiry_date=expiry.isoformat(),
        )
        self._last_option_chain_call = time.monotonic()
        return _parse_option_chain(raw)

    async def subscribe_ticks(
        self,
        symbols: list[Symbol],
        handler: Callable[[Tick], Awaitable[None]],
    ) -> str:
        sub_id = str(uuid4())
        self._subscriptions[sub_id] = set(symbols)
        # Register handler with DhanClient binary WebSocket
        await self._client.subscribe_market_feed(
            instruments=[s.dhan_instrument for s in symbols],
            callback=lambda raw: asyncio.create_task(
                handler(_parse_tick(raw))
            ),
        )
        return sub_id
```

---

## DhanOrderBrokerAdapter

```python
class DhanOrderBrokerAdapter:
    def __init__(self, client: DhanClient) -> None:
        self._client = client

    @property
    def capabilities(self) -> BrokerCapabilities:
        return DHAN_CAPABILITIES

    async def place_order(self, cmd: PlaceOrderCommand) -> OrderId:
        payload = {
            "dhanClientId": self._client.client_id,
            "transactionType": cmd.side.value,          # "BUY" | "SELL"
            "exchangeSegment": cmd.symbol.exchange.value,
            "productType": _PRODUCT_MAP[cmd.product_type],
            "orderType": _ORDER_TYPE_MAP[cmd.order_type],
            "quantity": cmd.qty,
            "price": str(cmd.limit_price) if cmd.limit_price else "0",
            "triggerPrice": str(cmd.trigger_price) if cmd.trigger_price else "0",
            "validity": "DAY",
            "securityId": cmd.symbol.dhan_id,
        }
        result = await self._client.place_order(**payload)
        return OrderId(result["orderId"])

    async def convert_product(self, cmd: ConvertProductCommand) -> None:
        await self._client.convert_position(
            from_product_type=_PRODUCT_MAP[cmd.from_product],
            to_product_type=_PRODUCT_MAP[cmd.to_product],
            exchange_segment=cmd.symbol.exchange.value,
            position_type=cmd.position_type.value,   # "LONG" | "SHORT"
            security_id=cmd.symbol.dhan_id,
            convert_qty=cmd.qty,
        )
```

---

## PaperOrderBrokerAdapter

```python
class PaperOrderBrokerAdapter:
    """
    Simulates order execution using real market data ticks.
    All state in PostgreSQL. Same code path as live trading.
    """

    def __init__(
        self,
        repo: PaperOrderRepository,
        account_id: UUID,
    ) -> None:
        self._repo = repo
        self._account_id = account_id

    @property
    def capabilities(self) -> BrokerCapabilities:
        return PAPER_CAPABILITIES

    async def place_order(self, cmd: PlaceOrderCommand) -> OrderId:
        order = PaperOrder(
            account_id=self._account_id,
            client_order_id=str(uuid4()),
            symbol=cmd.symbol.value,
            side=cmd.side.value,
            order_type=cmd.order_type.value,
            product_type=_PRODUCT_MAP[cmd.product_type],
            qty=cmd.qty,
            limit_price=cmd.limit_price,
            trigger_price=cmd.trigger_price,
            status="PENDING",
        )
        await self._repo.insert_order(order)
        return OrderId(order.client_order_id)

    async def get_positions(self) -> list[Position]:
        paper_pos = await self._repo.get_positions(self._account_id)
        return [_map_paper_position(p) for p in paper_pos]

    async def convert_product(self, cmd: ConvertProductCommand) -> None:
        await self._repo.update_position_product_type(
            account_id=self._account_id,
            symbol=cmd.symbol.value,
            from_product=_PRODUCT_MAP[cmd.from_product],
            to_product=_PRODUCT_MAP[cmd.to_product],
            qty=cmd.qty,
        )
```

---

## Capability-Aware Application Code

Application handlers check capabilities — never the broker name.

```python
# In PlaceOptionsStrategyHandler
class PlaceOptionsStrategyHandler:
    def __init__(self, broker: IOrderBrokerPort) -> None:
        self._broker = broker

    async def handle(self, cmd: PlaceOptionsStrategyCommand) -> StrategyId:
        if self._broker.capabilities.has_basket_orders:
            # Atomic multi-leg placement
            return await self._place_basket(cmd)
        else:
            # Sequential placement with abort-on-failure
            return await self._place_sequential(cmd)
```

```python
# In PositionPollingService
class PositionPollingService:
    def __init__(self, broker: IOrderBrokerPort) -> None:
        self._broker = broker

    def get_poll_interval(self) -> float:
        if self._broker.capabilities.has_realtime_positions:
            return 0.0   # no polling needed — WS pushes updates
        return 3.0        # Dhan: poll every 3 seconds
```

---

## Dependency Injection Configuration

```python
# src/infrastructure/config/settings.py
class BrokerSettings(BaseSettings):
    active_order_broker: Literal["dhan", "paper"] = "dhan"
    active_market_data: Literal["dhan"] = "dhan"   # always real data
    paper_starting_capital: Decimal = Decimal("1000000")
    paper_account_id: UUID | None = None
```

```python
# src/infrastructure/di/providers.py
def get_order_broker(
    settings: BrokerSettings = Depends(get_settings),
    container: Container = Depends(get_container),
) -> IOrderBrokerPort:
    match settings.active_order_broker:
        case "dhan":
            return container.dhan_order_adapter
        case "paper":
            return container.paper_order_adapter

def get_market_data(
    container: Container = Depends(get_container),
) -> IMarketDataPort:
    # Market data is always real (Dhan WebSocket)
    # Paper mode only simulates order execution
    return container.dhan_market_data_adapter
```

Switching brokers: change `ACTIVE_ORDER_BROKER` env var. No code changes.

---

## What the Broker Does NOT Control

| Cockpit Domain | Never the Broker's Job |
|----------------|----------------------|
| Signal scoring | Broker has no knowledge of setups |
| Position sizing | Cockpit calculates from risk % |
| LSL/CSL calculation | Cockpit calculates; sends as order |
| MIS→CNC eligibility | Cockpit decides; broker executes |
| Conversion quantity | Cockpit calculates swing risk budget |
| Daily loss limits | Cockpit enforces; broker is unaware |
| Pyramid logic | Cockpit flags; trader decides |
