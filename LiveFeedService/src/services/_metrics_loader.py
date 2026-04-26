from __future__ import annotations

from datetime import date

import asyncpg


async def load_daily_metrics(pool: asyncpg.Pool) -> dict[str, dict]:
    """Read precomputed daily metrics from symbol_metrics + symbol_indicators + symbol_patterns."""
    async with pool.acquire() as conn:
        await conn.execute("SET lock_timeout = '8s'")
        rows = await conn.fetch("""
        SELECT
            sm.symbol,
            COALESCE(s.is_fno, FALSE)        AS is_fno,
            sm.week52_high, sm.week52_low,
            sm.atr_14, sm.adv_20_cr,
            sm.ema_50, sm.ema_200,
            sm.week_return_pct, sm.week_gain_pct, sm.week_decline_pct,
            sm.trading_days,
            sm.prev_day_high, sm.prev_day_low, sm.prev_day_close,
            sm.prev_week_high, sm.prev_week_low,
            sm.prev_month_high, sm.prev_month_low,
            sm.cam_median_range_pct,
            COALESCE(si.weekly_bias, 'NEUTRAL') AS weekly_bias,
            si.stage,
            si.rs_vs_nifty,
            sp.vcp_detected,
            sp.vcp_contractions,
            sp.rect_breakout,
            sp.rect_range_pct,
            sp.consolidation_days,
            sip.iss_score,
            isp.session_type_pred,
            isp.pullback_depth_pred,
            COALESCE(ds.is_watchlist, FALSE)  AS is_watchlist
        FROM symbol_metrics sm
        LEFT JOIN symbols s ON s.symbol = sm.symbol
        LEFT JOIN symbol_indicators si ON si.symbol = sm.symbol
        LEFT JOIN symbol_patterns sp ON sp.symbol = sm.symbol
        LEFT JOIN symbol_intraday_profile sip ON sip.symbol = sm.symbol
        LEFT JOIN intraday_session_predictions isp
            ON isp.symbol = sm.symbol
           AND isp.prediction_date = (NOW() AT TIME ZONE 'Asia/Kolkata')::date
        LEFT JOIN (
            SELECT symbol, is_watchlist
            FROM daily_scores
            WHERE score_date = (SELECT MAX(score_date) FROM daily_scores)
        ) ds ON ds.symbol = sm.symbol
    """)
    return {
        row["symbol"]: {
            "is_fno":            bool(row["is_fno"]),
            "week52_high":       round(float(row["week52_high"]), 2)    if row["week52_high"]    else None,
            "week52_low":        round(float(row["week52_low"]),  2)    if row["week52_low"]     else None,
            "atr_14":            round(float(row["atr_14"] or 0), 2),
            "adv_20_cr":         round(float(row["adv_20_cr"] or 0), 1),
            "ema_50":            round(float(row["ema_50"]), 2)         if row["ema_50"]         else None,
            "ema_200":           round(float(row["ema_200"]), 2)        if row["ema_200"]        else None,
            "week_return_pct":   round(float(row["week_return_pct"]),  2) if row["week_return_pct"]  is not None else None,
            "week_gain_pct":     round(float(row["week_gain_pct"]),    2) if row["week_gain_pct"]    is not None else None,
            "week_decline_pct":  round(float(row["week_decline_pct"]), 2) if row["week_decline_pct"] is not None else None,
            "trading_days":      int(row["trading_days"]),
            "prev_day_high":     round(float(row["prev_day_high"]), 2)  if row["prev_day_high"]  else None,
            "prev_day_low":      round(float(row["prev_day_low"]),  2)  if row["prev_day_low"]   else None,
            "prev_day_close":    round(float(row["prev_day_close"]),2)  if row["prev_day_close"] else None,
            "prev_week_high":    round(float(row["prev_week_high"]),2)  if row["prev_week_high"] else None,
            "prev_week_low":     round(float(row["prev_week_low"]), 2)  if row["prev_week_low"]  else None,
            "prev_month_high":   round(float(row["prev_month_high"]),2) if row["prev_month_high"] else None,
            "prev_month_low":    round(float(row["prev_month_low"]), 2) if row["prev_month_low"]  else None,
            "weekly_bias":       row["weekly_bias"],
            "stage":             row["stage"],
            "rs_vs_nifty":       round(float(row["rs_vs_nifty"]), 2)    if row["rs_vs_nifty"]    else None,
            "vcp_detected":      bool(row["vcp_detected"])               if row["vcp_detected"] is not None else False,
            "vcp_contractions":  int(row["vcp_contractions"])            if row["vcp_contractions"] is not None else 0,
            "rect_breakout":     bool(row["rect_breakout"])              if row["rect_breakout"] is not None else False,
            "rect_range_pct":    round(float(row["rect_range_pct"]), 4)  if row["rect_range_pct"] is not None else None,
            "consolidation_days": int(row["consolidation_days"])         if row["consolidation_days"] is not None else 0,
            "is_watchlist":           bool(row["is_watchlist"]),
            "cam_median_range_pct":   round(float(row["cam_median_range_pct"]), 6) if row["cam_median_range_pct"] else None,
            "iss_score":              round(float(row["iss_score"]), 2) if row["iss_score"] is not None else None,
            "session_type_pred":      row["session_type_pred"],
            "pullback_depth_pred":    round(float(row["pullback_depth_pred"]), 4) if row["pullback_depth_pred"] is not None else None,
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
