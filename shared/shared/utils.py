"""Shared utility functions used across all backend services."""

from datetime import datetime, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Normalise a datetime to UTC. Returns None if input is None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_pg_command_result(result: str) -> int:
    """
    Parse the row-count from an asyncpg command result string.

    asyncpg returns strings like ``'INSERT 0 42'``, ``'UPDATE 5'``, or
    ``'DELETE 10'``.  This extracts the trailing integer safely.

    Returns -1 if the string cannot be parsed.
    """
    try:
        return int(result.strip().rsplit(" ", 1)[-1])
    except (ValueError, IndexError, AttributeError):
        return -1
