from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class EngineConfig:
    """All tunable parameters for SignalEngine — passed as **kwargs from __init__."""
    drive_candles:           int   = 5
    min_body_ratio:          float = 0.5
    confirmed_thresh:        float = 0.70
    weak_thresh:             float = 0.50
    range_lookback:          int   = 5
    range_vol_ratio:         float = 1.5
    range_max_pct:           float = 0.02
    vwap_hysteresis_min:     int   = 2
    min_adv_cr:              float = 5.0
    confluence_15m:          int   = 3
    confluence_1h:           int   = 12
    confluence_min_move_pct: float = 0.15
    gap_min_pct:             float = 1.5


def config_from_kwargs(**kwargs) -> EngineConfig:
    """Build EngineConfig from a dict, silently ignoring non-config keys."""
    fields = {f.name for f in dataclasses.fields(EngineConfig)}
    return EngineConfig(**{k: v for k, v in kwargs.items() if k in fields})
