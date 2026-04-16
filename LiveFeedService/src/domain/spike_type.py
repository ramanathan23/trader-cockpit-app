from enum import Enum


class SpikeType(str, Enum):
    BREAKOUT_SHOCK = "BREAKOUT_SHOCK"
    ABSORPTION     = "ABSORPTION"
    WEAK_SHOCK     = "WEAK_SHOCK"
    NONE           = "NONE"
