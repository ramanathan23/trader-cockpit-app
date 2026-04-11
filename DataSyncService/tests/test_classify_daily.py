"""
Unit tests for daily sync classification.

Pure-function tests — no DB, no network, no yfinance.
The classifier is the core branching logic for all sync decisions so
every branch is exercised explicitly.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.domain.daily_action import classify_daily

_IST = ZoneInfo("Asia/Kolkata")
_UTC = timezone.utc


def _now_ist(hour: int, minute: int = 0, day_offset: int = 0) -> datetime:
    """Return an IST datetime at today + day_offset at HH:MM."""
    base = datetime.now(tz=_IST).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return base + timedelta(days=day_offset)


def _utc(ist_dt: datetime) -> datetime:
    """Convert an IST datetime to a UTC-aware datetime."""
    return ist_dt.astimezone(_UTC)


class TestClassifyDailyInitial:
    def test_none_last_ts_returns_initial(self):
        assert classify_daily(None, _now_ist(10)) == "INITIAL"


class TestClassifyDailySkip:
    def test_todays_data_returns_skip(self):
        now  = _now_ist(10)
        last = _utc(_now_ist(9, 15))   # same day
        assert classify_daily(last, now) == "SKIP"

    def test_yesterday_before_close_returns_skip(self):
        now  = _now_ist(14, 0)                     # before 15:30
        last = _utc(_now_ist(9, 15, day_offset=-1))
        assert classify_daily(last, now) == "SKIP"

    def test_yesterday_at_1529_returns_skip(self):
        now  = _now_ist(15, 29)
        last = _utc(_now_ist(9, 15, day_offset=-1))
        assert classify_daily(last, now) == "SKIP"


class TestClassifyDailyFetchToday:
    def test_yesterday_at_market_close_returns_fetch_today(self):
        now  = _now_ist(15, 30)
        last = _utc(_now_ist(9, 15, day_offset=-1))
        assert classify_daily(last, now) == "FETCH_TODAY"

    def test_yesterday_after_close_returns_fetch_today(self):
        now  = _now_ist(16, 0)
        last = _utc(_now_ist(9, 15, day_offset=-1))
        assert classify_daily(last, now) == "FETCH_TODAY"

    def test_yesterday_late_evening_returns_fetch_today(self):
        now  = _now_ist(23, 59)
        last = _utc(_now_ist(9, 15, day_offset=-1))
        assert classify_daily(last, now) == "FETCH_TODAY"


class TestClassifyDailyFetchGap:
    def test_two_days_behind_returns_fetch_gap(self):
        now  = _now_ist(10)
        last = _utc(_now_ist(9, 15, day_offset=-2))
        assert classify_daily(last, now) == "FETCH_GAP"

    def test_one_week_behind_returns_fetch_gap(self):
        now  = _now_ist(10)
        last = _utc(_now_ist(9, 15, day_offset=-7))
        assert classify_daily(last, now) == "FETCH_GAP"

    def test_one_month_behind_returns_fetch_gap(self):
        now  = _now_ist(10)
        last = _utc(_now_ist(9, 15, day_offset=-30))
        assert classify_daily(last, now) == "FETCH_GAP"
