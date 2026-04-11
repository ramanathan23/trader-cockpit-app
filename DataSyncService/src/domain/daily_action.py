"""
Daily sync action classification — pure functions, no I/O.

The classifier is the single source of truth for deciding what a symbol needs:
  INITIAL     — no rows in price_data_daily           → pull full history
  SKIP        — data is current                        → nothing to do
  FETCH_TODAY — last bar was yesterday, market closed  → pull today only
  FETCH_GAP   — last bar is older than yesterday       → gap-fill
"""
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

_IST = ZoneInfo("Asia/Kolkata")
_MARKET_CLOSE = time(hour=15, minute=30)

DailyAction = Literal["INITIAL", "SKIP", "FETCH_TODAY", "FETCH_GAP"]


def classify_daily(last_ts: datetime | None, now_ist: datetime) -> DailyAction:
    """
    Decide what daily sync action a symbol needs based on its last price timestamp.

    Parameters
    ----------
    last_ts  : UTC timestamp of the symbol's last price row (None if never synced)
    now_ist  : current time in IST (caller provides, enabling deterministic testing)
    """
    if last_ts is None:
        return "INITIAL"

    last_date   = last_ts.astimezone(_IST).date()
    today       = now_ist.date()
    yesterday   = today - timedelta(days=1)
    after_close = now_ist.time() >= _MARKET_CLOSE

    if last_date >= today:
        return "SKIP"
    if last_date == yesterday and not after_close:
        return "SKIP"   # market hasn't closed; nothing new yet
    if last_date == yesterday and after_close:
        return "FETCH_TODAY"
    return "FETCH_GAP"  # last_date < yesterday — multi-day gap
