from __future__ import annotations

import asyncpg


async def load_daily_metrics(pool: asyncpg.Pool) -> dict[str, dict]:
    """Read precomputed daily metrics from symbol_metrics table."""
    rows = await pool.fetch("""
        SELECT
            symbol,
            week52_high, week52_low,
            atr_14, adv_20_cr,
            ema_50, ema_200,
            week_return_pct, week_gain_pct, week_decline_pct,
            trading_days,
            prev_day_high, prev_day_low, prev_day_close,
            prev_week_high, prev_week_low,
            prev_month_high, prev_month_low
        FROM symbol_metrics
    """)
    return {
        row["symbol"]: {
            "week52_high":      round(float(row["week52_high"]), 2)   if row["week52_high"]   else None,
            "week52_low":       round(float(row["week52_low"]),  2)   if row["week52_low"]    else None,
            "atr_14":           round(float(row["atr_14"] or 0), 2),
            "adv_20_cr":        round(float(row["adv_20_cr"] or 0), 1),
            "ema_50":           round(float(row["ema_50"]), 2)        if row["ema_50"]        else None,
            "ema_200":          round(float(row["ema_200"]), 2)       if row["ema_200"]       else None,
            "week_return_pct":  round(float(row["week_return_pct"]),  2) if row["week_return_pct"]  is not None else None,
            "week_gain_pct":    round(float(row["week_gain_pct"]),    2) if row["week_gain_pct"]    is not None else None,
            "week_decline_pct": round(float(row["week_decline_pct"]), 2) if row["week_decline_pct"] is not None else None,
            "trading_days":     int(row["trading_days"]),
            "prev_day_high":    round(float(row["prev_day_high"]), 2)  if row["prev_day_high"]  else None,
            "prev_day_low":     round(float(row["prev_day_low"]),  2)  if row["prev_day_low"]   else None,
            "prev_day_close":   round(float(row["prev_day_close"]),2)  if row["prev_day_close"] else None,
            "prev_week_high":   round(float(row["prev_week_high"]),2)  if row["prev_week_high"] else None,
            "prev_week_low":    round(float(row["prev_week_low"]), 2)  if row["prev_week_low"]  else None,
            "prev_month_high":  round(float(row["prev_month_high"]),2) if row["prev_month_high"] else None,
            "prev_month_low":   round(float(row["prev_month_low"]), 2) if row["prev_month_low"]  else None,
        }
        for row in rows
    }


async def fetch_intraday_metrics(pool: asyncpg.Pool, symbol: str, daily: dict) -> dict:
    """Fetch today's OHLC range from candles_5min for a single symbol."""
    row = await pool.fetchrow("""
        SELECT
            MIN(low)::float          AS day_low,
            MAX(high)::float         AS day_high,
            FIRST(open, time)::float AS day_open,
            LAST(close, time)::float AS day_close
        FROM candles_5min
        WHERE symbol = $1
          AND time >= (NOW() AT TIME ZONE 'Asia/Kolkata')::date
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
