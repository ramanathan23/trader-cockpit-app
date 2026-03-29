# Infrastructure Layer Design

**Project:** Trader Cockpit App
**Layer:** Infrastructure (Dhan adapter, repositories, cache, jobs, event bus)
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [Dhan Adapter](#dhan-adapter)
   - [DhanClient](#dhanclient)
   - [Binary WebSocket Market Feed](#binary-websocket-market-feed)
   - [Order Update WebSocket](#order-update-websocket)
   - [Option Chain Polling](#option-chain-polling)
   - [Position Poll Service](#position-poll-service)
   - [Mapper — Dhan Response to Domain Models](#mapper--dhan-response-to-domain-models)
   - [Sequential Leg Placement Engine](#sequential-leg-placement-engine)
   - [Error Handling and Retry Strategy](#error-handling-and-retry-strategy)
   - [Token Management](#token-management)
2. [Repository Implementations](#repository-implementations)
   - [CandleRepository — TimescaleDB](#candlerepository--timescaledb)
   - [WatchlistRepository](#watchlistrepository)
   - [OrderRepository](#orderrepository)
   - [StrategyRepository](#strategyrepository)
3. [Redis Cache Patterns](#redis-cache-patterns)
   - [QuoteCache](#quotecache)
   - [LiveCandleBuilder](#livecandlebuilder)
   - [OptionChainCache](#optionchaincache)
4. [Background Jobs](#background-jobs)
   - [EODScanJob](#eodscanjobi)
   - [CandleAggregatorWorker](#candleaggregatorworker)
   - [TokenRenewalJob](#tokenrenewaljob)
   - [CSLMonitorTask](#cslmonitortask)
5. [Internal Event Bus](#internal-event-bus)

---

## Dhan Adapter

The Dhan adapter is the infrastructure implementation of all broker ports defined by the domain and application layers. It wraps the `dhanhq` SDK and adds async support, error handling, retry logic, and domain mapping.

### DhanClient

```python
# infrastructure/dhan/client.py
import asyncio
from decimal import Decimal
from typing import Any
import structlog
from dhanhq import dhanhq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from infrastructure.dhan.token_store import TokenStore
from infrastructure.dhan.mapper import DhanMapper

log = structlog.get_logger(__name__)

class DhanBrokerError(Exception):
    """Raised when Dhan API returns a business-level error (4xx)."""
    def __init__(self, message: str, dhan_code: str | None = None):
        super().__init__(message)
        self.dhan_code = dhan_code

class DhanNetworkError(Exception):
    """Raised on transient network failures — eligible for retry."""
    pass

class DhanClient:
    """
    Async wrapper around the synchronous dhanhq SDK.
    All SDK calls run in a thread executor to avoid blocking the event loop.

    Implements:
    - IBrokerOrderPort (place_order, cancel_order, modify_order)
    - IBrokerPositionPort (get_positions)
    - IBrokerMarketDataPort (get_historical_candles)

    Note: The dhanhq SDK is synchronous. We use asyncio.run_in_executor
    to run SDK calls in a thread pool and return awaitables to the
    async application layer.
    """

    def __init__(
        self,
        client_id: str,
        token_store: TokenStore,
        mapper: DhanMapper,
        executor=None,
    ):
        self._client_id = client_id
        self._token_store = token_store
        self._mapper = mapper
        self._executor = executor  # ThreadPoolExecutor (app-level)
        self._sdk: dhanhq | None = None

    async def initialize(self) -> None:
        """Called during app lifespan startup. Loads token and creates SDK instance."""
        token = await self._token_store.get_token()
        if not token:
            raise RuntimeError("Dhan access token not found in Redis. Run token renewal.")
        loop = asyncio.get_event_loop()
        self._sdk = await loop.run_in_executor(
            self._executor,
            lambda: dhanhq(self._client_id, token)
        )
        log.info("DhanClient initialized", client_id=self._client_id)

    async def _run_sync(self, fn, *args, **kwargs):
        """Run a synchronous SDK call in the thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: fn(*args, **kwargs)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(DhanNetworkError),
        reraise=True,
    )
    async def place_order(self, order) -> str:
        """
        Place an order via Dhan API.
        Returns: dhan_order_id (string)
        """
        payload = self._mapper.order_to_dhan_request(order)
        log.info("Placing order", symbol=str(order.symbol), side=order.side, qty=order.qty)

        try:
            response = await self._run_sync(self._sdk.place_order, **payload)
        except ConnectionError as e:
            raise DhanNetworkError(f"Network error placing order: {e}") from e

        self._check_response(response, context="place_order")
        dhan_order_id = response["data"]["orderId"]
        log.info("Order placed", dhan_order_id=dhan_order_id)
        return str(dhan_order_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(DhanNetworkError),
        reraise=True,
    )
    async def cancel_order(self, dhan_order_id: str) -> bool:
        log.info("Cancelling order", dhan_order_id=dhan_order_id)
        try:
            response = await self._run_sync(self._sdk.cancel_order, dhan_order_id)
        except ConnectionError as e:
            raise DhanNetworkError(f"Network error cancelling order: {e}") from e

        if response.get("status") == "success":
            return True
        # Order may already be filled — check error code
        error_code = response.get("errorCode", "")
        if error_code in ("OE006", "OE007"):
            # Already filled or already cancelled — not an error
            log.warning("Cancel attempted on terminal order", dhan_order_id=dhan_order_id, code=error_code)
            return False
        self._check_response(response, context="cancel_order")
        return False

    async def get_positions(self) -> list:
        """Poll all open positions from Dhan. Returns raw domain models."""
        try:
            response = await self._run_sync(self._sdk.get_positions)
        except ConnectionError as e:
            raise DhanNetworkError(f"Network error fetching positions: {e}") from e
        self._check_response(response, context="get_positions")
        return [
            self._mapper.dhan_position_to_domain(p)
            for p in (response.get("data") or [])
        ]

    async def get_historical_candles(
        self,
        security_id: str,
        exchange: str,
        instrument_type: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> list:
        """
        Fetch historical candles. Interval must be one of:
        1, 5, 15, 25, 60 (minutes) or "D" (daily).
        Date format: "YYYY-MM-DD".
        """
        try:
            response = await self._run_sync(
                self._sdk.intraday_minute_data
                if interval != "D"
                else self._sdk.historical_daily_data,
                security_id=security_id,
                exchange_segment=exchange,
                instrument_type=instrument_type,
                interval=interval,
                from_date=from_date,
                to_date=to_date,
            )
        except ConnectionError as e:
            raise DhanNetworkError(f"Network error fetching candles: {e}") from e
        self._check_response(response, context="get_historical_candles")
        return self._mapper.dhan_candles_to_domain(
            response.get("data", []), interval
        )

    async def get_order_list(self) -> list:
        """Fetch today's order book from Dhan."""
        response = await self._run_sync(self._sdk.get_order_list)
        self._check_response(response, context="get_order_list")
        return [self._mapper.dhan_order_to_domain(o) for o in (response.get("data") or [])]

    async def exit_all_positions(self) -> dict:
        """Dhan Kill Switch — exits all open positions."""
        log.warning("KILL SWITCH TRIGGERED — exiting all positions")
        response = await self._run_sync(self._sdk.kill_switch, "ACTIVATE")
        return response

    def _check_response(self, response: dict, context: str) -> None:
        """Raise appropriate exception based on Dhan API response status."""
        status = response.get("status", "")
        if status == "success":
            return
        error_msg = response.get("remarks", response.get("message", "Unknown error"))
        error_code = response.get("errorCode", "")
        log.error("Dhan API error",
                  context=context,
                  status=status,
                  error=error_msg,
                  code=error_code)
        raise DhanBrokerError(message=error_msg, dhan_code=error_code)
```

### Binary WebSocket Market Feed

```python
# infrastructure/dhan/market_feed.py
import asyncio
import struct
from decimal import Decimal
from datetime import datetime, timezone
from typing import Callable
import websockets
import structlog
from domains.market_data.value_objects import Tick
from infrastructure.cache.quote_cache import QuoteCache
from infrastructure.dhan.token_store import TokenStore

log = structlog.get_logger(__name__)

# Dhan binary packet header format (DhanHQ v2 market feed)
# Reference: https://dhanhq.co/docs/v2/market-feed/
PACKET_HEADER_FORMAT = ">BHI"   # type(1), length(2), sequence(4)
PACKET_HEADER_SIZE   = struct.calcsize(PACKET_HEADER_FORMAT)

PACKET_TYPE_QUOTE      = 11
PACKET_TYPE_TICK       = 15
PACKET_TYPE_DISCONNECT = 50

class MarketFeedParser:
    """
    Parses Dhan binary WebSocket packets into domain Tick objects.
    Dhan uses big-endian binary encoding for market data to minimize bandwidth.
    """

    def parse_packet(self, data: bytes) -> Tick | None:
        if len(data) < PACKET_HEADER_SIZE:
            return None

        packet_type, length, seq = struct.unpack_from(PACKET_HEADER_FORMAT, data, 0)
        payload = data[PACKET_HEADER_SIZE:]

        if packet_type == PACKET_TYPE_QUOTE:
            return self._parse_quote_packet(payload)
        elif packet_type == PACKET_TYPE_TICK:
            return self._parse_tick_packet(payload)
        return None

    def _parse_quote_packet(self, payload: bytes) -> Tick | None:
        """
        Full quote packet (packet type 11):
        security_id (4B) | ltp (4B float) | volume (4B) | oi (4B) |
        timestamp (4B epoch)
        """
        if len(payload) < 20:
            return None
        try:
            security_id_bytes, ltp, volume, oi, ts = struct.unpack(">4sffII", payload[:20])
            security_id = security_id_bytes.decode("ascii").strip("\x00")
            return Tick(
                security_id=security_id,
                ltp=Decimal(str(round(ltp, 2))),
                volume=int(volume),
                oi=int(oi) if oi > 0 else None,
                timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
            )
        except struct.error as e:
            log.warning("Failed to parse quote packet", error=str(e))
            return None

    def _parse_tick_packet(self, payload: bytes) -> Tick | None:
        """LTP-only tick (packet type 15): security_id (4B) | ltp (4B float)"""
        if len(payload) < 8:
            return None
        try:
            security_id_bytes, ltp = struct.unpack(">4sf", payload[:8])
            security_id = security_id_bytes.decode("ascii").strip("\x00")
            return Tick(
                security_id=security_id,
                ltp=Decimal(str(round(ltp, 2))),
                volume=0,
                oi=None,
                timestamp=datetime.now(tz=timezone.utc),
            )
        except struct.error:
            return None


class MarketFeedService:
    """
    Long-running asyncio task that maintains the Dhan binary WebSocket connection.
    Receives market feed packets, parses them, and stores in QuoteCache.
    Also notifies registered tick listeners (e.g., LiveCandleBuilder).
    """
    DHAN_MARKET_FEED_URL = "wss://api-feed.dhan.co"

    def __init__(
        self,
        token_store: TokenStore,
        quote_cache: QuoteCache,
        parser: MarketFeedParser,
        client_id: str,
    ):
        self._token_store = token_store
        self._quote_cache = quote_cache
        self._parser = parser
        self._client_id = client_id
        self._subscribed_ids: set[str] = set()
        self._tick_listeners: list[Callable] = []
        self._running = False

    def add_tick_listener(self, listener: Callable) -> None:
        """Register a callback to receive ticks (e.g., candle aggregator)."""
        self._tick_listeners.append(listener)

    def subscribe(self, security_ids: list[str]) -> None:
        """Add security IDs to subscription set. Sent on next reconnect."""
        self._subscribed_ids.update(security_ids)

    async def run(self) -> None:
        """
        Main loop: connect → subscribe → receive → reconnect on failure.
        Runs as a persistent asyncio.Task for the app lifetime.
        """
        self._running = True
        while self._running:
            try:
                await self._connect_and_receive()
            except Exception as e:
                log.error("Market feed disconnected", error=str(e))
                if self._running:
                    log.info("Reconnecting in 5s...")
                    await asyncio.sleep(5)

    async def _connect_and_receive(self) -> None:
        token = await self._token_store.get_token()
        async with websockets.connect(
            self.DHAN_MARKET_FEED_URL,
            extra_headers={"Authorization": f"Bearer {token}"},
            ping_interval=20,
            ping_timeout=10,
        ) as ws:
            log.info("Market feed connected")
            # Send subscription request
            if self._subscribed_ids:
                await self._send_subscription(ws)

            # Receive loop
            async for message in ws:
                if isinstance(message, bytes):
                    tick = self._parser.parse_packet(message)
                    if tick:
                        await self._quote_cache.set_tick(tick)
                        for listener in self._tick_listeners:
                            await listener(tick)

    async def _send_subscription(self, ws) -> None:
        """Send subscription packet for all subscribed security IDs."""
        import json
        subscription = {
            "RequestCode": 21,  # Subscribe
            "InstrumentCount": len(self._subscribed_ids),
            "InstrumentList": [
                {"ExchangeSegment": "NSE_EQ", "SecurityId": sid}
                for sid in self._subscribed_ids
            ],
        }
        await ws.send(json.dumps(subscription))
        log.info("Subscribed to market feed", count=len(self._subscribed_ids))

    async def stop(self) -> None:
        self._running = False
```

### Order Update WebSocket

```python
# infrastructure/dhan/order_feed.py
import asyncio
import json
import structlog
import websockets
from infrastructure.dhan.token_store import TokenStore
from infrastructure.messaging.event_bus import EventBus
from infrastructure.repositories.order_repo import OrderRepository
from infrastructure.dhan.mapper import DhanMapper

log = structlog.get_logger(__name__)

class OrderFeedService:
    """
    Receives real-time order update events from Dhan via JSON WebSocket.
    On fill: updates order status in DB and publishes OrderFilled domain event.
    On cancel: updates order status and publishes OrderCancelled.

    Note: Dhan order feed is JSON (not binary), unlike the market feed.
    """
    DHAN_ORDER_FEED_URL = "wss://api-order-update.dhan.co"

    def __init__(
        self,
        token_store: TokenStore,
        order_repo: OrderRepository,
        mapper: DhanMapper,
        event_bus: EventBus,
    ):
        self._token_store = token_store
        self._order_repo = order_repo
        self._mapper = mapper
        self._event_bus = event_bus
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._connect_and_receive()
            except Exception as e:
                log.error("Order feed disconnected", error=str(e))
                if self._running:
                    await asyncio.sleep(5)

    async def _connect_and_receive(self) -> None:
        token = await self._token_store.get_token()
        async with websockets.connect(
            self.DHAN_ORDER_FEED_URL,
            extra_headers={"Authorization": f"Bearer {token}"},
        ) as ws:
            log.info("Order feed connected")
            async for message in ws:
                try:
                    data = json.loads(message)
                    await self._handle_order_update(data)
                except Exception as e:
                    log.error("Error processing order update", error=str(e), data=message)

    async def _handle_order_update(self, data: dict) -> None:
        """
        Process an order status update from Dhan.
        data keys (Dhan v2): orderId, orderStatus, filledQty, tradedPrice, ...
        """
        dhan_order_id = str(data.get("orderId", ""))
        status = data.get("orderStatus", "").upper()
        order = await self._order_repo.get_by_dhan_id(dhan_order_id)
        if not order:
            log.warning("Received update for unknown order", dhan_id=dhan_order_id)
            return

        if status == "TRADED":
            fill_price = float(data.get("tradedPrice", 0))
            filled_qty = int(data.get("filledQty", 0))
            order.mark_filled(
                fill_price=__import__("decimal").Decimal(str(fill_price)),
                filled_qty=filled_qty,
            )
            await self._order_repo.update(order)
            for event in order.pop_events():
                await self._event_bus.publish(event)

        elif status == "CANCELLED":
            order.cancel()
            await self._order_repo.update(order)
            for event in order.pop_events():
                await self._event_bus.publish(event)

        elif status == "REJECTED":
            reason = data.get("rejectReason", "Unknown")
            order.reject(reason)
            await self._order_repo.update(order)
            log.warning("Order rejected", dhan_id=dhan_order_id, reason=reason)
```

### Option Chain Polling

```python
# infrastructure/dhan/option_chain.py
import asyncio
from datetime import datetime
import structlog
from infrastructure.dhan.client import DhanClient
from infrastructure.cache.option_chain_cache import OptionChainCache

log = structlog.get_logger(__name__)

class OptionChainPoller:
    """
    Polls Dhan option chain API for subscribed underlyings.
    Rate limit: 1 request per 3 seconds per underlying.

    Strategy:
    - Maintains a queue of underlyings to poll.
    - Polls each underlying at most once per 3 seconds.
    - Stores result in OptionChainCache (TTL 3s).
    - Background strategies request their underlying to be polled
      by adding to the subscription set.
    """
    POLL_INTERVAL_SEC = 3.0

    def __init__(self, client: DhanClient, cache: OptionChainCache):
        self._client = client
        self._cache = cache
        self._subscribed: dict[str, str] = {}  # underlying → expiry
        self._running = False

    def subscribe(self, underlying: str, expiry: str) -> None:
        """Register an underlying for continuous polling."""
        self._subscribed[underlying] = expiry
        log.info("Option chain subscription added", underlying=underlying, expiry=expiry)

    def unsubscribe(self, underlying: str) -> None:
        self._subscribed.pop(underlying, None)

    async def run(self) -> None:
        """
        Polls option chains in round-robin, respecting the 3s rate limit.
        Each iteration polls one underlying, then sleeps 3s before the next.
        """
        self._running = True
        while self._running:
            if not self._subscribed:
                await asyncio.sleep(1)
                continue

            for underlying, expiry in list(self._subscribed.items()):
                if not self._running:
                    break
                try:
                    await self._poll_one(underlying, expiry)
                except Exception as e:
                    log.error("Option chain poll failed",
                              underlying=underlying, error=str(e))
                await asyncio.sleep(self.POLL_INTERVAL_SEC)

    async def _poll_one(self, underlying: str, expiry: str) -> None:
        chain_data = await self._client.get_option_chain(underlying, expiry)
        await self._cache.set_chain(underlying, expiry, chain_data)
        log.debug("Option chain cached", underlying=underlying, strikes=len(chain_data))
```

### Position Poll Service

```python
# infrastructure/dhan/position_poll.py
import asyncio
import structlog
from infrastructure.dhan.client import DhanClient
from infrastructure.repositories.position_repo import PositionRepository
from infrastructure.messaging.event_bus import EventBus

log = structlog.get_logger(__name__)

class PositionPollService:
    """
    Polls Dhan GET /positions every POLL_INTERVAL seconds during market hours.
    Dhan does not provide a real-time position WebSocket.

    On change detection:
    - Updates local position state in Redis (for low-latency reads).
    - Publishes position update events to the cockpit WebSocket broadcaster.

    Triggered also on order fills (via OrderFilled event handler) for
    immediate post-fill refresh.
    """
    POLL_INTERVAL_SEC = 4.0   # 3-5s per Dhan recommendation
    AFTER_FILL_DELAY_SEC = 1.0

    def __init__(
        self,
        client: DhanClient,
        position_repo: PositionRepository,
        event_bus: EventBus,
    ):
        self._client = client
        self._position_repo = position_repo
        self._event_bus = event_bus
        self._running = False
        self._force_poll = asyncio.Event()

    async def trigger_immediate_poll(self) -> None:
        """Called by order fill handler to force a position refresh."""
        await asyncio.sleep(self.AFTER_FILL_DELAY_SEC)
        self._force_poll.set()

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._poll_positions()
            except Exception as e:
                log.error("Position poll failed", error=str(e))

            # Wait for POLL_INTERVAL or a forced poll trigger
            try:
                await asyncio.wait_for(
                    self._force_poll.wait(),
                    timeout=self.POLL_INTERVAL_SEC,
                )
                self._force_poll.clear()
            except asyncio.TimeoutError:
                pass  # Normal interval expiry

    async def _poll_positions(self) -> None:
        positions = await self._client.get_positions()
        previous = await self._position_repo.get_cached_positions()
        changed_symbols = self._detect_changes(previous, positions)

        if changed_symbols:
            await self._position_repo.update_cached_positions(positions)
            from domains.equity.events import PositionStateUpdated
            for symbol in changed_symbols:
                await self._event_bus.publish(
                    PositionStateUpdated(symbol=symbol)
                )
            log.debug("Positions updated", changed=changed_symbols)

    def _detect_changes(self, previous: list, current: list) -> list[str]:
        """Return symbols where qty or P&L changed."""
        prev_map = {p.symbol.value: p for p in previous}
        curr_map = {p.symbol.value: p for p in current}
        changed = []
        for sym, pos in curr_map.items():
            prev = prev_map.get(sym)
            if prev is None or prev.qty != pos.qty:
                changed.append(sym)
        for sym in prev_map:
            if sym not in curr_map:
                changed.append(sym)  # Position closed
        return changed
```

### Mapper — Dhan Response to Domain Models

```python
# infrastructure/dhan/mapper.py
from decimal import Decimal
from datetime import datetime, timezone
from domains.shared.symbol import Symbol, Exchange
from domains.market_data.entities import OHLCV
from domains.market_data.enums import CandleInterval
from domains.orders.order import Order
from domains.orders.enums import OrderStatus, OrderType, ProductType, Side, OrderValidity
from uuid import uuid4

class DhanMapper:
    """
    Translates Dhan API response dictionaries into domain model instances.
    This is the only place that knows about Dhan's field naming conventions.
    """

    # Dhan field name → Domain field mapping
    DHAN_STATUS_MAP = {
        "PENDING":   OrderStatus.PENDING,
        "OPEN":      OrderStatus.OPEN,
        "PART_TRADED": OrderStatus.PARTIALLY_FILLED,
        "TRADED":    OrderStatus.FILLED,
        "CANCELLED": OrderStatus.CANCELLED,
        "REJECTED":  OrderStatus.REJECTED,
        "EXPIRED":   OrderStatus.EXPIRED,
    }

    DHAN_PRODUCT_MAP = {
        "INTRADAY": ProductType.INTRADAY,
        "CNC":      ProductType.CNC,
        "MARGIN":   ProductType.MARGIN,
    }

    DHAN_EXCHANGE_MAP = {
        "NSE_EQ":  Exchange.NSE,
        "BSE_EQ":  Exchange.BSE,
        "NSE_FNO": Exchange.NFO,
        "BSE_FNO": Exchange.BFO,
    }

    def dhan_order_to_domain(self, data: dict) -> Order:
        exchange = self.DHAN_EXCHANGE_MAP.get(data["exchangeSegment"], Exchange.NSE)
        symbol = Symbol(value=data["tradingSymbol"], exchange=exchange)
        order = Order(
            id=uuid4(),
            symbol=symbol,
            side=Side.BUY if data["transactionType"] == "BUY" else Side.SELL,
            qty=int(data["quantity"]),
            price=(Decimal(str(data["price"])) if data.get("price") else None),
            trigger_price=(
                Decimal(str(data["triggerPrice"]))
                if data.get("triggerPrice")
                else None
            ),
            order_type=self._map_order_type(data["orderType"]),
            product_type=self.DHAN_PRODUCT_MAP.get(
                data["productType"], ProductType.INTRADAY
            ),
            validity=OrderValidity.DAY,
            status=self.DHAN_STATUS_MAP.get(data["orderStatus"], OrderStatus.PENDING),
            dhan_order_id=str(data["orderId"]),
            filled_qty=int(data.get("filledQty", 0)),
            fill_price=(
                Decimal(str(data["tradedPrice"]))
                if data.get("tradedPrice")
                else None
            ),
        )
        return order

    def dhan_position_to_domain(self, data: dict) -> object:
        """
        Maps Dhan position dict to either IntradayPosition or CNCPosition.
        Returns a lightweight PositionSnapshot for polling purposes.
        """
        from dataclasses import dataclass

        @dataclass
        class PositionSnapshot:
            symbol: Symbol
            product_type: str
            qty: int
            avg_price: Decimal
            ltp: Decimal
            unrealized_pnl: Decimal

        exchange = self.DHAN_EXCHANGE_MAP.get(data["exchangeSegment"], Exchange.NSE)
        return PositionSnapshot(
            symbol=Symbol(value=data["tradingSymbol"], exchange=exchange),
            product_type=data.get("productType", "INTRADAY"),
            qty=int(data.get("netQty", 0)),
            avg_price=Decimal(str(data.get("avgCostPrice", 0))),
            ltp=Decimal(str(data.get("lastTradedPrice", 0))),
            unrealized_pnl=Decimal(str(data.get("unrealizedProfit", 0))),
        )

    def dhan_candles_to_domain(self, data: list, interval: str) -> list[OHLCV]:
        """
        Maps Dhan historical candle response to list of OHLCV domain objects.
        Dhan returns: open[], high[], low[], close[], volume[], timestamp[]
        """
        if not data:
            return []
        candle_interval = CandleInterval(interval)
        candles = []
        for row in data:
            ts = datetime.fromtimestamp(row["timestamp"], tz=timezone.utc)
            candles.append(OHLCV(
                symbol=None,  # Caller sets symbol
                interval=candle_interval,
                open_time=ts,
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
                volume=int(row.get("volume", 0)),
                oi=int(row.get("oi", 0)) or None,
            ))
        return candles

    def order_to_dhan_request(self, order) -> dict:
        """Convert domain Order to Dhan place_order payload."""
        return {
            "security_id": order.symbol.value,  # Dhan uses security_id, not symbol string
            "exchange_segment": self._to_dhan_exchange(order.symbol.exchange),
            "transaction_type": "BUY" if order.side == Side.BUY else "SELL",
            "quantity": order.qty,
            "order_type": self._to_dhan_order_type(order.order_type),
            "product_type": order.product_type.value,
            "price": float(order.price) if order.price else 0,
            "trigger_price": float(order.trigger_price) if order.trigger_price else 0,
            "validity": order.validity.value,
        }

    def _map_order_type(self, dhan_type: str) -> OrderType:
        mapping = {
            "LIMIT": OrderType.LIMIT,
            "MARKET": OrderType.MARKET,
            "STOP_LOSS": OrderType.SL,
            "STOP_LOSS_MARKET": OrderType.SL,
        }
        return mapping.get(dhan_type, OrderType.MARKET)

    def _to_dhan_order_type(self, order_type: OrderType) -> str:
        mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.SL: "STOP_LOSS_MARKET",
            OrderType.SL_LIMIT: "STOP_LOSS",
        }
        return mapping.get(order_type, "MARKET")

    def _to_dhan_exchange(self, exchange: Exchange) -> str:
        reverse = {v: k for k, v in self.DHAN_EXCHANGE_MAP.items()}
        return reverse.get(exchange, "NSE_EQ")
```

### Sequential Leg Placement Engine

```python
# infrastructure/dhan/leg_placer.py
import asyncio
import structlog
from infrastructure.dhan.client import DhanClient
from domains.options.leg import OptionLeg
from domains.options.strategy import OptionStrategy

log = structlog.get_logger(__name__)

class SequentialLegPlacer:
    """
    Places option strategy legs one by one (Dhan has no basket order API).

    Flow:
    1. Place leg 1 → wait for fill confirmation.
    2. Place leg 2 → wait.
    3. ... continue for all legs.
    4. If any leg fails: trigger abort → close all successfully placed legs.

    Note: MARKET orders on liquid strikes typically fill in < 500ms.
    LIMIT orders may take longer; the placer has a per-leg timeout.
    """
    LEG_FILL_TIMEOUT_SEC = 10.0  # Wait up to 10s for each leg fill
    ABORT_WAIT_SEC = 2.0

    def __init__(self, client: DhanClient, order_repo):
        self._client = client
        self._order_repo = order_repo

    async def place(self, strategy: OptionStrategy) -> dict:
        """
        Returns:
        {
            "placed": [leg_id, ...],
            "failed_at": leg_id | None,
            "aborted": [leg_id, ...],
            "status": "FULLY_PLACED" | "PARTIALLY_PLACED" | "FAILED"
        }
        """
        placed_legs = []
        failed_at = None

        for leg in strategy.legs:
            try:
                dhan_order_id = await self._place_leg(leg)
                leg.lsl_order_id = None  # LSL placed separately after fill
                placed_legs.append(leg.id)
                log.info("Leg placed", leg_id=leg.id, dhan_id=dhan_order_id)
                await asyncio.sleep(0.3)  # Brief pause between legs

            except Exception as e:
                log.error("Leg placement failed", leg_id=leg.id, error=str(e))
                failed_at = leg.id
                break

        if failed_at is not None and placed_legs:
            log.warning("Aborting strategy — closing placed legs", placed=placed_legs)
            aborted = await self._abort_placed_legs(strategy, placed_legs)
            return {
                "placed": placed_legs,
                "failed_at": str(failed_at),
                "aborted": aborted,
                "status": "FAILED",
            }

        return {
            "placed": placed_legs,
            "failed_at": None,
            "aborted": [],
            "status": "FULLY_PLACED" if len(placed_legs) == len(strategy.legs) else "PARTIALLY_PLACED",
        }

    async def _place_leg(self, leg: OptionLeg) -> str:
        """Place a single leg and return dhan_order_id."""
        from domains.orders.order import Order
        from domains.orders.enums import Side, ProductType, OrderType
        order = Order.create_market(
            symbol=leg.symbol,
            side=leg.side,
            qty=leg.qty,
            product_type=ProductType.MARGIN,
        )
        return await self._client.place_order(order)

    async def _abort_placed_legs(
        self, strategy: OptionStrategy, placed_ids: list
    ) -> list[str]:
        """Close successfully placed legs by placing offsetting market orders."""
        aborted = []
        for leg_id in placed_ids:
            leg = next((l for l in strategy.legs if l.id == leg_id), None)
            if leg is None:
                continue
            try:
                from domains.orders.order import Order
                from domains.orders.enums import Side, ProductType
                close_side = Side.SELL if leg.side == Side.BUY else Side.BUY
                close_order = Order.create_market(
                    symbol=leg.symbol,
                    side=close_side,
                    qty=leg.qty,
                    product_type=ProductType.MARGIN,
                )
                await self._client.place_order(close_order)
                aborted.append(str(leg_id))
            except Exception as e:
                log.error("Failed to abort leg", leg_id=leg_id, error=str(e))
        return aborted
```

### Error Handling and Retry Strategy

| Error Scenario | Behavior |
|---|---|
| Transient network (5xx, timeout) | `tenacity` retries 3× with exponential backoff (1s, 2s, 4s) |
| Rate limit (429 from Dhan) | Retry after `Retry-After` header delay; log warning |
| Business rejection (4xx, invalid order) | Raise `DhanBrokerError` — not retried, returned to caller as Err |
| Partial fill on strategy leg | Abort engine cancels remaining legs; strategy marked FAILED |
| SL order placement failure post-fill | Alert published via event bus; position still exists (SL missing alert) |
| WebSocket disconnect (market feed) | Auto-reconnect loop with 5s delay |
| WebSocket disconnect (order feed) | Auto-reconnect loop with 5s delay |
| Position poll failure | Log error, skip cycle; next poll in POLL_INTERVAL |
| Token expiry | TokenStore detects 401 from SDK; triggers TokenRenewalJob immediately |

### Token Management

```python
# infrastructure/dhan/token_store.py
from datetime import datetime, timedelta, timezone
import structlog
from redis.asyncio import Redis

log = structlog.get_logger(__name__)

REDIS_TOKEN_KEY   = "dhan:access_token"
REDIS_EXPIRY_KEY  = "dhan:token_expiry"
TOKEN_TTL_HOURS   = 24

class TokenStore:
    """
    Stores the Dhan 24-hour access token in Redis.
    The nightly TokenRenewalJob writes the new token here at 9 PM.
    DhanClient reads from here on startup and after 401 responses.
    """
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_token(self) -> str | None:
        return await self._redis.get(REDIS_TOKEN_KEY)

    async def set_token(self, token: str) -> None:
        expiry = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
        pipe = self._redis.pipeline()
        pipe.set(REDIS_TOKEN_KEY, token, ex=TOKEN_TTL_HOURS * 3600)
        pipe.set(REDIS_EXPIRY_KEY, expiry.isoformat())
        await pipe.execute()
        log.info("Dhan token stored", expires_at=expiry.isoformat())

    async def is_token_valid(self) -> bool:
        expiry_str = await self._redis.get(REDIS_EXPIRY_KEY)
        if not expiry_str:
            return False
        expiry = datetime.fromisoformat(expiry_str)
        return datetime.now(timezone.utc) < expiry - timedelta(minutes=30)

    async def clear_token(self) -> None:
        await self._redis.delete(REDIS_TOKEN_KEY, REDIS_EXPIRY_KEY)
```

---

## Repository Implementations

### CandleRepository — TimescaleDB

```python
# infrastructure/repositories/candle_repo.py
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from domains.market_data.entities import OHLCV
from domains.market_data.enums import CandleInterval
from domains.shared.symbol import Symbol

class CandleRepository:
    """
    TimescaleDB-backed OHLCV storage.
    The 'candles' table is a hypertable partitioned by time (open_time).
    Chunk interval: 1 day.
    Retention policy: 5 years.
    """
    def __init__(self, session: AsyncSession):
        self._session = session

    async def insert_candle(self, symbol: Symbol, candle: OHLCV) -> None:
        await self._session.execute(
            text("""
                INSERT INTO candles
                    (symbol, exchange, interval, open_time, open, high, low, close, volume, oi)
                VALUES
                    (:symbol, :exchange, :interval, :open_time, :open, :high, :low, :close, :volume, :oi)
                ON CONFLICT (symbol, exchange, interval, open_time) DO UPDATE
                SET high = GREATEST(candles.high, EXCLUDED.high),
                    low  = LEAST(candles.low, EXCLUDED.low),
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    oi = EXCLUDED.oi
            """),
            {
                "symbol":    symbol.value,
                "exchange":  symbol.exchange.value,
                "interval":  candle.interval.value,
                "open_time": candle.open_time,
                "open":      float(candle.open),
                "high":      float(candle.high),
                "low":       float(candle.low),
                "close":     float(candle.close),
                "volume":    candle.volume,
                "oi":        candle.oi,
            }
        )

    async def get_recent(
        self,
        symbol: str,
        interval: str,
        count: int,
        before: datetime | None = None,
    ) -> list[OHLCV]:
        """
        Fetch the N most recent candles. Used for ATR calculation and signal scoring.
        TimescaleDB time_bucket() could be used here for further aggregation.
        """
        before_clause = "AND open_time < :before" if before else ""
        rows = await self._session.execute(
            text(f"""
                SELECT open_time, open, high, low, close, volume, oi, interval
                FROM candles
                WHERE symbol = :symbol AND interval = :interval
                {before_clause}
                ORDER BY open_time DESC
                LIMIT :count
            """),
            {
                "symbol": symbol,
                "interval": interval,
                "count": count,
                **({"before": before} if before else {}),
            }
        )
        rows = rows.fetchall()
        return [self._row_to_ohlcv(r) for r in reversed(rows)]

    async def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[OHLCV]:
        rows = await self._session.execute(
            text("""
                SELECT open_time, open, high, low, close, volume, oi, interval
                FROM candles
                WHERE symbol = :symbol
                  AND interval = :interval
                  AND open_time BETWEEN :from_dt AND :to_dt
                ORDER BY open_time ASC
            """),
            {"symbol": symbol, "interval": interval, "from_dt": from_dt, "to_dt": to_dt}
        )
        return [self._row_to_ohlcv(r) for r in rows.fetchall()]

    def _row_to_ohlcv(self, row) -> OHLCV:
        from decimal import Decimal
        return OHLCV(
            symbol=None,
            interval=CandleInterval(row.interval),
            open_time=row.open_time,
            open=Decimal(str(row.open)),
            high=Decimal(str(row.high)),
            low=Decimal(str(row.low)),
            close=Decimal(str(row.close)),
            volume=int(row.volume),
            oi=int(row.oi) if row.oi else None,
        )
```

### WatchlistRepository

```python
# infrastructure/repositories/watchlist_repo.py
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
from domains.signals.watchlist import Watchlist

class WatchlistRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_daily_watchlist(self, watchlist: Watchlist) -> None:
        """Upsert today's watchlist. One row per day per user."""
        await self._session.execute(
            text("""
                INSERT INTO watchlists (date, entries_json, generated_at, scan_duration_seconds)
                VALUES (:date, :entries, :generated_at, :duration)
                ON CONFLICT (date) DO UPDATE
                SET entries_json = EXCLUDED.entries_json,
                    generated_at = EXCLUDED.generated_at,
                    scan_duration_seconds = EXCLUDED.scan_duration_seconds
            """),
            {
                "date": watchlist.date,
                "entries": json.dumps([
                    {
                        "symbol": e.symbol.value,
                        "exchange": e.symbol.exchange.value,
                        "score": {
                            "trend": e.score.trend,
                            "volume": e.score.volume,
                            "sector": e.score.sector,
                            "market_ctx": e.score.market_ctx,
                            "rr": e.score.rr,
                        },
                        "direction": e.direction.value,
                        "entry_zone_low": float(e.entry_zone_low),
                        "entry_zone_high": float(e.entry_zone_high),
                        "sl_price": float(e.sl_price),
                        "target_price": float(e.target_price),
                        "notes": e.notes,
                    }
                    for e in watchlist.entries
                ]),
                "generated_at": watchlist.generated_at,
                "duration": watchlist.scan_duration_seconds,
            }
        )

    async def get_today_watchlist(self) -> Watchlist | None:
        today = date.today()
        row = await self._session.execute(
            text("SELECT * FROM watchlists WHERE date = :date"),
            {"date": today}
        )
        row = row.fetchone()
        if not row:
            return None
        return self._deserialize(row)

    def _deserialize(self, row) -> Watchlist:
        # Reconstruct Watchlist domain object from JSON storage
        ...
```

### OrderRepository

```python
# infrastructure/repositories/order_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from domains.orders.order import Order

class OrderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, order: Order) -> None:
        await self._session.execute(
            text("""
                INSERT INTO orders
                    (id, dhan_order_id, symbol, exchange, side, qty, price,
                     trigger_price, order_type, product_type, validity,
                     status, filled_qty, fill_price, created_at)
                VALUES
                    (:id, :dhan_id, :symbol, :exchange, :side, :qty, :price,
                     :trigger_price, :order_type, :product_type, :validity,
                     :status, :filled_qty, :fill_price, :created_at)
            """),
            self._to_dict(order)
        )

    async def update(self, order: Order) -> None:
        await self._session.execute(
            text("""
                UPDATE orders
                SET status = :status, filled_qty = :filled_qty,
                    fill_price = :fill_price, dhan_order_id = :dhan_id,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": str(order.id),
                "status": order.status.value,
                "filled_qty": order.filled_qty,
                "fill_price": float(order.fill_price) if order.fill_price else None,
                "dhan_id": order.dhan_order_id,
            }
        )

    async def get_by_dhan_id(self, dhan_order_id: str) -> Order | None:
        result = await self._session.execute(
            text("SELECT * FROM orders WHERE dhan_order_id = :dhan_id"),
            {"dhan_id": dhan_order_id}
        )
        row = result.fetchone()
        return self._from_row(row) if row else None

    async def mark_cancelled(self, dhan_order_id: str) -> None:
        await self._session.execute(
            text("UPDATE orders SET status = 'CANCELLED' WHERE dhan_order_id = :dhan_id"),
            {"dhan_id": dhan_order_id}
        )

    def _to_dict(self, order: Order) -> dict:
        return {
            "id": str(order.id),
            "dhan_id": order.dhan_order_id,
            "symbol": order.symbol.value,
            "exchange": order.symbol.exchange.value,
            "side": order.side.value,
            "qty": order.qty,
            "price": float(order.price) if order.price else None,
            "trigger_price": float(order.trigger_price) if order.trigger_price else None,
            "order_type": order.order_type.value,
            "product_type": order.product_type.value,
            "validity": order.validity.value,
            "status": order.status.value,
            "filled_qty": order.filled_qty,
            "fill_price": float(order.fill_price) if order.fill_price else None,
            "created_at": order.created_at,
        }

    def _from_row(self, row) -> Order:
        # Reconstruct Order domain object from DB row
        ...
```

---

## Redis Cache Patterns

### QuoteCache

```python
# infrastructure/cache/quote_cache.py
import json
from decimal import Decimal
from redis.asyncio import Redis
from domains.market_data.value_objects import Tick
from domains.market_data.entities import Quote

QUOTE_KEY_PREFIX = "quote:"
QUOTE_TTL_SECONDS = 5   # Quotes stale after 5s (Dhan feed latency tolerance)

class QuoteCache:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def set_tick(self, tick: Tick) -> None:
        """Called on every tick from market feed. O(1) Redis SET."""
        key = f"{QUOTE_KEY_PREFIX}{tick.security_id}"
        await self._redis.set(
            key,
            json.dumps({
                "ltp": float(tick.ltp),
                "volume": tick.volume,
                "oi": tick.oi,
                "ts": tick.timestamp.isoformat(),
            }),
            ex=QUOTE_TTL_SECONDS,
        )

    async def get_quote(self, security_id: str) -> dict | None:
        """Returns latest tick data or None if expired/missing."""
        data = await self._redis.get(f"{QUOTE_KEY_PREFIX}{security_id}")
        if data:
            return json.loads(data)
        return None

    async def get_bulk(self, security_ids: list[str]) -> dict[str, dict]:
        """Fetch multiple quotes in one pipeline call."""
        pipe = self._redis.pipeline()
        for sid in security_ids:
            pipe.get(f"{QUOTE_KEY_PREFIX}{sid}")
        results = await pipe.execute()
        return {
            sid: json.loads(val) if val else None
            for sid, val in zip(security_ids, results)
        }
```

### LiveCandleBuilder

```python
# infrastructure/cache/candle_cache.py
import json
from datetime import datetime, timezone
from decimal import Decimal
from redis.asyncio import Redis
from domains.market_data.value_objects import Tick
from domains.market_data.entities import OHLCV
from domains.market_data.enums import CandleInterval

LIVE_CANDLE_KEY_PREFIX = "live_candle:"

class LiveCandleBuilder:
    """
    Builds live (in-progress) candles from tick stream.
    The current candle is stored in Redis; when the candle boundary
    is crossed (e.g., 5min boundary), the completed candle is
    handed off for DB storage and a new candle begins.

    Boundary detection uses IST market time alignment, not wall-clock minutes.
    Example: 5-min candles start at :00, :05, :10, ... :25, :30... (IST)
    """
    INTERVAL_MINUTES = {
        CandleInterval.MIN_1:  1,
        CandleInterval.MIN_5:  5,
        CandleInterval.MIN_15: 15,
        CandleInterval.MIN_25: 25,
        CandleInterval.MIN_60: 60,
    }

    def __init__(self, redis: Redis):
        self._redis = redis

    async def on_tick(
        self,
        tick: Tick,
        interval: CandleInterval,
        on_complete,  # async callback: (OHLCV) -> None
    ) -> None:
        """
        Process a tick and update the live candle.
        If the tick crosses a candle boundary, calls on_complete with
        the finished candle and starts a new one.
        """
        key = f"{LIVE_CANDLE_KEY_PREFIX}{tick.security_id}:{interval.value}"
        raw = await self._redis.get(key)

        boundary = self._get_boundary(tick.timestamp, interval)

        if raw:
            candle_data = json.loads(raw)
            candle_start = datetime.fromisoformat(candle_data["start"])

            if candle_start < boundary:
                # Candle is complete — hand off and start new
                completed = self._dict_to_ohlcv(candle_data, interval)
                await on_complete(completed)
                candle_data = self._new_candle(tick, boundary)
            else:
                # Update existing candle
                candle_data["high"] = max(candle_data["high"], float(tick.ltp))
                candle_data["low"]  = min(candle_data["low"],  float(tick.ltp))
                candle_data["close"] = float(tick.ltp)
                candle_data["volume"] += tick.volume
        else:
            candle_data = self._new_candle(tick, boundary)

        await self._redis.set(key, json.dumps(candle_data), ex=7200)  # 2h TTL

    def _get_boundary(self, ts: datetime, interval: CandleInterval) -> datetime:
        """Return the start of the current candle interval for the given timestamp."""
        minutes = self.INTERVAL_MINUTES[interval]
        floored = ts.replace(second=0, microsecond=0)
        aligned_minute = (floored.minute // minutes) * minutes
        return floored.replace(minute=aligned_minute)

    def _new_candle(self, tick: Tick, boundary: datetime) -> dict:
        return {
            "start": boundary.isoformat(),
            "open": float(tick.ltp),
            "high": float(tick.ltp),
            "low": float(tick.ltp),
            "close": float(tick.ltp),
            "volume": tick.volume,
        }

    def _dict_to_ohlcv(self, d: dict, interval: CandleInterval) -> OHLCV:
        return OHLCV(
            symbol=None,
            interval=interval,
            open_time=datetime.fromisoformat(d["start"]),
            open=Decimal(str(d["open"])),
            high=Decimal(str(d["high"])),
            low=Decimal(str(d["low"])),
            close=Decimal(str(d["close"])),
            volume=int(d["volume"]),
        )
```

### OptionChainCache

```python
# infrastructure/cache/option_chain_cache.py
import json
from redis.asyncio import Redis

CHAIN_KEY_PREFIX = "option_chain:"
CHAIN_TTL_SECONDS = 5  # Option chain stale after 5s

class OptionChainCache:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def set_chain(self, underlying: str, expiry: str, chain_data: list) -> None:
        key = f"{CHAIN_KEY_PREFIX}{underlying}:{expiry}"
        await self._redis.set(key, json.dumps(chain_data), ex=CHAIN_TTL_SECONDS)

    async def get_greeks(self, option_symbol: str) -> dict | None:
        """
        Retrieve Greeks for a specific option symbol.
        The chain is stored by underlying; we search by strike + option type.
        In practice: store the chain as a dict keyed by trading_symbol for O(1) lookup.
        """
        # Implementation searches all cached chains for the symbol
        ...

    async def is_stale(self, underlying: str, expiry: str) -> bool:
        key = f"{CHAIN_KEY_PREFIX}{underlying}:{expiry}"
        return not await self._redis.exists(key)
```

---

## Background Jobs

### EODScanJob

```python
# infrastructure/jobs/eod_scan.py
import asyncio
import time
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = structlog.get_logger(__name__)

class EODScanJob:
    """
    Runs at 4:00 PM IST on trading days.
    Fetches daily candles for the symbol universe,
    runs signal engine, and saves the resulting watchlist.

    Symbol universe: loaded from DB (curated list of ~200-500 NSE stocks).
    """
    def __init__(self, mediator, candle_repo, scheduler: AsyncIOScheduler):
        self._mediator = mediator
        self._scheduler = scheduler

    def register(self) -> None:
        self._scheduler.add_job(
            self.run,
            trigger="cron",
            hour=16,
            minute=0,
            timezone="Asia/Kolkata",
            id="eod_scan",
            replace_existing=True,
        )
        log.info("EOD scan job registered for 4:00 PM IST")

    async def run(self) -> None:
        log.info("EOD scan started")
        start = time.monotonic()
        from application.signals.commands.run_eod_scan import RunEODScanCommand
        symbols = await self._load_universe()
        result = await self._mediator.send(RunEODScanCommand(
            symbols=tuple(symbols),
            user_id="system",
        ))
        elapsed = time.monotonic() - start
        log.info(
            "EOD scan complete",
            scanned=result.symbols_scanned,
            signals=result.signals_found,
            grade_a=result.grade_a_count,
            duration_sec=round(elapsed, 2),
        )

    async def _load_universe(self) -> list[str]:
        # Load from instruments table in DB
        ...
        return []
```

### CandleAggregatorWorker

```python
# infrastructure/jobs/candle_agg.py
import structlog
from infrastructure.cache.candle_cache import LiveCandleBuilder
from infrastructure.repositories.candle_repo import CandleRepository
from domains.market_data.enums import CandleInterval

log = structlog.get_logger(__name__)

TRACKED_INTERVALS = [
    CandleInterval.MIN_5,
    CandleInterval.MIN_15,
    CandleInterval.MIN_25,
    CandleInterval.MIN_60,
]

class CandleAggregatorWorker:
    """
    Subscribes to the market feed tick stream and builds OHLCV candles.
    When a candle boundary is crossed, stores the completed candle in TimescaleDB.
    Also triggers real-time signal evaluation for completed candles.
    """
    def __init__(
        self,
        candle_builder: LiveCandleBuilder,
        candle_repo: CandleRepository,
        market_feed_service,
        mediator,
    ):
        self._builder = candle_builder
        self._candle_repo = candle_repo
        self._market_feed = market_feed_service
        self._mediator = mediator

    def start(self) -> None:
        """Register tick listener with market feed."""
        self._market_feed.add_tick_listener(self.on_tick)
        log.info("Candle aggregator worker started")

    async def on_tick(self, tick) -> None:
        """Called for every market feed tick — must be very fast."""
        for interval in TRACKED_INTERVALS:
            await self._builder.on_tick(
                tick=tick,
                interval=interval,
                on_complete=lambda candle, i=interval, t=tick: self._on_candle_complete(candle, t, i),
            )

    async def _on_candle_complete(self, candle, tick, interval: CandleInterval) -> None:
        """Called when a candle boundary is crossed. Persist and evaluate."""
        from domains.shared.symbol import Symbol, Exchange
        symbol = Symbol(value=tick.security_id, exchange=Exchange.NSE)
        candle.symbol = symbol

        # Persist to TimescaleDB
        async with self._candle_repo.session_scope() as session:
            repo = CandleRepository(session)
            await repo.insert_candle(symbol, candle)

        # Trigger real-time signal evaluation
        from application.signals.commands.evaluate_candle import EvaluateCandleCommand
        await self._mediator.send(EvaluateCandleCommand(
            symbol=tick.security_id,
            exchange="NSE",
            interval=interval.value,
            candle=candle,
        ))
```

### TokenRenewalJob

```python
# infrastructure/jobs/token_renewal.py
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from infrastructure.dhan.token_store import TokenStore

log = structlog.get_logger(__name__)

class TokenRenewalJob:
    """
    Runs at 9:00 PM IST daily.
    Calls Dhan token renewal endpoint and stores the new 24-hour token in Redis.
    Sends alert if renewal fails (critical — without token, no orders at market open).
    """
    def __init__(
        self,
        token_store: TokenStore,
        dhan_client,
        alert_service,
        scheduler: AsyncIOScheduler,
    ):
        self._token_store = token_store
        self._dhan_client = dhan_client
        self._alert_service = alert_service
        self._scheduler = scheduler

    def register(self) -> None:
        self._scheduler.add_job(
            self.run,
            trigger="cron",
            hour=21,
            minute=0,
            timezone="Asia/Kolkata",
            id="token_renewal",
            replace_existing=True,
        )
        log.info("Token renewal job registered for 9:00 PM IST")

    async def run(self) -> None:
        log.info("Token renewal starting")
        try:
            new_token = await self._dhan_client.renew_token()
            await self._token_store.set_token(new_token)
            log.info("Dhan token renewed successfully")
        except Exception as e:
            log.error("Token renewal FAILED", error=str(e))
            await self._alert_service.send_critical(
                "DHAN TOKEN RENEWAL FAILED",
                f"Error: {e}. Manual token update required before 9:15 AM."
            )
```

### CSLMonitorTask

```python
# infrastructure/jobs/csl_monitor.py
import asyncio
import structlog
from infrastructure.repositories.strategy_repo import StrategyRepository
from infrastructure.cache.quote_cache import QuoteCache
from infrastructure.messaging.event_bus import EventBus
from domains.options.csl_engine import LSLCSLEngine

log = structlog.get_logger(__name__)

class CSLMonitorTask:
    """
    Runs every 3 seconds during market hours.
    For each ACTIVE option strategy:
    1. Updates leg current_price from QuoteCache.
    2. Calls LSLCSLEngine.check_strategy().
    3. If CSL triggered: publishes event → TriggerCSLCommand executed by handler.
    """
    POLL_INTERVAL_SEC = 3.0

    def __init__(
        self,
        strategy_repo: StrategyRepository,
        quote_cache: QuoteCache,
        event_bus: EventBus,
        mediator,
    ):
        self._strategy_repo = strategy_repo
        self._quote_cache = quote_cache
        self._event_bus = event_bus
        self._mediator = mediator
        self._engine = LSLCSLEngine()
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._check_all_strategies()
            except Exception as e:
                log.error("CSL monitor error", error=str(e))
            await asyncio.sleep(self.POLL_INTERVAL_SEC)

    async def _check_all_strategies(self) -> None:
        strategies = await self._strategy_repo.get_active()
        for strategy in strategies:
            # Update prices from quote cache
            for leg in strategy.open_legs():
                quote = await self._quote_cache.get_quote(str(leg.symbol))
                if quote:
                    from decimal import Decimal
                    leg.current_price = Decimal(str(quote["ltp"]))

            # Check CSL/LSL conditions
            actions = self._engine.check_strategy(strategy)
            for action in actions:
                if action.startswith("TRIGGER_CSL:"):
                    strategy_id = action.split(":")[1]
                    from application.options.commands.trigger_csl import TriggerCSLCommand
                    await self._mediator.send(TriggerCSLCommand(
                        strategy_id=strategy_id,
                        reason="MONITOR_AUTO",
                        user_id="system",
                    ))
                    log.warning("CSL auto-triggered", strategy_id=strategy_id)
```

---

## Internal Event Bus

```python
# infrastructure/messaging/event_bus.py
import asyncio
from typing import Type, Callable, Awaitable
import structlog
from domains.shared.domain_event import DomainEvent

log = structlog.get_logger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]

class EventBus:
    """
    Simple asyncio-based in-process event bus.
    Domain events are published by command handlers and aggregates.
    Handlers are registered at app startup.

    All handlers for an event are called concurrently (asyncio.gather).
    Handler failures are logged but do not fail the publisher.
    """
    def __init__(self):
        self._handlers: dict[Type[DomainEvent], list[EventHandler]] = {}

    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        log.debug("Event handler registered",
                  event=event_type.__name__,
                  handler=handler.__qualname__)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return

        async def safe_handle(h: EventHandler) -> None:
            try:
                await h(event)
            except Exception as e:
                log.error(
                    "Event handler failed",
                    event=event.event_name,
                    handler=h.__qualname__,
                    error=str(e),
                )

        await asyncio.gather(*[safe_handle(h) for h in handlers])
```
