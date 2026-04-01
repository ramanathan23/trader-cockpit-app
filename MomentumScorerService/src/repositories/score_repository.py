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

    async def upsert(
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
            ON CONFLICT (symbol, timeframe) DO UPDATE SET
                score       = $3,
                rsi         = $4,
                macd_score  = $5,
                roc_score   = $6,
                vol_score   = $7,
                computed_at = NOW()
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
