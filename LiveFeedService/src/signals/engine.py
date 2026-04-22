"""
SignalEngine: per-symbol stateful signal orchestrator.
Session state resets each trading day via reset().
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

_IST = ZoneInfo("Asia/Kolkata")

from ..core.candle_builder import CandleBuilder
from ..core.session_manager import SessionManager
from ..core import mtf_bias as _mtf
from ..domain.candle import Candle
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from . import vwap_detector
from ._engine_config import EngineConfig
from ._engine_state import _SessionState
from ._confluence_filter import apply_confluence
from ._drive_handler import evaluate_drive, run_trail, _bootstrap_day, _bootstrap_orb
from ._breakout_handler import evaluate_breakouts
from .gap_detector import evaluate_gap

logger = logging.getLogger(__name__)


class SignalEngine:
    """Per-symbol signal engine — one instance per subscribed instrument."""

    def __init__(
        self,
        symbol:          str,
        builder:         CandleBuilder,
        session_manager: SessionManager,
        *,
        daily_metrics: Optional[dict] = None,
        **engine_kwargs,  # see EngineConfig for all available params
    ) -> None:
        self.symbol   = symbol
        self._builder = builder
        self._session = session_manager
        self._metrics = daily_metrics or {}
        self._state   = _SessionState()
        self._config  = EngineConfig(**engine_kwargs)

    def update_daily_metrics(self, metrics: dict) -> None:
        """Replace daily metrics (e.g. if reloaded at session start)."""
        self._metrics = metrics

    def current_vwap(self) -> float | None:
        return self._state.vwap.vwap

    def on_candle(
        self, candle: Candle, index_bias: IndexBias, at: datetime | None = None,
    ) -> list[Signal]:
        """Process one completed candle. Returns emitted signals."""
        phase   = self._session.current_phase(at)
        state   = self._state
        history = self._builder.get_history()
        config  = self._config
        _at     = at if at is not None else datetime.now(tz=_IST)
        today   = _at.astimezone(_IST).date()
        _bootstrap_day(candle, phase, state, self._builder, self.symbol)
        _bootstrap_orb(history, state, config.drive_candles, self.symbol, today)
        today_history = [c for c in history if c.boundary.astimezone(_IST).date() == today]
        adv = self._metrics.get("adv_20_cr", 0.0)
        skip_non_drive = adv < config.min_adv_cr
        if skip_non_drive and not state._adv_warned:
            logger.warning("[%s] ADV %.1f < %.1f — breakout/spike signals skipped",
                           self.symbol, adv, config.min_adv_cr)
            state._adv_warned = True
        signals: list[Signal] = []
        # Intraday gap: candle.open vs prev session candle.close — exempt from confluence
        signals.extend(evaluate_gap(self.symbol, candle, phase, state, config, today_history))
        if (phase in (SessionPhase.DRIVE_WINDOW, SessionPhase.EXECUTION)
                and not state.mid_session_start):
            # Drive uses today-only candles — seeded yesterday candles must not bleed in
            signals.extend(evaluate_drive(
                self.symbol, candle, today_history, index_bias, phase, state, config))
        if state.in_trade and state.trailing_stop is not None:
            signals.extend(run_trail(self.symbol, candle, phase, state))
        if not skip_non_drive:
            # Full history for vol baseline; today_history for intraday pattern checks
            signals.extend(evaluate_breakouts(
                self.symbol, candle, history, today_history, index_bias, phase, state, config, self._metrics))
        state.vwap = vwap_detector.update(state.vwap, candle)
        mtf = _mtf.compute(history, config.confluence_15m, config.confluence_1h,
                           config.confluence_min_move_pct, today_date=today)
        return apply_confluence(signals, mtf)

    def _apply_confluence(self, signals: list[Signal], mtf) -> list[Signal]:
        """Backward-compat shim — delegates to _confluence_filter.apply_confluence."""
        return apply_confluence(signals, mtf)

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._state = _SessionState()
