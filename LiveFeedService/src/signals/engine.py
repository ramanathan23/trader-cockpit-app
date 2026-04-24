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
from ..domain.signal import Signal
from ._engine_config import EngineConfig, config_from_kwargs
from ._engine_state import _SessionState
from ._confluence_filter import apply_confluence
from ._breakout_handler import evaluate_breakouts

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
        **engine_kwargs,
    ) -> None:
        self.symbol   = symbol
        self._builder = builder
        self._session = session_manager
        self._metrics = daily_metrics or {}
        self._state   = _SessionState()
        self._config  = config_from_kwargs(**engine_kwargs)

    def update_daily_metrics(self, metrics: dict) -> None:
        self._metrics = metrics

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
        today_history = [c for c in history if c.boundary.astimezone(_IST).date() == today]
        adv = self._metrics.get("adv_20_cr", 0.0)
        skip = adv < config.min_adv_cr
        if skip and not state._adv_warned:
            logger.warning("[%s] ADV %.1f < %.1f — signals skipped",
                           self.symbol, adv, config.min_adv_cr)
            state._adv_warned = True
        signals: list[Signal] = []
        if not skip:
            signals.extend(evaluate_breakouts(
                self.symbol, candle, history, today_history,
                index_bias, phase, state, config, self._metrics))
        mtf = _mtf.compute(history, config.confluence_15m, config.confluence_1h,
                           config.confluence_min_move_pct, today_date=today)
        return apply_confluence(signals, mtf)

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._state = _SessionState()
