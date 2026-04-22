"""
GapDetector: intraday price gaps between consecutive 5-min session candles.

Detects when candle.open gaps significantly away from the previous session
candle's close. This catches intraday circuit-filter resumptions, news shocks,
or auction gaps that occur DURING the trading day — not the overnight gap.

Fires on any candle where the gap threshold is met. No one-shot guard since
multiple intraday gaps can occur in the same session.

gap_pct = (candle.open - prev_session_candle.close) / prev_session_candle.close * 100
GAP_UP   if gap_pct >= +gap_min_pct
GAP_DOWN if gap_pct <= -gap_min_pct
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
    symbol:          str,
    candle:          Candle,
    phase:           SessionPhase,
    state:           _SessionState,
    config:          EngineConfig,
    session_history: list[Candle],  # today-only completed candles (before this candle)
) -> list[Signal]:
    # Need at least one prior session candle to measure gap against
    prior = [c for c in session_history if c.boundary < candle.boundary]
    if not prior:
        return []

    prev_close = prior[-1].close
    if prev_close == 0:
        return []

    gap_pct = (candle.open - prev_close) / prev_close * 100
    if abs(gap_pct) < config.gap_min_pct:
        return []

    sig_type  = SignalType.GAP_UP   if gap_pct > 0 else SignalType.GAP_DOWN
    direction = Direction.BULLISH   if gap_pct > 0 else Direction.BEARISH
    return [make_gap_signal(symbol, candle, sig_type, direction, gap_pct, phase, prev_close)]
