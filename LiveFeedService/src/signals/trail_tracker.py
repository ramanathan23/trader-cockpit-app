"""
TrailTracker — manages the trailing stop for an in-flight open drive trade.

Single responsibility: given a candle and session phase, decide whether to
tighten the stop, exit the trade, or do nothing.

State mutation is handled via callbacks so callers retain ownership of the
session state without this module needing to hold references to it.
"""
from __future__ import annotations

from typing import Callable

from ..domain.models import Candle, Direction, DriveState, SessionPhase, Signal
from . import signal_factory


def update_trail(
    symbol:       str,
    candle:       Candle,
    phase:        SessionPhase,
    drive:        DriveState,
    stop:         float,
    *,
    on_stop_moved: Callable[[float], None],
    on_exit:       Callable[[], None],
) -> list[Signal]:
    """
    Evaluate trailing stop logic for one completed candle.

    Parameters
    ----------
    symbol        : instrument ticker (included in emitted Signal)
    candle        : the just-completed candle
    phase         : current session phase
    drive         : the drive state that triggered the trade
    stop          : current trailing stop value
    on_stop_moved : callback(new_stop) — called when the stop tightens
    on_exit       : callback() — called when the trade is exited

    Returns a (possibly empty) list of Signal objects.
    """
    # 1. Hard session-end exit.
    if phase == SessionPhase.SESSION_END:
        on_exit()
        return [signal_factory.make_exit(symbol, candle, phase, reason="SESSION_END")]

    # 2. Structure break + compute new stop (mirrors original evaluation order).
    if drive.direction == Direction.BULLISH:
        if candle.close < stop:
            on_exit()
            return [signal_factory.make_exit(symbol, candle, phase, reason="STRUCTURE_BREAK")]
        new_stop = max(stop, candle.low)
    else:
        if candle.close > stop:
            on_exit()
            return [signal_factory.make_exit(symbol, candle, phase, reason="STRUCTURE_BREAK")]
        new_stop = min(stop, candle.high)

    # 3. Drive invalidation — price traded through day open.
    if drive.direction == Direction.BULLISH and candle.low < drive.day_open:
        on_exit()
        return [signal_factory.make_exit(symbol, candle, phase, reason="DRIVE_INVALIDATED")]
    if drive.direction == Direction.BEARISH and candle.high > drive.day_open:
        on_exit()
        return [signal_factory.make_exit(symbol, candle, phase, reason="DRIVE_INVALIDATED")]

    # 4. Tighten stop if it has moved.
    if new_stop != stop:
        on_stop_moved(new_stop)
        return [signal_factory.make_trail_update(
            symbol, candle, new_stop, phase, drive.direction,
        )]

    return []
