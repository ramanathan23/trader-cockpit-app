"""
1-minute sync action classification — pure functions, no I/O.

  INITIAL          — no 1min rows yet → pull full 90-day history
  SKIP             — last bar < 5 min ago → nothing new to fetch
  FETCH_INCREMENTAL — stale data → fetch from last bar to now
"""
from datetime import datetime
from typing import Literal

from shared.constants import IST

MinuteAction = Literal["INITIAL", "SKIP", "FETCH_INCREMENTAL"]

_SKIP_STALENESS_SECONDS = 5 * 60  # 5 minutes


def classify_minute(last_ts: datetime | None, now_ist: datetime) -> MinuteAction:
    """
    Decide what 1min sync action a symbol needs based on its last price timestamp.

    Parameters
    ----------
    last_ts  : UTC timestamp of the symbol's last 1min row (None if never synced)
    now_ist  : current time in IST (caller provides, enabling deterministic testing)
    """
    if last_ts is None:
        return "INITIAL"

    last_ist = last_ts.astimezone(IST)
    age_s = (now_ist - last_ist).total_seconds()

    if age_s < _SKIP_STALENESS_SECONDS:
        return "SKIP"

    return "FETCH_INCREMENTAL"
