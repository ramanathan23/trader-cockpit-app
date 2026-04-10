"""
FeedService: top-level orchestrator for the live market feed pipeline.

Lifecycle
---------
  run()
    ├── load instruments from DB (equities + index futures)
    ├── create SubscriptionManager → starts Dhan WebSocket connections
    ├── create one SignalEngine per instrument
    ├── create TickRouter (routes ticks → CandleBuilders)
    ├── create BufferedCandleWriter (batches DB writes)
    ├── launch periodic flush task
    └── enter main loop: drain tick_queue → route ticks

On each completed candle:
  ├── BufferedCandleWriter.add(candle)
  ├── Update IndexBias if it's an index future candle
  └── SignalEngine.on_candle(candle, index_bias)
        └── emits Signal objects → SignalPublisher.publish()

Session reset:
  At 9:15 IST each day, all SignalEngines and CandleBuilders are reset.
  This is handled by the main loop checking the session date.
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
from ..domain.models import (
    Candle, Direction, IndexBias, InstrumentMeta, Signal, SessionPhase,
)
from ..infrastructure.dhan.subscription_manager import SubscriptionManager
from ..infrastructure.redis.publisher import SignalPublisher
from ..repositories.candle_repository import BufferedCandleWriter, CandleRepository
from ..repositories.symbol_repository import SymbolRepository
from ..signals.engine import SignalEngine

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")


class FeedService:
    """
    Wires together all components and runs the main event loop.

    Designed to run as a single asyncio Task launched from main.py lifespan.
    """

    def __init__(
        self,
        symbol_repo: SymbolRepository,
        candle_repo: CandleRepository,
        publisher:   SignalPublisher,
        settings:    Settings,
    ) -> None:
        self._symbol_repo = symbol_repo
        self._candle_repo = candle_repo
        self._publisher   = publisher
        self._settings    = settings
        self._session_mgr = SessionManager()

        # Populated in run() after instruments are loaded.
        self._sub_mgr:      Optional[SubscriptionManager] = None
        self._tick_router:  Optional[TickRouter]          = None
        self._engines:      dict[str, SignalEngine]       = {}
        self._index_bias    = IndexBias()
        self._session_date: Optional[date]                = None

        # Shared candle writer.
        self._writer = BufferedCandleWriter(
            candle_repo,
            batch_size  = settings.candle_write_batch_size,
            flush_every = settings.candle_write_flush_s,
        )

        # Diagnostics counters.
        self._ticks_received:   int = 0
        self._candles_completed: int = 0
        self._signals_emitted:  int = 0
        self._last_tick_at:     Optional[datetime] = None

    # ── Public interface ───────────────────────────────────────────────────────

    async def run(self) -> None:
        """Main loop — runs until cancelled."""
        await self._initialise()
        flush_task = asyncio.create_task(
            self._writer.run_periodic_flush(), name="candle-flush"
        )
        try:
            await self._main_loop()
        except asyncio.CancelledError:
            pass
        finally:
            flush_task.cancel()
            await asyncio.gather(flush_task, return_exceptions=True)
            await self._writer.flush()   # final flush before shutdown
            if self._sub_mgr:
                await self._sub_mgr.stop()

    def status(self) -> dict:
        builders = (
            self._tick_router.builder_summary() if self._tick_router else []
        )
        active_builders   = [b for b in builders if b["candles_completed"] > 0]
        inactive_builders = [b for b in builders if b["candles_completed"] == 0]
        return {
            "session_phase":      self._session_mgr.current_phase().value,
            "session_date":       self._session_date.isoformat() if self._session_date else None,
            "connections":        self._sub_mgr.connection_count() if self._sub_mgr else 0,
            "instruments_total":  len(builders),
            "ticks_received":     self._ticks_received,
            "candles_completed":  self._candles_completed,
            "signals_emitted":    self._signals_emitted,
            "last_tick_at":       self._last_tick_at.isoformat() if self._last_tick_at else None,
            "index_bias": {
                "nifty":     self._index_bias.nifty.value,
                "banknifty": self._index_bias.banknifty.value,
                "sensex":    self._index_bias.sensex.value,
            },
            # Symbols that have completed at least one candle (active) vs silent.
            "active_symbols":   [b["symbol"] for b in active_builders],
            "silent_symbols":   [b["symbol"] for b in inactive_builders],
            # Candle progress per active instrument.
            "candle_counts":    {
                b["symbol"]: {"candles": b["candles_completed"], "last_price": b["last_price"]}
                for b in active_builders
            },
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _initialise(self) -> None:
        self._session_date = datetime.now(tz=_IST).date()

        equities      = await self._symbol_repo.load_equity_instruments()
        index_futures = await self._symbol_repo.load_index_future_instruments()

        all_instruments = equities + index_futures

        # Signal engines — one per instrument.
        for meta in all_instruments:
            key = meta.underlying if meta.is_index_future else meta.symbol
            # CandleBuilder is created inside TickRouter; we need it before
            # SignalEngine so we defer engine creation to _on_candle.
        # We'll lazily create engines when the first candle arrives.
        self._all_meta = {
            meta.dhan_security_id: meta for meta in all_instruments
        }

        # TickRouter — routes ticks, calls _on_candle on completion.
        self._tick_router = TickRouter(
            instruments     = all_instruments,
            session_manager = self._session_mgr,
            on_candle       = self._on_candle,
            open_h          = self._settings.market_open_h,
            open_m          = self._settings.market_open_m,
            candle_min      = self._settings.candle_minutes,
        )
        await self._hydrate_recent_history(equities, index_futures)

        # SubscriptionManager — manages Dhan WebSocket connections.
        self._sub_mgr = SubscriptionManager(
            equities          = equities,
            index_futures     = index_futures,
            client_id         = self._settings.dhan_client_id,
            access_token      = self._settings.dhan_access_token,
            reconnect_delay_s = self._settings.dhan_reconnect_delay_s,
            batch_size        = self._settings.dhan_ws_batch_size,
        )
        await self._sub_mgr.start()

        logger.info(
            "FeedService ready: %d equities + %d index futures across %d connection(s)",
            len(equities), len(index_futures), self._sub_mgr.connection_count(),
        )

    async def _hydrate_recent_history(
        self,
        equities: list[InstrumentMeta],
        index_futures: list[InstrumentMeta],
    ) -> None:
        warm_limit = max(self._settings.spike_window, self._settings.drive_candles)

        equity_history = await self._candle_repo.list_recent_by_symbol(
            [meta.symbol for meta in equities],
            is_index_future=False,
            limit_per_symbol=warm_limit,
        )
        future_history = await self._candle_repo.list_recent_by_symbol(
            [meta.symbol for meta in index_futures],
            is_index_future=True,
            limit_per_symbol=warm_limit,
        )

        seeded = 0
        for meta in equities:
            builder = self._tick_router.get_builder(meta.dhan_security_id)
            candles = equity_history.get(meta.symbol, [])
            if builder and candles:
                builder.seed_history(candles)
                seeded += 1

        for meta in index_futures:
            builder = self._tick_router.get_builder(meta.dhan_security_id)
            candles = future_history.get(meta.symbol, [])
            if builder and candles:
                builder.seed_history(candles)
                seeded += 1

        logger.info("Hydrated recent history for %d instruments", seeded)

    async def _main_loop(self) -> None:
        while True:
            tick = await self._sub_mgr.tick_queue.get()
            self._ticks_received += 1
            self._last_tick_at = datetime.now(tz=_IST)
            await self._tick_router.on_tick(tick)
            self._check_session_reset()

    def _check_session_reset(self) -> None:
        """Reset all engines + builders at the start of a new trading day."""
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
        """
        Called by TickRouter whenever a 3-min candle completes.

          1. Write candle to DB (buffered).
          2. Update index bias if this is an index future.
          3. Run signal engine and publish any resulting signals.
        """
        # 1. Persist.
        self._candles_completed += 1
        await self._writer.add(candle)

        # 2. Index bias update.
        if meta.is_index_future and meta.underlying:
            self._update_index_bias(meta.underlying, candle)

        # 3. Signal engine (equities only — index futures are proxy, not traded).
        if not meta.is_index_future:
            engine = self._get_or_create_engine(meta)
            signals = engine.on_candle(candle, self._index_bias)
            for signal in signals:
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
            builder = self._tick_router.get_builder(meta.dhan_security_id)
            self._engines[meta.symbol] = SignalEngine(
                symbol          = meta.symbol,
                builder         = builder,
                session_manager = self._session_mgr,
                drive_candles   = self._settings.drive_candles,
                min_body_ratio  = self._settings.drive_min_body_ratio,
                confirmed_thresh = self._settings.drive_confirmed_thresh,
                weak_thresh     = self._settings.drive_weak_thresh,
                spike_window    = self._settings.spike_window,
            )
        return self._engines[meta.symbol]
