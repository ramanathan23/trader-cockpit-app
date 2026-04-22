from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .direction import Direction
from .session_phase import SessionPhase
from .signal_type import SignalType
from .strength import Strength


@dataclass(frozen=True)
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

    drive_confidence:    Optional[float] = None
    volume_ratio:        Optional[float] = None
    bias_15m:            Direction       = Direction.NEUTRAL
    bias_1h:             Direction       = Direction.NEUTRAL
    message:             str = ""
    watchlist_conflict:  bool = False

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
            "bias_15m":            self.bias_15m.value,
            "bias_1h":             self.bias_1h.value,
            "message":             self.message,
            "watchlist_conflict":  self.watchlist_conflict,
        }
