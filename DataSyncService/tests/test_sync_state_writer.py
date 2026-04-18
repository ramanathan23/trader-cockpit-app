from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import asyncpg
import pandas as pd
import pytest

from src.services.sync_state_writer import SyncStateWriter, _to_utc_datetime


class AcquireContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


def make_frame(index: list[pd.Timestamp]) -> pd.DataFrame:
    return pd.DataFrame(
        {"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5], "Volume": [1000]},
        index=pd.DatetimeIndex(index),
    )


def build_writer():
    conn = AsyncMock()
    pool = Mock()
    pool.acquire.return_value = AcquireContext(conn)
    prices = AsyncMock()
    state = AsyncMock()
    return SyncStateWriter(pool, prices, state), conn, prices, state


@pytest.mark.parametrize(
    ("timestamp", "expected_hour"),
    [
        (pd.Timestamp("2026-04-16T09:15:00"), 9),
        (pd.Timestamp("2026-04-16T09:15:00", tz="Asia/Kolkata"), 3),
    ],
)
def test_to_utc_datetime_normalizes_naive_and_aware_timestamps(timestamp: pd.Timestamp, expected_hour: int) -> None:
    result = _to_utc_datetime(timestamp)
    assert result.tzinfo == timezone.utc
    assert result.hour == expected_hour


@pytest.mark.asyncio
async def test_persist_ingests_rows_and_marks_empty_symbols() -> None:
    writer, conn, prices, state = build_writer()
    data = {"ABC": make_frame([pd.Timestamp("2026-04-16T09:15:00")])}

    await writer.persist(["ABC", "XYZ"], data, "1d")

    prices.bulk_ingest.assert_awaited_once_with(data, "1d")
    state.upsert_many.assert_awaited_once()
    upsert_conn, records = state.upsert_many.await_args.args
    assert upsert_conn is conn
    assert ("XYZ", "1d", None, "empty", None) in records
    abc_record = next(record for record in records if record[0] == "ABC")
    assert abc_record[2] == datetime(2026, 4, 16, 9, 15, tzinfo=timezone.utc)
    assert abc_record[3] == "synced"


@pytest.mark.asyncio
async def test_persist_skips_ingest_when_batch_has_no_data() -> None:
    writer, _, prices, state = build_writer()

    await writer.persist(["ABC"], {}, "1d")

    prices.bulk_ingest.assert_not_called()
    records = state.upsert_many.await_args.args[1]
    assert records == [("ABC", "1d", None, "empty", None)]


@pytest.mark.asyncio
async def test_persist_marks_batch_as_error_when_ingest_fails() -> None:
    writer, _, prices, state = build_writer()
    prices.bulk_ingest.side_effect = OSError("boom")
    writer._mark_error = AsyncMock()

    await writer.persist(["ABC"], {"ABC": make_frame([pd.Timestamp("2026-04-16T09:15:00")])}, "1d")

    writer._mark_error.assert_awaited_once_with(["ABC"], "1d", "boom")
    state.upsert_many.assert_not_called()