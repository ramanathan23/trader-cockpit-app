import asyncpg

from ..domain.snapshots import IndicatorSnapshot, MetricsSnapshot, PatternSnapshot


class IndicatorRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_metrics_batch(self, snapshots: list[MetricsSnapshot]) -> int:
        if not snapshots:
            return 0
        records = [
            (
                s.symbol, s.week52_high, s.week52_low, s.atr_14, s.adv_20_cr,
                s.trading_days, s.prev_day_high, s.prev_day_low, s.prev_day_close,
                s.prev_week_high, s.prev_week_low, s.prev_month_high, s.prev_month_low,
                s.ema_20, s.ema_50, s.ema_200,
                s.week_return_pct, s.week_gain_pct, s.week_decline_pct,
                s.cam_median_range_pct,
            )
            for s in snapshots
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO symbol_metrics (
                    symbol, computed_at,
                    week52_high, week52_low, atr_14, adv_20_cr, trading_days,
                    prev_day_high, prev_day_low, prev_day_close,
                    prev_week_high, prev_week_low, prev_month_high, prev_month_low,
                    ema_20, ema_50, ema_200,
                    week_return_pct, week_gain_pct, week_decline_pct,
                    cam_median_range_pct
                ) VALUES (
                    $1, NOW(),
                    $2, $3, $4, $5, $6,
                    $7, $8, $9,
                    $10, $11, $12, $13,
                    $14, $15, $16,
                    $17, $18, $19,
                    $20
                )
                ON CONFLICT (symbol) DO UPDATE SET
                    computed_at          = NOW(),
                    week52_high          = EXCLUDED.week52_high,
                    week52_low           = EXCLUDED.week52_low,
                    atr_14               = EXCLUDED.atr_14,
                    adv_20_cr            = EXCLUDED.adv_20_cr,
                    trading_days         = EXCLUDED.trading_days,
                    prev_day_high        = EXCLUDED.prev_day_high,
                    prev_day_low         = EXCLUDED.prev_day_low,
                    prev_day_close       = EXCLUDED.prev_day_close,
                    prev_week_high       = EXCLUDED.prev_week_high,
                    prev_week_low        = EXCLUDED.prev_week_low,
                    prev_month_high      = EXCLUDED.prev_month_high,
                    prev_month_low       = EXCLUDED.prev_month_low,
                    ema_20               = EXCLUDED.ema_20,
                    ema_50               = EXCLUDED.ema_50,
                    ema_200              = EXCLUDED.ema_200,
                    week_return_pct      = EXCLUDED.week_return_pct,
                    week_gain_pct        = EXCLUDED.week_gain_pct,
                    week_decline_pct     = EXCLUDED.week_decline_pct,
                    cam_median_range_pct = EXCLUDED.cam_median_range_pct
            """, records)
        return len(records)

    async def upsert_indicators_batch(self, snapshots: list[IndicatorSnapshot]) -> int:
        if not snapshots:
            return 0
        records = [
            (
                s.symbol,
                s.rsi_14, s.macd_hist, s.macd_hist_std,
                s.roc_5, s.roc_20, s.roc_60, s.vol_ratio_20,
                s.adx_14, s.plus_di, s.minus_di, s.weekly_bias,
                s.bb_squeeze, s.squeeze_days, s.nr7,
                s.atr_ratio, s.atr_5, s.bb_width, s.kc_width,
                s.rs_vs_nifty, s.stage,
            )
            for s in snapshots
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO symbol_indicators (
                    symbol, computed_at,
                    rsi_14, macd_hist, macd_hist_std,
                    roc_5, roc_20, roc_60, vol_ratio_20,
                    adx_14, plus_di, minus_di, weekly_bias,
                    bb_squeeze, squeeze_days, nr7,
                    atr_ratio, atr_5, bb_width, kc_width,
                    rs_vs_nifty, stage
                ) VALUES (
                    $1, NOW(),
                    $2, $3, $4, $5, $6, $7, $8,
                    $9, $10, $11, $12,
                    $13, $14, $15,
                    $16, $17, $18, $19,
                    $20, $21
                )
                ON CONFLICT (symbol) DO UPDATE SET
                    computed_at   = NOW(),
                    rsi_14        = EXCLUDED.rsi_14,
                    macd_hist     = EXCLUDED.macd_hist,
                    macd_hist_std = EXCLUDED.macd_hist_std,
                    roc_5         = EXCLUDED.roc_5,
                    roc_20        = EXCLUDED.roc_20,
                    roc_60        = EXCLUDED.roc_60,
                    vol_ratio_20  = EXCLUDED.vol_ratio_20,
                    adx_14        = EXCLUDED.adx_14,
                    plus_di       = EXCLUDED.plus_di,
                    minus_di      = EXCLUDED.minus_di,
                    weekly_bias   = EXCLUDED.weekly_bias,
                    bb_squeeze    = EXCLUDED.bb_squeeze,
                    squeeze_days  = EXCLUDED.squeeze_days,
                    nr7           = EXCLUDED.nr7,
                    atr_ratio     = EXCLUDED.atr_ratio,
                    atr_5         = EXCLUDED.atr_5,
                    bb_width      = EXCLUDED.bb_width,
                    kc_width      = EXCLUDED.kc_width,
                    rs_vs_nifty   = EXCLUDED.rs_vs_nifty,
                    stage         = EXCLUDED.stage
            """, records)
        return len(records)

    async def upsert_patterns_batch(self, snapshots: list[PatternSnapshot]) -> int:
        if not snapshots:
            return 0
        records = [
            (
                s.symbol,
                s.vcp_detected, s.vcp_contractions,
                s.rect_breakout, s.rect_range_pct, s.consolidation_days,
            )
            for s in snapshots
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO symbol_patterns (
                    symbol, computed_at,
                    vcp_detected, vcp_contractions,
                    rect_breakout, rect_range_pct, consolidation_days
                ) VALUES ($1, NOW(), $2, $3, $4, $5, $6)
                ON CONFLICT (symbol) DO UPDATE SET
                    computed_at        = NOW(),
                    vcp_detected       = EXCLUDED.vcp_detected,
                    vcp_contractions   = EXCLUDED.vcp_contractions,
                    rect_breakout      = EXCLUDED.rect_breakout,
                    rect_range_pct     = EXCLUDED.rect_range_pct,
                    consolidation_days = EXCLUDED.consolidation_days
            """, records)
        return len(records)
