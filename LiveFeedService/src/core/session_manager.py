from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from ..domain.session_phase import SessionPhase

_IST = ZoneInfo("Asia/Kolkata")

_PHASES: list[tuple[tuple[int, int], SessionPhase]] = [
    ((9,  15), SessionPhase.PRE_SIGNAL),
    ((9,  20), SessionPhase.DRIVE_WINDOW),
    ((9,  45), SessionPhase.EXECUTION),
    ((11,  0), SessionPhase.TRANSITION),
    ((11, 30), SessionPhase.MID_SESSION),
    ((14,  0), SessionPhase.DEAD_ZONE),
    ((14, 30), SessionPhase.CLOSE_MOMENTUM),
    ((15, 20), SessionPhase.SESSION_END),
    ((15, 30), SessionPhase.POST_MARKET),
]


class SessionManager:
    """Stateless helper — all methods are pure functions of the current time."""

    def now_ist(self) -> datetime:
        return datetime.now(tz=_IST)

    def current_phase(self, at: datetime | None = None) -> SessionPhase:
        """Return the SessionPhase for the given time (default: now)."""
        ist = (at or self.now_ist()).astimezone(_IST)
        t   = (ist.hour, ist.minute)
        if t < (9, 15):
            return SessionPhase.PRE_MARKET
        phase = SessionPhase.PRE_MARKET
        for boundary, next_phase in _PHASES:
            if t >= boundary:
                phase = next_phase
            else:
                break
        return phase

    def is_market_open(self, at: datetime | None = None) -> bool:
        """True between 9:15 and 15:30 IST (inclusive start, exclusive end)."""
        phase = self.current_phase(at)
        return phase not in (SessionPhase.PRE_MARKET, SessionPhase.POST_MARKET)

    def is_trading_window(self, at: datetime | None = None) -> bool:
        """True during phases where signals are actionable."""
        phase = self.current_phase(at)
        return phase in (
            SessionPhase.DRIVE_WINDOW, SessionPhase.EXECUTION,
            SessionPhase.TRANSITION,   SessionPhase.MID_SESSION,
            SessionPhase.DEAD_ZONE,    SessionPhase.CLOSE_MOMENTUM,
        )

    def seconds_until_market_open(self, at: datetime | None = None) -> float:
        """Seconds until 9:15 IST. Returns 0 if already open."""
        ist  = (at or self.now_ist()).astimezone(_IST)
        open_today = ist.replace(hour=9, minute=15, second=0, microsecond=0)
        delta = (open_today - ist).total_seconds()
        return max(0.0, delta)

    def spike_vol_threshold(self, phase: SessionPhase) -> float:
        """Volume-ratio threshold for spike detection (dead zone requires higher bar)."""
        return {
            SessionPhase.DRIVE_WINDOW:   2.5,
            SessionPhase.EXECUTION:      3.0,
            SessionPhase.TRANSITION:     3.0,
            SessionPhase.MID_SESSION:    3.0,
            SessionPhase.DEAD_ZONE:      4.0,
            SessionPhase.CLOSE_MOMENTUM: 3.0,
        }.get(phase, 3.0)

    def spike_price_threshold(self, phase: SessionPhase) -> float:
        """% price-move threshold for shock detection."""
        return {
            SessionPhase.DRIVE_WINDOW:   1.0,
            SessionPhase.EXECUTION:      1.5,
            SessionPhase.TRANSITION:     1.5,
            SessionPhase.MID_SESSION:    1.5,
            SessionPhase.DEAD_ZONE:      1.5,
            SessionPhase.CLOSE_MOMENTUM: 1.2,
        }.get(phase, 1.5)
