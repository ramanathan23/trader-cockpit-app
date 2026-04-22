"""
GapDetector: fires GAP_UP / GAP_DOWN once per session on the first candle.

Logic:
  gap_pct = (day_open - prev_day_close) / prev_day_close * 100
  GAP_UP   if gap_pct >= +gap_min_pct (default 1.5%)
  GAP_DOWN if gap_pct <= -gap_min_pct

Fires on the first completed 5-min candle of the session so that prev_close
comes from yesterday's daily metrics (already loaded by MetricsService).
state.gap_signalled prevents re-firing for the rest of the day.
"""
from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ._engine_config import EngineConfig
from ._engine_state import _SessionState
from ._factory_gap import make_gap_signal


def evaluate_gap(
    symbol:  str,
    candle:  Candle,
    phase:   SessionPhase,
    state:   _SessionState,
    config:  EngineConfig,
    metrics: dict,
) -> list[Signal]:
    if state.gap_signalled or state.day_open is None:
        return []
    state.gap_signalled = True  # mark regardless — one gap assessment per session

    prev_close = metrics.get("prev_day_close")
    if not prev_close:
        return []

    gap_pct = (state.day_open - prev_close) / prev_close * 100
    if abs(gap_pct) < config.gap_min_pct:
        return []

    sig_type  = SignalType.GAP_UP   if gap_pct > 0 else SignalType.GAP_DOWN
    direction = Direction.BULLISH   if gap_pct > 0 else Direction.BEARISH
    return [make_gap_signal(symbol, candle, sig_type, direction, gap_pct, phase, prev_close)]
