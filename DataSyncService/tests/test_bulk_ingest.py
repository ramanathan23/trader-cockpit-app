"""
Tests for DataSyncService bulk_ingest validation logic.

Unit tests for the validation edge cases (unsupported intervals, empty data).
See test_to_records.py for _to_records helper tests.
"""

import pandas as pd
import pytest

from src.repositories.price_repository import PriceRepository


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

