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
from ta.trend import MACD, ADXIndicator
from ta.volatility import AverageTrueRange, BollingerBands, KeltnerChannel


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


# ── Extended indicators for unified scoring ──────────────────────────────────

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index.
    Returns (adx, +DI, -DI).
    ADX > 25 = trending, ADX < 20 = choppy.
    """
    ind = ADXIndicator(high=high, low=low, close=close, window=period)
    return ind.adx(), ind.adx_pos(), ind.adx_neg()


def bollinger_width(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    """Bollinger Band width = (upper - lower) / middle. Lower = tighter squeeze."""
    bb = BollingerBands(close=close, window=period, window_dev=std_dev)
    mid = bb.bollinger_mavg()
    return (bb.bollinger_hband() - bb.bollinger_lband()) / mid.replace(0, np.nan)


def keltner_width(
    high: pd.Series, low: pd.Series, close: pd.Series,
    period: int = 20, atr_mult: float = 1.5,
) -> pd.Series:
    """Keltner Channel width = (upper - lower) / middle."""
    kc = KeltnerChannel(high=high, low=low, close=close, window=period, window_atr=period,
                        multiplier=atr_mult, original_version=False)
    mid = kc.keltner_channel_mband()
    return (kc.keltner_channel_hband() - kc.keltner_channel_lband()) / mid.replace(0, np.nan)


def bollinger_squeeze(
    high: pd.Series, low: pd.Series, close: pd.Series,
    bb_period: int = 20, bb_std: float = 2.0,
    kc_period: int = 20, kc_mult: float = 1.5,
) -> pd.Series:
    """
    Bollinger Squeeze: True when BB width < KC width (volatility contracted inside Keltner).
    Returns boolean Series.
    """
    bw = bollinger_width(close, bb_period, bb_std)
    kw = keltner_width(high, low, close, kc_period, kc_mult)
    return bw < kw


def squeeze_days(squeeze_series: pd.Series) -> int:
    """Count consecutive True days at the end of a boolean squeeze series."""
    vals = squeeze_series.values
    count = 0
    for i in range(len(vals) - 1, -1, -1):
        if vals[i]:
            count += 1
        else:
            break
    return count


def narrowest_range(high: pd.Series, low: pd.Series, window: int = 7) -> bool:
    """NR7 (or NRn): True when today's range is strictly the narrowest of the last `window` bars."""
    if len(high) < window:
        return False
    ranges = (high - low).iloc[-window:]
    today = ranges.iloc[-1]
    prior = ranges.iloc[:-1]
    return bool(today < prior.min())
