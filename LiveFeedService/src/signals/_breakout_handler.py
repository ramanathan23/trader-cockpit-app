from __future__ import annotations

import dataclasses
import statistics

from ..domain.candle import Candle
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from . import range_breakout
from .level_breakout import (
    detect_orb, detect_week52, detect_pdh_pdl, compute_camarilla, detect_camarilla,
)
from .vwap_detector import detect_cross
from .signal_factory import (
    make_orb_signal, make_week52_signal, make_pdh_pdl_signal,
    make_camarilla_signal, make_vwap_signal, make_range_signal,
)
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
    m     = metrics
    vr    = lambda: _vol_ratio(candle, prior)

    if state.orb_high is not None and state.orb_low is not None and not state.orb_signalled:
        sig = detect_orb(candle, state.orb_high, state.orb_low, prior)
        if sig is not None:
            state.orb_signalled = True
            out.append(make_orb_signal(symbol, candle, sig, state.orb_high, state.orb_low,
                                       phase, bias, vol_ratio=vr()))

    w52_h, w52_l = m.get("week52_high"), m.get("week52_low")
    if w52_h and w52_l and not state.week52_signalled:
        sig = detect_week52(candle, w52_h, w52_l, prior)
        if sig is not None:
            state.week52_signalled = True
            out.append(make_week52_signal(
                symbol, candle, sig, w52_h if sig == SignalType.WEEK52_BREAKOUT else w52_l,
                vr(), phase, bias))

    pdh, pdl = m.get("prev_day_high"), m.get("prev_day_low")
    if pdh and pdl:
        sig = detect_pdh_pdl(candle, pdh, pdl, prior)
        if sig is not None:
            out.append(make_pdh_pdl_signal(
                symbol, candle, sig, pdh if sig == SignalType.PDH_BREAKOUT else pdl,
                vr(), phase, bias))

    pdc = m.get("prev_day_close")
    if pdh and pdl and pdc:
        levels  = compute_camarilla(pdh, pdl, pdc)
        prev_c  = prior[-1] if prior else None
        for cam in detect_camarilla(candle, levels, prev_c, prior):
            if cam.signal_type == SignalType.CAM_H4_BREAKOUT:
                if state.cam_h4_signalled:
                    continue
                state.cam_h4_signalled = True
            if cam.signal_type == SignalType.CAM_L4_BREAKDOWN:
                if state.cam_l4_signalled:
                    continue
                state.cam_l4_signalled = True
            out.append(make_camarilla_signal(symbol, candle, cam.signal_type, cam.level,
                                             vr(), phase, bias))

    vs  = state.vwap
    sig = detect_cross(candle, vs, prior, hysteresis_min=config.vwap_hysteresis_min)
    if sig is not None:
        out.append(make_vwap_signal(symbol, candle, sig, vs.vwap or candle.close, vr(), phase, bias))
        new_side   = 1 if sig == SignalType.VWAP_BREAKOUT else -1
        state.vwap = dataclasses.replace(vs, signalled=new_side)

    boundary = candle.boundary
    if state.range_signalled_at != boundary:
        # session_prior: today-only candles for consolidation — prevents overnight gap firing as range breakout
        sig = range_breakout.detect(candle, session_prior, lookback=config.range_lookback,
                                    max_range_pct=config.range_max_pct,
                                    min_vol_ratio=config.range_vol_ratio)
        if sig is not None:
            state.range_signalled_at = boundary
            rect   = session_prior[-config.range_lookback:] if len(session_prior) >= config.range_lookback else session_prior
            r_high = max(c.high for c in rect) if rect else candle.high
            r_low  = min(c.low  for c in rect) if rect else candle.low
            out.append(make_range_signal(symbol, candle, sig, r_high, r_low, vr(), phase, bias))

    return out
