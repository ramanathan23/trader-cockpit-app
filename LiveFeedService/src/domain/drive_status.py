from enum import Enum


class DriveStatus(str, Enum):
    PENDING   = "PENDING"
    CONFIRMED = "CONFIRMED"
    WEAK      = "WEAK"
    FAILED    = "FAILED"
    NO_DRIVE  = "NO_DRIVE"
