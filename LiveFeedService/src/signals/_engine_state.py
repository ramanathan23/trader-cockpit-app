from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class _SessionState:
    """Mutable session-scoped state per symbol — reset at day start."""
    range_signalled_at:  Optional[str] = None
    cam_h4_signalled:    bool          = False
    cam_l4_signalled:    bool          = False
    cam_h4r_signalled:   bool          = False   # H4 reversal (wide range)
    cam_l4r_signalled:   bool          = False   # L4 reversal (wide range)
    _adv_warned:         bool          = False
