"""
SignalEngine: per-symbol stateful signal orchestrator.

On each completed candle it:
  1. Bootstraps day_open and ORB levels from session history.
  2. Evaluates open drive conviction (DRIVE_WINDOW / EXECUTION phases).
  3. Manages trailing stop via TrailTracker (when in a drive trade).
  4. Evaluates spike patterns (all session phases).
  5. Evaluates level breakouts: ORB, VWAP, Range, 52-week, PDH/PDL, Camarilla.
  6. Returns Signal objects for publishing.

Session state is reset via reset() at the start of each trading day.
"""
from __future__ import annotations

import dataclasses as _dc
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..core.candle_builder import CandleBuilder
from ..core.session_manager import SessionManager
from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.drive_state import DriveState
from ..domain.drive_status import DriveStatus
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.spike_type import SpikeType
from ..domain.strength import Strength
from ..core import mtf_bias as _mtf
from ..signals import (
    open_drive, spike_detector, signal_factory, exhaustion_reversal,
    vwap_detector, range_breakout, level_breakout,
)
from ..signals.trail_tracker import update_trail
from ..signals.vwap_detector import VwapState

logger = logging.getLogger(__name__)

_SPIKE_COOLDOWN       = 5    # default; prefer config.settings values
_ABSORPTION_COOLDOWN  = 10
_ABSORPTION_NEAR_PCT  = 0.008


