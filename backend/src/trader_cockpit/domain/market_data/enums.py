from enum import Enum


class CandleInterval(str, Enum):
    MIN_1  = "1"
    MIN_5  = "5"
    MIN_15 = "15"
    MIN_25 = "25"
    MIN_60 = "60"
    DAILY  = "D"
    # Note: Dhan supports exactly these intervals for historical candles.
    # MIN_25 is unusual but valid per DhanHQ v2 API.


class MarketSessionType(str, Enum):
    PRE_OPEN    = "PRE_OPEN"     # 09:00–09:15
    NORMAL      = "NORMAL"       # 09:15–15:30
    POST_CLOSE  = "POST_CLOSE"   # 15:30–16:00
    AFTER_HOURS = "AFTER_HOURS"  # 16:00–09:00 next day
    HOLIDAY     = "HOLIDAY"
