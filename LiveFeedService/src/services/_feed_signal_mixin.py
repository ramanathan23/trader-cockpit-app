from __future__ import annotations

import dataclasses
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.instrument_meta import InstrumentMeta
from ..signals.engine import SignalEngine
from ..signals._regime_detector import detect_regime

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")


class _FeedSignalMixin:
    async def update_token(self, new_token: str) -> None:
        """Persist a new Dhan access token and reconnect all WebSocket feeds."""
        await self._token_store.set(new_token)
        if self._sub_mgr:
            await self._sub_mgr.reconnect_all()

    def _check_session_reset(self) -> None:
        today = datetime.now(tz=_IST).date()
        if self._session_date is None:
            self._session_date = today
            return
        if self._session_date == today:
            return
        self._session_date = today
        self._index_bias   = IndexBias()
        if self._tick_router:
            self._tick_router.reset_session()
        for engine in self._engines.values():
            engine.reset()
        logger.info("Session reset for %s", today)

    async def _on_candle(self, meta: InstrumentMeta, candle: Candle) -> None:
        self._candles_completed += 1
        await self._writer.add(candle)
        if meta.is_index_future and meta.underlying:
            self._update_index_bias(meta.underlying, candle)
        if not meta.is_index_future:
            engine   = self._get_or_create_engine(meta)
            metrics  = self._metrics_service.get_daily(meta.symbol) or {}
            regime = await self._maybe_publish_regime(meta, engine)
            wl_bias  = metrics.get("weekly_bias", "NEUTRAL")
            on_wl    = metrics.get("is_watchlist", False)
            for signal in engine.on_candle(candle, self._index_bias):
                conflict = (
                    on_wl
                    and signal.direction != Direction.NEUTRAL
                    and (
                        (wl_bias == "BULLISH" and signal.direction == Direction.BEARISH)
                        or (wl_bias == "BEARISH" and signal.direction == Direction.BULLISH)
                    )
                )
                if conflict:
                    signal = dataclasses.replace(signal, watchlist_conflict=True)
                if regime:
                    signal = dataclasses.replace(signal, regime=regime.regime.value)
                if metrics.get("iss_score") is not None:
                    signal = dataclasses.replace(signal, iss_score=float(metrics["iss_score"]))
                self._signals_emitted += 1
                await self._publisher.publish(signal)
                logger.info("[SIGNAL] %s %s %s score=%.2f%s",
                            signal.symbol, signal.signal_type.value,
                            signal.direction.value, signal.score,
                            " [WL-CONFLICT]" if conflict else "")

    def _update_index_bias(self, underlying: str, candle: Candle) -> None:
        direction = candle.direction
        if underlying == "NIFTY":
            self._index_bias.nifty     = direction
        elif underlying == "BANKNIFTY":
            self._index_bias.banknifty = direction
        elif underlying == "SENSEX":
            self._index_bias.sensex    = direction

    def _get_or_create_engine(self, meta: InstrumentMeta) -> SignalEngine:
        if meta.symbol not in self._engines:
            s       = self._settings
            metrics = self._metrics_service.get_daily(meta.symbol) or {}
            self._engines[meta.symbol] = SignalEngine(
                symbol                  = meta.symbol,
                builder                 = self._tick_router.get_builder(meta.dhan_security_id),
                session_manager         = self._session_mgr,
                range_lookback          = s.range_lookback,
                range_vol_ratio         = s.range_vol_ratio,
                range_max_pct           = s.range_max_pct,
                min_adv_cr              = s.min_adv_cr,
                confluence_15m          = s.confluence_15m_candles,
                confluence_1h           = s.confluence_1h_candles,
                confluence_min_move_pct = s.confluence_min_move_pct,
                cam_narrow_range_pct    = s.cam_narrow_range_pct,
                daily_metrics           = metrics,
            )
        return self._engines[meta.symbol]

    async def _maybe_publish_regime(self, meta: InstrumentMeta, engine: SignalEngine):
        history = engine._builder.get_history()
        regime = detect_regime(history)
        now = datetime.now(tz=timezone.utc)
        prev_regime, prev_at = self._regimes.get(meta.symbol, ("UNKNOWN", datetime.min.replace(tzinfo=timezone.utc)))
        should_push = regime.regime.value != prev_regime or now - prev_at >= timedelta(minutes=5)
        if should_push:
            self._regimes[meta.symbol] = (regime.regime.value, now)
            await self._publisher.publish_regime_update(meta.symbol, {
                "regime": regime.regime.value,
                "choppiness": regime.choppiness,
                "autocorr": regime.autocorr,
                "above_vwap": regime.above_vwap,
                "bar_range_ratio": regime.bar_range_ratio,
                "timestamp": now.isoformat(),
            })
        return regime
