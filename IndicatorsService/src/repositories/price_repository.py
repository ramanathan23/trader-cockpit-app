import asyncpg
import pandas as pd


class PriceRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_synced_symbols(self) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT symbol FROM sync_state WHERE status = 'synced'"
            )
        return [r["symbol"] for r in rows]

    async def fetch_ohlcv_batch(
        self,
        symbols: list[str],
        lookback: int,
    ) -> dict[str, pd.DataFrame]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT symbol, time, open, high, low, close, volume
                FROM (
                    SELECT symbol, time, open, high, low, close, volume,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC) AS rn
                    FROM   price_data_daily
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
                "open":   float(row["open"]),
                "high":   float(row["high"]),
                "low":    float(row["low"]),
                "close":  float(row["close"]),
                "volume": float(row["volume"]) if row["volume"] else 0.0,
            })

        return {sym: pd.DataFrame(records) for sym, records in by_symbol.items()}

    async def fetch_1min_bars(self, symbol: str, days: int = 90) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, open, high, low, close, volume
                FROM price_data_1min
                WHERE symbol = $1
                  AND time >= NOW() - ($2::int * INTERVAL '1 day')
                ORDER BY time ASC
            """, symbol, days)

        return [
            {
                "time": row["time"],
                "open": float(row["open"]) if row["open"] is not None else 0.0,
                "high": float(row["high"]) if row["high"] is not None else 0.0,
                "low": float(row["low"]) if row["low"] is not None else 0.0,
                "close": float(row["close"]) if row["close"] is not None else 0.0,
                "volume": float(row["volume"] or 0),
            }
            for row in rows
        ]

    async def fetch_daily_atr(self, symbol: str, lookback: int = 14) -> float | None:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, high, low, close
                FROM price_data_daily
                WHERE symbol = $1
                ORDER BY time DESC
                LIMIT $2
            """, symbol, lookback + 1)
        if len(rows) < 2:
            return None

        ordered = list(reversed(rows))
        trs: list[float] = []
        prev_close = float(ordered[0]["close"])
        for row in ordered[1:]:
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
            prev_close = close
        return sum(trs) / len(trs) if trs else None
