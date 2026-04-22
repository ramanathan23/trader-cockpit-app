"""Read mixin for ScoreRepository — balanced dashboard query."""

from datetime import date

import asyncpg


class ScoreReadBalancedMixin:
    _pool: asyncpg.Pool

    async def get_daily_scores_balanced(
        self,
        score_date: date | None = None,
        per_bucket: int = 50,
        watchlist_only: bool = False,
    ) -> list[dict]:
        """
        Fetch a balanced dashboard: top N per bucket (FNO, equity), all stages.
        """
        async with self._pool.acquire() as conn:
            date_clause = "ds.score_date = $1" if score_date else "ds.score_date = (SELECT MAX(score_date) FROM daily_scores)"
            watchlist_clause = "AND ds.is_watchlist = TRUE" if watchlist_only else ""

            base_cols = """
                    ds.symbol, s.company_name, s.is_fno, ds.score_date,
                    ds.total_score, ds.momentum_score, ds.trend_score,
                    ds.volatility_score, ds.structure_score, ds.rank,
                    ds.is_watchlist, ds.computed_at, ds.stage,
                    sm.prev_day_close, sm.atr_14, sm.adv_20_cr,
                    sm.week52_high, sm.week52_low, sm.ema_50, sm.ema_200,
                    sm.bb_squeeze, sm.squeeze_days, sm.nr7,
                    sm.adx_14, sm.rsi_14, sm.weekly_bias,
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
                    END AS is_new_watchlist"""
            base_join = """
                FROM daily_scores ds
                JOIN symbols s ON s.symbol = ds.symbol
                LEFT JOIN symbol_metrics sm ON sm.symbol = ds.symbol
                LEFT JOIN model_predictions mp ON mp.symbol = ds.symbol
                    AND mp.model_name = 'comfort_scorer'
                    AND mp.prediction_date = ds.score_date"""

            limit_param = "$2" if score_date else "$1"

            def _bucket(fno_clause: str) -> str:
                return f"""(
                    SELECT {base_cols}
                    {base_join}
                    WHERE {date_clause}
                    {watchlist_clause}
                    {fno_clause}
                    ORDER BY ds.rank ASC
                    LIMIT {limit_param}
                )"""

            query = " UNION ALL ".join([
                _bucket("AND s.is_fno = TRUE"),
                _bucket("AND (s.is_fno = FALSE OR s.is_fno IS NULL)"),
            ])
            query += " ORDER BY rank ASC"

            params = [score_date, per_bucket] if score_date else [per_bucket]
            rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]
