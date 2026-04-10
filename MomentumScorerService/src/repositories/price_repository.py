"""
Read-only price data access for the MomentumScorerService.

Uses a single windowed query to batch-fetch OHLCV for all symbols,
eliminating the N+1 query pattern from the original momentum.py.
"""

import logging

import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

_TABLE_MAP: dict[str, str] = {
    "1d": "price_data_daily",
}


class PriceRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_synced_symbols(self) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT symbol FROM sync_state WHERE status = 'synced'"
            )
        return [r["symbol"] for r in rows]

    async def fetch_synced_symbol_details(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT ss.symbol, s.company_name
                FROM   sync_state ss
                JOIN   symbols s ON s.symbol = ss.symbol
                WHERE  ss.status = 'synced'
                ORDER  BY ss.symbol
            """)
        return [dict(r) for r in rows]

    async def fetch_ohlcv_batch(
        self,
        symbols: list[str],
        timeframe: str,
        lookback: int,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch the last `lookback` bars for every symbol in one query.
        Returns {symbol: DataFrame(time, open, high, low, close, volume)}.
        """
        table = _TABLE_MAP.get(timeframe)
        if not table:
            raise ValueError(f"Unsupported timeframe: {timeframe!r}")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT symbol, time, open, high, low, close, volume
                FROM (
                    SELECT symbol, time, open, high, low, close, volume,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC) AS rn
                    FROM   {table}
                    WHERE  symbol = ANY($1::text[])
                ) ranked
                WHERE rn <= $2
                ORDER BY symbol, time
            """, symbols, lookback)

        by_symbol: dict[str, list] = {}
        for row in rows:
            sym = row["symbol"]
            if sym not in by_symbol:
                by_symbol[sym] = []
            by_symbol[sym].append({
                "time":   row["time"],
                "open":   row["open"],
                "high":   row["high"],
                "low":    row["low"],
                "close":  row["close"],
                "volume": row["volume"],
            })

        return {sym: pd.DataFrame(records) for sym, records in by_symbol.items()}
