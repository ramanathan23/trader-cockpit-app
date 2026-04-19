"""Forward comfort score computation from future price data."""

import logging
from datetime import date

import pandas as pd
import asyncpg

from ._normalizers import normalize_return, normalize_drawdown, normalize_volatility

logger = logging.getLogger(__name__)


def compute_comfort_from_slice(fwd: pd.DataFrame) -> float | None:
    """
    Compute comfort score from a pre-sliced DataFrame of the next 5 trading days.

    Expects columns: open, high, low, close (numeric).
    Returns None when fewer than 5 rows are available.
    """
    if len(fwd) < 5:
        return None

    close = fwd['close'].astype(float)
    high  = fwd['high'].astype(float)
    low   = fwd['low'].astype(float)

    returns      = close.pct_change().dropna()
    total_return = (close.iloc[-1] / close.iloc[0] - 1) * 100

    max_dd = 0.0
    peak   = float(close.iloc[0])
    for h, l in zip(high, low):
        peak   = max(peak, float(h))
        dd     = (float(l) - peak) / peak * 100
        max_dd = min(max_dd, dd)

    volatility         = float(returns.std()) * 100
    momentum_sustained = 1.0 if close.iloc[-1] > close.iloc[0] else 0.0

    comfort = (
        0.40 * normalize_return(total_return) +
        0.30 * normalize_drawdown(abs(max_dd)) +
        0.20 * normalize_volatility(volatility) +
        0.10 * momentum_sustained * 100
    )
    return round(float(comfort), 2)


async def compute_forward_comfort(
    db_pool: asyncpg.Pool,
    symbol: str,
    prediction_date: date,
) -> float | None:
    """
    Compute comfort score from next 5 trading days (single-symbol async version).
    Kept for backward compatibility — prefer compute_comfort_from_slice for bulk use.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT time::date AS dt, open::float, high::float, low::float, close::float
            FROM price_data_daily
            WHERE symbol = $1 AND time::date > $2
            ORDER BY time
            LIMIT 5
        """, symbol, prediction_date)

    if len(rows) < 5:
        return None

    fwd = pd.DataFrame([dict(r) for r in rows])
    return compute_comfort_from_slice(fwd)
