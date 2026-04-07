"""
High-performance bulk ingestion into TimescaleDB via asyncpg COPY.

Strategy:
  1. COPY all records into a temporary table (fastest write path).
  2. INSERT INTO target ... SELECT FROM temp ON CONFLICT DO NOTHING
     -> idempotent; re-running the same data is safe.
"""

import logging
from datetime import datetime

import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

_TABLE_MAP: dict[str, str] = {
    "1m": "price_data_1m",
    "1d": "price_data_daily",
}
_CONFLICT_COLUMNS: dict[str, str] = {
    "1m": "symbol, time",
    "1d": "symbol, time",
}

_COLUMNS = ("time", "symbol", "open", "high", "low", "close", "volume")
_INGEST_CHUNK_SIZE: dict[str, int] = {
    "1m": 10_000,
    "1d": 50_000,
}


def _to_records(symbol: str, df: pd.DataFrame) -> list[tuple]:
    records: list[tuple] = []
    for ts, row in df.iterrows():
        if hasattr(ts, "tzinfo"):
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        records.append((
            ts.to_pydatetime(),
            symbol,
            float(row["Open"]) if pd.notna(row["Open"]) else None,
            float(row["High"]) if pd.notna(row["High"]) else None,
            float(row["Low"]) if pd.notna(row["Low"]) else None,
            float(row["Close"]) if pd.notna(row["Close"]) else None,
            int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
        ))
    return records


_QUERY_TABLE: dict[str, str] = {
    "1m": "price_data_1m",
    "1d": "price_data_daily",
}


class PriceRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_last_data_ts_bulk(
        self,
        symbols: list[str],
        interval: str,
        *,
        query_timeout: float = 300.0,
    ) -> dict[str, datetime | None]:
        """
        Single query: returns {symbol: MAX(time)} from the actual price table.

        This is the source of truth for gap detection — not sync_state, which
        can lag if a previous run crashed after ingest but before state update.
        Symbols with no rows at all get None.

        query_timeout overrides the pool-level command_timeout (default 60 s)
        because a full-table MAX(time) GROUP BY on a TimescaleDB hypertable can
        be slow right after startup when background workers restart and hold
        chunk locks.
        """
        table = _TABLE_MAP.get(interval)
        if not table:
            raise ValueError(f"Unsupported interval: {interval!r}")
        if not symbols:
            return {}
        async with self._pool.acquire(timeout=30) as conn:
            rows = await conn.fetch(
                f"SELECT DISTINCT ON (symbol) symbol, time AS last_ts "
                f"FROM {table} "
                f"WHERE symbol = ANY($1::text[]) "
                f"ORDER BY symbol, time DESC",
                symbols,
                timeout=query_timeout,
            )
        result = {row["symbol"]: row["last_ts"] for row in rows}
        return {s: result.get(s) for s in symbols}

    async def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list[dict]:
        """Query OHLCV rows for a symbol from a static table whitelist."""
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
        conflict_columns = _CONFLICT_COLUMNS[interval]

        all_records: list[tuple] = []
        for symbol, df in symbol_data.items():
            all_records.extend(_to_records(symbol, df))

        if not all_records:
            return 0

        chunk_size = _INGEST_CHUNK_SIZE.get(interval, len(all_records))
        inserted = 0

        async with self._pool.acquire() as conn:
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
                    inserted += int(result.split()[-1])

        logger.debug("[%s] Inserted %d / %d records", interval, inserted, len(all_records))
        return inserted
