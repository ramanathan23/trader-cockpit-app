import logging

import asyncpg
import pandas as pd

from shared.utils import parse_pg_command_result

logger = logging.getLogger(__name__)

_TABLE_MAP: dict[str, str] = {
    "1d": "price_data_daily",
    "1m": "price_data_1min",
}
_CONFLICT_COLUMNS: dict[str, str] = {
    "1d": "symbol, time",
    "1m": "symbol, time",
}
_COLUMNS = ("time", "symbol", "open", "high", "low", "close", "volume")
_INGEST_CHUNK_SIZE: dict[str, int] = {
    "1d": 50_000,
    "1m": 100_000,
}


def _to_records(symbol: str, df: pd.DataFrame) -> list[tuple]:
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    times  = idx.to_pydatetime()
    syms   = [symbol] * len(df)
    opens  = df["Open"].where(df["Open"].notna()).tolist()
    highs  = df["High"].where(df["High"].notna()).tolist()
    lows   = df["Low"].where(df["Low"].notna()).tolist()
    closes = df["Close"].where(df["Close"].notna()).tolist()
    vols   = df["Volume"].where(df["Volume"].notna(), 0).astype(int).tolist()
    return list(zip(times, syms, opens, highs, lows, closes, vols))


async def bulk_ingest(
    pool: asyncpg.Pool,
    symbol_data: dict[str, pd.DataFrame],
    interval: str,
) -> int:
    """Bulk-insert OHLCV rows. Returns count of new rows (duplicates skipped)."""
    table = _TABLE_MAP.get(interval)
    if not table:
        raise ValueError(f"Unsupported interval: {interval!r}")
    conflict_columns = _CONFLICT_COLUMNS[interval]

    all_records: list[tuple] = []
    for symbol, df in symbol_data.items():
        all_records.extend(_to_records(symbol, df))

    if not all_records:
        return 0

    chunk_size = _INGEST_CHUNK_SIZE.get(interval, len(all_records))
    total      = len(all_records)
    n_chunks   = (total + chunk_size - 1) // chunk_size
    inserted   = 0
    logger.info("[%s] Persisting %d rows (%d chunks) for %d symbols",
                interval, total, n_chunks, len(symbol_data))

    async with pool.acquire() as conn:
        for i in range(0, total, chunk_size):
            chunk     = all_records[i: i + chunk_size]
            chunk_num = i // chunk_size + 1
            async with conn.transaction():
                await conn.execute(f"""
                    CREATE TEMP TABLE _ingest_tmp
                        (LIKE {table} INCLUDING DEFAULTS)
                    ON COMMIT DROP
                """)
                await conn.copy_records_to_table(
                    "_ingest_tmp",
                    records=chunk,
                    columns=list(_COLUMNS),
                )
                result = await conn.execute(f"""
                    INSERT INTO {table} ({", ".join(_COLUMNS)})
                    SELECT {", ".join(_COLUMNS)} FROM _ingest_tmp
                    ON CONFLICT ({conflict_columns}) DO NOTHING
                """)
                inserted += parse_pg_command_result(result)            logger.info("[%s] chunk %d/%d done — %d rows inserted so far",
                        interval, chunk_num, n_chunks, inserted)
    logger.debug("[%s] Inserted %d / %d records", interval, inserted, len(all_records))
    return inserted
