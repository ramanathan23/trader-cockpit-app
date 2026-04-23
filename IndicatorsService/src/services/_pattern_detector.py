"""
Daily pattern detection: VCP and Rectangle Breakout.

VCP (Volatility Contraction Pattern — Minervini):
  - Price above EMA 50 (Stage 2 context)
  - 2–3 successive range contractions, each ≤80% of prior
  - Volume declining across contractions

Rectangle Breakout:
  - Price oscillates in tight range (≤10% H-L / avg close) for 20–40 bars
  - Last bar close breaks above range high with volume confirmation
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..domain.snapshots import PatternSnapshot


def detect_patterns(symbol: str, df: pd.DataFrame, *, rect_lookback: int = 40, rect_max_range_pct: float = 0.10, vcp_min_contractions: int = 2) -> PatternSnapshot:
    vcp, vcp_n = _detect_vcp(df, min_contractions=vcp_min_contractions)
    rect, range_pct, consol_days = _detect_rect_breakout(df, lookback=rect_lookback, max_range_pct=rect_max_range_pct)
    return PatternSnapshot(
        symbol=symbol,
        vcp_detected=vcp,
        vcp_contractions=vcp_n,
        rect_breakout=rect,
        rect_range_pct=range_pct if range_pct else None,
        consolidation_days=consol_days,
    )


def _detect_vcp(df: pd.DataFrame, *, min_contractions: int = 2) -> tuple[bool, int]:
    if len(df) < 60:
        return False, 0

    tail = df.iloc[-60:].copy()
    close = tail["close"].astype(float)
    high = tail["high"].astype(float)
    low = tail["low"].astype(float)
    volume = tail["volume"].astype(float)

    ema50 = close.ewm(span=50, adjust=False).mean()
    if close.iloc[-1] < ema50.iloc[-1]:
        return False, 0

    n = len(tail)
    seg = n // 3
    segs = [tail.iloc[i * seg:(i + 1) * seg] for i in range(3)]

    ranges = [float(s["high"].max() - s["low"].min()) for s in segs]
    vol_means = [float(s["volume"].mean()) for s in segs]

    # segs[0] = most recent, segs[2] = oldest
    contractions = 0
    if ranges[0] < ranges[1] * 0.80:
        contractions += 1
    if ranges[1] < ranges[2] * 0.80:
        contractions += 1

    volume_declining = vol_means[0] < vol_means[2] * 0.85

    if contractions >= min_contractions and volume_declining:
        return True, contractions
    return False, 0


def _detect_rect_breakout(
    df: pd.DataFrame,
    *,
    lookback: int = 40,
    max_range_pct: float = 0.10,
) -> tuple[bool, float | None, int]:
    if len(df) < lookback + 2:
        return False, None, 0

    consol = df.iloc[-(lookback + 1):-1]
    last = df.iloc[-1]

    max_h = float(consol["high"].max())
    min_l = float(consol["low"].min())
    avg_c = float(consol["close"].mean())

    if avg_c <= 0:
        return False, None, 0

    range_pct = (max_h - min_l) / avg_c
    range_pct_rounded = round(range_pct * 100, 2)

    if range_pct > max_range_pct:
        return False, range_pct_rounded, 0

    last_close = float(last["close"])
    avg_vol = float(consol["volume"].mean())
    last_vol = float(last["volume"])

    if last_close > max_h and avg_vol > 0 and last_vol > avg_vol * 1.2:
        return True, range_pct_rounded, len(consol)

    return False, range_pct_rounded, 0
