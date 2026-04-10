from dataclasses import dataclass
from typing import Literal, NamedTuple


class ScoreBreakdown(NamedTuple):
    score:      float
    rsi:        float
    macd_score: float
    roc_score:  float
    vol_score:  float


@dataclass(frozen=True)
class WatchlistCandidate:
    symbol: str
    company_name: str | None
    side: Literal["bull", "bear"]
    pattern_score: float
    run_move_pct: float
    base_range_pct: float
    retracement_pct: float
    distance_to_trigger_pct: float
    volume_contraction: float
    trigger_price: float
    last_close: float
