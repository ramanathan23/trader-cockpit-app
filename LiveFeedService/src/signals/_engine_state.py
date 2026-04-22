from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..domain.drive_state import DriveState
from ._exhaustion_state import ExhaustionCandidate
from ._vwap_state import VwapState


@dataclass
class _SessionState:
    """Mutable session-scoped state per symbol — reset at day start."""
    day_open:             Optional[float]            = None
    orb_high:             Optional[float]            = None
    orb_low:              Optional[float]            = None
    drive:                Optional[DriveState]        = None
    drive_signalled:      bool                       = False
    trailing_stop:        Optional[float]            = None
    in_trade:             bool                       = False
    mid_session_start:    bool                       = False
    exhaustion_candidate: Optional[ExhaustionCandidate] = None
    spike_cooldown:       dict                       = field(default_factory=dict)
    vwap:                 VwapState                  = field(default_factory=VwapState)
    orb_signalled:        bool                       = False
    week52_signalled:     bool                       = False
    range_signalled_at:   Optional[str]              = None
    cam_h4_signalled:     bool                       = False
    cam_l4_signalled:     bool                       = False
    gap_signalled:        bool                       = False
    _adv_warned:          bool                       = False
