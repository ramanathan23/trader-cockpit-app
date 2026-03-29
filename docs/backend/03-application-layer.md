# Application Layer — CQRS Design

**Project:** Trader Cockpit App
**Pattern:** CQRS (Command Query Responsibility Segregation)
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [CQRS Foundation](#cqrs-foundation)
2. [Command Pattern](#command-pattern)
3. [Query Pattern](#query-pattern)
4. [Mediator](#mediator)
5. [Key Commands](#key-commands)
6. [Key Queries](#key-queries)
7. [Full Use Case Example — ConvertToDelivery](#full-use-case-example--converttodelivery)
8. [Event Handling — Side Effects from Domain Events](#event-handling--side-effects-from-domain-events)
9. [Error Strategy](#error-strategy)
10. [Testing Application Handlers](#testing-application-handlers)

---

## CQRS Foundation

The application layer enforces a strict split:

| Side | Name | Role | Returns | Mutates State? |
|---|---|---|---|---|
| Write | Command | Expresses user intent to change state | Success/failure result | Yes |
| Read | Query | Requests a projection of current state | Typed result (no side effects) | No |

This separation allows:
- **Commands** to use write-optimized DB connections (with transactions).
- **Queries** to use read replicas, Redis cache, or denormalized projections.
- Independent optimization of read and write paths.

---

## Command Pattern

```python
# application/shared/command.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic

C = TypeVar("C")
R = TypeVar("R")

@dataclass(frozen=True)
class BaseCommand:
    """
    All commands are immutable value objects.
    frozen=True ensures commands cannot be modified after creation.
    """
    pass

class CommandHandler(ABC, Generic[C, R]):
    """
    Abstract base for all command handlers.
    Each command has exactly one handler.
    """
    @abstractmethod
    async def handle(self, command: C) -> R:
        ...
```

### Command Result Types

Command handlers return explicit result types — never raw dicts or untyped values. This makes handler contracts clear and testable.

```python
# Conventions for command results:
#
# 1. Simple commands — return a typed dataclass
@dataclass
class PlaceOrderResult:
    order_id: str
    dhan_order_id: str
    status: str

# 2. Commands that may fail for business reasons — return Result[T]
#    (not exceptions — business failures are expected)
from domains.shared.result import Result, Ok, Err

async def handle(self, cmd: PlaceIntradayTradeCommand) -> Result[PlaceOrderResult]:
    if not can_trade:
        return Err("Daily loss limit reached")
    ...
    return Ok(PlaceOrderResult(...))

# 3. Exception vs Result usage:
# - Use Result[T] for expected business failures (limit breach, ineligible conversion)
# - Raise exceptions for programming errors and infrastructure failures
```

---

## Query Pattern

```python
# application/shared/query.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic

Q = TypeVar("Q")
R = TypeVar("R")

@dataclass(frozen=True)
class BaseQuery:
    """
    Queries are also immutable value objects (parameters to the read model).
    Queries never modify state.
    """
    pass

class QueryHandler(ABC, Generic[Q, R]):
    """
    Abstract base for all query handlers.
    Queries may read from DB, Redis, or any combination.
    They must never write.
    """
    @abstractmethod
    async def handle(self, query: Q) -> R:
        ...
```

---

## Mediator

The Mediator dispatches commands and queries to their handlers. FastAPI routers use it as an alternative to importing specific handler types directly.

```python
# application/shared/mediator.py
from typing import Type

class Mediator:
    """
    Simple command/query mediator.
    Handlers are registered at application startup via the lifespan.
    """
    def __init__(self):
        self._command_handlers: dict = {}
        self._query_handlers: dict = {}

    def register_command(self, command_type: Type, handler) -> None:
        self._command_handlers[command_type] = handler

    def register_query(self, query_type: Type, handler) -> None:
        self._query_handlers[query_type] = handler

    async def send(self, command_or_query):
        """Dispatch a command or query to its registered handler."""
        handler = (
            self._command_handlers.get(type(command_or_query)) or
            self._query_handlers.get(type(command_or_query))
        )
        if handler is None:
            raise ValueError(f"No handler registered for {type(command_or_query).__name__}")
        return await handler.handle(command_or_query)
```

---

## Key Commands

### PlaceIntradayTradeCommand

```python
# application/equity/commands/place_intra_trade.py
from dataclasses import dataclass
from decimal import Decimal
from application.shared.command import BaseCommand, CommandHandler
from domains.shared.result import Result, Ok, Err
from domains.equity.enums import PositionMode
from domains.orders.enums import Side, ProductType, OrderType
from domains.orders.order import Order
from domains.equity.positions import IntradayPosition
from domains.equity.events import PositionOpened
from domains.risk.profile import RiskProfile
from domains.risk.sizer import PositionSizer
from domains.risk.atr_validator import ATRValidator

@dataclass(frozen=True)
class PlaceIntradayTradeCommand(BaseCommand):
    symbol: str
    exchange: str
    direction: str          # "BUY" or "SELL"
    entry_price: float
    sl_price: float
    qty: int                # Override qty (if 0, use PositionSizer)
    user_id: str

@dataclass
class PlaceIntradayTradeResult:
    position_id: str
    order_id: str
    dhan_order_id: str
    sl_order_id: str
    qty: int
    capital_at_risk: float

class PlaceIntradayTradeHandler(
    CommandHandler[PlaceIntradayTradeCommand, Result["PlaceIntradayTradeResult"]]
):
    def __init__(
        self,
        risk_repo,          # IRiskRepository
        position_repo,      # IPositionRepository
        order_repo,         # IOrderRepository
        broker,             # IBrokerOrderPort
        candle_repo,        # ICandleRepository (for ATR)
        event_bus,          # IEventBus
    ):
        self._risk_repo = risk_repo
        self._position_repo = position_repo
        self._order_repo = order_repo
        self._broker = broker
        self._candle_repo = candle_repo
        self._event_bus = event_bus

    async def handle(
        self, cmd: PlaceIntradayTradeCommand
    ) -> Result[PlaceIntradayTradeResult]:
        # 1. Load risk profile and daily state
        profile = await self._risk_repo.get_profile(cmd.user_id)
        daily_state = await self._risk_repo.get_daily_state(cmd.user_id)

        can_trade, reason = daily_state.can_trade(profile)
        if not can_trade:
            return Err(reason)

        # 2. Check position count limit
        open_count = await self._position_repo.count_open_intraday()
        if open_count >= profile.max_intra_positions:
            return Err(f"Max intraday positions ({profile.max_intra_positions}) reached")

        # 3. Validate SL against ATR
        candles = await self._candle_repo.get_recent(
            cmd.symbol, interval="15", count=14
        )
        atr = self._calculate_atr(candles, period=14)
        validator = ATRValidator()
        valid, msg = validator.validate(
            entry_price=Decimal(str(cmd.entry_price)),
            sl_price=Decimal(str(cmd.sl_price)),
            atr=atr,
            mode=PositionMode.INTRADAY,
        )
        if not valid:
            return Err(f"ATR validation failed: {msg}")

        # 4. Calculate qty if not provided
        qty = cmd.qty
        if qty == 0:
            sizer = PositionSizer()
            size_result = sizer.calculate(
                entry_price=Decimal(str(cmd.entry_price)),
                sl_price=Decimal(str(cmd.sl_price)),
                mode=PositionMode.INTRADAY,
                profile=profile,
            )
            qty = size_result.qty

        # 5. Place entry order on Dhan
        entry_order = Order.create_market(
            symbol=self._to_symbol(cmd.symbol, cmd.exchange),
            side=Side[cmd.direction],
            qty=qty,
            product_type=ProductType.INTRADAY,
        )
        dhan_entry_id = await self._broker.place_order(entry_order)
        entry_order.assign_dhan_id(dhan_entry_id)
        await self._order_repo.save(entry_order)

        # 6. Place SL order on Dhan
        sl_order = Order.create_sl(
            symbol=self._to_symbol(cmd.symbol, cmd.exchange),
            side=Side.SELL if cmd.direction == "BUY" else Side.BUY,
            qty=qty,
            trigger_price=Decimal(str(cmd.sl_price)),
            product_type=ProductType.INTRADAY,
        )
        dhan_sl_id = await self._broker.place_order(sl_order)
        sl_order.assign_dhan_id(dhan_sl_id)
        await self._order_repo.save(sl_order)

        # 7. Create position record
        position = IntradayPosition(
            id=entry_order.id,
            symbol=self._to_symbol(cmd.symbol, cmd.exchange),
            qty=qty,
            entry_price=Decimal(str(cmd.entry_price)),
            sl_price=Decimal(str(cmd.sl_price)),
            sl_order_id=dhan_sl_id,
            target_price=None,
        )
        await self._position_repo.save(position)

        # 8. Publish domain event
        await self._event_bus.publish(PositionOpened(
            position_id=position.id,
            symbol=cmd.symbol,
            mode="INTRADAY",
            qty=qty,
            entry_price=cmd.entry_price,
        ))

        return Ok(PlaceIntradayTradeResult(
            position_id=str(position.id),
            order_id=str(entry_order.id),
            dhan_order_id=dhan_entry_id,
            sl_order_id=dhan_sl_id,
            qty=qty,
            capital_at_risk=float(
                abs(Decimal(str(cmd.entry_price)) - Decimal(str(cmd.sl_price))) * qty
            ),
        ))

    def _to_symbol(self, symbol: str, exchange: str):
        from domains.shared.symbol import Symbol, Exchange
        return Symbol(value=symbol, exchange=Exchange[exchange])

    def _calculate_atr(self, candles, period: int) -> Decimal:
        # Delegates to numpy via run_in_executor in actual implementation
        # Shown as simple placeholder here
        import numpy as np
        highs = [float(c.high) for c in candles]
        lows  = [float(c.low)  for c in candles]
        closes = [float(c.close) for c in candles]
        trs = [
            max(h - l, abs(h - pc), abs(l - pc))
            for h, l, pc in zip(highs[1:], lows[1:], closes[:-1])
        ]
        atr = sum(trs[-period:]) / period
        return Decimal(str(round(atr, 2)))
```

### ConvertToDeliveryCommand

```python
# application/equity/commands/convert_to_delivery.py
from dataclasses import dataclass
from decimal import Decimal
from application.shared.command import BaseCommand, CommandHandler
from domains.shared.result import Result, Ok, Err

@dataclass(frozen=True)
class ConvertToDeliveryCommand(BaseCommand):
    """
    Convert an open INTRADAY position (or part of it) to CNC delivery.

    cnc_qty:    Number of shares to carry as CNC (swing_qty).
    swing_sl:   Absolute price for the CNC stop loss (wide SL).
    user_id:    Authenticated user making the request.

    The remaining shares (intraday_pos.qty - cnc_qty) will be closed
    as INTRADAY (sold before market close).

    Note: CNC qty is always < intraday qty because:
      - Intraday uses leverage (many shares, tight SL)
      - CNC uses full capital (few shares, wide SL)
    """
    position_id: str
    cnc_qty: int
    swing_sl: float
    swing_target: float | None
    user_id: str

@dataclass
class ConvertToDeliveryResult:
    success: bool
    cnc_position_id: str | None
    closed_intra_qty: int
    cnc_qty: int
    message: str
```

### PlaceOptionStrategyCommand

```python
# application/options/commands/place_strategy.py
from dataclasses import dataclass
from application.shared.command import BaseCommand, CommandHandler
from domains.shared.result import Result

@dataclass(frozen=True)
class LegConfig:
    """Configuration for a single option leg."""
    symbol: str         # Full option symbol
    exchange: str       # "NFO"
    side: str           # "BUY" or "SELL"
    qty: int            # Number of lots * lot_size
    entry_price: float  # Limit price (or 0 for market)
    lsl_price: float    # Leg stop loss

@dataclass(frozen=True)
class PlaceOptionStrategyCommand(BaseCommand):
    """
    Place a multi-leg option strategy.
    Legs are placed sequentially (Dhan has no basket order API).
    If any leg fails, the engine aborts and attempts to flatten
    any legs already placed.
    """
    basket_id: str | None
    strategy_type: str      # StrategyType enum value
    legs_config: tuple[LegConfig, ...]  # Tuple for immutability
    csl_amount: float       # Combined stop loss (₹)
    user_id: str

@dataclass
class PlaceOptionStrategyResult:
    strategy_id: str
    placed_legs: int
    total_legs: int
    net_premium: float
    status: str     # "FULLY_PLACED", "PARTIALLY_PLACED", "FAILED"
    message: str
```

### TriggerCSLCommand

```python
# application/options/commands/trigger_csl.py
from dataclasses import dataclass
from application.shared.command import BaseCommand, CommandHandler

@dataclass(frozen=True)
class TriggerCSLCommand(BaseCommand):
    """
    Manually trigger Combined Stop Loss for a strategy.
    Also triggered automatically by the CSL monitor task.
    """
    strategy_id: str
    reason: str         # "MANUAL" | "MONITOR_AUTO" | "BASKET_CSL"
    user_id: str

@dataclass
class TriggerCSLResult:
    strategy_id: str
    legs_closed: int
    failed_legs: list[str]  # Leg IDs that failed to close
    status: str
    message: str
```

### RunEODScanCommand

```python
# application/signals/commands/run_eod_scan.py
from dataclasses import dataclass
from application.shared.command import BaseCommand

@dataclass(frozen=True)
class RunEODScanCommand(BaseCommand):
    """
    Run the end-of-day signal scan across the given symbol universe.
    Triggered by the nightly APScheduler job at 4 PM IST.
    Produces a new Watchlist saved to the database.
    """
    symbols: tuple[str, ...]    # Universe of symbols to scan
    user_id: str

@dataclass
class RunEODScanResult:
    watchlist_id: str
    symbols_scanned: int
    signals_found: int
    grade_a_count: int
    grade_b_count: int
    scan_duration_seconds: float
```

### EvaluateCandleCommand

```python
# application/signals/commands/evaluate_candle.py
from dataclasses import dataclass
from application.shared.command import BaseCommand
from domains.market_data.entities import OHLCV

@dataclass(frozen=True)
class EvaluateCandleCommand(BaseCommand):
    """
    Evaluate a newly completed candle for a signal.
    Called by the candle aggregator worker when a candle boundary is crossed.
    Enables real-time intraday alerts when a setup forms mid-session.
    """
    symbol: str
    exchange: str
    interval: str   # CandleInterval enum value
    candle: OHLCV   # The completed candle to evaluate
```

---

## Key Queries

### GetConversionCandidatesQuery

```python
# application/equity/queries/get_conversion_candidates.py
from dataclasses import dataclass
from application.shared.query import BaseQuery, QueryHandler
from domains.equity.conversion import ConversionCandidate

@dataclass(frozen=True)
class GetConversionCandidatesQuery(BaseQuery):
    """
    Returns all open INTRADAY positions that are eligible for
    CNC conversion, along with pre-calculated swing qty,
    intra qty to close, and suggested swing SL.

    Called from the EOD conversion panel in the cockpit UI.
    """
    user_id: str

class GetConversionCandidatesHandler(
    QueryHandler[GetConversionCandidatesQuery, list[ConversionCandidate]]
):
    def __init__(self, position_repo, risk_repo, candle_repo, quote_cache):
        self._position_repo = position_repo
        self._risk_repo = risk_repo
        self._candle_repo = candle_repo
        self._quote_cache = quote_cache

    async def handle(
        self, query: GetConversionCandidatesQuery
    ) -> list[ConversionCandidate]:
        profile = await self._risk_repo.get_profile(query.user_id)
        positions = await self._position_repo.get_all_intraday()
        candidates = []

        for pos in positions:
            # Get current quote for staleness check
            quote = await self._quote_cache.get_quote(str(pos.symbol))
            current_price = quote.ltp if quote else pos.entry_price

            # Calculate available CNC capital
            cnc_capital = profile.cnc_capital()

            # CNC qty = available_capital / current_price (no leverage)
            swing_qty = int(cnc_capital / current_price)
            swing_qty = min(swing_qty, pos.qty)  # Cannot exceed held qty

            # Qty to close intraday = total - swing
            intra_to_close = pos.qty - swing_qty

            # Suggest swing SL from daily ATR
            candles = await self._candle_repo.get_recent(
                str(pos.symbol), interval="D", count=14
            )
            daily_atr = self._calc_atr(candles)
            suggested_sl = current_price - (daily_atr * 2)  # 2×ATR swing SL

            eligible = (
                swing_qty > 0 and
                current_price > pos.entry_price  # Only convert profitable trades
            )
            reason = "Eligible for conversion" if eligible else (
                "Position in loss — wait for profit before converting" if current_price <= pos.entry_price
                else "Insufficient capital for CNC shares"
            )

            candidates.append(ConversionCandidate(
                intraday_pos=pos,
                eligible=eligible,
                swing_qty=swing_qty,
                intra_qty_to_close=intra_to_close,
                suggested_swing_sl=Decimal(str(round(float(suggested_sl), 2))),
                suggested_swing_target=None,  # User sets target
                reason=reason,
                available_capital=cnc_capital,
            ))

        return candidates

    def _calc_atr(self, candles) -> Decimal:
        from decimal import Decimal
        if not candles:
            return Decimal("10")  # Fallback
        trs = [
            max(c.high - c.low, abs(c.high - pc.close), abs(c.low - pc.close))
            for c, pc in zip(candles[1:], candles[:-1])
        ]
        atr = sum(trs[-14:]) / len(trs[-14:])
        return Decimal(str(round(float(atr), 2)))
```

### GetPositionSizeQuery

```python
# application/risk/queries/get_position_size.py
from dataclasses import dataclass
from decimal import Decimal
from application.shared.query import BaseQuery, QueryHandler
from domains.risk.sizer import PositionSizer, PositionSizeResult
from domains.equity.enums import PositionMode

@dataclass(frozen=True)
class GetPositionSizeQuery(BaseQuery):
    """
    Calculate position size for a given symbol, mode, and SL.
    Pure calculation — no state changes.
    Used by the cockpit UI to show size before placing a trade.
    """
    symbol: str
    exchange: str
    mode: str           # "INTRADAY" or "CNC"
    entry_price: float
    sl_price: float
    user_id: str

class GetPositionSizeHandler(QueryHandler[GetPositionSizeQuery, PositionSizeResult]):
    def __init__(self, risk_repo, quote_cache):
        self._risk_repo = risk_repo
        self._quote_cache = quote_cache

    async def handle(self, query: GetPositionSizeQuery) -> PositionSizeResult:
        profile = await self._risk_repo.get_profile(query.user_id)
        mode = PositionMode[query.mode]

        # For CNC, get available capital (total CNC capital minus deployed)
        available_capital = None
        if mode == PositionMode.CNC:
            # Could fetch from portfolio service — simplified here
            available_capital = profile.cnc_capital()

        sizer = PositionSizer()
        return sizer.calculate(
            entry_price=Decimal(str(query.entry_price)),
            sl_price=Decimal(str(query.sl_price)),
            mode=mode,
            profile=profile,
            available_capital=available_capital,
        )
```

### GetSignalQuery

```python
# application/signals/queries/get_signal.py
from dataclasses import dataclass
from application.shared.query import BaseQuery, QueryHandler
from domains.signals.signal import Signal

@dataclass(frozen=True)
class GetSignalQuery(BaseQuery):
    """
    Get the current signal for a symbol at a given interval.
    Returns None if no valid signal exists (not generated or expired).
    """
    symbol: str
    interval: str   # CandleInterval enum value

class GetSignalHandler(QueryHandler[GetSignalQuery, Signal | None]):
    def __init__(self, signal_repo):
        self._signal_repo = signal_repo

    async def handle(self, query: GetSignalQuery) -> Signal | None:
        signal = await self._signal_repo.get_latest(
            symbol=query.symbol,
            interval=query.interval,
        )
        if signal and signal.is_valid:
            return signal
        return None
```

### GetActiveStrategiesQuery

```python
# application/options/queries/get_strategies.py
from dataclasses import dataclass
from application.shared.query import BaseQuery, QueryHandler
from domains.options.strategy import OptionStrategy

@dataclass(frozen=True)
class GetActiveStrategiesQuery(BaseQuery):
    """Returns all ACTIVE option strategies with live Greeks from cache."""
    user_id: str

class GetActiveStrategiesHandler(
    QueryHandler[GetActiveStrategiesQuery, list[OptionStrategy]]
):
    def __init__(self, strategy_repo, option_chain_cache):
        self._strategy_repo = strategy_repo
        self._option_chain_cache = option_chain_cache

    async def handle(self, query: GetActiveStrategiesQuery) -> list[OptionStrategy]:
        strategies = await self._strategy_repo.get_active()
        # Enrich legs with latest Greeks from option chain cache
        for strategy in strategies:
            for leg in strategy.open_legs():
                greeks = await self._option_chain_cache.get_greeks(str(leg.symbol))
                if greeks:
                    leg.delta = Decimal(str(greeks.get("delta", 0)))
                    leg.theta = Decimal(str(greeks.get("theta", 0)))
                    leg.vega  = Decimal(str(greeks.get("vega", 0)))
                    leg.gamma = Decimal(str(greeks.get("gamma", 0)))
        return strategies
```

---

## Full Use Case Example — ConvertToDelivery

This is the most complex equity use case. It demonstrates the full orchestration pattern: cross-domain coordination, Dhan API calls, domain event publishing, and SL order cleanup.

```python
# application/equity/commands/convert_to_delivery.py
import asyncio
from dataclasses import dataclass
from decimal import Decimal
from domains.shared.result import Result, Ok, Err
from domains.equity.positions import IntradayPosition, CNCPosition
from domains.equity.conversion import ConversionCandidate
from domains.equity.events import PositionConverted
from domains.equity.enums import PositionMode
from domains.orders.order import Order
from domains.orders.enums import Side, ProductType, OrderType, OrderValidity
from domains.risk.atr_validator import ATRValidator
from application.shared.command import CommandHandler
from uuid import uuid4

class ConvertToDeliveryHandler(
    CommandHandler[ConvertToDeliveryCommand, Result[ConvertToDeliveryResult]]
):
    def __init__(
        self,
        position_repo,      # IPositionRepository
        order_repo,         # IOrderRepository
        broker,             # IBrokerOrderPort
        risk_repo,          # IRiskRepository
        candle_repo,        # ICandleRepository
        event_bus,          # IEventBus
    ):
        self._position_repo = position_repo
        self._order_repo = order_repo
        self._broker = broker
        self._risk_repo = risk_repo
        self._candle_repo = candle_repo
        self._event_bus = event_bus

    async def handle(
        self, cmd: ConvertToDeliveryCommand
    ) -> Result[ConvertToDeliveryResult]:
        # ── Step 1: Load the intraday position ──────────────────────────────
        position = await self._position_repo.get_intraday(cmd.position_id)
        if not position:
            return Err(f"Intraday position {cmd.position_id} not found")

        # ── Step 2: Validate CNC qty ─────────────────────────────────────────
        if cmd.cnc_qty <= 0:
            return Err("CNC qty must be positive")

        if cmd.cnc_qty >= position.qty:
            return Err(
                f"CNC qty ({cmd.cnc_qty}) must be less than intraday qty "
                f"({position.qty}). Full conversion not supported — "
                f"some INTRADAY shares must be closed due to leverage."
            )

        intra_qty_to_close = position.qty - cmd.cnc_qty

        # ── Step 3: Validate swing SL against daily ATR ──────────────────────
        candles = await self._candle_repo.get_recent(
            str(position.symbol), interval="D", count=14
        )
        atr = self._calc_atr(candles)
        validator = ATRValidator()
        valid, msg = validator.validate(
            entry_price=position.entry_price,
            sl_price=Decimal(str(cmd.swing_sl)),
            atr=atr,
            mode=PositionMode.CNC,
        )
        if not valid:
            return Err(f"Swing SL validation failed: {msg}")

        # ── Step 4: Cancel the existing intraday SL order ───────────────────
        # Must cancel before placing closing order to avoid double-trigger
        if position.sl_order_id:
            try:
                await self._broker.cancel_order(position.sl_order_id)
                await self._order_repo.mark_cancelled(position.sl_order_id)
            except Exception as e:
                return Err(f"Failed to cancel intraday SL order: {e}")

        # ── Step 5: Close the INTRADAY portion (sell intra_qty_to_close) ────
        close_order = Order.create_market(
            symbol=position.symbol,
            side=Side.SELL,
            qty=intra_qty_to_close,
            product_type=ProductType.INTRADAY,
        )
        try:
            dhan_close_id = await self._broker.place_order(close_order)
            close_order.assign_dhan_id(dhan_close_id)
            await self._order_repo.save(close_order)
        except Exception as e:
            # Attempt to re-place the SL order if close failed
            await self._attempt_restore_sl(position)
            return Err(f"Failed to close intraday portion: {e}")

        # ── Step 6: Wait briefly for close order to fill ────────────────────
        # In practice, MARKET orders on liquid stocks fill in < 1s.
        # The position poll (3-5s) will confirm — we proceed optimistically.
        await asyncio.sleep(0.5)

        # ── Step 7: Create the CNC position record ────────────────────────
        cnc_position = CNCPosition(
            id=uuid4(),
            symbol=position.symbol,
            qty=cmd.cnc_qty,
            avg_price=position.entry_price,  # CNC entry = original intraday entry
            swing_sl=Decimal(str(cmd.swing_sl)),
            swing_target=(
                Decimal(str(cmd.swing_target)) if cmd.swing_target else None
            ),
        )
        await self._position_repo.save_cnc(cnc_position)

        # ── Step 8: Place CNC SL order (GTC, wide SL) ────────────────────
        cnc_sl_order = Order.create_sl(
            symbol=position.symbol,
            side=Side.SELL,
            qty=cmd.cnc_qty,
            trigger_price=Decimal(str(cmd.swing_sl)),
            product_type=ProductType.CNC,
        )
        try:
            dhan_cnc_sl_id = await self._broker.place_order(cnc_sl_order)
            cnc_sl_order.assign_dhan_id(dhan_cnc_sl_id)
            await self._order_repo.save(cnc_sl_order)
        except Exception as e:
            # CNC position is created but SL not placed — alert user
            await self._event_bus.publish(
                SLOrderFailedAlert(
                    position_id=str(cnc_position.id),
                    symbol=str(position.symbol),
                    reason=str(e),
                )
            )
            # Do not return Err — conversion succeeded, SL placement is separate concern

        # ── Step 9: Close the original intraday position record ──────────────
        await self._position_repo.close_intraday(cmd.position_id)

        # ── Step 10: Publish PositionConverted domain event ──────────────────
        await self._event_bus.publish(PositionConverted(
            position_id=cnc_position.id,
            symbol=str(position.symbol),
            intra_qty_closed=intra_qty_to_close,
            cnc_qty_created=cmd.cnc_qty,
        ))

        return Ok(ConvertToDeliveryResult(
            success=True,
            cnc_position_id=str(cnc_position.id),
            closed_intra_qty=intra_qty_to_close,
            cnc_qty=cmd.cnc_qty,
            message=(
                f"Converted {cmd.cnc_qty} shares to CNC. "
                f"Closed {intra_qty_to_close} intraday shares. "
                f"CNC SL set at ₹{cmd.swing_sl}."
            ),
        ))

    async def _attempt_restore_sl(self, position: IntradayPosition) -> None:
        """Best-effort attempt to re-place the SL order if close failed."""
        try:
            sl_order = Order.create_sl(
                symbol=position.symbol,
                side=Side.SELL,
                qty=position.qty,
                trigger_price=position.sl_price,
                product_type=ProductType.INTRADAY,
            )
            dhan_id = await self._broker.place_order(sl_order)
            sl_order.assign_dhan_id(dhan_id)
            await self._order_repo.save(sl_order)
        except Exception:
            pass  # Logged at infrastructure level; alert sent separately

    def _calc_atr(self, candles) -> Decimal:
        if not candles or len(candles) < 2:
            return Decimal("10")
        trs = [
            max(
                float(c.high) - float(c.low),
                abs(float(c.high) - float(pc.close)),
                abs(float(c.low) - float(pc.close)),
            )
            for c, pc in zip(candles[1:], candles[:-1])
        ]
        atr = sum(trs[-14:]) / len(trs[-14:])
        return Decimal(str(round(atr, 2)))
```

---

## Event Handling — Side Effects from Domain Events

Domain events published to the event bus trigger side-effect handlers. These are registered at application startup.

```python
# application/equity/event_handlers.py
from domains.equity.events import PositionConverted
from domains.orders.events import OrderFilled

class EquityEventHandlers:
    """
    Handles domain events related to equity positions.
    Registered with the event bus at startup.
    """
    def __init__(self, journal_repo, alert_service, cockpit_ws_broadcaster):
        self._journal = journal_repo
        self._alerts = alert_service
        self._broadcaster = cockpit_ws_broadcaster

    async def on_position_converted(self, event: PositionConverted) -> None:
        """
        When a position is converted INTRADAY → CNC:
        1. Write a journal entry for review/audit.
        2. Broadcast updated position list to cockpit WebSocket clients.
        3. Send an in-app notification.
        """
        await self._journal.write_entry(
            event_type="POSITION_CONVERTED",
            symbol=event.symbol,
            details={
                "intra_qty_closed": event.intra_qty_closed,
                "cnc_qty_created": event.cnc_qty_created,
                "position_id": str(event.position_id),
            }
        )
        await self._broadcaster.broadcast_position_update(event.symbol)
        await self._alerts.send_in_app(
            f"Converted {event.cnc_qty_created} shares of {event.symbol} to CNC delivery."
        )
```

### Event Bus Registration (lifespan.py)

```python
# lifespan.py (excerpt)
from infrastructure.messaging.event_bus import EventBus
from domains.equity.events import PositionConverted, PositionClosed
from domains.orders.events import OrderFilled, OrderCancelled
from domains.options.events import CSLTriggered
from application.equity.event_handlers import EquityEventHandlers
from application.options.event_handlers import OptionsEventHandlers

def register_event_handlers(event_bus: EventBus, handlers) -> None:
    equity_h = handlers["equity"]
    options_h = handlers["options"]

    event_bus.subscribe(PositionConverted, equity_h.on_position_converted)
    event_bus.subscribe(PositionClosed,    equity_h.on_position_closed)
    event_bus.subscribe(OrderFilled,       equity_h.on_order_filled)
    event_bus.subscribe(OrderCancelled,    equity_h.on_order_cancelled)
    event_bus.subscribe(CSLTriggered,      options_h.on_csl_triggered)
```

---

## Error Strategy

| Error Type | Handling |
|---|---|
| Business rule violation (daily limit, invalid SL) | Return `Err(message)` — no exception |
| Dhan API transient failure (5xx, timeout) | `tenacity` retries in infrastructure; raises `BrokerUnavailableError` if exhausted |
| Dhan API rejection (4xx, invalid order) | Raises `BrokerRejectedError(reason)` — not retried |
| Partial leg fill on options strategy | Infrastructure engine tracks fill status; marks strategy `PARTIALLY_PLACED` |
| DB connection failure | Propagates as `RepositoryError` — caught by API layer, returns 503 |
| Unexpected errors | Logged with `structlog`; API layer returns 500 with correlation ID |

---

## Testing Application Handlers

Application handlers are testable without any running services by injecting fake/stub implementations.

```python
# tests/application/equity/test_convert_to_delivery.py
import pytest
from decimal import Decimal
from application.equity.commands.convert_to_delivery import (
    ConvertToDeliveryCommand,
    ConvertToDeliveryHandler,
)
from tests.fakes import (
    FakePositionRepository,
    FakeOrderRepository,
    FakeBrokerPort,
    FakeRiskRepository,
    FakeCandleRepository,
    FakeEventBus,
)
from tests.factories import make_intraday_position

@pytest.mark.asyncio
async def test_convert_to_delivery_success():
    # Arrange
    position = make_intraday_position(qty=100, entry_price=500.0, sl_price=495.0)
    position_repo = FakePositionRepository(intraday=[position])
    risk_repo = FakeRiskRepository(cnc_capital=Decimal("100000"))
    broker = FakeBrokerPort()
    event_bus = FakeEventBus()

    handler = ConvertToDeliveryHandler(
        position_repo=position_repo,
        order_repo=FakeOrderRepository(),
        broker=broker,
        risk_repo=risk_repo,
        candle_repo=FakeCandleRepository(),
        event_bus=event_bus,
    )

    cmd = ConvertToDeliveryCommand(
        position_id=str(position.id),
        cnc_qty=20,         # 20 CNC shares, 80 intraday closed
        swing_sl=470.0,     # Wide swing SL (6% below entry)
        swing_target=560.0,
        user_id="user_1",
    )

    # Act
    result = await handler.handle(cmd)

    # Assert
    assert result.is_ok
    assert result.value.cnc_qty == 20
    assert result.value.closed_intra_qty == 80
    assert len(broker.placed_orders) == 2  # Close intra + CNC SL order
    assert len(event_bus.published_events) == 1
    from domains.equity.events import PositionConverted
    assert isinstance(event_bus.published_events[0], PositionConverted)

@pytest.mark.asyncio
async def test_convert_full_qty_rejected():
    """Cannot convert 100% to CNC — leverage gap means fewer CNC shares needed."""
    position = make_intraday_position(qty=100, entry_price=500.0, sl_price=495.0)
    position_repo = FakePositionRepository(intraday=[position])
    handler = ConvertToDeliveryHandler(
        position_repo=position_repo,
        order_repo=FakeOrderRepository(),
        broker=FakeBrokerPort(),
        risk_repo=FakeRiskRepository(cnc_capital=Decimal("100000")),
        candle_repo=FakeCandleRepository(),
        event_bus=FakeEventBus(),
    )
    cmd = ConvertToDeliveryCommand(
        position_id=str(position.id),
        cnc_qty=100,    # Full qty — should be rejected
        swing_sl=470.0,
        swing_target=None,
        user_id="user_1",
    )
    result = await handler.handle(cmd)
    assert result.is_err
    assert "less than intraday qty" in result.error
```
