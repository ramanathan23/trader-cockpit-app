from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.repositories.sync_state_repository import SyncStateSnapshot
from src.services.sync_service import _needs_1m_sync, _needs_daily_sync

IST = ZoneInfo("Asia/Kolkata")


def _utc(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _snapshot(
    *,
    last_synced_at: datetime | None = None,
    last_data_ts: datetime | None = None,
) -> SyncStateSnapshot:
    return SyncStateSnapshot(
        symbol="RELIANCE",
        timeframe="1m",
        last_synced_at=last_synced_at,
        last_data_ts=last_data_ts,
        status="synced",
    )


def test_daily_sync_skips_when_today_is_already_present_after_market_close() -> None:
    now_ist = datetime(2026, 4, 2, 15, 31, tzinfo=IST)
    snapshot = _snapshot(last_data_ts=datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc))
    assert _needs_daily_sync(snapshot, now_ist) is False


def test_daily_sync_skips_when_yesterday_is_present_before_market_close() -> None:
    now_ist = datetime(2026, 4, 2, 15, 0, tzinfo=IST)
    snapshot = _snapshot(last_data_ts=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc))
    assert _needs_daily_sync(snapshot, now_ist) is False


def test_daily_sync_runs_when_expected_day_is_missing() -> None:
    now_ist = datetime(2026, 4, 2, 15, 31, tzinfo=IST)
    snapshot = _snapshot(last_data_ts=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc))
    assert _needs_daily_sync(snapshot, now_ist) is True


def test_intraday_sync_skips_within_fifteen_minutes() -> None:
    now_utc = _utc(2026, 4, 2, 9, 20)
    now_ist = now_utc.astimezone(IST)
    snapshot = _snapshot(
        last_synced_at=_utc(2026, 4, 2, 9, 10),
        last_data_ts=_utc(2026, 4, 2, 9, 9),
    )
    assert _needs_1m_sync(snapshot, now_utc, now_ist) is False


def test_intraday_sync_runs_before_market_close_when_grace_period_has_elapsed() -> None:
    now_utc = _utc(2026, 4, 2, 9, 20)
    now_ist = now_utc.astimezone(IST)
    snapshot = _snapshot(
        last_synced_at=_utc(2026, 4, 2, 9, 0),
        last_data_ts=_utc(2026, 4, 2, 8, 59),
    )
    assert _needs_1m_sync(snapshot, now_utc, now_ist) is True


def test_intraday_sync_skips_after_market_close_when_1530_bar_exists() -> None:
    now_utc = _utc(2026, 4, 2, 10, 31)
    now_ist = now_utc.astimezone(IST)
    snapshot = _snapshot(
        last_synced_at=_utc(2026, 4, 2, 10, 0),
        last_data_ts=_utc(2026, 4, 2, 10, 0),
    )
    assert _needs_1m_sync(snapshot, now_utc, now_ist) is False


def test_intraday_sync_runs_after_market_close_when_1530_bar_is_missing() -> None:
    now_utc = _utc(2026, 4, 2, 10, 31)
    now_ist = now_utc.astimezone(IST)
    snapshot = _snapshot(
        last_synced_at=_utc(2026, 4, 2, 10, 0),
        last_data_ts=_utc(2026, 4, 2, 9, 59),
    )
    assert _needs_1m_sync(snapshot, now_utc, now_ist) is True
