"""
Tests for DataSyncService _to_records helper and bulk_ingest validation logic.

These are unit tests that don't need a real database — they test the record
transformation and edge cases (empty data, NaN values, unsupported intervals).
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from src.repositories.price_repository import _to_records, PriceRepository


# ── _to_records tests ─────────────────────────────────────────────────────────

class TestToRecords:

    def _make_df(self, n: int = 5) -> pd.DataFrame:
        idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
        return pd.DataFrame(
            {
                "Open": [100.0 + i for i in range(n)],
                "High": [101.0 + i for i in range(n)],
                "Low": [99.0 + i for i in range(n)],
                "Close": [100.5 + i for i in range(n)],
                "Volume": [1000 * (i + 1) for i in range(n)],
            },
            index=idx,
        )

    def test_correct_record_count(self):
        df = self._make_df(5)
        records = _to_records("INFY", df)
        assert len(records) == 5

    def test_record_shape(self):
        df = self._make_df(1)
        records = _to_records("TCS", df)
        assert len(records[0]) == 7  # time, symbol, O, H, L, C, V

    def test_symbol_embedded_in_record(self):
        df = self._make_df(1)
        records = _to_records("RELIANCE", df)
        assert records[0][1] == "RELIANCE"

    def test_timestamp_is_utc(self):
        df = self._make_df(1)
        records = _to_records("TEST", df)
        ts = records[0][0]
        assert ts.tzinfo is not None

    def test_nan_values_become_none(self):
        idx = pd.date_range("2025-01-01", periods=1, freq="D", tz="UTC")
        df = pd.DataFrame(
            {"Open": [np.nan], "High": [np.nan], "Low": [np.nan],
             "Close": [np.nan], "Volume": [np.nan]},
            index=idx,
        )
        records = _to_records("TEST", df)
        _, _, o, h, l, c, v = records[0]
        assert o is None
        assert h is None
        assert l is None
        assert c is None
        assert v == 0  # NaN volume → 0

    def test_empty_dataframe_returns_empty_list(self):
        df = pd.DataFrame(
            {"Open": [], "High": [], "Low": [], "Close": [], "Volume": []},
            index=pd.DatetimeIndex([], tz="UTC"),
        )
        records = _to_records("TEST", df)
        assert records == []

    def test_naive_timestamps_localized_to_utc(self):
        idx = pd.date_range("2025-01-01", periods=1, freq="D")
        df = pd.DataFrame(
            {"Open": [100.0], "High": [101.0], "Low": [99.0],
             "Close": [100.5], "Volume": [1000]},
            index=idx,
        )
        records = _to_records("TEST", df)
        ts = records[0][0]
        assert ts.tzinfo is not None


# ── bulk_ingest validation tests ──────────────────────────────────────────────

class TestBulkIngestValidation:

    @pytest.mark.asyncio
    async def test_unsupported_interval_raises(self):
        repo = PriceRepository.__new__(PriceRepository)
        repo._pool = None
        with pytest.raises(ValueError, match="Unsupported interval"):
            await repo.bulk_ingest({"TEST": pd.DataFrame()}, "15m")

    @pytest.mark.asyncio
    async def test_empty_data_returns_zero(self):
        repo = PriceRepository.__new__(PriceRepository)
        repo._pool = None
        result = await repo.bulk_ingest({}, "1d")
        assert result == 0
