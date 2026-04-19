"""Feature extraction functions for ComfortScorer."""

from datetime import date
from typing import Any, Dict, Optional

import numpy as np
import asyncpg


def _encode_weekly_bias(bias: Optional[str]) -> float:
    """Encode weekly bias: BULLISH=1, NEUTRAL=0, BEARISH=-1."""
    if bias == "BULLISH":
        return 1.0
    elif bias == "BEARISH":
        return -1.0
    return 0.0


async def fetch_features(
    db_pool: asyncpg.Pool,
    symbol: str,
    pred_date: date,
    context: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """Build 22-dim feature vector from daily_scores for a symbol on given date."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                total_score, momentum_score, trend_score,
                volatility_score, structure_score,
                rsi_14, macd_hist, roc_5, roc_20, roc_60, vol_ratio_20,
                adx_14, plus_di, minus_di,
                bb_squeeze, squeeze_days, nr7,
                atr_ratio, atr_5, bb_width, kc_width, rs_vs_nifty
            FROM daily_scores
            WHERE symbol = $1 AND score_date = $2
        """, symbol, pred_date)

    if not row:
        raise ValueError(f"No scores found for {symbol} on {pred_date}")

    def _f(v, default=0.0):
        return default if v is None else float(v)

    return np.array([
        _f(row['total_score']),       _f(row['momentum_score']),
        _f(row['trend_score']),       _f(row['volatility_score']),
        _f(row['structure_score']),
        _f(row['rsi_14'], 50.0),      _f(row['macd_hist']),
        _f(row['roc_5']),             _f(row['roc_20']),
        _f(row['roc_60']),            _f(row['vol_ratio_20'], 1.0),
        _f(row['adx_14']),            _f(row['plus_di']),    _f(row['minus_di']),
        1.0 if row['bb_squeeze'] else 0.0,
        _f(row['squeeze_days']),      1.0 if row['nr7'] else 0.0,
        _f(row['atr_ratio'], 1.0),    _f(row['atr_5']),
        _f(row['bb_width']),          _f(row['kc_width']),   _f(row['rs_vs_nifty']),
    ], dtype=np.float32)
