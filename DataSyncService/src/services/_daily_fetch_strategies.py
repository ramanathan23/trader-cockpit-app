import asyncio
import logging
from datetime import datetime

from shared.utils import ensure_utc

from ..config import settings

logger = logging.getLogger(__name__)


def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


async def fetch_full(yf, writer, symbols: list[str]) -> int:
    """Fetch full history for INITIAL symbols (no prior data)."""
    total = -(-len(symbols) // settings.sync_batch_size)
    logger.info("[1d/initial] %d symbols, %d batches of %d",
                len(symbols), total, settings.sync_batch_size)
    updated = 0
    for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
        data = await yf.fetch_batch(batch, "1d", settings.sync_1d_history_days)
        missing = len(batch) - len(data)
        if missing:
            logger.warning("[1d/initial] batch %d/%d — no data for %d symbol(s): %s",
                           i + 1, total, missing, [s for s in batch if s not in data])
        await writer.persist(batch, data, "1d")
        updated += len(data)
        logger.info("[1d/initial] %d / %d processed (%d with data)",
                    min((i + 1) * settings.sync_batch_size, len(symbols)),
                    len(symbols), updated)
        await asyncio.sleep(settings.sync_batch_delay_s)
    logger.info("[1d/initial] done — %d / %d had data", updated, len(symbols))
    return updated


async def fetch_since_uniform(yf, writer, symbols: list[str], since_dt: datetime) -> int:
    """Batch-download for FETCH_TODAY symbols sharing the same since date."""
    total = -(-len(symbols) // settings.sync_batch_size)
    logger.info("[1d/today] %d symbols since %s, %d batches",
                len(symbols), since_dt.date(), total)
    updated = 0
    for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
        data = await yf.fetch_batch(
            batch, "1d", settings.sync_1d_history_days, start=since_dt
        )
        await writer.persist(batch, data, "1d")
        updated += len(data)
        logger.info("[1d/today] %d / %d processed (%d with data)",
                    min((i + 1) * settings.sync_batch_size, len(symbols)),
                    len(symbols), updated)
        await asyncio.sleep(settings.sync_batch_delay_s)
    logger.info("[1d/today] done — %d / %d had new data", updated, len(symbols))
    return updated


async def fetch_gap(yf, writer, symbols: list[str], last_ts_map: dict) -> int:
    """Per-symbol gap-fill for FETCH_GAP symbols with individual since dates."""
    total = -(-len(symbols) // settings.sync_batch_size)
    logger.info("[1d/gap] %d symbols, %d batches", len(symbols), total)
    updated = 0
    sem = asyncio.Semaphore(settings.sync_batch_size)
    for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):

        async def _fetch_one(sym: str) -> tuple | None:
            since = ensure_utc(last_ts_map.get(sym))
            if since is None:
                logger.warning("[1d/gap] %s has no last_ts — skipping", sym)
                return None
            async with sem:
                df = await yf.fetch_since(sym, "1d", since)
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

        await writer.persist(batch, batch_data, "1d")
        updated += len(batch_data)
        logger.info("[1d/gap] %d / %d processed, %d updated",
                    min((i + 1) * settings.sync_batch_size, len(symbols)),
                    len(symbols), updated)
        await asyncio.sleep(settings.sync_batch_delay_s)
    logger.info("[1d/gap] done — %d / %d gaps filled", updated, len(symbols))
    return updated
