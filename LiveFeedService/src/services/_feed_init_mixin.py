from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from ..core.tick_router import TickRouter
from ..infrastructure.dhan.subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")


class _FeedInitMixin:
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
            price_update = await self._tick_router.on_tick(tick)
            if price_update is not None:
                await self._publisher.publish_price(price_update)
            self._check_session_reset()
