import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, ROCIndicator
from ta.trend import MACD


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
