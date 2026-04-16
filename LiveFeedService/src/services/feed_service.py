"""
FeedService: top-level orchestrator for the live market feed pipeline.

Lifecycle
---------
  run()
    ├── InstrumentLoader: load instruments + seed candle history
    ├── TickRouter: one CandleBuilder per instrument
    ├── SubscriptionManager: connect Dhan WebSocket(s)
    └── Main loop: drain tick_queue → route ticks → emit signals

On each completed candle:
  ├── BufferedCandleWriter.add(candle)
  ├── Update IndexBias if index future
  └── SignalEngine.on_candle(candle, bias) → publish signals

Session reset at 9:15 IST each day via _check_session_reset().
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import Settings
from ..core.session_manager import SessionManager
from ..core.tick_router import TickRouter
from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.instrument_meta import InstrumentMeta
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..infrastructure.dhan.subscription_manager import SubscriptionManager
from ..infrastructure.redis.publisher import SignalPublisher
from ..infrastructure.redis.token_store import TokenStore
from ..repositories.candle_repository import BufferedCandleWriter, CandleRepository
from ..repositories.symbol_repository import SymbolRepository
from ..signals.engine import SignalEngine
from .instrument_loader import InstrumentLoader
from .metrics_service import MetricsService

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")


class FeedService:
    """Wires all components together and runs the main tick-processing loop."""

    def __init__(
        self,
        symbol_repo:     SymbolRepository,
        candle_repo:     CandleRepository,
        publisher:       SignalPublisher,
        token_store:     TokenStore,
        settings:        Settings,
        metrics_service: MetricsService,
    ) -> None:
        self._publisher       = publisher
        self._token_store     = token_store
        self._settings        = settings
        self._metrics_service = metrics_service
        self._session_mgr     = SessionManager()
        self._loader          = InstrumentLoader(
            symbol_repo,
            candle_repo,
            warm_limit=max(settings.spike_window, settings.drive_candles, settings.confluence_1h_candles),
        )
        self._writer = BufferedCandleWriter(
            candle_repo,
            batch_size  = settings.candle_write_batch_size,
            flush_every = settings.candle_write_flush_s,
        )

        self._sub_mgr:      Optional[SubscriptionManager] = None
        self._tick_router:  Optional[TickRouter]          = None
        self._engines:      dict[str, SignalEngine]       = {}
        self._index_bias    = IndexBias()
        self._session_date: Optional[date]                = None

        self._ticks_received:    int = 0
        self._candles_completed: int = 0
        self._signals_emitted:   int = 0
        self._last_tick_at:      Optional[datetime] = None

    # ── Public interface ───────────────────────────────────────────────────────

    async def run(self) -> None:
        """Main loop — runs until cancelled."""
        await self._initialise()
        flush_task  = asyncio.create_task(
            self._writer.run_periodic_flush(), name="candle-flush"
        )
        status_task = asyncio.create_task(
            self._status_broadcast_loop(), name="status-broadcast"
        )
        try:
            await self._main_loop()
        except asyncio.CancelledError:
            pass
        finally:
            flush_task.cancel()
            status_task.cancel()
            await asyncio.gather(flush_task, status_task, return_exceptions=True)
            await self._writer.flush()
            if self._sub_mgr:
                await self._sub_mgr.stop()

    def status(self) -> dict:
        builders          = self._tick_router.builder_summary() if self._tick_router else []
        active_builders   = [b for b in builders if b["candles_completed"] > 0]
        inactive_builders = [b for b in builders if b["candles_completed"] == 0]
        return {
            "session_phase":     self._session_mgr.current_phase().value,
            "session_date":      self._session_date.isoformat() if self._session_date else None,
            "connections":       self._sub_mgr.connection_count() if self._sub_mgr else 0,
            "instruments_total": len(builders),
            "ticks_received":    self._ticks_received,
            "candles_completed": self._candles_completed,
            "signals_emitted":   self._signals_emitted,
            "last_tick_at":      self._last_tick_at.isoformat() if self._last_tick_at else None,
            "index_bias": {
                "nifty":     self._index_bias.nifty.value,
                "banknifty": self._index_bias.banknifty.value,
                "sensex":    self._index_bias.sensex.value,
            },
            "active_symbols": [b["symbol"] for b in active_builders],
            "silent_symbols": [b["symbol"] for b in inactive_builders],
            "candle_counts":  {
                b["symbol"]: {"candles": b["candles_completed"], "last_price": b["last_price"]}
                for b in active_builders
            },
        }

    async def _status_broadcast_loop(self) -> None:
        """Push market phase + per-index bias to WS clients every 10 s."""
        while True:
            try:
                await self._publisher.publish_status({
                    "session_phase": self._session_mgr.current_phase().value,
                    "index_bias": {
                        "nifty":     self._index_bias.nifty.value,
                        "banknifty": self._index_bias.banknifty.value,
                        "sensex":    self._index_bias.sensex.value,
                    },
                })
            except Exception as exc:
                logger.warning("status broadcast failed: %s", exc)
            await asyncio.sleep(10)

    def screener_live_metrics(self) -> dict[str, dict]:
        """
        Lightweight live snapshot for the screener.

        Returns per-symbol current price from the active builder plus current
        session VWAP when the symbol has already emitted at least one candle.
        """
        if not self._tick_router:
            return {}

        live: dict[str, dict] = {}
        for row in self._tick_router.builder_summary():
            if row["is_index_future"]:
                continue

            symbol = row["symbol"]
            snapshot: dict[str, float] = {}

            if row["last_price"] is not None:
                snapshot["current_price"] = round(float(row["last_price"]), 2)

            engine = self._engines.get(symbol)
            if engine is not None:
                vwap = engine.current_vwap()
                if vwap is not None:
                    snapshot["daily_vwap"] = round(float(vwap), 2)

            if snapshot:
                live[symbol] = snapshot

        return live

    async def update_token(self, new_token: str) -> None:
        """
        Persist a new Dhan access token and reconnect all WebSocket feeds.

        The token is written to Redis first so that it survives service restarts.
        All active WebSocket connections are then cancelled and restarted; each
        picks up the new token at the start of its reconnect loop.
        """
        await self._token_store.set(new_token)
        if self._sub_mgr:
            await self._sub_mgr.reconnect_all()

    # ── Private ───────────────────────────────────────────────────────────────

    async def _initialise(self) -> None:
        self._session_date = datetime.now(tz=_IST).date()
        s = self._settings

        await self._metrics_service.precompute_daily()

        equities, index_futures = await self._loader.load()

        self._tick_router = TickRouter(
            instruments     = equities + index_futures,
            session_manager = self._session_mgr,
            on_candle       = self._on_candle,
            open_h          = s.market_open_h,
            open_m          = s.market_open_m,
            candle_min      = s.candle_minutes,
        )
        await self._loader.hydrate(self._tick_router, equities, index_futures)

        self._sub_mgr = SubscriptionManager(
            equities          = equities,
            index_futures     = index_futures,
            client_id         = s.dhan_client_id,
            token_getter      = self._token_store.get,
            reconnect_delay_s = s.dhan_reconnect_delay_s,
            batch_size        = s.dhan_ws_batch_size,
        )
        await self._sub_mgr.start()
        logger.info(
            "FeedService ready: %d equities + %d index futures across %d connection(s)",
            len(equities), len(index_futures), self._sub_mgr.connection_count(),
        )

    async def _main_loop(self) -> None:
        while True:
            tick = await self._sub_mgr.tick_queue.get()
            self._ticks_received += 1
            self._last_tick_at = datetime.now(tz=_IST)
            await self._tick_router.on_tick(tick)
            self._check_session_reset()

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
            engine = self._get_or_create_engine(meta)
            for signal in engine.on_candle(candle, self._index_bias):
                self._signals_emitted += 1
                await self._publisher.publish(signal)
                logger.info("[SIGNAL] %s %s %s score=%.2f",
                            signal.symbol, signal.signal_type.value,
                            signal.direction.value, signal.score)

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
                symbol           = meta.symbol,
                builder          = self._tick_router.get_builder(meta.dhan_security_id),
                session_manager  = self._session_mgr,
                drive_candles    = s.drive_candles,
                min_body_ratio   = s.drive_min_body_ratio,
                confirmed_thresh = s.drive_confirmed_thresh,
                weak_thresh      = s.drive_weak_thresh,
                spike_window     = s.spike_window,
                spike_cooldown        = s.spike_cooldown,
                absorption_cooldown   = s.absorption_cooldown,
                absorption_near_pct   = s.absorption_near_pct,
                exhaustion_downtrend_candles = s.exhaustion_downtrend_candles,
                exhaustion_vol_ratio_min     = s.exhaustion_vol_ratio_min,
                exhaustion_lower_lows        = s.exhaustion_lower_lows,
                range_lookback   = s.range_lookback,
                range_vol_ratio  = s.range_vol_ratio,
                range_max_pct    = s.range_max_pct,
                vwap_hysteresis_min = s.vwap_hysteresis_min,
                min_adv_cr       = s.min_adv_cr,
                confluence_15m   = s.confluence_15m_candles,
                confluence_1h    = s.confluence_1h_candles,
                daily_metrics    = metrics,
            )
        return self._engines[meta.symbol]
