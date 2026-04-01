"""
High-performance bulk ingestion into TimescaleDB.

Strategy:
  1. COPY all records to a temporary table (fastest write path).
  2. INSERT INTO target … SELECT FROM temp ON CONFLICT DO NOTHING
     → idempotent upsert; re-running the same data is safe.

asyncpg's copy_records_to_table uses the PostgreSQL COPY binary protocol,
which is ~10× faster than parameterised INSERT statements.
"""

import logging
from datetime import timezone

import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

TABLE_MAP: dict[str, str] = {
    "1m": "price_data_1m",
    "1d": "price_data_daily",
}

COLUMNS = ("time", "symbol", "open", "high", "low", "close", "volume")


def _to_records(symbol: str, df: pd.DataFrame) -> list[tuple]:
    records: list[tuple] = []
    for ts, row in df.iterrows():
        # Normalise to UTC-aware datetime
        if hasattr(ts, "tzinfo"):
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")
        records.append((
            ts.to_pydatetime(),
            symbol,
            float(row["Open"])   if pd.notna(row["Open"])   else None,
            float(row["High"])   if pd.notna(row["High"])   else None,
            float(row["Low"])    if pd.notna(row["Low"])    else None,
            float(row["Close"])  if pd.notna(row["Close"])  else None,
            int(row["Volume"])   if pd.notna(row["Volume"]) else 0,
        ))
    return records


async def ingest_ohlcv(
    pool: asyncpg.Pool,
    symbol_data: dict[str, pd.DataFrame],
    interval: str,
) -> int:
    """
    Bulk-ingest OHLCV data for multiple symbols.

    Returns the total number of new rows inserted (duplicates are skipped).
    """
    table = TABLE_MAP.get(interval)
    if not table:
        raise ValueError(f"Unsupported interval: {interval!r}")

    all_records: list[tuple] = []
    for symbol, df in symbol_data.items():
        all_records.extend(_to_records(symbol, df))

    if not all_records:
        return 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Temp table mirrors target schema but has no constraints.
            await conn.execute(f"""
                CREATE TEMP TABLE _ingest_tmp
                    (LIKE {table} INCLUDING DEFAULTS)
                ON COMMIT DROP
            """)

            await conn.copy_records_to_table(
                "_ingest_tmp",
                records=all_records,
                columns=list(COLUMNS),
            )

            result = await conn.execute(f"""
                INSERT INTO {table} ({", ".join(COLUMNS)})
                SELECT {", ".join(COLUMNS)} FROM _ingest_tmp
                ON CONFLICT (time, symbol) DO NOTHING
            """)

    inserted = int(result.split()[-1])
    logger.debug("[%s] Inserted %d / %d records", interval, inserted, len(all_records))
    return inserted
