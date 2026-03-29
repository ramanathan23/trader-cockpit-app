from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from trader_cockpit.domain.shared.symbol import Symbol
from .enums import CandleInterval


@dataclass
class Quote:
    """Live quote for a single instrument. Updated from market feed ticks."""
    id: UUID
    symbol: Symbol
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal       # Previous day close
    volume: int
    oi: int | None
    updated_at: datetime

    @classmethod
    def create(cls, symbol: Symbol, ltp: Decimal, close: Decimal) -> "Quote":
        return cls(
            id=uuid4(),
            symbol=symbol,
            ltp=ltp,
            open=ltp,
            high=ltp,
            low=ltp,
            close=close,
            volume=0,
            oi=None,
            updated_at=datetime.utcnow(),
        )

    def apply_tick(self, ltp: Decimal, volume: int, oi: int | None, ts: datetime) -> None:
        self.ltp = ltp
        self.volume = volume
        self.oi = oi
        self.updated_at = ts
        if ltp > self.high:
            self.high = ltp
        if ltp < self.low:
            self.low = ltp

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


@dataclass
class OHLCV:
    """Single OHLCV candle. Stored in TimescaleDB."""
    symbol: Symbol
    interval: CandleInterval
    open_time: datetime    # Candle open timestamp (IST, NSE-anchored boundary)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: int | None = None
    is_partial: bool = False   # True if aggregated from incomplete data

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

    @property
    def is_doji(self) -> bool:
        if self.high == self.low:
            return False
        return self.body_size / (self.high - self.low) < Decimal("0.1")

    def update(self, ltp: Decimal, volume: int, oi: int | None) -> None:
        """Update partial candle with new tick."""
        self.close = ltp
        self.volume = volume
        if ltp > self.high:
            self.high = ltp
        if ltp < self.low:
            self.low = ltp
        if oi is not None:
            self.oi = oi


@dataclass
class KeyLevel:
    price: Decimal
    level_type: str     # "SUPPORT", "RESISTANCE", "52W_HIGH", "52W_LOW"
    description: str


@dataclass
class Instrument:
    """
    Aggregate root for a tradeable instrument.
    Carries static metadata plus computed key levels used by the signals domain.
    """
    security_id: str        # Dhan's internal security ID
    symbol: Symbol
    name: str               # Full company name
    sector: str | None
    industry: str | None
    face_value: Decimal
    lot_size: int           # 1 for equity, N for F&O
    tick_size: Decimal
    key_levels: list[KeyLevel] = field(default_factory=list)

    def add_key_level(self, level: KeyLevel) -> None:
        self.key_levels.append(level)

    def nearest_support(self, price: Decimal) -> KeyLevel | None:
        supports = [l for l in self.key_levels if l.level_type == "SUPPORT" and l.price < price]
        return max(supports, key=lambda l: l.price, default=None)

    def nearest_resistance(self, price: Decimal) -> KeyLevel | None:
        resistances = [l for l in self.key_levels if l.level_type == "RESISTANCE" and l.price > price]
        return min(resistances, key=lambda l: l.price, default=None)
