from typing import NamedTuple


class ScoreBreakdown(NamedTuple):
    score:      float
    rsi:        float
    macd_score: float
    roc_score:  float
    vol_score:  float
