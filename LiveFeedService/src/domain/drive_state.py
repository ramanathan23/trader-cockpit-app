from dataclasses import dataclass
from typing import Optional

from .direction import Direction
from .drive_status import DriveStatus


@dataclass
class DriveState:
    """Result of open drive evaluation after each candle in the drive window."""
    status:            DriveStatus
    direction:         Direction
    confidence:        float
    day_open:          float
    candles_evaluated: int
    trailing_stop:     Optional[float] = None
