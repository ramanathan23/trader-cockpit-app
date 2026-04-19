from __future__ import annotations

import logging

from ..core.candle_builder import CandleBuilder
from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.drive_status import DriveStatus
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.strength import Strength
from . import open_drive, signal_factory
from .trail_tracker import update_trail
from ._engine_config import EngineConfig
from ._engine_state import _SessionState

logger = logging.getLogger(__name__)


def _bootstrap_day(
    candle: Candle, phase: SessionPhase, state: _SessionState,
    builder: CandleBuilder, symbol: str,
) -> None:
    if state.day_open is not None:
        return
    tick_open = builder.session_open_price
    state.day_open = tick_open if tick_open is not None else candle.open
    state.mid_session_start = phase not in (
        SessionPhase.PRE_SIGNAL, SessionPhase.DRIVE_WINDOW
    )
    if state.mid_session_start:
        logger.info("[%s] Mid-session start (%s) — open drive disabled",
                    symbol, phase.value)


def _bootstrap_orb(
    history: list[Candle], state: _SessionState, drive_candles: int, symbol: str,
) -> None:
    if len(history) >= drive_candles and state.orb_high is None:
        first = history[:drive_candles]
        state.orb_high = max(c.high for c in first)
        state.orb_low  = min(c.low  for c in first)
        logger.info("[%s] ORB bootstrapped: high=%.2f low=%.2f (from %d candles)",
                    symbol, state.orb_high, state.orb_low, len(first))


def evaluate_drive(
    symbol: str, candle: Candle, history: list[Candle],
    bias: IndexBias, phase: SessionPhase,
    state: _SessionState, config: EngineConfig,
) -> list[Signal]:
    if state.day_open is None:
        return []

    drive = open_drive.evaluate(
        history, state.day_open,
        drive_candles    = config.drive_candles,
        min_body_ratio   = config.min_body_ratio,
        confirmed_thresh = config.confirmed_thresh,
        weak_thresh      = config.weak_thresh,
    )
    state.drive = drive

    if drive.status == DriveStatus.FAILED and not state.drive_signalled:
        state.drive_signalled = True
        return [signal_factory.make_drive_failed(symbol, candle, phase)]

    if drive.status in (DriveStatus.CONFIRMED, DriveStatus.WEAK) and not state.drive_signalled:
        index_aligned = bias.majority() in (drive.direction, Direction.NEUTRAL)
        score    = signal_factory.composite_score(drive, candle, state.orb_high, state.orb_low, bias)
        strength = (Strength.HIGH if drive.status == DriveStatus.CONFIRMED and index_aligned
                    else Strength.MEDIUM)
        state.drive_signalled = True
        state.in_trade        = True
        state.trailing_stop   = candle.low if drive.direction == Direction.BULLISH else candle.high
        return [signal_factory.make_drive_entry(symbol, candle, drive, score, strength, phase, bias)]

    return []


def run_trail(
    symbol: str, candle: Candle, phase: SessionPhase, state: _SessionState,
) -> list[Signal]:
    if state.drive is None or state.trailing_stop is None:
        return []

    def on_stop_moved(new_stop: float) -> None:
        state.trailing_stop = new_stop

    def on_exit() -> None:
        state.in_trade      = False
        state.trailing_stop = None

    return update_trail(
        symbol, candle, phase, state.drive, state.trailing_stop,
        on_stop_moved=on_stop_moved, on_exit=on_exit,
    )
