from dataclasses import dataclass

from .direction import Direction
from .spike_type import SpikeType


@dataclass
class SpikeState:
    """Result of price-volume spike evaluation for a single candle."""
    spike_type:     SpikeType
    direction:      Direction
    volume_ratio:   float
    price_pct_move: float
    body_ratio:     float
