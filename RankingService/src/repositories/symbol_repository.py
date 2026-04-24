"""
Reads pre-computed indicator + structural data for all ranked symbols.
RankingService never accesses raw OHLCV — indicators come from IndicatorsService.
"""
from decimal import Decimal

import asyncpg


def _coerce(v):
    """asyncpg returns Decimal for NUMERIC columns; scorers need float."""
    return float(v) if isinstance(v, Decimal) else v


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_ranked_candidates(self, *, min_adv_crores: float = 1.0) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    si.symbol,
                    COALESCE(s.is_fno, FALSE)  AS is_fno,
                    si.rsi_14, si.macd_hist, si.macd_hist_std,
                    si.roc_5, si.roc_20, si.roc_60, si.vol_ratio_20,
                    si.adx_14, si.plus_di, si.minus_di, si.weekly_bias,
                    si.bb_squeeze, si.squeeze_days, si.nr7,
                    si.atr_ratio, si.atr_5, si.bb_width, si.kc_width,
                    si.rs_vs_nifty, si.stage,
                    sm.prev_day_close, sm.week52_high, sm.week52_low,
                    sm.ema_20, sm.ema_50, sm.ema_200, sm.adv_20_cr
                FROM symbol_indicators si
                JOIN symbol_metrics sm ON sm.symbol = si.symbol
                JOIN symbols s ON s.symbol = si.symbol
                WHERE COALESCE(sm.adv_20_cr, 0) >= $1
            """, min_adv_crores)
        return [{k: _coerce(v) for k, v in dict(r).items()} for r in rows]

    async def fetch_candidate_counts(self, *, min_adv_crores: float = 1.0) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    (SELECT COUNT(*) FROM symbol_indicators)                                         AS total_indicators,
                    (SELECT COUNT(*) FROM symbol_metrics)                                            AS total_metrics,
                    (SELECT COUNT(*) FROM symbol_indicators si JOIN symbol_metrics sm ON sm.symbol = si.symbol) AS joined,
                    (SELECT COUNT(*) FROM symbol_indicators si JOIN symbol_metrics sm ON sm.symbol = si.symbol
                       WHERE COALESCE(sm.adv_20_cr, 0) >= $1)                                       AS after_adv_filter
            """, min_adv_crores)
        return dict(row)
