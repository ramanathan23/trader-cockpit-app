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
                    ds.is_watchlist, ds.computed_at, ds.stage,
                    sm.prev_day_close, sm.atr_14, sm.adv_20_cr,
                    sm.week52_high, sm.week52_low, sm.ema_50, sm.ema_200,
                    ds.bb_squeeze, ds.squeeze_days, ds.nr7,
                    ds.adx_14, ds.rsi_14, ds.weekly_bias,
                    COALESCE(
                        (mp.predictions->>'comfort_score_v3')::numeric,
                        (mp.predictions->>'comfort_score')::numeric
                    ) AS comfort_score,
                    (mp.predictions->>'comfort_score_v2')::numeric AS comfort_score_v2,
                    (mp.predictions->>'comfort_score_v3')::numeric AS comfort_score_v3,
                    mp.predictions->>'interpretation' AS comfort_interpretation,
                    isp.session_type_pred,
                    isp.trend_up_prob,
                    isp.chop_prob,
                    isp.pullback_depth_pred,
                    sip.iss_score,
                    sip.choppiness_idx,
                    sip.stop_hunt_rate,
                    sip.pullback_depth_on_up_days AS pullback_depth_hist,
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
                LEFT JOIN intraday_session_predictions isp
                    ON isp.symbol = ds.symbol AND isp.prediction_date = ds.score_date
                LEFT JOIN symbol_intraday_profile sip
                    ON sip.symbol = ds.symbol
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
            date_clause = "ds.score_date = $1" if score_date else "ds.score_date = (SELECT MAX(score_date) FROM daily_scores)"
            params = [score_date] if score_date else []

            row = await conn.fetchrow(f"""
                SELECT
                    COUNT(*)                                      AS total_scored,
                    COUNT(*) FILTER (WHERE ds.is_watchlist)       AS watchlist_count,
                    ROUND(AVG(ds.total_score), 2)                 AS avg_score,
                    ROUND(MAX(ds.total_score), 2)                 AS max_score,
                    ROUND(MIN(ds.total_score), 2)                 AS min_score,
                    COUNT(*) FILTER (WHERE ds.total_score >= 70)  AS high_conviction,
                    COUNT(*) FILTER (WHERE ds.total_score >= 50)  AS above_average,
                    ROUND(AVG(sip.iss_score), 2)                 AS avg_iss_score,
                    COUNT(*) FILTER (WHERE ds.is_watchlist AND sip.iss_score < 40)
                                                                  AS low_iss_watchlist_count,
                    MAX(ds.score_date)                            AS score_date,
                    MAX(ds.computed_at)                           AS computed_at
                FROM daily_scores ds
                LEFT JOIN symbol_intraday_profile sip ON sip.symbol = ds.symbol
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
