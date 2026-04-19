"""Forward comfort score computation from future price data."""

import logging
from datetime import date

import pandas as pd
import asyncpg

from ._normalizers import normalize_return, normalize_drawdown, normalize_volatility

logger = logging.getLogger(__name__)


async def compute_forward_comfort(
    db_pool: asyncpg.Pool,
    symbol: str,
    prediction_date: date,
) -> float | None:
    """
    Compute comfort score from next 5 trading days.

    Comfort = weighted average of:
    - Return quality (40%)
    - Drawdown quality (30%)
    - Volatility quality (20%)
    - Momentum sustained (10%)
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT date, open, high, low, close, volume
            FROM price_data_daily
            WHERE symbol = $1 AND date > $2
            ORDER BY date
            LIMIT 5
        """, symbol, prediction_date)

    if len(rows) < 5:
        return None

    df = pd.DataFrame(rows)
    returns = df['close'].pct_change().dropna()
    total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100

    max_dd = 0.0
    peak = df['close'].iloc[0]
    for _, row in df.iterrows():
        peak = max(peak, row['high'])
        dd = (row['low'] - peak) / peak * 100
        max_dd = min(max_dd, dd)

    volatility = returns.std() * 100
    momentum_sustained = 1.0 if df['close'].iloc[-1] > df['close'].iloc[0] else 0.0

    comfort = (
        0.40 * normalize_return(total_return) +
        0.30 * normalize_drawdown(abs(max_dd)) +
        0.20 * normalize_volatility(volatility) +
        0.10 * momentum_sustained * 100
    )

    return round(float(comfort), 2)
