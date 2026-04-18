"""Shared constants used across all backend services."""

from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

DEFAULT_ACQUIRE_TIMEOUT = 30  # seconds — pool.acquire() timeout
