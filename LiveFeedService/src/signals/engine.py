"""
SignalEngine: per-symbol stateful signal orchestrator.

One SignalEngine instance per subscribed instrument.  On each completed candle
it:
  1. Runs OpenDriveDetector (during DRIVE_WINDOW / EXECUTION phases).
  2. Runs SpikeDetector (all session phases).
  3. Computes a composite score.
  4. Manages trailing stop state for in-flight drive trades.
  5. Emits Signal objects for the publisher / SSE stream.

The engine is intentionally stateful (drive state, trailing stop, ORB levels)
because these must persist across candle boundaries within a session.
Callers reset() the engine at the start of each trading day.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..core.candle_builder import CandleBuilder
from ..core.session_manager import SessionManager
from ..domain.models import (
    Candle, Direction, DriveState, DriveStatus, IndexBias,
    Signal, SignalType, SessionPhase, SpikeState, SpikeType, Strength,
)
from ..signals import open_drive, spike_detector

logger = logging.getLogger(__name__)


@dataclass
class _SessionState:
    """Mutable session-scoped state per symbol."""
    day_open:           Optional[float]    = None   # set from first complete candle
    orb_high:           Optional[float]    = None   # set after drive_candles candles
    orb_low:            Optional[float]    = None
    drive:              Optional[DriveState] = None
    drive_signalled:    bool               = False   # True after entry signal emitted
    trailing_stop:      Optional[float]    = None
    in_trade:           bool               = False
    mid_session_start:  bool               = False   # True when connected after DRIVE_WINDOW


class SignalEngine:
    """
    Per-symbol signal engine.

    Parameters
    ----------
    symbol          : instrument ticker
    session_manager : shared SessionManager
    drive_candles   : number of candles for open drive evaluation
    min_body_ratio  : minimum body/range for drive conviction
    confirmed_thresh: confidence threshold for CONFIRMED drive
    weak_thresh     : confidence threshold for WEAK drive
    spike_window    : rolling window for spike baselines
    """

    def __init__(
        self,
        symbol:           str,
        builder:          CandleBuilder,
        session_manager:  SessionManager,
        *,
        drive_candles:      int   = 5,
        min_body_ratio:     float = 0.6,
        confirmed_thresh:   float = 0.70,
        weak_thresh:        float = 0.50,
        spike_window:       int   = 20,
    ) -> None:
        self.symbol          = symbol
        self._builder        = builder
        self._session        = session_manager
        self._dc             = drive_candles
        self._mbr            = min_body_ratio
        self._ct             = confirmed_thresh
        self._wt             = weak_thresh
        self._sw             = spike_window
        self._state          = _SessionState()

    # ── Public interface ───────────────────────────────────────────────────────

    def on_candle(
        self,
        candle:     Candle,
        index_bias: IndexBias,
        at:         datetime | None = None,
    ) -> list[Signal]:
        """
        Called once per completed 3-min candle.

        Returns a (possibly empty) list of Signal objects to be published.
        """
        phase  = self._session.current_phase(at)
        state  = self._state
        history = self._builder.get_history()

        # ── Bootstrap day_open from first candle ──────────────────────────────
        if state.day_open is None:
            state.day_open = candle.open
            # If we connected after the drive window, day_open is meaningless
            # for open drive purposes — mark so we skip that detector entirely.
            state.mid_session_start = phase not in (
                SessionPhase.PRE_SIGNAL, SessionPhase.DRIVE_WINDOW
            )
            if state.mid_session_start:
                logger.info(
                    "[%s] Mid-session start detected (%s) — open drive disabled",
                    self.symbol, phase.value,
                )

        # ── ORB: set after drive_candles candles ──────────────────────────────
        if len(history) == self._dc and state.orb_high is None:
            state.orb_high = max(c.high  for c in history)
            state.orb_low  = min(c.low   for c in history)

        signals: list[Signal] = []

        # ── Open Drive (DRIVE_WINDOW + EXECUTION, session-start only) ─────────
        if (phase in (SessionPhase.DRIVE_WINDOW, SessionPhase.EXECUTION)
                and not state.mid_session_start):
            drive_signals = self._evaluate_drive(candle, history, index_bias, phase)
            signals.extend(drive_signals)

        # ── Trailing stop update (when in a drive trade) ──────────────────────
        if state.in_trade and state.trailing_stop is not None:
            trail_signals = self._update_trail(candle, phase)
            signals.extend(trail_signals)

        # ── Spike detection (all phases) ──────────────────────────────────────
        spike_signals = self._evaluate_spike(candle, history, index_bias, phase)
        signals.extend(spike_signals)

        return signals

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._state = _SessionState()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _evaluate_drive(
        self,
        candle:     Candle,
        history:    list[Candle],
        bias:       IndexBias,
        phase:      SessionPhase,
    ) -> list[Signal]:
        state = self._state
        if state.day_open is None:
            return []

        drive = open_drive.evaluate(
            history,
            state.day_open,
            drive_candles    = self._dc,
            min_body_ratio   = self._mbr,
            confirmed_thresh = self._ct,
            weak_thresh      = self._wt,
        )
        state.drive = drive

        if drive.status == DriveStatus.FAILED and state.in_trade:
            return [self._make_drive_failed(candle, drive, phase)]

        if drive.status == DriveStatus.FAILED:
            return [self._make_drive_failed(candle, drive, phase)]

        if drive.status in (DriveStatus.CONFIRMED, DriveStatus.WEAK) and not state.drive_signalled:
            index_aligned = (bias.majority() == drive.direction or
                             bias.majority() == Direction.NEUTRAL)

            score = self._composite_score(drive, candle, state, bias)
            strength = Strength.HIGH if (drive.status == DriveStatus.CONFIRMED and
                                         index_aligned) else Strength.MEDIUM

            state.drive_signalled = True
            state.in_trade        = True
            state.trailing_stop   = (candle.low  if drive.direction == Direction.BULLISH
                                     else candle.high)

            return [self._make_drive_entry(candle, drive, score, strength, phase, bias)]

        return []

    def _update_trail(self, candle: Candle, phase: SessionPhase) -> list[Signal]:
        state = self._state
        drive = state.drive
        if drive is None:
            return []

        old_stop = state.trailing_stop

        # Hard session-end exit.
        if phase == SessionPhase.SESSION_END:
            state.in_trade      = False
            state.trailing_stop = None
            return [self._make_exit(candle, phase, reason="SESSION_END")]

        # Structure break exit.
        if drive.direction == Direction.BULLISH:
            if candle.close < state.trailing_stop:
                state.in_trade = False
                return [self._make_exit(candle, phase, reason="STRUCTURE_BREAK")]
            new_stop = max(state.trailing_stop, candle.low)
        else:
            if candle.close > state.trailing_stop:
                state.in_trade = False
                return [self._make_exit(candle, phase, reason="STRUCTURE_BREAK")]
            new_stop = min(state.trailing_stop, candle.high)

        # Drive invalidation exit.
        if drive.direction == Direction.BULLISH and candle.low < drive.day_open:
            state.in_trade = False
            return [self._make_exit(candle, phase, reason="DRIVE_INVALIDATED")]
        if drive.direction == Direction.BEARISH and candle.high > drive.day_open:
            state.in_trade = False
            return [self._make_exit(candle, phase, reason="DRIVE_INVALIDATED")]

        if new_stop != old_stop:
            state.trailing_stop = new_stop
            return [self._make_trail_update(candle, new_stop, phase)]

        return []

    def _evaluate_spike(
        self,
        candle:  Candle,
        history: list[Candle],
        bias:    IndexBias,
        phase:   SessionPhase,
    ) -> list[Signal]:
        prior_history = history[:-1] if history and history[-1].boundary == candle.boundary else history

        vol_thresh   = self._session.spike_vol_threshold(phase)
        price_thresh = self._session.spike_price_threshold(phase)

        spike = spike_detector.evaluate(
            candle, prior_history,
            vol_spike_ratio = vol_thresh,
            price_shock_pct = price_thresh,
        )
        if spike is None:
            return []

        index_aligned = (bias.majority() == spike.direction or
                         bias.majority() == Direction.NEUTRAL)
        strength = Strength.HIGH if index_aligned else Strength.MEDIUM

        if spike.spike_type == SpikeType.BREAKOUT_SHOCK:
            return [self._make_spike_signal(
                candle, spike, SignalType.SPIKE_BREAKOUT, strength, phase, bias
            )]

        if spike.spike_type == SpikeType.ABSORPTION:
            return [self._make_spike_signal(
                candle, spike, SignalType.ABSORPTION, Strength.MEDIUM, phase, bias
            )]

        # WEAK_SHOCK — low confidence, only emit if score warrants it.
        return []

    # ── Signal factories ───────────────────────────────────────────────────────

    def _make_drive_entry(
        self,
        candle:   Candle,
        drive:    DriveState,
        score:    float,
        strength: Strength,
        phase:    SessionPhase,
        bias:     IndexBias,
    ) -> Signal:
        rng = abs(candle.close - drive.day_open)
        if drive.direction == Direction.BULLISH:
            entry_low  = drive.day_open + rng * 0.3
            entry_high = candle.close
            t1 = drive.day_open + rng * 2
            t2 = drive.day_open + rng * 3
        else:
            entry_low  = candle.close
            entry_high = drive.day_open - rng * 0.3
            t1 = drive.day_open - rng * 2
            t2 = drive.day_open - rng * 3

        return Signal(
            symbol            = self.symbol,
            signal_type       = SignalType.OPEN_DRIVE_ENTRY,
            direction         = drive.direction,
            strength          = strength,
            score             = score,
            session_phase     = phase,
            index_bias        = bias.majority(),
            price             = candle.close,
            entry_low         = round(entry_low,  2),
            entry_high        = round(entry_high, 2),
            stop              = round(drive.day_open, 2),
            target_1          = round(t1, 2),
            target_2          = round(t2, 2),
            drive_confidence  = drive.confidence,
            message           = (
                f"Open Drive {drive.status.value} ({drive.confidence:.0%}) | "
                f"Index bias: {bias.majority().value}"
            ),
        )

    def _make_drive_failed(self, candle: Candle, drive: DriveState, phase: SessionPhase) -> Signal:
        return Signal(
            symbol        = self.symbol,
            signal_type   = SignalType.DRIVE_FAILED,
            direction     = Direction.NEUTRAL,
            strength      = Strength.LOW,
            score         = 0.0,
            session_phase = phase,
            price         = candle.close,
            message       = "Drive failed — price returned through day open. Stand down.",
        )

    def _make_trail_update(self, candle: Candle, new_stop: float, phase: SessionPhase) -> Signal:
        return Signal(
            symbol        = self.symbol,
            signal_type   = SignalType.TRAIL_UPDATE,
            direction     = self._state.drive.direction if self._state.drive else Direction.NEUTRAL,
            strength      = Strength.LOW,
            score         = 0.0,
            session_phase = phase,
            price         = candle.close,
            trail_stop    = round(new_stop, 2),
            message       = f"Trail stop moved → {new_stop:.2f}",
        )

    def _make_exit(self, candle: Candle, phase: SessionPhase, *, reason: str) -> Signal:
        return Signal(
            symbol        = self.symbol,
            signal_type   = SignalType.EXIT,
            direction     = Direction.NEUTRAL,
            strength      = Strength.LOW,
            score         = 0.0,
            session_phase = phase,
            price         = candle.close,
            message       = f"Exit — {reason}",
        )

    def _make_spike_signal(
        self,
        candle:      Candle,
        spike:       SpikeState,
        signal_type: SignalType,
        strength:    Strength,
        phase:       SessionPhase,
        bias:        IndexBias,
    ) -> Signal:
        msg_map = {
            SignalType.SPIKE_BREAKOUT: (
                f"Breakout shock | Vol {spike.volume_ratio:.1f}× | "
                f"Move {spike.price_pct_move:.1f}%"
            ),
            SignalType.ABSORPTION: (
                f"Absorption at {candle.close:.2f} | Vol {spike.volume_ratio:.1f}× | "
                "Watch for reversal"
            ),
        }
        return Signal(
            symbol        = self.symbol,
            signal_type   = signal_type,
            direction     = spike.direction,
            strength      = strength,
            score         = spike.volume_ratio * 0.5,
            session_phase = phase,
            index_bias    = bias.majority(),
            price         = candle.close,
            volume_ratio  = spike.volume_ratio,
            message       = msg_map.get(signal_type, ""),
        )

    @staticmethod
    def _composite_score(
        drive: DriveState,
        candle: Candle,
        state: _SessionState,
        bias: IndexBias,
    ) -> float:
        score = 0.0
        score += drive.confidence * 2           # 0–2: drive strength
        if bias.majority() == drive.direction:
            score += 1.0                        # +1: index aligned
        if state.orb_high and state.orb_low:    # +1: ORB breakout
            if drive.direction == Direction.BULLISH and candle.close > state.orb_high:
                score += 1.0
            elif drive.direction == Direction.BEARISH and candle.close < state.orb_low:
                score += 1.0
        return round(score, 2)
