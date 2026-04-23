import logging

logger = logging.getLogger(__name__)

_STAGE_LABELS = {
    "STAGE_2": "bull",
    "STAGE_4": "bear",
}


class ScoreWatchlistMixin:
    async def build_watchlist(self, *, stage: str = "both", limit: int = 100) -> list[dict]:
        if stage == "bull":
            stage_filter = ("STAGE_2",)
        elif stage == "bear":
            stage_filter = ("STAGE_4",)
        else:
            stage_filter = ("STAGE_2", "STAGE_4")

        placeholders = ", ".join(f"${i + 2}" for i in range(len(stage_filter)))
        query = f"""
            SELECT
                ds.symbol, s.company_name, s.is_fno,
                ds.score_date, ds.total_score, ds.momentum_score,
                ds.trend_score, ds.volatility_score, ds.structure_score,
                ds.rs_vs_nifty, ds.vol_ratio_20, ds.rsi_14,
                ds.stage, ds.rank
            FROM daily_scores ds
            JOIN symbols s ON s.symbol = ds.symbol
            WHERE ds.score_date = (SELECT MAX(score_date) FROM daily_scores)
              AND ds.stage IN ({placeholders})
            ORDER BY ds.total_score DESC
            LIMIT $1
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, limit, *stage_filter)
        return [{**dict(r), "side": _STAGE_LABELS.get(r["stage"], r["stage"])} for r in rows]
