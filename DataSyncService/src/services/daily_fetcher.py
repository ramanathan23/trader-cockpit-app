"""
DailyFetcher — executes the three daily price fetch strategies.

Single responsibility: given a list of symbols and their last timestamps,
download the appropriate price history from yfinance and persist it via
SyncStateWriter.

Strategies
----------
  fetch_full          — INITIAL symbols → pull full N-year history in batches
  fetch_since_uniform — FETCH_TODAY symbols share a since date → batched download
  fetch_gap           — FETCH_GAP symbols each have an individual since date
"""
import asyncio
import logging
from datetime import datetime, timezone

from shared.utils import ensure_utc

from ..config import settings
from ..infrastructure.fetchers.yfinance.fetcher import YFinanceFetcher
from .sync_state_writer import SyncStateWriter

logger = logging.getLogger(__name__)


def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


class DailyFetcher:
    """
    Executes daily price fetch strategies for DataSyncService.

    Parameters
    ----------
    yf     : yfinance data fetcher (injectable for testing)
    writer : SyncStateWriter that persists results to the DB
    """

    def __init__(self, yf: YFinanceFetcher, writer: SyncStateWriter) -> None:
        self._yf     = yf
        self._writer = writer

    async def fetch_full(self, symbols: list[str]) -> int:
        """Fetch full history for INITIAL symbols (no prior data)."""
        total = -(-len(symbols) // settings.sync_batch_size)
        logger.info("[1d/initial] %d symbols, %d batches of %d",
                    len(symbols), total, settings.sync_batch_size)
        updated = 0
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            data = await self._yf.fetch_batch(batch, "1d", settings.sync_1d_history_days)
            missing = len(batch) - len(data)
            if missing:
                logger.warning("[1d/initial] batch %d/%d — no data for %d symbol(s): %s",
                               i + 1, total, missing, [s for s in batch if s not in data])
            await self._writer.persist(batch, data, "1d")
            updated += len(data)
            logger.info("[1d/initial] %d / %d processed (%d with data)",
                        min((i + 1) * settings.sync_batch_size, len(symbols)),
                        len(symbols), updated)
            await asyncio.sleep(settings.sync_batch_delay_s)
        logger.info("[1d/initial] done — %d / %d had data", updated, len(symbols))
        return updated

    async def fetch_since_uniform(self, symbols: list[str], since_dt: datetime) -> int:
        """Batch-download for FETCH_TODAY symbols sharing the same since date."""
        total = -(-len(symbols) // settings.sync_batch_size)
        logger.info("[1d/today] %d symbols since %s, %d batches",
                    len(symbols), since_dt.date(), total)
        updated = 0
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            data = await self._yf.fetch_batch(
                batch, "1d", settings.sync_1d_history_days, start=since_dt
            )
            await self._writer.persist(batch, data, "1d")
            updated += len(data)
            logger.info("[1d/today] %d / %d processed (%d with data)",
                        min((i + 1) * settings.sync_batch_size, len(symbols)),
                        len(symbols), updated)
            await asyncio.sleep(settings.sync_batch_delay_s)
        logger.info("[1d/today] done — %d / %d had new data", updated, len(symbols))
        return updated

    async def fetch_gap(
        self,
        symbols:     list[str],
        last_ts_map: dict[str, datetime | None],
    ) -> int:
        """Per-symbol gap-fill for FETCH_GAP symbols with individual since dates."""
        total = -(-len(symbols) // settings.sync_batch_size)
        logger.info("[1d/gap] %d symbols, %d batches", len(symbols), total)
        updated = 0
        sem = asyncio.Semaphore(settings.sync_batch_size)
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):

            async def _fetch_one(sym: str) -> tuple[str, object] | None:
                since = ensure_utc(last_ts_map.get(sym))
                if since is None:
                    logger.warning("[1d/gap] %s has no last_ts — skipping", sym)
                    return None
                async with sem:
                    df = await self._yf.fetch_since(sym, "1d", since)
                if not df.empty:
                    logger.debug("[1d/gap] %s — got %d new bars", sym, len(df))
                    return sym, df
                return None

            results = await asyncio.gather(
                *[_fetch_one(s) for s in batch],
                return_exceptions=True,
            )
            batch_data: dict = {}
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("[1d/gap] fetch error: %s", result)
                elif result is not None:
                    batch_data[result[0]] = result[1]

            await self._writer.persist(batch, batch_data, "1d")
            updated += len(batch_data)
            logger.info("[1d/gap] %d / %d processed, %d updated",
                        min((i + 1) * settings.sync_batch_size, len(symbols)),
                        len(symbols), updated)
            await asyncio.sleep(settings.sync_batch_delay_s)
        logger.info("[1d/gap] done — %d / %d gaps filled", updated, len(symbols))
        return updated
