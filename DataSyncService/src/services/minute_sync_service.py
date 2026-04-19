"""
MinuteSyncService — orchestrates 1-minute OHLCV sync for F&O stocks via Dhan.

Strategy:
  INITIAL          → fetch 90-day history (1 Dhan API call per symbol)
  FETCH_INCREMENTAL → fetch from last bar to today (1 call per symbol)
  SKIP             → last bar < 5 min ago → nothing to do

Rate limits (enforced by DhanHistoricalFetcher):
  - 10 requests/second
  - 10,000 requests/day (IST midnight reset)

F&O universe: symbols WHERE is_fno = TRUE AND dhan_security_id IS NOT NULL
  (~200 symbols → 200 API calls for initial, ~200 per incremental run)

Both MinuteSyncService.run_sync() and the daily SyncService.run_sync()
are safe to run in parallel via asyncio.gather().
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
    """Sync 1-minute OHLCV for F&O stocks from the Dhan historical API."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool    = pool
        self._fetcher = DhanHistoricalFetcher(
            client_id     = settings.dhan_client_id,
            access_token  = settings.dhan_access_token,
            url           = settings.dhan_historical_url,
            rate_per_sec  = settings.dhan_1min_rate_per_sec,
            daily_budget  = settings.dhan_daily_budget,
            budget_safety = settings.dhan_budget_safety,
        )
        self._redis  = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._prices = PriceRepository(pool)
        self._state  = SyncStateRepository(pool)
        self._writer = SyncStateWriter(pool, self._prices, self._state)

    # ── Public ────────────────────────────────────────────────────────────────

    async def run_sync(self) -> dict:
        """Classify F&O symbols and sync 1-min data from Dhan."""
        await self._refresh_token_from_redis()
        symbols = await self._load_fno_symbols()
        if not symbols:
            logger.warning(
                "[1m] No F&O symbols with Dhan IDs. Run POST /symbols/refresh-master first."
            )
            return {
                "error":             "no_fno_symbols_mapped",
                "fno_symbols":       0,
                "initial":           0,
                "incremental":       0,
                "skip":              0,
                "updated":           0,
                "budget_remaining":  self._fetcher.remaining_budget(),
            }

        symbol_names = [s["symbol"] for s in symbols]
        snapshots    = await self._state.get_snapshots(symbol_names, _TIMEFRAME)
        last_ts_map  = {snap.symbol: snap.last_data_ts for snap in snapshots}

        now_ist      = datetime.now(tz=IST)
        initial:     list[tuple[str, int, str]]           = []
        incremental: list[tuple[str, int, str, datetime]] = []
        skip_count   = 0

        for s in symbols:
            sym    = s["symbol"]
            sec_id = int(s["dhan_security_id"])
            seg    = s["exchange_segment"] or "NSE_EQ"
            last_ts = ensure_utc(last_ts_map.get(sym))
            action  = classify_minute(last_ts, now_ist)

            if action == "INITIAL":
                initial.append((sym, sec_id, seg))
            elif action == "FETCH_INCREMENTAL":
                incremental.append((sym, sec_id, seg, last_ts))
            else:
                skip_count += 1

        logger.info(
            "[1m] F&O=%d  INITIAL=%d  INCREMENTAL=%d  SKIP=%d  budget_remaining=%d",
            len(symbols), len(initial), len(incremental),
            skip_count, self._fetcher.remaining_budget(),
        )

        updated = 0

        if initial:
            logger.info("[1m/init] Fetching 90-day history for %d symbols", len(initial))
            data = await self._fetcher.fetch_initial(initial)
            await self._writer.persist([s for s, _, _ in initial], data, _TIMEFRAME)
            updated += len(data)
            logger.info("[1m/init] Done — %d/%d had data", len(data), len(initial))

        if incremental:
            logger.info("[1m/incr] Incremental fetch for %d symbols", len(incremental))
            data = await self._fetcher.fetch_incremental(incremental)
            await self._writer.persist([s for s, _, _, _ in incremental], data, _TIMEFRAME)
            updated += len(data)
            logger.info("[1m/incr] Done — %d/%d had new data", len(data), len(incremental))

        return {
            "fno_symbols":      len(symbols),
            "initial":          len(initial),
            "incremental":      len(incremental),
            "skip":             skip_count,
            "updated":          updated,
            "budget_remaining": self._fetcher.remaining_budget(),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _refresh_token_from_redis(self) -> None:
        """Pull the latest Dhan token from Redis (written by LiveFeedService /token API)."""
        try:
            token = await self._redis.get("dhan:access_token")
            if token:
                self._fetcher.refresh_token(token)
                logger.debug("[1m] Refreshed Dhan token from Redis")
            else:
                logger.debug("[1m] Redis key dhan:access_token absent — using existing token")
        except Exception:
            logger.warning("[1m] Could not read token from Redis — using existing token", exc_info=True)

    async def _load_fno_symbols(self) -> list[dict]:
        """Return F&O symbols that have a Dhan security ID mapped."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT symbol, dhan_security_id, exchange_segment
                FROM   symbols
                WHERE  is_fno = TRUE
                  AND  dhan_security_id IS NOT NULL
                ORDER  BY symbol
            """)
        return [dict(r) for r in rows]
