from __future__ import annotations

import dataclasses as _dc
import logging

from ..core import mtf_bias as _mtf
from ..domain.direction import Direction
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength

logger = logging.getLogger(__name__)

_CONFLUENCE_EXEMPT = frozenset({
    SignalType.TRAIL_UPDATE,
    SignalType.EXIT,
    SignalType.DRIVE_FAILED,
    SignalType.FADE_ALERT,
    SignalType.CAM_H3_REVERSAL,
    SignalType.CAM_H4_BREAKOUT,
    SignalType.CAM_L3_REVERSAL,
    SignalType.CAM_L4_BREAKDOWN,
})


def apply_confluence(signals: list[Signal], mtf: _mtf.MTFBias) -> list[Signal]:
    """
    Filter and re-grade signals based on 15-min and 1-hr bias.
    Stamps bias_15m / bias_1h onto every emitted signal for display.

    15-min OPPOSING     → drop signal.
    15-min ALIGNED, 1h ALIGNED   → upgrade strength.
    15-min ALIGNED, 1h OPPOSING  → downgrade strength (LOW dropped).
    15-min NEUTRAL      → pass through unchanged.
    """
    out: list[Signal] = []
    for sig in signals:
        if sig.signal_type in _CONFLUENCE_EXEMPT or sig.direction == Direction.NEUTRAL:
            out.append(_dc.replace(sig, bias_15m=mtf.bias_15m, bias_1h=mtf.bias_1h))
            continue

        dir15 = mtf.bias_15m
        dir1h  = mtf.bias_1h

        if dir15 != Direction.NEUTRAL and dir15 != sig.direction:
            logger.debug("[CONFLUENCE-BLOCK] %s %s: 15m=%s",
                         sig.symbol, sig.signal_type.value, dir15.value)
            continue

        if dir1h == sig.direction:
            new_strength = (
                Strength.HIGH   if sig.strength == Strength.MEDIUM else
                Strength.MEDIUM if sig.strength == Strength.LOW    else
                sig.strength
            )
        elif dir1h != Direction.NEUTRAL and dir1h != sig.direction:
            if sig.strength == Strength.LOW:
                logger.debug("[CONFLUENCE-DROP-1H] %s %s: 1h=%s",
                             sig.symbol, sig.signal_type.value, dir1h.value)
                continue
            new_strength = Strength.MEDIUM if sig.strength == Strength.HIGH else Strength.LOW
        else:
            new_strength = sig.strength

        mtf_boost = (0.5 if dir15 == sig.direction else 0.0) + (1.0 if dir1h == sig.direction else 0.0)
        out.append(_dc.replace(sig, strength=new_strength, bias_15m=dir15, bias_1h=dir1h,
                               score=round(sig.score + mtf_boost, 2)))
    return out
