from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

_IST = ZoneInfo("Asia/Kolkata")


def _boundary(
    dt: datetime,
    open_h: int,
    open_m: int,
    candle_min: int,
) -> Optional[datetime]:
    """Floor dt to nearest candle boundary >= MARKET_OPEN; None if outside market hours."""
    ist = dt.astimezone(_IST)
    open_total  = open_h * 60 + open_m
    close_total = 15 * 60 + 30
    tick_total  = ist.hour * 60 + ist.minute
    if tick_total < open_total or tick_total >= close_total:
        return None
    minutes_since_open = tick_total - open_total
    floored            = (minutes_since_open // candle_min) * candle_min
    boundary_total     = open_total + floored
    return ist.replace(
        hour        = boundary_total // 60,
        minute      = boundary_total % 60,
        second      = 0,
        microsecond = 0,
    )
