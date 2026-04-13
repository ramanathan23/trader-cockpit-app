"""
SignalEngine: per-symbol stateful signal orchestrator.

On each completed candle it:
  1. Bootstraps day_open and ORB levels from session history.
  2. Evaluates open drive conviction (DRIVE_WINDOW / EXECUTION phases).
  3. Manages trailing stop via TrailTracker (when in a drive trade).
  4. Evaluates spike patterns (all session phases).
  5. Returns Signal objects for publishing.

Session state is reset via reset() at the start of each trading day.
Drive evaluation, trail management and signal construction each live
in dedicated modules — this class orchestrates but does not implement them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..core.candle_builder import CandleBuilder
from ..core.session_manager import SessionManager
from ..domain.models import (
    Candle, Direction, DriveState, DriveStatus,
    IndexBias, Signal, SignalType, SessionPhase, SpikeType, Strength,
)
from ..signals import open_drive, spike_detector, signal_factory, exhaustion_reversal
from ..signals.trail_tracker import update_trail

logger = logging.getLogger(__name__)


@dataclass
class _SessionState:
    """Mutable session-scoped state per symbol — reset at day start."""
    day_open:             Optional[float]     = None
    orb_high:             Optional[float]     = None
    orb_low:              Optional[float]     = None
    drive:                Optional[DriveState] = None
    drive_signalled:      bool                = False
    trailing_stop:        Optional[float]     = None
    in_trade:             bool                = False
    mid_session_start:    bool                = False
    exhaustion_candidate: Optional[exhaustion_reversal.ExhaustionCandidate] = None


class SignalEngine:
    """Per-symbol signal engine — one instance per subscribed instrument."""

    def __init__(
        self,
        symbol:           str,
        builder:          CandleBuilder,
        session_manager:  SessionManager,
        *,
        drive_candles:    int   = 5,
        min_body_ratio:   float = 0.6,
        confirmed_thresh: float = 0.70,
        weak_thresh:      float = 0.50,
        spike_window:     int   = 20,
    ) -> None:
        self.symbol         = symbol
        self._builder       = builder
        self._session       = session_manager
        self._dc            = drive_candles
        self._mbr           = min_body_ratio
        self._ct            = confirmed_thresh
        self._wt            = weak_thresh
        self._sw            = spike_window
        self._state         = _SessionState()

    # ── Public interface ───────────────────────────────────────────────────────

    def on_candle(
        self,
        candle:     Candle,
        index_bias: IndexBias,
        at:         datetime | None = None,
    ) -> list[Signal]:
        """Called once per completed 3-min candle. Returns emitted signals."""
        phase   = self._session.current_phase(at)
        state   = self._state
        history = self._builder.get_history()

        self._bootstrap_day(candle, phase, state)
        self._bootstrap_orb(history, state)

        signals: list[Signal] = []

        if (phase in (SessionPhase.DRIVE_WINDOW, SessionPhase.EXECUTION)
                and not state.mid_session_start):
            signals.extend(self._evaluate_drive(candle, history, index_bias, phase))

        if state.in_trade and state.trailing_stop is not None:
            signals.extend(self._run_trail(candle, phase))

        signals.extend(self._evaluate_spike(candle, history, index_bias, phase))
        return signals

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._state = _SessionState()

    # ── Session bootstrapping ──────────────────────────────────────────────────

    def _bootstrap_day(self, candle: Candle, phase: SessionPhase, state: _SessionState) -> None:
        if state.day_open is not None:
            return
        state.day_open = candle.open
        state.mid_session_start = phase not in (
            SessionPhase.PRE_SIGNAL, SessionPhase.DRIVE_WINDOW
        )
        if state.mid_session_start:
            logger.info("[%s] Mid-session start (%s) — open drive disabled",
                        self.symbol, phase.value)

    def _bootstrap_orb(self, history: list[Candle], state: _SessionState) -> None:
        if len(history) == self._dc and state.orb_high is None:
            state.orb_high = max(c.high for c in history)
            state.orb_low  = min(c.low  for c in history)

    # ── Drive evaluation ───────────────────────────────────────────────────────

    def _evaluate_drive(
        self,
        candle:  Candle,
        history: list[Candle],
        bias:    IndexBias,
        phase:   SessionPhase,
    ) -> list[Signal]:
        state = self._state
        if state.day_open is None:
            return []

        drive = open_drive.evaluate(
            history, state.day_open,
            drive_candles    = self._dc,
            min_body_ratio   = self._mbr,
            confirmed_thresh = self._ct,
            weak_thresh      = self._wt,
        )
        state.drive = drive

        if drive.status == DriveStatus.FAILED:
            return [signal_factory.make_drive_failed(self.symbol, candle, phase)]

        if drive.status in (DriveStatus.CONFIRMED, DriveStatus.WEAK) and not state.drive_signalled:
            index_aligned = bias.majority() in (drive.direction, Direction.NEUTRAL)
            score    = signal_factory.composite_score(drive, candle, state.orb_high, state.orb_low, bias)
            strength = (Strength.HIGH if drive.status == DriveStatus.CONFIRMED and index_aligned
                        else Strength.MEDIUM)
            state.drive_signalled = True
            state.in_trade        = True
            state.trailing_stop   = (candle.low if drive.direction == Direction.BULLISH
                                     else candle.high)
            return [signal_factory.make_drive_entry(
                self.symbol, candle, drive, score, strength, phase, bias
            )]

        return []

    # ── Trailing stop ──────────────────────────────────────────────────────────

    def _run_trail(self, candle: Candle, phase: SessionPhase) -> list[Signal]:
        state = self._state
        if state.drive is None or state.trailing_stop is None:
            return []

        def on_stop_moved(new_stop: float) -> None:
            state.trailing_stop = new_stop

        def on_exit() -> None:
            state.in_trade      = False
            state.trailing_stop = None

        return update_trail(
            self.symbol, candle, phase, state.drive, state.trailing_stop,
            on_stop_moved=on_stop_moved, on_exit=on_exit,
        )

    # ── Spike detection ────────────────────────────────────────────────────────

    def _evaluate_spike(
        self,
        candle:  Candle,
        history: list[Candle],
        bias:    IndexBias,
        phase:   SessionPhase,
    ) -> list[Signal]:
        prior        = history[:-1] if history and history[-1].boundary == candle.boundary else history
        vol_thresh   = self._session.spike_vol_threshold(phase)
        price_thresh = self._session.spike_price_threshold(phase)

        out:   list[Signal] = []
        state: _SessionState = self._state

        # ── Standard single-candle spike signals ──────────────────────────────
        spike = spike_detector.evaluate(
            candle, prior,
            vol_spike_ratio = vol_thresh,
            price_shock_pct = price_thresh,
        )
        if spike is not None:
            index_aligned = bias.majority() in (spike.direction, Direction.NEUTRAL)
            strength      = Strength.HIGH if index_aligned else Strength.MEDIUM

            if spike.spike_type == SpikeType.BREAKOUT_SHOCK:
                out.append(signal_factory.make_spike_signal(
                    self.symbol, candle, spike, SignalType.SPIKE_BREAKOUT, strength, phase, bias
                ))
            elif spike.spike_type == SpikeType.ABSORPTION:
                out.append(signal_factory.make_spike_signal(
                    self.symbol, candle, spike, SignalType.ABSORPTION, Strength.MEDIUM, phase, bias
                ))

        # ── Exhaustion reversal (multi-candle sequence) ────────────────────────
        # Step 1: if holding a climax candidate, try to confirm on this candle.
        # Runs unconditionally — the confirmation candle is NOT a spike.
        if state.exhaustion_candidate is not None:
            confirmed = exhaustion_reversal.confirm(candle, state.exhaustion_candidate)
            state.exhaustion_candidate = None   # always clear after one attempt
            if confirmed is not None:
                out.append(signal_factory.make_exhaustion_reversal(
                    self.symbol, candle, confirmed, phase, bias
                ))

        # Step 2: check if this candle is a new climax candidate.
        candidate = exhaustion_reversal.detect_candidate(
            candle, prior, state.day_open,
        )
        if candidate is not None:
            state.exhaustion_candidate = candidate

        return out
