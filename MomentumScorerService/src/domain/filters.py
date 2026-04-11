"""
Liquidity filters — pure functions, no I/O.

Single responsibility: determine whether a symbol meets quality thresholds
before it is scored or included in a watchlist.
"""
import pandas as pd


def is_liquid(df: pd.DataFrame, min_avg_daily_turnover: float) -> bool:
    """
    Return True when the symbol's 20-day average turnover meets the threshold.

    Turnover is approximated as close × volume over the last 20 bars,
    reflecting recent liquidity rather than a stale historical average.

    Parameters
    ----------
    df                     : OHLCV DataFrame with 'close' and 'volume' columns
    min_avg_daily_turnover : minimum acceptable average daily turnover (INR)
    """
    avg_turnover = (
        df["close"].astype(float) * df["volume"].astype(float)
    ).tail(20).mean()
    return float(avg_turnover) >= min_avg_daily_turnover
