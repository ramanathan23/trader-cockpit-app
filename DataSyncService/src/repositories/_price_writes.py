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
    records: list[tuple] = []
    for row in df.itertuples():
        ts = row.Index
        if hasattr(ts, "tzinfo"):
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        records.append((
            ts.to_pydatetime(),
            symbol,
            float(row.Open)   if pd.notna(row.Open)   else None,
            float(row.High)   if pd.notna(row.High)   else None,
            float(row.Low)    if pd.notna(row.Low)    else None,
            float(row.Close)  if pd.notna(row.Close)  else None,
            int(row.Volume)   if pd.notna(row.Volume) else 0,
        ))
    return records


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
    inserted   = 0

    async with pool.acquire() as conn:
        for i in range(0, len(all_records), chunk_size):
            chunk = all_records[i: i + chunk_size]
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
                inserted += parse_pg_command_result(result)

    logger.debug("[%s] Inserted %d / %d records", interval, inserted, len(all_records))
    return inserted
