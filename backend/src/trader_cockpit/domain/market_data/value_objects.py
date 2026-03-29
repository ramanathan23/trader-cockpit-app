from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .enums import MarketSessionType


@dataclass(frozen=True)
class Tick:
    """Real-time market tick from Dhan binary WebSocket feed."""
    security_id: str
    ltp: Decimal
    volume: int
    oi: int | None        # Open interest (derivatives only)
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.ltp, Decimal):
            object.__setattr__(self, "ltp", Decimal(str(self.ltp)))

    @property
    def ltp_float(self) -> float:
        return float(self.ltp)


@dataclass(frozen=True)
class MarketSession:
    session_type: MarketSessionType
    open_time: datetime
    close_time: datetime

    def is_active(self, at: datetime | None = None) -> bool:
        from datetime import datetime, timezone
        now = at or datetime.now(timezone.utc)
        return (
            self.session_type == MarketSessionType.NORMAL
            and self.open_time <= now <= self.close_time
        )

    def is_eod_conversion_window(self, at: datetime | None = None) -> bool:
        """Returns True if we're in the 2:45–3:15 PM EOD conversion window."""
        from datetime import datetime, timezone
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        now = (at or datetime.now(timezone.utc)).astimezone(ist)
        # 14:45 to 15:15 IST
        return (
            self.session_type == MarketSessionType.NORMAL
            and (now.hour == 14 and now.minute >= 45)
            or (now.hour == 15 and now.minute < 15)
        )
