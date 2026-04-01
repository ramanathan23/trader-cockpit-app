"""
High-performance bulk ingestion into TimescaleDB via asyncpg COPY.

Strategy:
  1. COPY all records into a temporary table (fastest write path).
  2. INSERT INTO target … SELECT FROM temp ON CONFLICT DO NOTHING
     → idempotent; re-running the same data is safe.
"""

import logging

import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

_TABLE_MAP: dict[str, str] = {
    "1m": "price_data_1m",
    "1d": "price_data_daily",
}

_COLUMNS = ("time", "symbol", "open", "high", "low", "close", "volume")


def _to_records(symbol: str, df: pd.DataFrame) -> list[tuple]:
    records: list[tuple] = []
    for ts, row in df.iterrows():
        if hasattr(ts, "tzinfo"):
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
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


_QUERY_TABLE: dict[str, str] = {
    "1m": "price_data_1m",
    "1d": "price_data_daily",
}


class PriceRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list[dict]:
        """Query OHLCV rows for a symbol. Table is selected from a static whitelist — no injection risk."""
        table = _QUERY_TABLE.get(interval)
        if not table:
            raise ValueError(f"Unsupported interval: {interval!r}")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT time, open, high, low, close, volume "
                f"FROM {table} "
                f"WHERE symbol = $1 "
                f"  AND ($2::timestamptz IS NULL OR time >= $2::timestamptz) "
                f"  AND ($3::timestamptz IS NULL OR time <= $3::timestamptz) "
                f"ORDER BY time DESC LIMIT $4",
                symbol, from_ts, to_ts, limit,
            )
        return [dict(r) for r in rows]

    async def get_ohlcv_hourly(
        self,
        symbol: str,
        *,
        limit: int = 168,
    ) -> list[dict]:
        """Query from the pre-built hourly continuous aggregate view."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT bucket AS time, open, high, low, close, volume "
                "FROM price_1m_hourly "
                "WHERE symbol = $1 "
                "ORDER BY bucket DESC LIMIT $2",
                symbol, limit,
            )
        return [dict(r) for r in rows]

    async def bulk_ingest(
        self,
        symbol_data: dict[str, pd.DataFrame],
        interval: str,
    ) -> int:
        """Bulk-insert OHLCV rows. Returns count of new rows (duplicates skipped)."""
        table = _TABLE_MAP.get(interval)
        if not table:
            raise ValueError(f"Unsupported interval: {interval!r}")

        all_records: list[tuple] = []
        for symbol, df in symbol_data.items():
            all_records.extend(_to_records(symbol, df))

        if not all_records:
            return 0

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f"""
                    CREATE TEMP TABLE _ingest_tmp
                        (LIKE {table} INCLUDING DEFAULTS)
                    ON COMMIT DROP
                """)
                await conn.copy_records_to_table(
                    "_ingest_tmp",
                    records=all_records,
                    columns=list(_COLUMNS),
                )
                result = await conn.execute(f"""
                    INSERT INTO {table} ({", ".join(_COLUMNS)})
                    SELECT {", ".join(_COLUMNS)} FROM _ingest_tmp
                    ON CONFLICT (time, symbol) DO NOTHING
                """)

        inserted = int(result.split()[-1])
        logger.debug("[%s] Inserted %d / %d records", interval, inserted, len(all_records))
        return inserted
