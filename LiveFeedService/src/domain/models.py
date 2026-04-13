"""
Core domain models for LiveFeedService.

These are plain dataclasses — no DB or framework dependencies.
All times are timezone-aware (IST via ZoneInfo).

Enums live in domain/enums.py and are re-exported here so that existing
import sites (``from ..domain.models import Direction``) continue to work
without modification.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Re-export all enums — canonical source is domain/enums.py.
from .enums import (  # noqa: F401
    Direction,
    DriveStatus,
    SessionPhase,
    SignalType,
    SpikeType,
    Strength,
)


# ── Core data structures ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Candle:
    """Completed 3-minute OHLCV candle for a single instrument."""
    symbol:          str
    boundary:        datetime   # candle open time (IST, 3-min aligned)
    open:            float
    high:            float
    low:             float
    close:           float
    volume:          int
    tick_count:      int
    is_index_future: bool = False

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low or 0.001   # guard division by zero

    @property
    def body_ratio(self) -> float:
        return self.body / self.range

    @property
    def direction(self) -> Direction:
        if self.close > self.open:
            return Direction.BULLISH
        if self.close < self.open:
            return Direction.BEARISH
        return Direction.NEUTRAL


@dataclass
class DriveState:
    """Result of open drive evaluation after each candle in the drive window."""
    status:            DriveStatus
    direction:         Direction
    confidence:        float       # 0.0–1.0
    day_open:          float
    candles_evaluated: int
    trailing_stop:     Optional[float] = None


@dataclass
class SpikeState:
    """Result of price-volume spike evaluation for a single candle."""
    spike_type:     SpikeType
    direction:      Direction
    volume_ratio:   float    # current vol / rolling avg vol
    price_pct_move: float    # abs % price move vs prev close
    body_ratio:     float


@dataclass
class IndexBias:
    """Aggregated directional bias from index futures (market proxy)."""
    nifty:     Direction = Direction.NEUTRAL
    banknifty: Direction = Direction.NEUTRAL
    sensex:    Direction = Direction.NEUTRAL

    def majority(self) -> Direction:
        votes   = [self.nifty, self.banknifty, self.sensex]
        bullish = votes.count(Direction.BULLISH)
        bearish = votes.count(Direction.BEARISH)
        if bullish > bearish:
            return Direction.BULLISH
        if bearish > bullish:
            return Direction.BEARISH
        return Direction.NEUTRAL


@dataclass
class Signal:
    """
    A trading alert emitted by the signal engine.

    Serialised to JSON and published to Redis / streamed via SSE.
    """
    id:            str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    symbol:        str = ""
    signal_type:   SignalType   = SignalType.OPEN_DRIVE_ENTRY
    direction:     Direction    = Direction.NEUTRAL
    strength:      Strength     = Strength.MEDIUM
    score:         float        = 0.0
    session_phase: SessionPhase = SessionPhase.EXECUTION
    index_bias:    Direction    = Direction.NEUTRAL

    price:      float = 0.0

    entry_low:  Optional[float] = None
    entry_high: Optional[float] = None
    stop:       Optional[float] = None
    target_1:   Optional[float] = None
    target_2:   Optional[float] = None
    trail_stop: Optional[float] = None

    drive_confidence: Optional[float] = None
    volume_ratio:     Optional[float] = None
    message:          str = ""

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "timestamp":        self.timestamp.isoformat(),
            "symbol":           self.symbol,
            "signal_type":      self.signal_type.value,
            "direction":        self.direction.value,
            "strength":         self.strength.value,
            "score":            round(self.score, 2),
            "session_phase":    self.session_phase.value,
            "index_bias":       self.index_bias.value,
            "price":            self.price,
            "entry_low":        self.entry_low,
            "entry_high":       self.entry_high,
            "stop":             self.stop,
            "target_1":         self.target_1,
            "target_2":         self.target_2,
            "trail_stop":       self.trail_stop,
            "drive_confidence": self.drive_confidence,
            "volume_ratio":     self.volume_ratio,
            "message":          self.message,
        }


@dataclass
class InstrumentMeta:
    """Lightweight descriptor for a subscribed instrument."""
    symbol:           str
    dhan_security_id: int
    exchange_segment: str
    is_index_future:  bool = False
    underlying:       Optional[str] = None   # set when is_index_future=True
