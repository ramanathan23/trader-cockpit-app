# Domain Model Specifications

**Project:** Trader Cockpit App
**Layer:** Domain (pure Python, zero framework imports)
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [shared/ — Cross-Cutting Value Objects](#shared--cross-cutting-value-objects)
2. [market_data/ — Market Feed Domain](#market_data--market-feed-domain)
3. [signals/ — Signal and Watchlist Domain](#signals--signal-and-watchlist-domain)
4. [equity/ — Equity Position Domain](#equity--equity-position-domain)
5. [orders/ — Order Lifecycle Domain](#orders--order-lifecycle-domain)
6. [risk/ — Risk Management Domain](#risk--risk-management-domain)
7. [options/ — Options Trading Domain](#options--options-trading-domain)
8. [portfolio/ — Portfolio Aggregate Domain](#portfolio--portfolio-aggregate-domain)

---

## shared/ — Cross-Cutting Value Objects

The `shared` package provides primitive value objects and infrastructure types used across all domains. It has no dependencies on any other domain.

### Money

```python
# domains/shared/money.py
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class Currency(str, Enum):
    INR = "INR"

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency = Currency.INR

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError(f"Money amount cannot be negative: {self.amount}")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    @classmethod
    def from_float(cls, value: float) -> "Money":
        return cls(amount=Decimal(str(round(value, 2))))

    def is_zero(self) -> bool:
        return self.amount == Decimal("0")
```

### Symbol

```python
# domains/shared/symbol.py
from dataclasses import dataclass
from enum import Enum

class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"     # NSE Futures and Options
    BFO = "BFO"     # BSE Futures and Options
    MCX = "MCX"

@dataclass(frozen=True)
class Symbol:
    value: str           # e.g. "RELIANCE", "NIFTY24DEC24000CE"
    exchange: Exchange

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Symbol value cannot be empty")

    def __str__(self) -> str:
        return f"{self.exchange.value}:{self.value}"

    @property
    def is_derivative(self) -> bool:
        return self.exchange in (Exchange.NFO, Exchange.BFO)
```

### Price and Quantity

```python
# domains/shared/price.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Price:
    value: Decimal

    def __post_init__(self):
        if self.value <= 0:
            raise ValueError(f"Price must be positive: {self.value}")

    def pct_diff(self, other: "Price") -> Decimal:
        """Returns percentage difference from other to self."""
        return ((self.value - other.value) / other.value) * 100

    @classmethod
    def from_float(cls, value: float) -> "Price":
        return cls(value=Decimal(str(round(value, 2))))

# domains/shared/quantity.py
@dataclass(frozen=True)
class Quantity:
    value: int

    def __post_init__(self):
        if self.value <= 0:
            raise ValueError(f"Quantity must be positive: {self.value}")
```

### DomainEvent Base Class

```python
# domains/shared/domain_event.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def event_name(self) -> str:
        return self.__class__.__name__
```

### Result[T] Monad

```python
# domains/shared/result.py
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")

@dataclass
class Ok(Generic[T]):
    value: T
    is_ok: bool = True
    is_err: bool = False

    def map(self, fn: Callable[[T], "T"]) -> "Ok[T]":
        return Ok(fn(self.value))

    def unwrap(self) -> T:
        return self.value

@dataclass
class Err(Generic[E]):
    error: E
    is_ok: bool = False
    is_err: bool = True

    def map(self, fn) -> "Err[E]":
        return self  # errors pass through

    def unwrap(self):
        raise RuntimeError(f"Called unwrap() on Err: {self.error}")

# Type alias
Result = Ok[T] | Err[str]
```

---

## market_data/ — Market Feed Domain

### Enums

```python
# domains/market_data/enums.py
from enum import Enum

class CandleInterval(str, Enum):
    MIN_1  = "1"
    MIN_5  = "5"
    MIN_15 = "15"
    MIN_25 = "25"
    MIN_60 = "60"
    DAILY  = "D"
    # Note: Dhan supports exactly these intervals for historical candles.
    # MIN_25 is unusual but valid per DhanHQ v2 API.

class MarketSessionType(str, Enum):
    PRE_OPEN     = "PRE_OPEN"       # 09:00–09:15
    NORMAL       = "NORMAL"         # 09:15–15:30
    POST_CLOSE   = "POST_CLOSE"     # 15:30–16:00
    AFTER_HOURS  = "AFTER_HOURS"    # 16:00–09:00 next day
    HOLIDAY      = "HOLIDAY"
```

### Tick Value Object

```python
# domains/market_data/value_objects.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class Tick:
    """Real-time market tick from Dhan binary WebSocket feed."""
    security_id: str
    ltp: Decimal            # Last traded price
    volume: int
    oi: int | None          # Open interest (derivatives only)
    timestamp: datetime

    @property
    def ltp_float(self) -> float:
        return float(self.ltp)

@dataclass(frozen=True)
class MarketSession:
    session_type: MarketSessionType
    open_time: datetime
    close_time: datetime

    def is_active(self, at: datetime | None = None) -> bool:
        from datetime import datetime, timezone
        now = at or datetime.now(timezone.utc)
        return self.session_type == MarketSessionType.NORMAL and \
               self.open_time <= now <= self.close_time
```

### Quote Entity

```python
# domains/market_data/entities.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from domains.shared.symbol import Symbol

@dataclass
class Quote:
    """Live quote for a single instrument. Updated from market feed ticks."""
    id: UUID
    symbol: Symbol
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal          # Previous day close
    volume: int
    oi: int | None
    updated_at: datetime

    @property
    def day_change_pct(self) -> Decimal:
        if self.close == 0:
            return Decimal("0")
        return ((self.ltp - self.close) / self.close) * 100

    @property
    def day_range_pct(self) -> Decimal:
        """Intraday range as % of previous close."""
        if self.close == 0:
            return Decimal("0")
        return ((self.high - self.low) / self.close) * 100
```

### OHLCV Entity

```python
@dataclass
class OHLCV:
    """Single OHLCV candle. Stored in TimescaleDB."""
    symbol: Symbol
    interval: CandleInterval
    open_time: datetime     # Candle open timestamp (IST)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: int | None = None

    @property
    def body_size(self) -> Decimal:
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> Decimal:
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> Decimal:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
```

### Instrument Aggregate

```python
@dataclass
class KeyLevel:
    price: Decimal
    level_type: str     # "SUPPORT", "RESISTANCE", "52W_HIGH", "52W_LOW"
    description: str

@dataclass
class Instrument:
    """
    Aggregate root for a tradeable instrument.
    Carries static metadata plus computed key levels used by signals domain.
    """
    security_id: str        # Dhan's internal security ID
    symbol: Symbol
    name: str               # Full company name
    sector: str | None
    industry: str | None
    face_value: Decimal
    lot_size: int           # 1 for equity, N for F&O
    tick_size: Decimal
    key_levels: list[KeyLevel] = None

    def __post_init__(self):
        self.key_levels = self.key_levels or []

    def add_key_level(self, level: KeyLevel) -> None:
        self.key_levels.append(level)

    def nearest_support(self, price: Decimal) -> KeyLevel | None:
        supports = [l for l in self.key_levels if l.level_type == "SUPPORT" and l.price < price]
        return max(supports, key=lambda l: l.price, default=None)

    def nearest_resistance(self, price: Decimal) -> KeyLevel | None:
        resistances = [l for l in self.key_levels if l.level_type == "RESISTANCE" and l.price > price]
        return min(resistances, key=lambda l: l.price, default=None)
```

---

## signals/ — Signal and Watchlist Domain

### ScoreFactors Value Object

```python
# domains/signals/score.py
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

class SignalGrade(str, Enum):
    A = "A"   # Score 80-100 — strongest conviction
    B = "B"   # Score 60-79  — good setup
    C = "C"   # Score 40-59  — watchlist only
    D = "D"   # Score < 40   — reject

@dataclass(frozen=True)
class ScoreFactors:
    """
    Each factor scored 0-20 for a max total of 100.
    - trend:       Price above/below key MAs, MA slope
    - volume:      Volume vs 20-day average; volume spike on signal candle
    - sector:      Sector relative strength vs Nifty
    - market_ctx:  Nifty/BankNifty breadth, index trend
    - rr:          Risk/Reward ratio quality (target / stop distance)
    """
    trend: int      # 0-20
    volume: int     # 0-20
    sector: int     # 0-20
    market_ctx: int # 0-20
    rr: int         # 0-20

    def __post_init__(self):
        for name, val in [
            ("trend", self.trend),
            ("volume", self.volume),
            ("sector", self.sector),
            ("market_ctx", self.market_ctx),
            ("rr", self.rr),
        ]:
            if not (0 <= val <= 20):
                raise ValueError(f"Factor '{name}' must be 0-20, got {val}")

    @property
    def total(self) -> int:
        return self.trend + self.volume + self.sector + self.market_ctx + self.rr

    @property
    def grade(self) -> SignalGrade:
        t = self.total
        if t >= 80: return SignalGrade.A
        if t >= 60: return SignalGrade.B
        if t >= 40: return SignalGrade.C
        return SignalGrade.D
```

### Signal Entity

```python
# domains/signals/signal.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal
from enum import Enum
from domains.shared.symbol import Symbol
from domains.signals.score import ScoreFactors, SignalGrade
from domains.market_data.enums import CandleInterval

class SignalDirection(str, Enum):
    LONG  = "LONG"
    SHORT = "SHORT"

@dataclass
class Signal:
    """
    A trading signal for a symbol at a given timeframe.
    Generated by the signal engine during EOD scan or candle evaluation.
    """
    id: UUID
    symbol: Symbol
    direction: SignalDirection
    score: ScoreFactors
    entry_price: Decimal
    sl_price: Decimal
    target_price: Decimal
    interval: CandleInterval
    generated_at: datetime
    valid_until: datetime       # Typically next trading session close
    notes: str = ""

    @property
    def grade(self) -> SignalGrade:
        return self.score.grade

    @property
    def risk_reward(self) -> Decimal:
        reward = abs(self.target_price - self.entry_price)
        risk = abs(self.entry_price - self.sl_price)
        if risk == 0:
            return Decimal("0")
        return reward / risk

    @property
    def is_valid(self) -> bool:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) <= self.valid_until

    @classmethod
    def create(cls, symbol, direction, score, entry, sl, target, interval) -> "Signal":
        now = datetime.utcnow()
        return cls(
            id=uuid4(),
            symbol=symbol,
            direction=direction,
            score=score,
            entry_price=entry,
            sl_price=sl,
            target_price=target,
            interval=interval,
            generated_at=now,
            valid_until=now,  # Set by caller to next session close
        )
```

### Watchlist Aggregate

```python
# domains/signals/watchlist.py
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from domains.shared.symbol import Symbol
from domains.signals.score import ScoreFactors, SignalGrade
from domains.signals.signal import SignalDirection

@dataclass
class WatchlistEntry:
    """A single entry in the daily watchlist."""
    symbol: Symbol
    score: ScoreFactors
    direction: SignalDirection
    entry_zone_low: Decimal
    entry_zone_high: Decimal
    sl_price: Decimal
    target_price: Decimal
    key_levels: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def grade(self) -> SignalGrade:
        return self.score.grade

    def is_stale(self, price: Decimal) -> bool:
        """
        Returns True if current price has moved significantly beyond the entry zone,
        making the watchlist setup no longer actionable.
        """
        if self.direction.value == "LONG":
            # Price has already run 3% above entry zone high — stale
            return price > self.entry_zone_high * Decimal("1.03")
        else:
            # Price has already dropped 3% below entry zone low — stale
            return price < self.entry_zone_low * Decimal("0.97")

@dataclass
class Watchlist:
    """
    Daily watchlist aggregate. Refreshed once per EOD scan.
    Contains all Grade A and B signals for the next trading session.
    """
    date: date
    entries: list[WatchlistEntry] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    scan_duration_seconds: float = 0.0

    def add_entry(self, entry: WatchlistEntry) -> None:
        # Prevent duplicate symbols
        existing = [e for e in self.entries if e.symbol == entry.symbol]
        if existing:
            # Replace if new score is higher
            if entry.score.total > existing[0].score.total:
                self.entries.remove(existing[0])
                self.entries.append(entry)
        else:
            self.entries.append(entry)

    def top_entries(self, n: int = 10) -> list[WatchlistEntry]:
        return sorted(self.entries, key=lambda e: e.score.total, reverse=True)[:n]

    def grade_a_entries(self) -> list[WatchlistEntry]:
        return [e for e in self.entries if e.grade == SignalGrade.A]
```

---

## equity/ — Equity Position Domain

### Enums and Events

```python
# domains/equity/enums.py
from enum import Enum

class PositionMode(str, Enum):
    INTRADAY = "INTRADAY"   # MIS — leveraged, must exit by 3:20 PM
    CNC      = "CNC"        # Delivery — full capital, no leverage

# domains/equity/events.py
from dataclasses import dataclass
from domains.shared.domain_event import DomainEvent
from uuid import UUID

@dataclass(frozen=True)
class PositionOpened(DomainEvent):
    position_id: UUID
    symbol: str
    mode: str
    qty: int
    entry_price: float

@dataclass(frozen=True)
class PositionConverted(DomainEvent):
    position_id: UUID
    symbol: str
    intra_qty_closed: int
    cnc_qty_created: int

@dataclass(frozen=True)
class PositionClosed(DomainEvent):
    position_id: UUID
    symbol: str
    mode: str
    realized_pnl: float
```

### IntradayPosition Entity

```python
# domains/equity/positions.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal
from domains.shared.symbol import Symbol
from domains.equity.enums import PositionMode

@dataclass
class IntradayPosition:
    """
    An open INTRADAY (MIS) position.
    - Tight SL — typically 0.5% to 1.5% from entry.
    - Higher quantity due to leverage.
    - Must be squared off or converted by auto-square-off time (3:20 PM).
    - sl_order_id: the Dhan SL order currently live for this position.
    """
    id: UUID
    symbol: Symbol
    qty: int
    entry_price: Decimal
    sl_price: Decimal
    sl_order_id: str | None     # Dhan order ID of the active SL order
    target_price: Decimal | None
    product_type: str = "INTRADAY"
    opened_at: datetime = field(default_factory=datetime.utcnow)
    _events: list = field(default_factory=list, repr=False)

    @property
    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        return (current_price - self.entry_price) * self.qty

    @property
    def sl_distance_pct(self) -> Decimal:
        return ((self.entry_price - self.sl_price) / self.entry_price) * 100

    @property
    def capital_at_risk(self) -> Decimal:
        """Maximum loss if SL is hit."""
        return abs(self.entry_price - self.sl_price) * self.qty

    def is_eligible_for_conversion(self) -> bool:
        """
        Position is eligible for INTRADAY → CNC conversion if:
        - Position is in profit (price > entry)
        - Current time allows conversion (before 3:20 PM)
        Basic eligibility only — full validation in ConversionCandidate.
        """
        return True  # Time and profit checks done in domain service

    def can_pyramid(self, current_price: Decimal) -> bool:
        """Allow adding to position only if already 1%+ in profit."""
        return current_price >= self.entry_price * Decimal("1.01")
```

### CNCPosition Entity

```python
@dataclass
class CNCPosition:
    """
    A delivery (CNC) position.
    - Wide SL — typically 5-10% from average price (swing trade).
    - Fewer shares due to no leverage.
    - No auto-square-off. Can hold overnight / for days.
    - swing_sl: price-based SL for the swing trade.
    - swing_target: first target price for the swing.
    """
    id: UUID
    symbol: Symbol
    qty: int
    avg_price: Decimal
    swing_sl: Decimal
    swing_target: Decimal | None
    hold_days: int = 0
    product_type: str = "CNC"
    opened_at: datetime = field(default_factory=datetime.utcnow)
    _events: list = field(default_factory=list, repr=False)

    @property
    def sl_distance_pct(self) -> Decimal:
        return ((self.avg_price - self.swing_sl) / self.avg_price) * 100

    @property
    def is_sl_valid(self) -> bool:
        """CNC SL must be at least 3% below entry (wide stop philosophy)."""
        return self.sl_distance_pct >= Decimal("3.0")

    def update_avg_price(self, new_qty: int, new_price: Decimal) -> None:
        """Update average price when adding to position (cost averaging or pyramid)."""
        total_cost = (self.avg_price * self.qty) + (new_price * new_qty)
        self.qty += new_qty
        self.avg_price = total_cost / self.qty
```

### ConversionCandidate Value Object

```python
# domains/equity/conversion.py
from dataclasses import dataclass
from decimal import Decimal
from domains.equity.positions import IntradayPosition

@dataclass(frozen=True)
class ConversionCandidate:
    """
    Represents the evaluation of whether an intraday position
    can and should be converted to CNC delivery.

    Key constraint: CNC requires full capital (no leverage).
    So the CNC qty that can be held = available_capital / current_price.
    This is ALWAYS fewer shares than the intraday qty.

    intra_qty_to_close: the INTRADAY shares to close (sell)
    swing_qty:          the CNC shares to carry forward
    intra_qty_to_close + swing_qty = intraday_pos.qty (total)
    """
    intraday_pos: IntradayPosition
    eligible: bool
    swing_qty: int
    intra_qty_to_close: int
    suggested_swing_sl: Decimal
    suggested_swing_target: Decimal | None
    reason: str  # Human-readable explanation (eligible or why not)
    available_capital: Decimal

    def __post_init__(self):
        if self.eligible:
            total = self.swing_qty + self.intra_qty_to_close
            if total != self.intraday_pos.qty:
                raise ValueError(
                    f"swing_qty ({self.swing_qty}) + intra_qty_to_close "
                    f"({self.intra_qty_to_close}) must equal total qty "
                    f"({self.intraday_pos.qty})"
                )
```

---

## orders/ — Order Lifecycle Domain

### Enums

```python
# domains/orders/enums.py
from enum import Enum

class OrderStatus(str, Enum):
    PENDING    = "PENDING"      # Sent to Dhan, awaiting confirmation
    OPEN       = "OPEN"         # Active in exchange order book
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED     = "FILLED"       # Fully executed
    CANCELLED  = "CANCELLED"
    REJECTED   = "REJECTED"
    EXPIRED    = "EXPIRED"      # DAY order not filled before close

class OrderType(str, Enum):
    MARKET     = "MARKET"
    LIMIT      = "LIMIT"
    SL         = "SL"           # Stop-loss (SL-M in Dhan terminology)
    SL_LIMIT   = "SL_LIMIT"     # Stop-loss with limit price

class ProductType(str, Enum):
    INTRADAY   = "INTRADAY"     # MIS — leveraged intraday
    CNC        = "CNC"          # Delivery equity (no leverage)
    MARGIN     = "MARGIN"       # F&O carry-forward

class Side(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"

class OrderValidity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"     # Immediate or cancel
    GTC = "GTC"     # Good till cancelled (Forever Orders)
```

### Order Aggregate

```python
# domains/orders/order.py
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from domains.shared.symbol import Symbol
from domains.orders.enums import (
    OrderStatus, OrderType, ProductType, Side, OrderValidity
)
from domains.orders.events import OrderPlaced, OrderFilled, OrderCancelled

@dataclass
class Order:
    """
    Order aggregate. Single source of truth for an order's lifecycle.
    dhan_order_id is the external reference returned by Dhan API.
    """
    id: UUID
    symbol: Symbol
    side: Side
    qty: int
    price: Decimal | None       # None for MARKET orders
    trigger_price: Decimal | None   # For SL orders
    order_type: OrderType
    product_type: ProductType
    validity: OrderValidity
    status: OrderStatus = OrderStatus.PENDING
    dhan_order_id: str | None = None
    filled_qty: int = 0
    fill_price: Decimal | None = None
    rejection_reason: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list = field(default_factory=list, repr=False)

    @classmethod
    def create_market(
        cls,
        symbol: Symbol,
        side: Side,
        qty: int,
        product_type: ProductType,
    ) -> "Order":
        order = cls(
            id=uuid4(),
            symbol=symbol,
            side=side,
            qty=qty,
            price=None,
            trigger_price=None,
            order_type=OrderType.MARKET,
            product_type=product_type,
            validity=OrderValidity.DAY,
        )
        order._events.append(OrderPlaced(order_id=order.id, symbol=str(symbol)))
        return order

    @classmethod
    def create_sl(
        cls,
        symbol: Symbol,
        side: Side,
        qty: int,
        trigger_price: Decimal,
        product_type: ProductType,
    ) -> "Order":
        """SL-Market order — triggers at trigger_price, executes at market."""
        order = cls(
            id=uuid4(),
            symbol=symbol,
            side=side,
            qty=qty,
            price=None,
            trigger_price=trigger_price,
            order_type=OrderType.SL,
            product_type=product_type,
            validity=OrderValidity.GTC,
        )
        order._events.append(OrderPlaced(order_id=order.id, symbol=str(symbol)))
        return order

    def assign_dhan_id(self, dhan_order_id: str) -> None:
        self.dhan_order_id = dhan_order_id
        self.status = OrderStatus.OPEN
        self.updated_at = datetime.utcnow()

    def mark_filled(self, fill_price: Decimal, filled_qty: int) -> None:
        self.fill_price = fill_price
        self.filled_qty = filled_qty
        self.status = OrderStatus.FILLED
        self.updated_at = datetime.utcnow()
        self._events.append(OrderFilled(
            order_id=self.id,
            symbol=str(self.symbol),
            fill_price=float(fill_price),
            filled_qty=filled_qty,
        ))

    def cancel(self) -> None:
        if self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order in status: {self.status}")
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()
        self._events.append(OrderCancelled(order_id=self.id, symbol=str(self.symbol)))

    def reject(self, reason: str) -> None:
        self.status = OrderStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def pop_events(self) -> list:
        events, self._events = self._events, []
        return events
```

---

## risk/ — Risk Management Domain

### RiskProfile Entity

```python
# domains/risk/profile.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class RiskProfile:
    """
    User-defined risk parameters. Set once, rarely changed.
    - intra_risk_pct:  Max % of intraday capital risked per trade (e.g., 0.5%)
    - cnc_risk_pct:    Max % of CNC capital risked per swing trade (e.g., 1.0%)
    - daily_loss_limit: Max absolute loss (INR) allowed in a single day
    - max_intra_positions: Max concurrent INTRADAY positions
    - max_cnc_positions:   Max concurrent CNC positions
    """
    intra_risk_pct: Decimal      # e.g. Decimal("0.5")
    cnc_risk_pct: Decimal        # e.g. Decimal("1.0")
    daily_loss_limit: Decimal    # e.g. Decimal("5000")
    max_intra_positions: int     # e.g. 5
    max_cnc_positions: int       # e.g. 10
    total_capital: Decimal       # Total trading capital (INR)

    def intra_capital(self) -> Decimal:
        """Intraday capital = 40% of total (configurable)."""
        return self.total_capital * Decimal("0.4")

    def cnc_capital(self) -> Decimal:
        """CNC/swing capital = 60% of total (configurable)."""
        return self.total_capital * Decimal("0.6")

    def max_intra_risk_per_trade(self) -> Decimal:
        return self.intra_capital() * (self.intra_risk_pct / 100)

    def max_cnc_risk_per_trade(self) -> Decimal:
        return self.cnc_capital() * (self.cnc_risk_pct / 100)

@dataclass
class DailyRiskState:
    """
    Mutable runtime state tracking daily risk consumption.
    Reset at market open each day.
    """
    date: str               # "YYYY-MM-DD"
    consumed_loss: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    positions_open: int = 0
    intra_trades_today: int = 0
    cnc_trades_today: int = 0

    def can_trade(self, profile: RiskProfile) -> tuple[bool, str]:
        if self.consumed_loss >= profile.daily_loss_limit:
            return False, f"Daily loss limit ₹{profile.daily_loss_limit} reached"
        return True, "OK"

    def add_loss(self, amount: Decimal) -> None:
        if amount > 0:
            self.consumed_loss += amount
            self.realized_pnl -= amount

    def add_profit(self, amount: Decimal) -> None:
        if amount > 0:
            self.realized_pnl += amount
```

### PositionSizer Domain Service

```python
# domains/risk/sizer.py
from dataclasses import dataclass
from decimal import Decimal
from domains.risk.profile import RiskProfile
from domains.equity.enums import PositionMode

@dataclass(frozen=True)
class PositionSizeResult:
    qty: int
    risk_per_share: Decimal
    total_risk: Decimal
    capital_required: Decimal
    mode: PositionMode
    warning: str | None = None

class PositionSizer:
    """
    Domain service to calculate position size based on risk profile.

    INTRADAY (tight SL philosophy):
    - SL is tight: 0.5%-1.5% from entry typically.
    - Leverage is available: qty = max_risk / risk_per_share.
    - Many shares, small SL distance.

    CNC (wide SL philosophy):
    - SL is wide: 3%-10% from entry (swing SL).
    - No leverage: capital_required = qty * entry_price must fit available capital.
    - Few shares, wide SL distance.
    - Conversion always produces fewer CNC shares than held intraday.
    """

    def calculate(
        self,
        entry_price: Decimal,
        sl_price: Decimal,
        mode: PositionMode,
        profile: RiskProfile,
        available_capital: Decimal | None = None,
    ) -> PositionSizeResult:
        risk_per_share = abs(entry_price - sl_price)
        if risk_per_share == 0:
            raise ValueError("SL price cannot equal entry price")

        if mode == PositionMode.INTRADAY:
            max_risk = profile.max_intra_risk_per_trade()
            raw_qty = int(max_risk / risk_per_share)
            capital_required = entry_price * raw_qty  # Leverage: broker funds excess
            total_risk = risk_per_share * raw_qty
            warning = None
            if total_risk > max_risk * Decimal("1.05"):
                warning = "Actual risk slightly exceeds limit due to rounding"

        else:  # CNC
            max_risk = profile.max_cnc_risk_per_trade()
            risk_based_qty = int(max_risk / risk_per_share)
            # Capital constraint: full capital needed for CNC (no leverage)
            capital = available_capital or profile.cnc_capital()
            capital_based_qty = int(capital / entry_price)
            raw_qty = min(risk_based_qty, capital_based_qty)
            capital_required = entry_price * raw_qty  # Must fit within available capital
            total_risk = risk_per_share * raw_qty
            warning = None
            if risk_based_qty > capital_based_qty:
                warning = "Position size limited by available capital (CNC: no leverage)"

        if raw_qty <= 0:
            raise ValueError(
                f"Calculated qty is 0 or negative. "
                f"Risk per share ₹{risk_per_share} may be too large for "
                f"max risk ₹{max_risk}. Widen your entry or reduce risk %."
            )

        return PositionSizeResult(
            qty=raw_qty,
            risk_per_share=risk_per_share,
            total_risk=total_risk,
            capital_required=capital_required,
            mode=mode,
            warning=warning,
        )
```

### ATRValidator Domain Service

```python
# domains/risk/atr_validator.py
from decimal import Decimal
from domains.equity.enums import PositionMode

class ATRValidator:
    """
    Validates that a proposed SL is meaningful relative to ATR.
    - INTRADAY: SL must be >= 0.5 * ATR(14) of the candle interval used.
      (If SL is tighter than 0.5×ATR, market noise will hit it randomly.)
    - CNC/Swing: SL must be >= 1.0 * ATR(14) of the daily candle.
      (Swing SL must clear normal daily volatility.)
    """
    INTRADAY_ATR_MULTIPLIER = Decimal("0.5")
    CNC_ATR_MULTIPLIER      = Decimal("1.0")

    def validate(
        self,
        entry_price: Decimal,
        sl_price: Decimal,
        atr: Decimal,
        mode: PositionMode,
    ) -> tuple[bool, str]:
        sl_distance = abs(entry_price - sl_price)
        multiplier = (
            self.INTRADAY_ATR_MULTIPLIER
            if mode == PositionMode.INTRADAY
            else self.CNC_ATR_MULTIPLIER
        )
        min_sl = atr * multiplier

        if sl_distance < min_sl:
            return False, (
                f"SL distance ₹{sl_distance:.2f} is below minimum "
                f"₹{min_sl:.2f} ({multiplier}×ATR={atr:.2f}). "
                f"Tighten SL will likely be hit by noise."
            )
        return True, "SL is valid relative to ATR"
```

---

## options/ — Options Trading Domain

### Enums

```python
# domains/options/enums.py
from enum import Enum

class OptionType(str, Enum):
    CE = "CE"   # Call
    PE = "PE"   # Put

class StrategyType(str, Enum):
    LONG_CALL         = "LONG_CALL"
    LONG_PUT          = "LONG_PUT"
    BULL_CALL_SPREAD  = "BULL_CALL_SPREAD"
    BEAR_PUT_SPREAD   = "BEAR_PUT_SPREAD"
    IRON_CONDOR       = "IRON_CONDOR"
    STRADDLE          = "STRADDLE"
    STRANGLE          = "STRANGLE"
    CUSTOM            = "CUSTOM"

class CSLStatus(str, Enum):
    ACTIVE    = "ACTIVE"    # Strategy is live, CSL monitoring active
    TRIGGERED = "TRIGGERED" # CSL threshold hit, flattening in progress
    CLOSED    = "CLOSED"    # All legs closed
```

### OptionLeg Entity

```python
# domains/options/leg.py
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4
from domains.shared.symbol import Symbol
from domains.orders.enums import Side

@dataclass
class OptionLeg:
    """
    A single option leg within a strategy.
    - lsl_price: Leg-level Stop Loss. Individual leg protection.
    - lsl_order_id: Active SL order for this leg on Dhan.
    - delta: option delta at time of entry (for Greeks tracking).
    """
    id: UUID
    symbol: Symbol          # Full option symbol e.g. NIFTY24DEC24000CE
    side: Side              # BUY or SELL
    qty: int                # Number of lots * lot_size
    entry_price: Decimal
    lsl_price: Decimal      # Leg Stop Loss price
    lsl_order_id: str | None = None
    current_price: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    is_closed: bool = False
    exit_price: Decimal | None = None

    @property
    def unrealized_pnl(self) -> Decimal | None:
        if self.current_price is None:
            return None
        multiplier = Decimal("1") if self.side == Side.BUY else Decimal("-1")
        return multiplier * (self.current_price - self.entry_price) * self.qty

    @property
    def premium_paid(self) -> Decimal:
        """Positive = debit (bought), Negative = credit (sold)."""
        if self.side == Side.BUY:
            return self.entry_price * self.qty
        return -(self.entry_price * self.qty)
```

### OptionStrategy Aggregate

```python
# domains/options/strategy.py
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from domains.options.leg import OptionLeg
from domains.options.enums import StrategyType, CSLStatus
from domains.options.events import CSLTriggered

@dataclass
class OptionStrategy:
    """
    Aggregate root for a multi-leg option strategy.
    Owns its legs and the combined stop loss (CSL) logic.

    CSL (Combined Stop Loss):
    - csl_amount: Maximum total loss allowed across ALL legs combined.
    - When combined_pnl() <= -csl_amount, the CSL is triggered.
    - On CSL trigger: close all open legs at market.
    """
    id: UUID
    basket_id: UUID | None
    strategy_type: StrategyType
    legs: list[OptionLeg]
    csl_amount: Decimal         # CSL threshold (positive amount e.g. ₹5000)
    csl_status: CSLStatus = CSLStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: datetime | None = None
    _events: list = field(default_factory=list, repr=False)

    def combined_pnl(self) -> Decimal | None:
        """Sum of unrealized P&L across all open legs."""
        pnls = [leg.unrealized_pnl for leg in self.legs if not leg.is_closed]
        if any(p is None for p in pnls):
            return None  # Not all prices available yet
        return sum(pnls)

    def net_premium(self) -> Decimal:
        """Net premium: positive = net debit, negative = net credit."""
        return sum(leg.premium_paid for leg in self.legs)

    def is_csl_breached(self) -> bool:
        pnl = self.combined_pnl()
        if pnl is None:
            return False
        return pnl <= -self.csl_amount

    def trigger_csl(self, reason: str) -> None:
        if self.csl_status != CSLStatus.ACTIVE:
            return
        self.csl_status = CSLStatus.TRIGGERED
        self._events.append(CSLTriggered(
            strategy_id=self.id,
            combined_pnl=float(self.combined_pnl() or 0),
            csl_amount=float(self.csl_amount),
            reason=reason,
        ))

    def mark_closed(self) -> None:
        self.csl_status = CSLStatus.CLOSED
        self.closed_at = datetime.utcnow()

    def open_legs(self) -> list[OptionLeg]:
        return [leg for leg in self.legs if not leg.is_closed]

    def pop_events(self) -> list:
        events, self._events = self._events, []
        return events
```

### Basket Aggregate

```python
# domains/options/basket.py
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4
from domains.options.strategy import OptionStrategy
from domains.options.enums import CSLStatus

@dataclass
class Basket:
    """
    A named collection of option strategies on the same underlying.
    Allows grouping related trades (e.g. all NIFTY strategies for the week).
    Each strategy within has its own CSL; the basket has an overall CSL limit.
    """
    id: UUID
    name: str               # e.g. "NIFTY_WEEKLY_JAN5"
    underlying: str         # e.g. "NIFTY", "BANKNIFTY"
    strategies: list[OptionStrategy] = field(default_factory=list)
    csl_limit: Decimal = Decimal("0")   # 0 = no basket-level CSL

    def add_strategy(self, strategy: OptionStrategy) -> None:
        strategy.basket_id = self.id
        self.strategies.append(strategy)

    def active_strategies(self) -> list[OptionStrategy]:
        return [s for s in self.strategies if s.csl_status == CSLStatus.ACTIVE]

    def total_pnl(self) -> Decimal | None:
        pnls = [s.combined_pnl() for s in self.strategies]
        if any(p is None for p in pnls):
            return None
        return sum(pnls)

    def is_basket_csl_breached(self) -> bool:
        if self.csl_limit == 0:
            return False
        pnl = self.total_pnl()
        return pnl is not None and pnl <= -self.csl_limit
```

### LSLCSLEngine Domain Service

```python
# domains/options/csl_engine.py
from decimal import Decimal
from domains.options.strategy import OptionStrategy
from domains.options.basket import Basket
from domains.options.enums import CSLStatus

class LSLCSLEngine:
    """
    Domain service that monitors LSL (Leg Stop Loss) and CSL (Combined Stop Loss).

    This service is called by the infrastructure CSL monitor task every 3 seconds.
    It is pure domain logic — it decides WHAT should happen,
    but the application layer and infrastructure handle HOW (placing orders, etc.).
    """

    def check_strategy(self, strategy: OptionStrategy) -> list[str]:
        """
        Returns a list of action strings needed for this strategy.
        Actions: "TRIGGER_CSL:{strategy_id}" or "CLOSE_LEG:{leg_id}"
        """
        actions = []

        if strategy.csl_status != CSLStatus.ACTIVE:
            return actions

        # 1. Check combined P&L against CSL
        if strategy.is_csl_breached():
            strategy.trigger_csl(reason=f"Combined P&L breached CSL of ₹{strategy.csl_amount}")
            actions.append(f"TRIGGER_CSL:{strategy.id}")
            return actions  # CSL overrides individual LSLs

        # 2. Check individual leg LSLs
        for leg in strategy.open_legs():
            if leg.current_price is None:
                continue
            if leg.lsl_order_id is None:
                # LSL order not placed yet (should have been placed on entry)
                actions.append(f"PLACE_LSL:{leg.id}")
                continue

        return actions

    def orphaned_lsl_orders(
        self,
        strategy: OptionStrategy,
    ) -> list[str]:
        """
        Returns Dhan order IDs of LSL orders that need to be cancelled
        because their corresponding leg is already closed.
        """
        return [
            leg.lsl_order_id
            for leg in strategy.legs
            if leg.is_closed and leg.lsl_order_id is not None
        ]
```

---

## portfolio/ — Portfolio Aggregate Domain

### Portfolio Aggregate

```python
# domains/portfolio/portfolio.py
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID
from domains.equity.positions import CNCPosition
from domains.options.strategy import OptionStrategy

@dataclass
class Allocation:
    """Snapshot of how capital is deployed."""
    equity_intraday: Decimal = Decimal("0")
    equity_cnc: Decimal = Decimal("0")
    options: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")

    @property
    def total_deployed(self) -> Decimal:
        return self.equity_intraday + self.equity_cnc + self.options

    @property
    def utilization_pct(self) -> Decimal:
        total = self.total_deployed + self.cash
        if total == 0:
            return Decimal("0")
        return (self.total_deployed / total) * 100

@dataclass(frozen=True)
class DailyPnL:
    date: date
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    charges: Decimal            # Brokerage + STT + exchange fees

    @property
    def net_pnl(self) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl - self.charges

@dataclass
class Portfolio:
    """
    Aggregate view of the entire trading portfolio.
    Read-model — constructed from equity + options domains.
    """
    id: UUID
    user_id: str
    cnc_positions: list[CNCPosition] = field(default_factory=list)
    option_strategies: list[OptionStrategy] = field(default_factory=list)
    allocation: Allocation = field(default_factory=Allocation)
    daily_pnl: DailyPnL | None = None

    def total_unrealized_pnl(self) -> Decimal:
        cnc_pnl = Decimal("0")  # Requires current prices — calculated by query
        options_pnl = sum(
            s.combined_pnl() or Decimal("0")
            for s in self.option_strategies
        )
        return cnc_pnl + options_pnl

    def active_cnc_count(self) -> int:
        return len(self.cnc_positions)

    def active_strategy_count(self) -> int:
        from domains.options.enums import CSLStatus
        return sum(1 for s in self.option_strategies if s.csl_status == CSLStatus.ACTIVE)
```
