from __future__ import annotations

import statistics

from ..domain.candle import Candle
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from . import range_breakout
from .level_breakout import compute_camarilla, detect_camarilla
from .signal_factory import make_camarilla_signal, make_range_signal
from ._engine_config import EngineConfig
from ._engine_state import _SessionState


def _vol_ratio(candle: Candle, prior: list[Candle], window: int = 20) -> float:
    w    = prior[-window:] if len(prior) >= window else prior
    vols = [c.volume for c in w if c.volume > 0]
    med  = statistics.median(vols) if vols else 0.0
    return round(candle.volume / med, 2) if med else 0.0


def evaluate_breakouts(
    symbol:          str,
    candle:          Candle,
    history:         list[Candle],  # full history — for vol baseline
    session_history: list[Candle],  # today-only — for range consolidation pattern
    bias:            IndexBias,
    phase:           SessionPhase,
    state:           _SessionState,
    config:          EngineConfig,
    metrics:         dict,
) -> list[Signal]:
    out   = []
    prior = history[:-1] if history and history[-1].boundary == candle.boundary else history
    session_prior = (
        session_history[:-1]
        if session_history and session_history[-1].boundary == candle.boundary
        else session_history
    )
    vr = lambda: _vol_ratio(candle, prior)

    # ── Rectangle breakout ────────────────────────────────────────────────────
    boundary = candle.boundary
    if state.range_signalled_at != boundary:
        sig = range_breakout.detect(candle, session_prior, lookback=config.range_lookback,
                                    max_range_pct=config.range_max_pct,
                                    min_vol_ratio=config.range_vol_ratio)
        if sig is not None:
            state.range_signalled_at = boundary
            rect   = session_prior[-config.range_lookback:] if len(session_prior) >= config.range_lookback else session_prior
            r_high = max(c.high for c in rect) if rect else candle.high
            r_low  = min(c.low  for c in rect) if rect else candle.low
            out.append(make_range_signal(symbol, candle, sig, r_high, r_low, vr(), phase, bias))

    # ── Camarilla (narrow = breakout, wide = pin-bar reversal) ───────────────
    pdc = metrics.get("prev_day_close")
    pdh = metrics.get("prev_day_high")
    pdl = metrics.get("prev_day_low")
    if pdh and pdl and pdc:
        levels     = compute_camarilla(pdh, pdl, pdc)
        prev_c     = prior[-1] if prior else None
        # Per-stock threshold: use symbol's own 60-day median Camarilla range; fall back to config
        cam_thresh = metrics.get("cam_median_range_pct") or config.cam_narrow_range_pct
        for cam in detect_camarilla(candle, levels, prev_c, prior, pdc,
                                    narrow_range_pct=cam_thresh):
            st = cam.signal_type
            if st == SignalType.CAM_H4_BREAKOUT:
                if state.cam_h4_signalled:
                    continue
                state.cam_h4_signalled = True
            elif st == SignalType.CAM_L4_BREAKDOWN:
                if state.cam_l4_signalled:
                    continue
                state.cam_l4_signalled = True
            elif st == SignalType.CAM_H4_REVERSAL:
                if state.cam_h4r_signalled:
                    continue
                state.cam_h4r_signalled = True
            elif st == SignalType.CAM_L4_REVERSAL:
                if state.cam_l4r_signalled:
                    continue
                state.cam_l4r_signalled = True
            out.append(make_camarilla_signal(symbol, candle, st, cam.level, vr(), phase, bias))

    return out
