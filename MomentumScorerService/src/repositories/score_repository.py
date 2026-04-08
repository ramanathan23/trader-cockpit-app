"""
Persistence and queries for the momentum_scores table.
"""

import logging

import asyncpg

from ..domain.models import ScoreBreakdown

logger = logging.getLogger(__name__)


class ScoreRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def delete_by_timeframe(self, conn: asyncpg.Connection, timeframe: str) -> int:
        """Delete all scores for a timeframe. Returns number of rows deleted."""
        result = await conn.execute(
            "DELETE FROM momentum_scores WHERE timeframe = $1", timeframe
        )
        # asyncpg returns e.g. "DELETE 42"
        return int(result.split()[-1])

    async def insert(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        timeframe: str,
        breakdown: ScoreBreakdown,
    ) -> None:
        await conn.execute("""
            INSERT INTO momentum_scores
                (symbol, timeframe, score, rsi, macd_score, roc_score, vol_score, computed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, symbol, timeframe,
            breakdown.score, breakdown.rsi,
            breakdown.macd_score, breakdown.roc_score, breakdown.vol_score)

    async def get_top(
        self,
        timeframe: str,
        limit: int,
        min_score: float,
    ) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    ms.symbol,
                    s.company_name,
                    ms.score,
                    ms.rsi,
                    ms.macd_score,
                    ms.roc_score,
                    ms.vol_score,
                    ms.computed_at
                FROM   momentum_scores ms
                JOIN   symbols s ON s.symbol = ms.symbol
                WHERE  ms.timeframe = $1
                   AND ms.score >= $2
                ORDER  BY ms.score DESC
                LIMIT  $3
            """, timeframe, min_score, limit)
        return [dict(r) for r in rows]

    async def get_for_symbol(self, symbol: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM momentum_scores WHERE symbol = $1 ORDER BY timeframe",
                symbol.upper(),
            )
        return [dict(r) for r in rows]

    async def get_latest_computed_at(self, timeframe: str):
        """Return the most recent computed_at timestamp for the given timeframe, or None."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(computed_at) AS latest FROM momentum_scores WHERE timeframe = $1",
                timeframe,
            )
        return row["latest"] if row else None

    async def get_distribution(self, timeframe: str, buckets: int) -> list[dict]:
        bucket_width = 100.0 / buckets
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    floor(score / $2) * $2        AS bucket_start,
                    floor(score / $2) * $2 + $2   AS bucket_end,
                    COUNT(*)                       AS count
                FROM momentum_scores
                WHERE timeframe = $1
                GROUP BY bucket_start
                ORDER BY bucket_start
            """, timeframe, bucket_width)
        return [dict(r) for r in rows]
