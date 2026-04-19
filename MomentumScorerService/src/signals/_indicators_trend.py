import pandas as pd
from ta.trend import ADXIndicator


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index.
    Returns (adx, +DI, -DI).
    ADX > 25 = trending, ADX < 20 = choppy.
    """
    ind = ADXIndicator(high=high, low=low, close=close, window=period)
    return ind.adx(), ind.adx_pos(), ind.adx_neg()
