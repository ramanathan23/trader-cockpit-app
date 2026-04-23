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
                atr_ratio, atr_5, bb_width, kc_width, rs_vs_nifty, stage
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(),
                $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19,
                $20, $21, $22,
                $23, $24, $25, $26, $27, $28
            )
            ON CONFLICT (symbol, score_date) DO UPDATE SET
                total_score      = EXCLUDED.total_score,
                momentum_score   = EXCLUDED.momentum_score,
                trend_score      = EXCLUDED.trend_score,
                volatility_score = EXCLUDED.volatility_score,
                structure_score  = EXCLUDED.structure_score,
                rank             = EXCLUDED.rank,
                is_watchlist     = EXCLUDED.is_watchlist,
                computed_at      = NOW(),
                rsi_14           = EXCLUDED.rsi_14,
                macd_hist        = EXCLUDED.macd_hist,
                roc_5            = EXCLUDED.roc_5,
                roc_20           = EXCLUDED.roc_20,
                roc_60           = EXCLUDED.roc_60,
                vol_ratio_20     = EXCLUDED.vol_ratio_20,
                adx_14           = EXCLUDED.adx_14,
                plus_di          = EXCLUDED.plus_di,
                minus_di         = EXCLUDED.minus_di,
                weekly_bias      = EXCLUDED.weekly_bias,
                bb_squeeze       = EXCLUDED.bb_squeeze,
                squeeze_days     = EXCLUDED.squeeze_days,
                nr7              = EXCLUDED.nr7,
                atr_ratio        = EXCLUDED.atr_ratio,
                atr_5            = EXCLUDED.atr_5,
                bb_width         = EXCLUDED.bb_width,
                kc_width         = EXCLUDED.kc_width,
                rs_vs_nifty      = EXCLUDED.rs_vs_nifty,
                stage            = EXCLUDED.stage
        """, symbol, score_date,
            breakdown.total_score, breakdown.momentum_score, breakdown.trend_score,
            breakdown.volatility_score, breakdown.structure_score,
            rank, is_watchlist,
            breakdown.rsi_14, breakdown.macd_hist,
            breakdown.roc_5, breakdown.roc_20, breakdown.roc_60, breakdown.vol_ratio_20,
            breakdown.adx_14, breakdown.plus_di, breakdown.minus_di, breakdown.weekly_bias,
            breakdown.bb_squeeze, breakdown.squeeze_days, breakdown.nr7,
            breakdown.atr_ratio, breakdown.atr_5, breakdown.bb_width,
            breakdown.kc_width, breakdown.rs_vs_nifty, breakdown.stage)

