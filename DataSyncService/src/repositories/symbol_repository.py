"""Symbol persistence: CSV loading and database upserts."""

import logging

import asyncpg

from ._symbol_csv import load_from_csv  # noqa: F401 — re-exported for callers

logger = logging.getLogger(__name__)


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_many(self, symbols) -> int:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany("""
                    INSERT INTO symbols
                        (symbol, company_name, series, isin, listed_date, face_value)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (symbol) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        series       = EXCLUDED.series,
                        isin         = EXCLUDED.isin
                """, [(s.symbol, s.company_name, s.series,
                       s.isin, s.listed_date, s.face_value) for s in symbols])
        logger.info("Upserted %d symbols", len(symbols))
        return len(symbols)

    async def list_by_series(self, series: str = "EQ") -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol, company_name, series, isin, listed_date "
                "FROM symbols WHERE series = $1 ORDER BY symbol",
                series.upper(),
            )
        return [dict(r) for r in rows]

    async def list_mapped(self) -> list[dict]:
        """Return all symbols that have a Dhan security ID (ready for live feed)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT symbol, dhan_security_id, exchange_segment
                FROM   symbols
                WHERE  dhan_security_id IS NOT NULL
                ORDER  BY symbol
            """)
        return [dict(r) for r in rows]

    async def get_dhan_mapping_stats(self) -> dict:
        """Summary of Dhan ID mapping coverage."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*)                           AS total,
                    COUNT(dhan_security_id)            AS mapped,
                    COUNT(*) - COUNT(dhan_security_id) AS unmapped
                FROM symbols
                WHERE series = 'EQ'
            """)
        return dict(row)

