"""
MinuteSyncService - orchestrates 1-minute OHLCV sync via Dhan.

Strategy:
  INITIAL           - no 1min rows yet, pull full 90-day history
  FETCH_INCREMENTAL - pull from last bar to today
  SKIP              - last bar is fresh enough

Default universe: all EQ symbols with a Dhan security ID.
Set DHAN_1MIN_UNIVERSE=fno to restrict this to F&O symbols.
"""

import logging
from datetime import datetime

import asyncpg
import redis.asyncio as aioredis

from shared.constants import IST
from shared.utils import ensure_utc

from ..config import settings
from ..domain.minute_action import classify_minute
from ..infrastructure.dhan.historical_fetcher import DhanHistoricalFetcher
from ..repositories.price_repository import PriceRepository
from ..repositories.sync_state_repository import SyncStateRepository
from .sync_state_writer import SyncStateWriter

logger = logging.getLogger(__name__)

_TIMEFRAME = "1m"


class MinuteSyncService:
    """Sync 1-minute OHLCV from the Dhan historical API."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._fetcher = DhanHistoricalFetcher(
            client_id=settings.dhan_client_id,
            access_token=settings.dhan_access_token,
            url=settings.dhan_historical_url,
            rate_per_sec=settings.dhan_1min_rate_per_sec,
            daily_budget=settings.dhan_daily_budget,
            budget_safety=settings.dhan_budget_safety,
        )
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._prices = PriceRepository(pool)
        self._state = SyncStateRepository(pool)
        self._writer = SyncStateWriter(pool, self._prices, self._state)

    async def run_sync(self) -> dict:
        """Classify configured symbols and sync 1-min data from Dhan."""
        try:
            return await self._run_sync_inner()
        except Exception:
            logger.exception("[1m] run_sync fatal error")
            raise

    async def _run_sync_inner(self) -> dict:
        await self._refresh_token_from_redis()
        symbols = await self._load_symbols()
        if not symbols:
            logger.warning("[1m] No symbols with Dhan IDs. Run POST /symbols/refresh-master first.")
            return {
                "error": "no_symbols_mapped",
                "symbols": 0,
                "universe": settings.dhan_1min_universe,
                "initial": 0,
                "incremental": 0,
                "skip": 0,
                "updated": 0,
                "budget_remaining": self._fetcher.remaining_budget(),
            }

        symbol_names = [s["symbol"] for s in symbols]
        snapshots = await self._state.get_snapshots(symbol_names, _TIMEFRAME)
        last_ts_map = {snap.symbol: snap.last_data_ts for snap in snapshots}

        now_ist = datetime.now(tz=IST)
        initial: list[tuple[str, int, str]] = []
        incremental: list[tuple[str, int, str, datetime]] = []
        skip_count = 0

        for s in symbols:
            sym = s["symbol"]
            sec_id = int(s["dhan_security_id"])
            seg = s["exchange_segment"] or "NSE_EQ"
            last_ts = ensure_utc(last_ts_map.get(sym))
            action = classify_minute(last_ts, now_ist)

            if action == "INITIAL":
                initial.append((sym, sec_id, seg))
            elif action == "FETCH_INCREMENTAL":
                incremental.append((sym, sec_id, seg, last_ts))
            else:
                skip_count += 1

        logger.info(
            "[1m] universe=%s symbols=%d INITIAL=%d INCREMENTAL=%d SKIP=%d budget_remaining=%d",
            settings.dhan_1min_universe,
            len(symbols),
            len(initial),
            len(incremental),
            skip_count,
            self._fetcher.remaining_budget(),
        )

        updated = 0

        if initial:
            logger.info("[1m/init] Fetching 90-day history for %d symbols", len(initial))
            initial_updated = await self._fetch_initial_and_persist(initial)
            updated += initial_updated
            logger.info("[1m/init] Done - %d/%d had data", initial_updated, len(initial))

        if incremental:
            logger.info("[1m/incr] Incremental fetch for %d symbols", len(incremental))
            incremental_updated = await self._fetch_incremental_and_persist(incremental)
            updated += incremental_updated
            logger.info("[1m/incr] Done - %d/%d had new data", incremental_updated, len(incremental))

        return {
            "symbols": len(symbols),
            "universe": settings.dhan_1min_universe,
            "initial": len(initial),
            "incremental": len(incremental),
            "skip": skip_count,
            "updated": updated,
            "budget_remaining": self._fetcher.remaining_budget(),
        }

    async def _refresh_token_from_redis(self) -> None:
        """Pull the latest Dhan token from Redis, if LiveFeedService wrote one."""
        try:
            token = await self._redis.get("dhan:access_token")
            if token:
                self._fetcher.refresh_token(token)
                logger.debug("[1m] Refreshed Dhan token from Redis")
            else:
                logger.debug("[1m] Redis key dhan:access_token absent; using existing token")
        except Exception:
            logger.warning("[1m] Could not read token from Redis; using existing token", exc_info=True)

    async def _fetch_initial_and_persist(self, symbols: list[tuple[str, int, str]]) -> int:
        updated = 0
        chunk_size = max(1, settings.dhan_1min_persist_chunk_size)
        for offset in range(0, len(symbols), chunk_size):
            chunk = symbols[offset : offset + chunk_size]
            data = await self._fetcher.fetch_initial(chunk)
            await self._writer.persist([s for s, _, _ in chunk], data, _TIMEFRAME)
            updated += len(data)
            logger.info(
                "[1m/init] Persisted chunk %d-%d/%d: %d had data",
                offset + 1,
                offset + len(chunk),
                len(symbols),
                len(data),
            )
        return updated

    async def _fetch_incremental_and_persist(
        self,
        symbols: list[tuple[str, int, str, datetime]],
    ) -> int:
        updated = 0
        chunk_size = max(1, settings.dhan_1min_persist_chunk_size)
        for offset in range(0, len(symbols), chunk_size):
            chunk = symbols[offset : offset + chunk_size]
            data = await self._fetcher.fetch_incremental(chunk)
            await self._writer.persist([s for s, _, _, _ in chunk], data, _TIMEFRAME)
            updated += len(data)
            logger.info(
                "[1m/incr] Persisted chunk %d-%d/%d: %d had data",
                offset + 1,
                offset + len(chunk),
                len(symbols),
                len(data),
            )
        return updated

    async def _load_symbols(self) -> list[dict]:
        """Return configured symbols that have a Dhan security ID mapped."""
        universe = settings.dhan_1min_universe.strip().lower()
        if universe not in {"all", "fno"}:
            logger.warning("[1m] Unknown DHAN_1MIN_UNIVERSE=%s; using all", universe)
            universe = "all"

        fno_filter = "AND is_fno = TRUE" if universe == "fno" else ""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT symbol, dhan_security_id, exchange_segment
                FROM   symbols
                WHERE  series = 'EQ'
                  AND  dhan_security_id IS NOT NULL
                  {fno_filter}
                ORDER  BY symbol
            """)
        return [dict(r) for r in rows]
