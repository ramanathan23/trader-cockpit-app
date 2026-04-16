from datetime import datetime
from zoneinfo import ZoneInfo

from src.core.session_manager import SessionManager
from src.domain.session_phase import SessionPhase


IST = ZoneInfo("Asia/Kolkata")


def ist(hour: int, minute: int) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=IST)


def test_current_phase_tracks_session_boundaries() -> None:
    manager = SessionManager()

    assert manager.current_phase(ist(9, 14)) == SessionPhase.PRE_MARKET
    assert manager.current_phase(ist(9, 15)) == SessionPhase.PRE_SIGNAL
    assert manager.current_phase(ist(9, 20)) == SessionPhase.DRIVE_WINDOW
    assert manager.current_phase(ist(9, 45)) == SessionPhase.EXECUTION
    assert manager.current_phase(ist(14, 0)) == SessionPhase.DEAD_ZONE
    assert manager.current_phase(ist(15, 30)) == SessionPhase.POST_MARKET


def test_market_open_and_trading_window_flags() -> None:
    manager = SessionManager()

    assert manager.is_market_open(ist(9, 15)) is True
    assert manager.is_market_open(ist(15, 30)) is False
    assert manager.is_trading_window(ist(9, 17)) is False
    assert manager.is_trading_window(ist(10, 0)) is True
    assert manager.is_trading_window(ist(15, 25)) is False


def test_seconds_until_market_open_clamps_at_zero_after_open() -> None:
    manager = SessionManager()

    assert manager.seconds_until_market_open(ist(9, 0)) == 900.0
    assert manager.seconds_until_market_open(ist(9, 16)) == 0.0


def test_phase_specific_spike_thresholds_are_explicit() -> None:
    manager = SessionManager()

    assert manager.spike_vol_threshold(SessionPhase.DRIVE_WINDOW) == 2.5
    assert manager.spike_vol_threshold(SessionPhase.DEAD_ZONE) == 4.0
    assert manager.spike_price_threshold(SessionPhase.CLOSE_MOMENTUM) == 1.2
    assert manager.spike_price_threshold(SessionPhase.POST_MARKET) == 1.5