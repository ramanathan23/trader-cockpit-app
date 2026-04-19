"""
Technical indicator implementations backed by the `ta` library.

All functions accept a pd.Series and return a pd.Series of the same length,
preserving the index.

`ta` docs: https://technical-analysis-library-in-python.readthedocs.io/
"""

from ._indicators_momentum import macd, rate_of_change, rsi, volume_ratio
from ._indicators_trend import adx
from ._indicators_volatility import (
    atr,
    bollinger_squeeze,
    bollinger_width,
    keltner_width,
    narrowest_range,
    squeeze_days,
)

__all__ = [
    "adx", "atr", "bollinger_squeeze", "bollinger_width",
    "keltner_width", "macd", "narrowest_range", "rate_of_change",
    "rsi", "squeeze_days", "volume_ratio",
]
