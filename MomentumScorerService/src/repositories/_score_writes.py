"""Write mixins for ScoreRepository."""

import asyncpg

from ..domain.unified_score_breakdown import UnifiedScoreBreakdown


class ScoreWriteMixin:
    _pool: asyncpg.Pool

    async def upsert_daily_score(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        score_date,
        breakdown: UnifiedScoreBreakdown,
        rank: int,
        is_watchlist: bool,
    ) -> None:
        await conn.execute("""
            INSERT INTO daily_scores (
                symbol, score_date, total_score, momentum_score, trend_score,
                volatility_score, structure_score, rank, is_watchlist, computed_at,
                rsi_14, macd_hist, roc_5, roc_20, roc_60, vol_ratio_20,
                adx_14, plus_di, minus_di, weekly_bias,
                bb_squeeze, squeeze_days, nr7,
                atr_ratio, atr_5, bb_width, kc_width, rs_vs_nifty
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(),
                $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19,
                $20, $21, $22,
                $23, $24, $25, $26, $27
            )
            ON CONFLICT (symbol, score_date) DO NOTHING
        """, symbol, score_date,
            breakdown.total_score, breakdown.momentum_score, breakdown.trend_score,
            breakdown.volatility_score, breakdown.structure_score,
            rank, is_watchlist,
            breakdown.rsi_14, breakdown.macd_hist,
            breakdown.roc_5, breakdown.roc_20, breakdown.roc_60, breakdown.vol_ratio_20,
            breakdown.adx_14, breakdown.plus_di, breakdown.minus_di, breakdown.weekly_bias,
            breakdown.bb_squeeze, breakdown.squeeze_days, breakdown.nr7,
            breakdown.atr_ratio, breakdown.atr_5, breakdown.bb_width,
            breakdown.kc_width, breakdown.rs_vs_nifty)

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
