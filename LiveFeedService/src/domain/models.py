"""
Core domain models for LiveFeedService.

These are plain dataclasses — no DB or framework dependencies.
All times are timezone-aware (IST via ZoneInfo).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class SessionPhase(str, Enum):
    PRE_MARKET     = "PRE_MARKET"      # before 9:15
    PRE_SIGNAL     = "PRE_SIGNAL"      # 9:15–9:18 (first candle building)
    DRIVE_WINDOW   = "DRIVE_WINDOW"    # 9:18–9:33 (open drive detection)
    EXECUTION      = "EXECUTION"       # 9:33–11:00 (primary trading window)
    TRANSITION     = "TRANSITION"      # 11:00–11:30
    MID_SESSION    = "MID_SESSION"     # 11:30–14:00
    DEAD_ZONE      = "DEAD_ZONE"       # 14:00–14:30 (low volume)
    CLOSE_MOMENTUM = "CLOSE_MOMENTUM"  # 14:30–15:20
    SESSION_END    = "SESSION_END"     # 15:20–15:30 (hard exit)
    POST_MARKET    = "POST_MARKET"     # after 15:30


class DriveStatus(str, Enum):
    PENDING   = "PENDING"    # not enough candles yet
    CONFIRMED = "CONFIRMED"  # >= 70% confidence
    WEAK      = "WEAK"       # 50–70% confidence
    FAILED    = "FAILED"     # price returned through day_open
    NO_DRIVE  = "NO_DRIVE"   # < 50% confidence after DRIVE_CANDLES candles


class SpikeType(str, Enum):
    BREAKOUT_SHOCK = "BREAKOUT_SHOCK"  # vol spike + large price move (same direction)
    ABSORPTION     = "ABSORPTION"      # vol spike + flat price (reversal watch)
    WEAK_SHOCK     = "WEAK_SHOCK"      # price move without vol (likely to fade)
    NONE           = "NONE"


class SignalType(str, Enum):
    OPEN_DRIVE_ENTRY  = "OPEN_DRIVE_ENTRY"   # open drive confirmed, entry setup
    DRIVE_FAILED      = "DRIVE_FAILED"       # drive invalidated
    SPIKE_BREAKOUT    = "SPIKE_BREAKOUT"     # mid-session breakout shock
    ABSORPTION        = "ABSORPTION"         # absorption detected, reversal watch
    TRAIL_UPDATE      = "TRAIL_UPDATE"       # trailing stop moved
    EXIT              = "EXIT"               # exit triggered


class Direction(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Strength(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


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
    spike_type:    SpikeType
    direction:     Direction
    volume_ratio:  float   # current vol / rolling avg vol
    price_pct_move: float  # abs % price move vs prev close
    body_ratio:    float


@dataclass
class IndexBias:
    """Aggregated directional bias from index futures (market proxy)."""
    nifty:     Direction = Direction.NEUTRAL
    banknifty: Direction = Direction.NEUTRAL
    sensex:    Direction = Direction.NEUTRAL

    def majority(self) -> Direction:
        votes = [self.nifty, self.banknifty, self.sensex]
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
    id:           str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:    datetime = field(default_factory=datetime.now)
    symbol:       str = ""
    signal_type:  SignalType = SignalType.OPEN_DRIVE_ENTRY
    direction:    Direction  = Direction.NEUTRAL
    strength:     Strength   = Strength.MEDIUM
    score:        float      = 0.0          # composite, –4 to +4
    session_phase: SessionPhase = SessionPhase.EXECUTION
    index_bias:   Direction  = Direction.NEUTRAL

    # Current price context
    price:        float = 0.0

    # Trade levels (None when not applicable, e.g. TRAIL_UPDATE)
    entry_low:    Optional[float] = None
    entry_high:   Optional[float] = None
    stop:         Optional[float] = None
    target_1:     Optional[float] = None
    target_2:     Optional[float] = None
    trail_stop:   Optional[float] = None    # updated on TRAIL_UPDATE signals

    # Diagnostic context
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
