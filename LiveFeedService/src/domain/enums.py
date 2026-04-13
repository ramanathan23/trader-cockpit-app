"""
Domain enums for LiveFeedService.

All signal-pipeline enums live here so they can be imported independently
of the heavier dataclass models. Re-exported by domain/models.py for
backward compatibility with existing import sites.
"""
from enum import Enum


class SessionPhase(str, Enum):
    PRE_MARKET     = "PRE_MARKET"      # before 9:15
    PRE_SIGNAL     = "PRE_SIGNAL"      # 9:15–9:18 (first candle building)
    DRIVE_WINDOW   = "DRIVE_WINDOW"    # 9:18–9:33 (open drive detection)
    EXECUTION      = "EXECUTION"       # 9:33–11:00 (primary trading window)
    TRANSITION     = "TRANSITION"      # 11:00–11:30
    MID_SESSION    = "MID_SESSION"     # 11:30–14:00
    DEAD_ZONE      = "DEAD_ZONE"       # 14:00–14:30 (low volume)
    CLOSE_MOMENTUM = "CLOSE_MOMENTUM"  # 14:30–15:20
    SESSION_END    = "SESSION_END"     # 15:20–15:30 (hard exit)
    POST_MARKET    = "POST_MARKET"     # after 15:30


class DriveStatus(str, Enum):
    PENDING   = "PENDING"    # not enough candles yet
    CONFIRMED = "CONFIRMED"  # >= 70% confidence
    WEAK      = "WEAK"       # 50–70% confidence
    FAILED    = "FAILED"     # price returned through day_open
    NO_DRIVE  = "NO_DRIVE"   # < 50% confidence after drive window


class SpikeType(str, Enum):
    BREAKOUT_SHOCK = "BREAKOUT_SHOCK"  # vol spike + large price move (same direction)
    ABSORPTION     = "ABSORPTION"      # vol spike + flat price (reversal watch)
    WEAK_SHOCK     = "WEAK_SHOCK"      # price move without vol (likely to fade)
    NONE           = "NONE"


class SignalType(str, Enum):
    OPEN_DRIVE_ENTRY    = "OPEN_DRIVE_ENTRY"    # open drive confirmed, entry setup
    DRIVE_FAILED        = "DRIVE_FAILED"        # drive invalidated
    SPIKE_BREAKOUT      = "SPIKE_BREAKOUT"      # mid-session breakout shock
    ABSORPTION          = "ABSORPTION"          # absorption detected, reversal watch
    EXHAUSTION_REVERSAL = "EXHAUSTION_REVERSAL" # downtrend → volume climax → price held → reversal
    TRAIL_UPDATE        = "TRAIL_UPDATE"        # trailing stop moved
    EXIT                = "EXIT"                # exit triggered
    FADE_ALERT          = "FADE_ALERT"          # large price move with no volume — likely to fade


class Direction(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Strength(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"
