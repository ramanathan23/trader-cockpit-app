"""
Persistence and queries for the daily_scores table.
"""

import logging
from datetime import date

import asyncpg

from ..domain.unified_score_breakdown import UnifiedScoreBreakdown

logger = logging.getLogger(__name__)


class ScoreRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_daily_score(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        score_date: date,
        breakdown: UnifiedScoreBreakdown,
        rank: int,
        is_watchlist: bool,
    ) -> None:
        await conn.execute("""
            INSERT INTO daily_scores
                (symbol, score_date, total_score, momentum_score, trend_score,
                 volatility_score, structure_score, rank, is_watchlist, computed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            ON CONFLICT (symbol, score_date) DO UPDATE SET
                total_score      = EXCLUDED.total_score,
                momentum_score   = EXCLUDED.momentum_score,
                trend_score      = EXCLUDED.trend_score,
                volatility_score = EXCLUDED.volatility_score,
                structure_score  = EXCLUDED.structure_score,
                rank             = EXCLUDED.rank,
                is_watchlist     = EXCLUDED.is_watchlist,
                computed_at      = EXCLUDED.computed_at
        """, symbol, score_date,
            breakdown.total_score, breakdown.momentum_score, breakdown.trend_score,
            breakdown.volatility_score, breakdown.structure_score,
            rank, is_watchlist)

    async def update_symbol_metrics_indicators(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        breakdown: UnifiedScoreBreakdown,
    ) -> None:
        """Update symbol_metrics with computed indicator values from scoring."""
        await conn.execute("""
            UPDATE symbol_metrics SET
                atr_5         = $2,
                adx_14        = $3,
                plus_di       = $4,
                minus_di      = $5,
                bb_width      = $6,
                kc_width      = $7,
                bb_squeeze    = $8,
                squeeze_days  = $9,
                nr7           = $10,
                atr_ratio     = $11,
                rsi_14        = $12,
                macd_hist     = $13,
                roc_5         = $14,
                roc_20        = $15,
                roc_60        = $16,
                vol_ratio_20  = $17,
                rs_vs_nifty   = $18,
                weekly_bias   = $19
            WHERE symbol = $1
        """, symbol,
            breakdown.atr_5, breakdown.adx_14,
            breakdown.plus_di, breakdown.minus_di,
            breakdown.bb_width, breakdown.kc_width,
            breakdown.bb_squeeze, breakdown.squeeze_days,
            breakdown.nr7, breakdown.atr_ratio,
            breakdown.rsi_14, breakdown.macd_hist,
            breakdown.roc_5, breakdown.roc_20, breakdown.roc_60,
            breakdown.vol_ratio_20,
            breakdown.rs_vs_nifty, breakdown.weekly_bias)

    async def get_daily_scores(
        self,
        score_date: date | None = None,
        limit: int = 50,
        watchlist_only: bool = False,
        is_fno: bool | None = None,
        offset: int = 0,
    ) -> list[dict]:
        """Fetch daily scores for dashboard display."""
        async with self._pool.acquire() as conn:
            date_clause = "ds.score_date = $1" if score_date else "ds.score_date = (SELECT MAX(score_date) FROM daily_scores)"
            watchlist_clause = "AND ds.is_watchlist = TRUE" if watchlist_only else ""
            fno_clause = "AND s.is_fno = TRUE" if is_fno is True else ("AND (s.is_fno = FALSE OR s.is_fno IS NULL)" if is_fno is False else "")

            query = f"""
                SELECT
                    ds.symbol,
                    s.company_name,
                    s.is_fno,
                    ds.score_date,
                    ds.total_score,
                    ds.momentum_score,
                    ds.trend_score,
                    ds.volatility_score,
                    ds.structure_score,
                    ds.rank,
                    ds.is_watchlist,
                    ds.computed_at,
                    sm.prev_day_close,
                    sm.atr_14,
                    sm.adv_20_cr,
                    sm.week52_high,
                    sm.week52_low,
                    sm.ema_50,
                    sm.ema_200,
                    sm.bb_squeeze,
                    sm.squeeze_days,
                    sm.nr7,
                    sm.adx_14,
                    sm.rsi_14,
                    sm.weekly_bias
                FROM daily_scores ds
                JOIN symbols s ON s.symbol = ds.symbol
                LEFT JOIN symbol_metrics sm ON sm.symbol = ds.symbol
                WHERE {date_clause}
                {watchlist_clause}
                {fno_clause}
                ORDER BY ds.rank ASC
                LIMIT ${"2" if score_date else "1"}
                OFFSET ${"3" if score_date else "2"}
            """
            params = [score_date, limit, offset] if score_date else [limit, offset]
            rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]

    async def get_daily_scores_balanced(
        self,
        score_date: date | None = None,
        per_bucket: int = 50,
        watchlist_only: bool = False,
    ) -> list[dict]:
        """
        Fetch a balanced dashboard: top N per bucket
        (bull F&O, bear F&O, bull equity, bear equity), ordered by rank.
        """
        async with self._pool.acquire() as conn:
            date_clause = "ds.score_date = $1" if score_date else "ds.score_date = (SELECT MAX(score_date) FROM daily_scores)"
            watchlist_clause = "AND ds.is_watchlist = TRUE" if watchlist_only else ""

            # $1 or ($1 unused) for date, per_bucket is always the last param
            base_cols = """
                    ds.symbol,
                    s.company_name,
                    s.is_fno,
                    ds.score_date,
                    ds.total_score,
                    ds.momentum_score,
                    ds.trend_score,
                    ds.volatility_score,
                    ds.structure_score,
                    ds.rank,
                    ds.is_watchlist,
                    ds.computed_at,
                    sm.prev_day_close,
                    sm.atr_14,
                    sm.adv_20_cr,
                    sm.week52_high,
                    sm.week52_low,
                    sm.ema_50,
                    sm.ema_200,
                    sm.bb_squeeze,
                    sm.squeeze_days,
                    sm.nr7,
                    sm.adx_14,
                    sm.rsi_14,
                    sm.weekly_bias"""
            base_join = """
                FROM daily_scores ds
                JOIN symbols s ON s.symbol = ds.symbol
                LEFT JOIN symbol_metrics sm ON sm.symbol = ds.symbol"""

            limit_param = "$2" if score_date else "$1"

            def _bucket(fno_clause: str, bias_clause: str) -> str:
                return f"""(
                    SELECT {base_cols}
                    {base_join}
                    WHERE {date_clause}
                    {watchlist_clause}
                    {fno_clause}
                    {bias_clause}
                    ORDER BY ds.rank ASC
                    LIMIT {limit_param}
                )"""

            query = " UNION ALL ".join([
                _bucket("AND s.is_fno = TRUE",  "AND sm.weekly_bias = 'BULLISH'"),
                _bucket("AND s.is_fno = TRUE",  "AND sm.weekly_bias = 'BEARISH'"),
                _bucket("AND (s.is_fno = FALSE OR s.is_fno IS NULL)", "AND sm.weekly_bias = 'BULLISH'"),
                _bucket("AND (s.is_fno = FALSE OR s.is_fno IS NULL)", "AND sm.weekly_bias = 'BEARISH'"),
            ])
            query += " ORDER BY rank ASC"

            params = [score_date, per_bucket] if score_date else [per_bucket]
            rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]

    async def get_dashboard_stats(self, score_date: date | None = None) -> dict:
        """Summary statistics for the scoring dashboard."""
        async with self._pool.acquire() as conn:
            date_clause = "score_date = $1" if score_date else "score_date = (SELECT MAX(score_date) FROM daily_scores)"
            params = [score_date] if score_date else []

            row = await conn.fetchrow(f"""
                SELECT
                    COUNT(*)                                     AS total_scored,
                    COUNT(*) FILTER (WHERE is_watchlist)         AS watchlist_count,
                    ROUND(AVG(total_score), 2)                   AS avg_score,
                    ROUND(MAX(total_score), 2)                   AS max_score,
                    ROUND(MIN(total_score), 2)                   AS min_score,
                    COUNT(*) FILTER (WHERE total_score >= 70)    AS high_conviction,
                    COUNT(*) FILTER (WHERE total_score >= 50)    AS above_average,
                    MAX(score_date)                               AS score_date,
                    MAX(computed_at)                              AS computed_at
                FROM daily_scores
                WHERE {date_clause}
            """, *params)
        return dict(row) if row else {}

    async def get_watchlist_symbols(self, score_date: date | None = None) -> list[str]:
        """Return the symbol list for the live feed watchlist."""
        async with self._pool.acquire() as conn:
            date_clause = "score_date = $1" if score_date else "score_date = (SELECT MAX(score_date) FROM daily_scores)"
            params = [score_date] if score_date else []
            rows = await conn.fetch(f"""
                SELECT symbol
                FROM daily_scores
                WHERE {date_clause} AND is_watchlist = TRUE
                ORDER BY rank ASC
            """, *params)
        return [r["symbol"] for r in rows]
