"""
Technical indicator implementations backed by the `ta` library.

All functions accept a pd.Series and return a pd.Series of the same length,
preserving the index. Implementations delegate to battle-tested ta classes
rather than re-implementing rolling/EWM logic by hand.

`ta` docs: https://technical-analysis-library-in-python.readthedocs.io/
"""

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, ROCIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder's RSI — Range: 0–100.
    Values > 60 indicate bullish momentum; < 40 indicate weakness.
    """
    return RSIIndicator(close=prices, window=period).rsi()


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Returns (macd_line, signal_line, histogram).
    Positive histogram = bullish momentum acceleration.
    """
    m = MACD(close=prices, window_slow=slow, window_fast=fast, window_sign=signal)
    return m.macd(), m.macd_signal(), m.macd_diff()


def rate_of_change(prices: pd.Series, period: int = 10) -> pd.Series:
    """Percentage price change over `period` bars. Range: unbounded."""
    return ROCIndicator(close=prices, window=period).roc()


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Current volume relative to its rolling average.
    > 1 means above-average volume (confirms momentum).
    """
    avg = volume.rolling(period, min_periods=1).mean()
    return volume / avg.replace(0, np.nan)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — volatility measure."""
    return AverageTrueRange(high=high, low=low, close=close, window=period).average_true_range()
