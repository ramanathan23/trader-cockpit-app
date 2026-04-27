from __future__ import annotations

from datetime import date

import asyncpg


async def load_daily_metrics(pool: asyncpg.Pool) -> dict[str, dict]:
    """Read daily OHLCV metrics from price_data_daily + symbols."""
    async with pool.acquire() as conn:
        await conn.execute("SET lock_timeout = '8s'")
        rows = await conn.fetch("""
        WITH latest_day AS (
            SELECT
                symbol,
                MAX(time) AS last_date
            FROM price_data_daily
            GROUP BY symbol
        ),
        prev_day AS (
            SELECT
                p.symbol,
                p.time::date        AS bar_date,
                p.open::float       AS open,
                p.high::float       AS high,
                p.low::float        AS low,
                p.close::float      AS close,
                p.volume::bigint    AS volume,
                ROW_NUMBER() OVER (PARTITION BY p.symbol ORDER BY p.time DESC) AS rn
            FROM price_data_daily p
            JOIN latest_day ld ON ld.symbol = p.symbol
            WHERE p.time <= ld.last_date
        ),
        week_candles AS (
            SELECT
                p.symbol,
                p.time::date        AS bar_date,
                p.close::float      AS close
            FROM price_data_daily p
            WHERE p.time >= NOW() - INTERVAL '8 days'
        ),
        atr_data AS (
            SELECT
                p.symbol,
                AVG(GREATEST(
                    p.high - p.low,
                    ABS(p.high - LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.time)),
                    ABS(p.low  - LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.time))
                ))::float AS atr_14
            FROM (
                SELECT symbol, time, high, low, close
                FROM price_data_daily
                WHERE time >= NOW() - INTERVAL '20 days'
            ) p
            GROUP BY p.symbol
        ),
        adv_data AS (
            SELECT
                p.symbol,
                AVG(p.close * p.volume / 1e7)::float AS adv_20_cr
            FROM price_data_daily p
            WHERE p.time >= NOW() - INTERVAL '30 days'
            GROUP BY p.symbol
        ),
        year_range AS (
            SELECT
                p.symbol,
                MAX(p.high)::float  AS week52_high,
                MIN(p.low)::float   AS week52_low
            FROM price_data_daily p
            WHERE p.time >= NOW() - INTERVAL '365 days'
            GROUP BY p.symbol
        )
        SELECT
            d1.symbol,
            COALESCE(s.is_fno, FALSE)   AS is_fno,
            yr.week52_high,
            yr.week52_low,
            atr.atr_14,
            adv.adv_20_cr,
            d1.high                     AS prev_day_high,
            d1.low                      AS prev_day_low,
            d1.close                    AS prev_day_close,
            d2.high                     AS prev_2day_high,
            d2.low                      AS prev_2day_low
        FROM prev_day d1
        LEFT JOIN prev_day d2          ON d2.symbol = d1.symbol AND d2.rn = 2
        LEFT JOIN symbols s            ON s.symbol  = d1.symbol
        LEFT JOIN atr_data atr         ON atr.symbol = d1.symbol
        LEFT JOIN adv_data adv         ON adv.symbol = d1.symbol
        LEFT JOIN year_range yr        ON yr.symbol  = d1.symbol
        WHERE d1.rn = 1
    """)
    return {
        row["symbol"]: {
            "is_fno":          bool(row["is_fno"]),
            "week52_high":     round(float(row["week52_high"]), 2)    if row["week52_high"]    else None,
            "week52_low":      round(float(row["week52_low"]),  2)    if row["week52_low"]     else None,
            "atr_14":          round(float(row["atr_14"] or 0), 2),
            "adv_20_cr":       round(float(row["adv_20_cr"] or 0), 1),
            "prev_day_high":   round(float(row["prev_day_high"]), 2)  if row["prev_day_high"]  else None,
            "prev_day_low":    round(float(row["prev_day_low"]),  2)  if row["prev_day_low"]   else None,
            "prev_day_close":  round(float(row["prev_day_close"]),2)  if row["prev_day_close"] else None,
            "weekly_bias":     "NEUTRAL",
            "stage":           None,
            "rs_vs_nifty":     None,
            "vcp_detected":    False,
            "vcp_contractions": 0,
            "rect_breakout":   False,
            "rect_range_pct":  None,
            "consolidation_days": 0,
            "is_watchlist":    False,
            "cam_median_range_pct": None,
            "execution_score":  None,
            "execution_grade":  None,
            "fakeout_rate":     None,
            "deep_pullback_rate": None,
            "liquidity_score":  None,
        }
        for row in rows
    }


async def fetch_intraday_metrics(pool: asyncpg.Pool, symbol: str, daily: dict) -> dict:
    """Fetch today's OHLC range from price_data_1min for a single symbol."""
    row = await pool.fetchrow("""
        SELECT
            MIN(low)::float          AS day_low,
            MAX(high)::float         AS day_high,
            FIRST(open, time)::float AS day_open,
            LAST(close, time)::float AS day_close
        FROM price_data_1min
        WHERE symbol = $1
          AND time >= (NOW() AT TIME ZONE 'Asia/Kolkata')::date
          AND (time AT TIME ZONE 'Asia/Kolkata')::time >= '09:14:00'
    """, symbol)
    if row and row["day_high"] is not None:
        day_close   = round(float(row["day_close"]), 2)
        prev_close  = (daily.get(symbol) or {}).get("prev_day_close")
        day_chg_pct = (
            round((day_close - prev_close) / prev_close * 100, 2) if prev_close else None
        )
        return {
            "day_high":    round(float(row["day_high"]), 2),
            "day_low":     round(float(row["day_low"]),  2),
            "day_open":    round(float(row["day_open"]), 2),
            "day_close":   day_close,
            "day_chg_pct": day_chg_pct,
        }
    return {}


async def fetch_daily_reference_closes(pool: asyncpg.Pool, symbols: list[str]) -> dict[str, dict]:
    """Fetch latest and previous daily closes in one query for daily % change."""
    if not symbols:
        return {}
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH requested AS (
                SELECT unnest($1::text[]) AS symbol
            ),
            ranked AS (
                SELECT
                    r.symbol,
                    p.time::date AS bar_date,
                    p.close::float AS close,
                    row_number() OVER (PARTITION BY r.symbol ORDER BY p.time DESC) AS rn
                FROM requested r
                LEFT JOIN LATERAL (
                    SELECT time, close
                    FROM price_data_daily
                    WHERE symbol = r.symbol
                    ORDER BY time DESC
                    LIMIT 2
                ) p ON TRUE
            )
            SELECT
                symbol,
                max(bar_date) FILTER (WHERE rn = 1) AS latest_date,
                max(close)    FILTER (WHERE rn = 1) AS latest_close,
                max(close)    FILTER (WHERE rn = 2) AS previous_close
            FROM ranked
            WHERE rn <= 2 AND close IS NOT NULL
            GROUP BY symbol
        """, symbols)
    return {
        row["symbol"]: {
            "latest_date": row["latest_date"] if isinstance(row["latest_date"], date) else None,
            "latest_close": round(float(row["latest_close"]), 2) if row["latest_close"] is not None else None,
            "previous_close": round(float(row["previous_close"]), 2) if row["previous_close"] is not None else None,
        }
        for row in rows
    }
