"""
Downloads, caches, and parses the Dhan security master CSV.
Handles column-name variations across master file versions.
"""

import asyncio
import io
import logging
import tempfile
import time
from pathlib import Path

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

_SECURITY_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
_MASTER_TTL_HOURS = 24
_CACHE_PATH = Path(tempfile.gettempdir()) / "dhan_security_master.csv"

_COL_ALIASES: dict[str, list[str]] = {
    "symbol":      ["sem_trading_symbol", "trading_symbol", "symbol"],
    "security_id": ["sem_smst_security_id", "security_id", "scrip_id", "sm_security_id"],
    "exchange":    ["sem_exm_exch_id", "exchange", "exch_id", "sem_segment"],
    "series":      ["sem_series", "series"],
    "instrument":  ["sem_instrument_name", "instrument_name", "instrument"],
}


def _find_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    for alias in aliases:
        if alias in df.columns:
            return alias
    for col in df.columns:
        for alias in aliases:
            if alias in col:
                return col
    return None


class DhanSecurityMaster:
    """Thread-safe, lazily-loaded Dhan security master with TTL-based cache."""

    def __init__(self) -> None:
        self._map: dict[str, str] | None = None
        self._lock = asyncio.Lock()

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_stale() -> bool:
        if not _CACHE_PATH.exists():
            return True
        age_hours = (time.time() - _CACHE_PATH.stat().st_mtime) / 3600
        return age_hours > _MASTER_TTL_HOURS

    @staticmethod
    def _load_from_disk() -> pd.DataFrame:
        return pd.read_csv(_CACHE_PATH, low_memory=False)

    @staticmethod
    def _download_sync() -> pd.DataFrame:
        logger.info("Downloading Dhan security master…")
        resp = httpx.get(_SECURITY_MASTER_URL, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_bytes(resp.content)
        return pd.read_csv(io.BytesIO(resp.content), low_memory=False)

    @staticmethod
    def _build_map(df: pd.DataFrame) -> dict[str, str]:
        df = df.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        sym_col  = _find_col(df, _COL_ALIASES["symbol"])
        id_col   = _find_col(df, _COL_ALIASES["security_id"])
        exch_col = _find_col(df, _COL_ALIASES["exchange"])
        ser_col  = _find_col(df, _COL_ALIASES["series"])
        inst_col = _find_col(df, _COL_ALIASES["instrument"])

        if not sym_col or not id_col:
            raise RuntimeError(
                f"Cannot parse Dhan master — missing symbol/security_id columns. "
                f"Available: {list(df.columns)}"
            )

        mask = pd.Series([True] * len(df))
        if exch_col:
            mask &= df[exch_col].astype(str).str.upper().str.contains("NSE")
        if ser_col:
            mask &= df[ser_col].astype(str).str.strip().str.upper() == "EQ"
        if inst_col:
            mask &= df[inst_col].astype(str).str.strip().str.upper() == "EQUITY"

        filtered = df[mask]
        result = dict(zip(
            filtered[sym_col].astype(str).str.strip(),
            filtered[id_col].astype(str).str.strip(),
        ))
        logger.info("Security master: %d NSE EQ symbols mapped", len(result))
        return result

    # ── Public API ────────────────────────────────────────────────────────────

    async def get(self) -> dict[str, str]:
        """Return cached security map, refreshing from disk/network as needed."""
        if self._map is not None:
            return self._map

        async with self._lock:
            if self._map is not None:
                return self._map

            if self._is_stale():
                try:
                    df = await asyncio.to_thread(self._download_sync)
                except Exception:
                    if _CACHE_PATH.exists():
                        logger.warning("Security master download failed; using stale cache")
                        df = await asyncio.to_thread(self._load_from_disk)
                    else:
                        raise
            else:
                df = await asyncio.to_thread(self._load_from_disk)

            self._map = self._build_map(df)
        return self._map

    async def refresh(self) -> int:
        """Force re-download. Returns number of symbols mapped."""
        df = await asyncio.to_thread(self._download_sync)
        async with self._lock:
            self._map = self._build_map(df)
        return len(self._map)