@dataclass
class _SessionState:
    """Mutable session-scoped state per symbol — reset at day start."""
    day_open:             Optional[float]      = None
    orb_high:             Optional[float]      = None
    orb_low:              Optional[float]      = None
    drive:                Optional[DriveState]  = None
    drive_signalled:      bool                 = False
    trailing_stop:        Optional[float]      = None
    in_trade:             bool                 = False
    mid_session_start:    bool                 = False
    exhaustion_candidate: Optional[exhaustion_reversal.ExhaustionCandidate] = None
    spike_cooldown:       dict                 = field(default_factory=dict)

    # ── NEW: VWAP accumulator ─────────────────────────────────────────────────
    vwap:                 VwapState            = field(default_factory=VwapState)

    # ── NEW: once-per-session flags ───────────────────────────────────────────
    orb_signalled:        bool                 = False
    week52_signalled:     bool                 = False
    range_signalled_at:   Optional[str]        = None   # ISO boundary of last range signal


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
        spike_window:          int   = 20,
        spike_cooldown:        int   = _SPIKE_COOLDOWN,
        absorption_cooldown:   int   = _ABSORPTION_COOLDOWN,
        absorption_near_pct:   float = _ABSORPTION_NEAR_PCT,
        exhaustion_downtrend_candles: int   = 4,
        exhaustion_vol_ratio_min:    float = 6.0,
        exhaustion_lower_lows:       int   = 3,
        range_lookback:        int   = 5,
        range_vol_ratio:       float = 1.5,
        range_max_pct:         float = 0.02,
        vwap_hysteresis_min:   int   = 2,
        min_adv_cr:            float = 5.0,
        confluence_15m:        int   = 3,
        confluence_1h:         int   = 12,
        daily_metrics:         Optional[dict] = None,
    ) -> None:
        self.symbol        = symbol
        self._builder      = builder
        self._session      = session_manager
        self._dc           = drive_candles
        self._mbr          = min_body_ratio
        self._ct           = confirmed_thresh
        self._wt           = weak_thresh
        self._sw           = spike_window
        self._spike_cooldown      = spike_cooldown
        self._absorption_cooldown = absorption_cooldown
        self._absorption_near_pct = absorption_near_pct
        self._exhaust_dt    = exhaustion_downtrend_candles
        self._exhaust_vr    = exhaustion_vol_ratio_min
        self._exhaust_ll    = exhaustion_lower_lows
        self._range_lb      = range_lookback
        self._range_vr      = range_vol_ratio
        self._range_max     = range_max_pct
        self._vwap_hyst     = vwap_hysteresis_min
        self._min_adv_cr    = min_adv_cr
        self._conf_15m      = confluence_15m
        self._conf_1h       = confluence_1h
        self._metrics       = daily_metrics or {}
        self._state         = _SessionState()

    # ── Public interface ───────────────────────────────────────────────────────

    def update_daily_metrics(self, metrics: dict) -> None:
        """Replace daily metrics (e.g. if reloaded at session start)."""
        self._metrics = metrics

    def current_vwap(self) -> float | None:
        """Current session VWAP built from completed intraday candles."""
        return self._state.vwap.vwap

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

        # ── ADV floor: skip breakout/spike signals for illiquid stocks ────────
        adv = self._metrics.get("adv_20_cr", 0.0)
        skip_non_drive = adv < self._min_adv_cr

        signals: list[Signal] = []

        if (phase in (SessionPhase.DRIVE_WINDOW, SessionPhase.EXECUTION)
                and not state.mid_session_start):
            signals.extend(self._evaluate_drive(candle, history, index_bias, phase))

        if state.in_trade and state.trailing_stop is not None:
            signals.extend(self._run_trail(candle, phase))

        if not skip_non_drive:
            signals.extend(self._evaluate_spike(candle, history, index_bias, phase))
            signals.extend(self._evaluate_breakouts(candle, history, index_bias, phase))

        # VWAP state is updated unconditionally (needed as accurate accumulator).
        state.vwap = vwap_detector.update(state.vwap, candle)

        # Apply 15-min / 1-hr confluence filter to all emitted directional signals.
        mtf = _mtf.compute(history, self._conf_15m, self._conf_1h)
        return self._apply_confluence(signals, mtf)

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._state = _SessionState()

    # ── Multi-timeframe confluence filter ──────────────────────────────────────

    # Signal types exempt from confluence (session-management or counter-directional).
    # ABSORPTION is intentionally NOT exempt — MTF confirmation required for tradable signals.
    # Camarilla reversals are counter-trend by design; blocking on 15-min bias would
    # suppress H3/L3 reversals almost every time.  Exempt all Camarilla types.
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

    def _apply_confluence(
        self,
        signals: list[Signal],
        mtf:     _mtf.MTFBias,
    ) -> list[Signal]:
        """
        Filter and re-grade signals based on 15-min and 1-hr bias.
        Also stamps bias_15m / bias_1h onto every emitted signal for display.

        Rules (per signal direction):
          15-min OPPOSING → drop signal entirely.
          15-min ALIGNED, 1-hr ALIGNED → upgrade strength (MEDIUM→HIGH, LOW→MEDIUM).
          15-min ALIGNED, 1-hr OPPOSING → downgrade strength (HIGH→MEDIUM, MEDIUM→LOW; LOW dropped).
          15-min NEUTRAL → pass through unchanged.
        """

        out: list[Signal] = []
        for sig in signals:
            if sig.signal_type in self._CONFLUENCE_EXEMPT or sig.direction == Direction.NEUTRAL:
                # Still stamp the bias for display, but skip filter logic.
                out.append(_dc.replace(sig, bias_15m=mtf.bias_15m, bias_1h=mtf.bias_1h))
                continue

            dir15 = mtf.bias_15m
            dir1h  = mtf.bias_1h

            # 15-min opposing → block.
            if dir15 != Direction.NEUTRAL and dir15 != sig.direction:
                logger.debug("[CONFLUENCE-BLOCK] %s %s: 15m=%s",
                             sig.symbol, sig.signal_type.value, dir15.value)
                continue

            # Strength adjustment from 1-hr.
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
                new_strength = (
                    Strength.MEDIUM if sig.strength == Strength.HIGH else Strength.LOW
                )
            else:
                new_strength = sig.strength

            # Score boost for MTF alignment: +0.5 for 15m aligned, +1.0 for 1h aligned.
            mtf_boost = (0.5 if dir15 == sig.direction else 0.0) + (1.0 if dir1h == sig.direction else 0.0)

            out.append(_dc.replace(sig, strength=new_strength, bias_15m=dir15, bias_1h=dir1h,
                                   score=round(sig.score + mtf_boost, 2)))

        return out

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

    def _near_key_level(self, price: float, state: _SessionState) -> bool:
        """
        Return True if *price* is within _ABSORPTION_NEAR_PCT of any key structural level:
        PDH, PDL, ORB high/low, or current VWAP.

        Absorption without a nearby level is too common to be actionable.
        """
        levels: list[float] = []
        if self._metrics.get("prev_day_high"):
            levels.append(self._metrics["prev_day_high"])
        if self._metrics.get("prev_day_low"):
            levels.append(self._metrics["prev_day_low"])
        if state.orb_high:
            levels.append(state.orb_high)
        if state.orb_low:
            levels.append(state.orb_low)
        vwap = state.vwap.vwap
        if vwap:
            levels.append(vwap)
        return any(abs(price - lvl) / lvl <= self._absorption_near_pct for lvl in levels)

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

        for k in list(state.spike_cooldown):
            state.spike_cooldown[k] -= 1
            if state.spike_cooldown[k] <= 0:
                del state.spike_cooldown[k]

        spike = spike_detector.evaluate(
            candle, prior,
            vol_spike_ratio = vol_thresh,
            price_shock_pct = price_thresh,
        )
        if spike is not None:
            index_aligned = bias.majority() in (spike.direction, Direction.NEUTRAL)
            strength      = Strength.HIGH if index_aligned else Strength.MEDIUM

            if spike.spike_type == SpikeType.BREAKOUT_SHOCK:
                if SpikeType.BREAKOUT_SHOCK not in state.spike_cooldown:
                    out.append(signal_factory.make_spike_signal(
                        self.symbol, candle, spike, SignalType.SPIKE_BREAKOUT, strength, phase, bias
                    ))
                    state.spike_cooldown[SpikeType.BREAKOUT_SHOCK] = self._spike_cooldown
            elif spike.spike_type == SpikeType.ABSORPTION:
                if (SpikeType.ABSORPTION not in state.spike_cooldown
                        and self._near_key_level(candle.close, state)):
                    out.append(signal_factory.make_spike_signal(
                        self.symbol, candle, spike, SignalType.ABSORPTION, Strength.MEDIUM, phase, bias
                    ))
                    state.spike_cooldown[SpikeType.ABSORPTION] = self._absorption_cooldown
            elif spike.spike_type == SpikeType.WEAK_SHOCK:
                if SpikeType.WEAK_SHOCK not in state.spike_cooldown:
                    out.append(signal_factory.make_fade_alert(
                        self.symbol, candle, spike, phase, bias
                    ))
                    state.spike_cooldown[SpikeType.WEAK_SHOCK] = self._spike_cooldown

        if state.exhaustion_candidate is not None:
            confirmed = exhaustion_reversal.confirm(candle, state.exhaustion_candidate)
            state.exhaustion_candidate = None
            if confirmed is not None:
                out.append(signal_factory.make_exhaustion_reversal(
                    self.symbol, candle, confirmed, phase, bias
                ))

        candidate = exhaustion_reversal.detect_candidate(
            candle, prior, state.day_open,
            downtrend_candles=self._exhaust_dt,
            vol_ratio_min=self._exhaust_vr,
            lower_lows_needed=self._exhaust_ll,
        )
        if candidate is not None:
            state.exhaustion_candidate = candidate

        return out

    # ── Level & pattern breakouts ──────────────────────────────────────────────

    def _evaluate_breakouts(
        self,
        candle:  Candle,
        history: list[Candle],
        bias:    IndexBias,
        phase:   SessionPhase,
    ) -> list[Signal]:
        state   = self._state
        out:    list[Signal] = []
        prior   = history[:-1] if history and history[-1].boundary == candle.boundary else history
        m       = self._metrics

        # Helper: median volume ratio for the candle vs prior window.
        def _vol_ratio(window: int = 20) -> float:
            w = prior[-window:] if len(prior) >= window else prior
            vols = [c.volume for c in w if c.volume > 0]
            if not vols:
                return 0.0
            med = statistics.median(vols)
            return round(candle.volume / med, 2) if med else 0.0

        # ── ORB ──────────────────────────────────────────────────────────────
        if (state.orb_high is not None
                and state.orb_low is not None
                and not state.orb_signalled):
            sig = level_breakout.detect_orb(candle, state.orb_high, state.orb_low, prior)
            if sig is not None:
                state.orb_signalled = True
                out.append(signal_factory.make_orb_signal(
                    self.symbol, candle, sig,
                    state.orb_high, state.orb_low,
                    phase, bias, vol_ratio=_vol_ratio(),
                ))

        # ── 52-week ──────────────────────────────────────────────────────────
        w52_h = m.get("week52_high")
        w52_l = m.get("week52_low")
        if w52_h and w52_l and not state.week52_signalled:
            sig = level_breakout.detect_week52(candle, w52_h, w52_l, prior)
            if sig is not None:
                state.week52_signalled = True
                out.append(signal_factory.make_week52_signal(
                    self.symbol, candle, sig,
                    w52_h if sig == SignalType.WEEK52_BREAKOUT else w52_l,
                    _vol_ratio(), phase, bias,
                ))

        # ── PDH / PDL ────────────────────────────────────────────────────────
        pdh = m.get("prev_day_high")
        pdl = m.get("prev_day_low")
        if pdh and pdl:
            sig = level_breakout.detect_pdh_pdl(candle, pdh, pdl, prior)
            if sig is not None:
                out.append(signal_factory.make_pdh_pdl_signal(
                    self.symbol, candle, sig,
                    pdh if sig == SignalType.PDH_BREAKOUT else pdl,
                    _vol_ratio(), phase, bias,
                ))

        # ── Camarilla ────────────────────────────────────────────────────────
        pdc = m.get("prev_day_close")
        if pdh and pdl and pdc:
            levels = level_breakout.compute_camarilla(pdh, pdl, pdc)
            for cam_sig in level_breakout.detect_camarilla(candle, levels, None, prior):
                out.append(signal_factory.make_camarilla_signal(
                    self.symbol, candle, cam_sig.signal_type, cam_sig.level,
                    _vol_ratio(), phase, bias,
                ))

        # ── VWAP cross ───────────────────────────────────────────────────────
        vwap_state_before = state.vwap   # capture before update (update happens in on_candle)
        sig = vwap_detector.detect_cross(candle, vwap_state_before, prior,
                                          hysteresis_min=self._vwap_hyst)
        if sig is not None:
            vwap_val = vwap_state_before.vwap or candle.close
            out.append(signal_factory.make_vwap_signal(
                self.symbol, candle, sig, vwap_val, _vol_ratio(), phase, bias,
            ))
            # Update signalled side so we don't re-fire until price crosses back.
            new_side = 1 if sig == SignalType.VWAP_BREAKOUT else -1
            state.vwap = VwapState(
                cum_tp_vol = state.vwap.cum_tp_vol,
                cum_vol    = state.vwap.cum_vol,
                last_side  = state.vwap.last_side,
                side_count = state.vwap.side_count,
                signalled  = new_side,
            )

        # ── 5-candle range breakout ──────────────────────────────────────────
        boundary = candle.boundary
        if state.range_signalled_at != boundary:
            sig = range_breakout.detect(candle, prior,
                                       lookback=self._range_lb,
                                       max_range_pct=self._range_max,
                                       min_vol_ratio=self._range_vr)
            if sig is not None:
                state.range_signalled_at = boundary
                rect = prior[-self._range_lb:] if len(prior) >= self._range_lb else prior
                r_high = max(c.high for c in rect) if rect else candle.high
                r_low  = min(c.low  for c in rect) if rect else candle.low
                out.append(signal_factory.make_range_signal(
                    self.symbol, candle, sig, r_high, r_low, _vol_ratio(), phase, bias,
                ))

        return out
