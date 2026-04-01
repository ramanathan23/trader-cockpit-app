"""
Pure-pandas technical indicator implementations.
All functions accept a pd.Series and return a pd.Series of the same length.
"""

import numpy as np
import pandas as pd


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder's RSI.  Range: 0–100.
    Values > 60 indicate bullish momentum; < 40 indicate weakness.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing = EWM with com = period - 1
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


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
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def rate_of_change(prices: pd.Series, period: int = 10) -> pd.Series:
    """Percentage price change over `period` bars. Range: unbounded."""
    return (prices / prices.shift(period) - 1.0) * 100.0


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Current volume relative to rolling average.
    > 1 means above-average volume (confirms momentum).
    """
    avg = volume.rolling(period, min_periods=1).mean()
    return volume / avg.replace(0, np.nan)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — volatility measure."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()
