from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from statistics import mean


class Regime(StrEnum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    CHOPPY = "CHOPPY"
    SQUEEZE = "SQUEEZE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RegimeState:
    regime: Regime
    choppiness: float
    autocorr: float
    above_vwap: bool
    bar_range_ratio: float


WINDOW = 20


def detect_regime(bars: list) -> RegimeState:
    if len(bars) < WINDOW:
        return RegimeState(Regime.UNKNOWN, 61.8, 0.0, True, 1.0)

    recent = bars[-WINDOW:]
    closes = [float(b.close) for b in recent]
    highs = [float(b.high) for b in recent]
    lows = [float(b.low) for b in recent]

    tr_sum = sum(highs[i] - lows[i] for i in range(min(14, len(recent))))
    h_max = max(highs)
    l_min = min(lows)
    chop = min(100.0, max(0.0, tr_sum * 14 / (h_max - l_min + 1e-8)))

    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] != 0
    ]
    autocorr = _lag1_autocorr(returns)

    total_vol = sum(max(0, int(getattr(b, "volume", 0))) for b in bars)
    vwap = sum(float(b.close) * max(0, int(getattr(b, "volume", 0))) for b in bars) / max(total_vol, 1)
    above_vwap = float(bars[-1].close) > vwap

    avg_range = mean(max(0.0, highs[i] - lows[i]) for i in range(WINDOW))
    cur_range = float(bars[-1].high) - float(bars[-1].low)
    range_ratio = cur_range / max(avg_range, 1e-8)

    if chop < 40 and autocorr > 0.15:
        regime = Regime.TRENDING_UP if above_vwap else Regime.TRENDING_DOWN
    elif range_ratio < 0.3:
        regime = Regime.SQUEEZE
    elif chop > 61.8 or autocorr < -0.10:
        regime = Regime.CHOPPY
    else:
        regime = Regime.NEUTRAL

    return RegimeState(regime, round(chop, 4), round(autocorr, 4), above_vwap, round(range_ratio, 4))


def _lag1_autocorr(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    x = values[:-1]
    y = values[1:]
    mx = mean(x)
    my = mean(y)
    denom_x = sum((v - mx) ** 2 for v in x)
    denom_y = sum((v - my) ** 2 for v in y)
    denom = (denom_x * denom_y) ** 0.5
    if denom <= 1e-12:
        return 0.0
    return max(-1.0, min(1.0, sum((a - mx) * (b - my) for a, b in zip(x, y)) / denom))
