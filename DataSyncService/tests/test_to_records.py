"""
Tests for DataSyncService _to_records helper.

Unit tests that don't need a real database — they test the record
transformation and edge cases (NaN values, timezone handling).
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.repositories.price_repository import _to_records


class TestToRecords:

    def _make_df(self, n: int = 5) -> pd.DataFrame:
        idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
        return pd.DataFrame(
            {
                "Open":   [100.0 + i for i in range(n)],
                "High":   [101.0 + i for i in range(n)],
                "Low":    [99.0  + i for i in range(n)],
                "Close":  [100.5 + i for i in range(n)],
                "Volume": [1000 * (i + 1) for i in range(n)],
            },
            index=idx,
        )

    def test_correct_record_count(self):
        records = _to_records("INFY", self._make_df(5))
        assert len(records) == 5

    def test_record_shape(self):
        records = _to_records("TCS", self._make_df(1))
        assert len(records[0]) == 7  # time, symbol, O, H, L, C, V

    def test_symbol_embedded_in_record(self):
        records = _to_records("RELIANCE", self._make_df(1))
        assert records[0][1] == "RELIANCE"

    def test_timestamp_is_utc(self):
        records = _to_records("TEST", self._make_df(1))
        assert records[0][0].tzinfo is not None

    def test_nan_values_become_none(self):
        idx = pd.date_range("2025-01-01", periods=1, freq="D", tz="UTC")
        df = pd.DataFrame(
            {"Open": [np.nan], "High": [np.nan], "Low": [np.nan],
             "Close": [np.nan], "Volume": [np.nan]},
            index=idx,
        )
        _, _, o, h, l, c, v = _to_records("TEST", df)[0]
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
        assert _to_records("TEST", df) == []

    def test_naive_timestamps_localized_to_utc(self):
        idx = pd.date_range("2025-01-01", periods=1, freq="D")
        df = pd.DataFrame(
            {"Open": [100.0], "High": [101.0], "Low": [99.0],
             "Close": [100.5], "Volume": [1000]},
            index=idx,
        )
        records = _to_records("TEST", df)
        assert records[0][0].tzinfo is not None
