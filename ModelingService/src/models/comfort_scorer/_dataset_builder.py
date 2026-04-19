"""Training dataset builder for ComfortScorer."""

import logging
from datetime import date, timedelta
from typing import Tuple

import numpy as np
import pandas as pd
import asyncpg

from ._comfort_target import compute_comfort_from_slice
from ._normalizers import extract_features_from_row

logger = logging.getLogger(__name__)


async def build_dataset(
    db_pool: asyncpg.Pool,
    start_date: date,
    end_date: date,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Build training dataset from historical scores + forward outcomes.

    Uses two bulk queries (scores + forward prices) instead of one query per
    sample — O(1) DB round-trips regardless of dataset size.
    """
    logger.info(f"Building training dataset: {start_date} to {end_date}")

    # ── 1. Fetch all scored rows in window ────────────────────────────────────
    async with db_pool.acquire() as conn:
        score_rows = await conn.fetch("""
            SELECT
                ds.symbol, ds.score_date,
                ds.total_score, ds.momentum_score, ds.trend_score,
                ds.volatility_score, ds.structure_score,
                ds.rsi_14, ds.macd_hist, ds.roc_5, ds.roc_20, ds.roc_60,
                ds.vol_ratio_20, ds.adx_14, ds.plus_di, ds.minus_di,
                ds.weekly_bias, ds.bb_squeeze, ds.squeeze_days, ds.nr7,
                ds.atr_ratio, ds.atr_5, ds.bb_width, ds.kc_width,
                ds.rs_vs_nifty
            FROM daily_scores ds
            WHERE ds.score_date >= $1
              AND ds.score_date <= $2
              AND ds.total_score > 50
              AND ds.rsi_14 IS NOT NULL
            ORDER BY ds.score_date, ds.symbol
        """, start_date, end_date)

    if not score_rows:
        logger.info("No scored samples found")
        return pd.DataFrame(), pd.Series(name='comfort_score')

    logger.info(f"Found {len(score_rows)} scored samples — fetching forward prices...")

    # ── 2. Bulk fetch all forward prices needed (one query) ───────────────────
    # Need up to 5 trading days after each score_date; add a 14-day calendar buffer.
    fwd_end = end_date + timedelta(days=14)
    symbols = list({r['symbol'] for r in score_rows})

    async with db_pool.acquire() as conn:
        price_rows = await conn.fetch("""
            SELECT symbol, time::date AS dt,
                   open::float, high::float, low::float, close::float, volume::float
            FROM price_data_daily
            WHERE symbol = ANY($1)
              AND time::date > $2
              AND time::date <= $3
            ORDER BY symbol, time
        """, symbols, start_date, fwd_end)

    # Build lookup: symbol → sorted list of (dt, open, high, low, close)
    price_df = pd.DataFrame(
        [(r['symbol'], r['dt'], r['open'], r['high'], r['low'], r['close'])
         for r in price_rows],
        columns=['symbol', 'dt', 'open', 'high', 'low', 'close'],
    )
    price_df['dt'] = pd.to_datetime(price_df['dt']).dt.date
    price_df = price_df.sort_values(['symbol', 'dt'])

    # Group by symbol — store as numpy arrays for O(log n) date lookup
    price_by_symbol: dict[str, tuple] = {}  # sym → (date_array, df)
    for sym, grp in price_df.groupby('symbol', sort=False):
        grp = grp.sort_values('dt').reset_index(drop=True)
        price_by_symbol[sym] = (np.array(grp['dt'].tolist()), grp)

    # ── 3. Compute comfort targets in-memory (O(n log n)) ────────────────────
    X_data: list = []
    y_data: list = []

    for row in score_rows:
        sym      = row['symbol']
        score_dt = row['score_date']
        entry    = price_by_symbol.get(sym)
        if entry is None:
            continue

        date_arr, sym_prices = entry
        # Binary search: first index where date > score_dt
        idx = int(np.searchsorted(date_arr, score_dt, side='right'))
        fwd = sym_prices.iloc[idx:idx + 5]
        comfort = compute_comfort_from_slice(fwd)
        if comfort is None:
            continue

        X_data.append(extract_features_from_row(row))
        y_data.append(comfort)

    logger.info(f"Built {len(X_data)} training samples")
    return pd.DataFrame(X_data), pd.Series(y_data, name='comfort_score')
