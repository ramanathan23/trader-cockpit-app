from __future__ import annotations

import logging

from ..core.session_manager import SessionManager
from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.spike_type import SpikeType
from ..domain.strength import Strength
from . import exhaustion_reversal, signal_factory, spike_detector
from ._engine_config import EngineConfig
from ._engine_state import _SessionState

logger = logging.getLogger(__name__)


def near_key_level(
    price: float, state: _SessionState, metrics: dict, absorption_near_pct: float,
) -> bool:
    """True if price is within absorption_near_pct of any key structural level."""
    levels: list[float] = []
    if metrics.get("prev_day_high"):
        levels.append(metrics["prev_day_high"])
    if metrics.get("prev_day_low"):
        levels.append(metrics["prev_day_low"])
    if state.orb_high:
        levels.append(state.orb_high)
    if state.orb_low:
        levels.append(state.orb_low)
    vwap = state.vwap.vwap
    if vwap:
        levels.append(vwap)
    return any(abs(price - lvl) / lvl <= absorption_near_pct for lvl in levels)


def evaluate_spike(
    symbol:          str,
    candle:          Candle,
    history:         list[Candle],  # full history (yesterday + today) — for vol baseline
    session_history: list[Candle],  # today-only — for exhaustion intraday pattern
    bias:            IndexBias,
    phase:           SessionPhase,
    state:           _SessionState,
    config:          EngineConfig,
    session_manager: SessionManager,
    metrics:         dict,
) -> list[Signal]:
    prior        = history[:-1] if history and history[-1].boundary == candle.boundary else history
    session_prior = (
        session_history[:-1]
        if session_history and session_history[-1].boundary == candle.boundary
        else session_history
    )
    vol_thresh   = session_manager.spike_vol_threshold(phase)
    price_thresh = session_manager.spike_price_threshold(phase)
    out: list[Signal] = []

    for k in list(state.spike_cooldown):
        state.spike_cooldown[k] -= 1
        if state.spike_cooldown[k] <= 0:
            del state.spike_cooldown[k]

    spike = spike_detector.evaluate(candle, prior,
                                    vol_spike_ratio=vol_thresh,
                                    price_shock_pct=price_thresh)
    if spike is not None:
        index_aligned = bias.majority() in (spike.direction, Direction.NEUTRAL)
        strength      = Strength.HIGH if index_aligned else Strength.MEDIUM

        if spike.spike_type == SpikeType.BREAKOUT_SHOCK:
            if SpikeType.BREAKOUT_SHOCK not in state.spike_cooldown:
                out.append(signal_factory.make_spike_signal(
                    symbol, candle, spike, SignalType.SPIKE_BREAKOUT, strength, phase, bias))
                state.spike_cooldown[SpikeType.BREAKOUT_SHOCK] = config.spike_cooldown
        elif spike.spike_type == SpikeType.ABSORPTION:
            if (SpikeType.ABSORPTION not in state.spike_cooldown
                    and near_key_level(candle.close, state, metrics, config.absorption_near_pct)):
                out.append(signal_factory.make_spike_signal(
                    symbol, candle, spike, SignalType.ABSORPTION, Strength.MEDIUM, phase, bias))
                state.spike_cooldown[SpikeType.ABSORPTION] = config.absorption_cooldown
        elif spike.spike_type == SpikeType.WEAK_SHOCK:
            if SpikeType.WEAK_SHOCK not in state.spike_cooldown:
                out.append(signal_factory.make_fade_alert(symbol, candle, spike, phase, bias))
                state.spike_cooldown[SpikeType.WEAK_SHOCK] = config.spike_cooldown

    if state.exhaustion_candidate is not None:
        confirmed = exhaustion_reversal.confirm(candle, state.exhaustion_candidate)
        state.exhaustion_candidate = None
        if confirmed is not None:
            out.append(signal_factory.make_exhaustion_reversal(symbol, candle, confirmed, phase, bias))

    # session_prior: today-only candles — prevents cross-day lower-low detection;
    # vol baseline inside detect_candidate uses session_prior[-20:] which is fine
    # once we have enough today candles, otherwise returns None early
    candidate = exhaustion_reversal.detect_candidate(
        candle, session_prior, state.day_open,
        downtrend_candles = config.exhaustion_downtrend_candles,
        vol_ratio_min     = config.exhaustion_vol_ratio_min,
        lower_lows_needed = config.exhaustion_lower_lows,
    )
    if candidate is not None:
        state.exhaustion_candidate = candidate

    return out
