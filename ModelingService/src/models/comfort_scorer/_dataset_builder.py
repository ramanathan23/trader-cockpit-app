"""Training dataset builder for ComfortScorer."""

import logging
from datetime import date
from typing import Tuple

import pandas as pd
import asyncpg

from ._comfort_target import compute_forward_comfort
from ._normalizers import extract_features_from_row

logger = logging.getLogger(__name__)


async def build_dataset(
    db_pool: asyncpg.Pool,
    start_date: date,
    end_date: date,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Build training dataset from historical scores + forward outcomes."""
    logger.info(f"Building training dataset: {start_date} to {end_date}")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                ds.symbol, ds.score_date,
                ds.total_score, ds.momentum_score, ds.trend_score,
                ds.volatility_score, ds.structure_score,
                sm.rsi_14, sm.macd_hist, sm.roc_5, sm.roc_20, sm.roc_60,
                sm.vol_ratio_20, sm.adx_14, sm.plus_di, sm.minus_di,
                sm.weekly_bias, sm.bb_squeeze, sm.squeeze_days, sm.nr7,
                sm.atr_ratio, sm.atr_5, sm.bb_width, sm.kc_width,
                sm.rs_vs_nifty
            FROM daily_scores ds
            LEFT JOIN symbol_metrics sm ON ds.symbol = sm.symbol
            WHERE ds.score_date >= $1
              AND ds.score_date <= $2
              AND ds.total_score > 50
            ORDER BY ds.score_date, ds.symbol
        """, start_date, end_date)

    logger.info(f"Found {len(rows)} scored samples")

    X_data: list = []
    y_data: list = []

    for row in rows:
        comfort = await compute_forward_comfort(db_pool, row['symbol'], row['score_date'])
        if comfort is None:
            continue
        X_data.append(extract_features_from_row(row))
        y_data.append(comfort)

    logger.info(f"Built {len(X_data)} training samples")
    return pd.DataFrame(X_data), pd.Series(y_data, name='comfort_score')
