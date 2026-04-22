"""
Multi-timeframe bias: derives 15-min and 1-hr directional bias from 5-min candle history.

Since 15 min = 3 × 5-min candles and 1 hr = 12 × 5-min candles, we can roll up
the in-memory 5-min history without building separate CandleBuilders.

Algorithm
---------
For each window (N most recent 5-min candles):
  - aggregate_open  = first candle open
  - aggregate_close = last candle close
  - aggregate_high  = max(all highs)
  - aggregate_low   = min(all lows)

Direction is then:
  - BULLISH  if close > open  (+threshold)
  - BEARISH  if close < open  (-threshold)
  - NEUTRAL  otherwise or if not enough candles

Confluence rules applied in engine.py
--------------------------------------
  15-min OPPOSING  → block signal entirely
  1-hr   ALIGNED   → upgrade signal strength one level
  1-hr   OPPOSING  → downgrade signal strength one level
  1-hr   NEUTRAL   → no change

Exempt signal types (no confluence check):
  TRAIL_UPDATE, EXIT, DRIVE_FAILED, ABSORPTION, FADE_ALERT
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional
from zoneinfo import ZoneInfo

from ..domain.candle import Candle
from ..domain.direction import Direction

_IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class MTFBias:
    bias_15m: Direction
    bias_1h:  Direction


def compute(
    history:        list[Candle],
    candles_15m:    int   = 3,
    candles_1h:     int   = 12,
    min_move_pct:   float = 0.05,
    today_date:     Optional[date] = None,
) -> MTFBias:
    """
    Derive 15-min and 1-hr directional bias from a list of 5-min candles
    (newest last, same as CandleBuilder.get_history() output).

    today_date: when provided, only today's IST candles are used so that
    seeded prior-session candles don't pollute bias at market open.
    Returns Direction.NEUTRAL when there is not enough history.
    """
    if today_date is not None:
        history = [c for c in history if c.boundary.astimezone(_IST).date() == today_date]
    return MTFBias(
        bias_15m = _aggregate_direction(history, candles_15m, min_move_pct),
        bias_1h  = _aggregate_direction(history, candles_1h,  min_move_pct),
    )


def _aggregate_direction(
    history:  list[Candle],
    n:        int,
    min_pct:  float,
) -> Direction:
    if len(history) < n:
        return Direction.NEUTRAL

    window = history[-n:]
    agg_open  = window[0].open
    agg_close = window[-1].close

    if agg_open == 0:
        return Direction.NEUTRAL

    move_pct = (agg_close - agg_open) / agg_open * 100

    if move_pct >= min_pct:
        return Direction.BULLISH
    if move_pct <= -min_pct:
        return Direction.BEARISH
    return Direction.NEUTRAL
