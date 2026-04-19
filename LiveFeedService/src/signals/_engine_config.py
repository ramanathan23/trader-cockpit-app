from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class EngineConfig:
    """All tunable parameters for SignalEngine — passed as **kwargs from __init__."""
    drive_candles:                int   = 5
    min_body_ratio:               float = 0.5
    confirmed_thresh:             float = 0.70
    weak_thresh:                  float = 0.50
    spike_window:                 int   = 20
    spike_cooldown:               int   = 5
    absorption_cooldown:          int   = 10
    absorption_near_pct:          float = 0.008
    exhaustion_downtrend_candles: int   = 4
    exhaustion_vol_ratio_min:     float = 2.5
    exhaustion_lower_lows:        int   = 2
    range_lookback:               int   = 5
    range_vol_ratio:              float = 1.5
    range_max_pct:                float = 0.02
    vwap_hysteresis_min:          int   = 2
    min_adv_cr:                   float = 5.0
    confluence_15m:               int   = 3
    confluence_1h:                int   = 12
    confluence_min_move_pct:      float = 0.15


def config_from_kwargs(**kwargs) -> EngineConfig:
    """Build EngineConfig from a dict, silently ignoring non-config keys."""
    fields = {f.name for f in dataclasses.fields(EngineConfig)}
    return EngineConfig(**{k: v for k, v in kwargs.items() if k in fields})
