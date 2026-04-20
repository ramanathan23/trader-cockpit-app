"""Read mixin for ScoreRepository — basic lookups."""

from datetime import date

import asyncpg


class ScoreReadMixin:
    _pool: asyncpg.Pool

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
                    ds.symbol, s.company_name, s.is_fno, ds.score_date,
                    ds.total_score, ds.momentum_score, ds.trend_score,
                    ds.volatility_score, ds.structure_score, ds.rank,
                    ds.is_watchlist, ds.computed_at,
                    sm.prev_day_close, sm.atr_14, sm.adv_20_cr,
                    sm.week52_high, sm.week52_low, sm.ema_50, sm.ema_200,
                    ds.bb_squeeze, ds.squeeze_days, ds.nr7,
                    ds.adx_14, ds.rsi_14, ds.weekly_bias,
                    (mp.predictions->>'comfort_score')::numeric AS comfort_score,
                    mp.predictions->>'interpretation' AS comfort_interpretation,
                    CASE
                        WHEN ds.is_watchlist
                             AND NOT EXISTS (
                                SELECT 1
                                FROM daily_scores prev_ds
                                WHERE prev_ds.symbol = ds.symbol
                                  AND prev_ds.is_watchlist = TRUE
                                  AND prev_ds.score_date >= ds.score_date - 7
                                  AND prev_ds.score_date < ds.score_date
                             )
                        THEN TRUE
                        ELSE FALSE
                    END AS is_new_watchlist
                FROM daily_scores ds
                JOIN symbols s ON s.symbol = ds.symbol
                LEFT JOIN symbol_metrics sm ON sm.symbol = ds.symbol
                LEFT JOIN model_predictions mp ON mp.symbol = ds.symbol
                    AND mp.model_name = 'comfort_scorer'
                    AND mp.prediction_date = ds.score_date
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
