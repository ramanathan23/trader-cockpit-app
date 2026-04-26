from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import asyncpg

_IST = ZoneInfo("Asia/Kolkata")


async def push_session_predictions(pool: asyncpg.Pool, publisher) -> int:
    today = datetime.now(tz=_IST).date()
    rows = await fetch_session_predictions(pool, today)
    for row in rows:
        await publisher.publish_session_prediction(row)
    return len(rows)


async def fetch_session_predictions(pool: asyncpg.Pool, prediction_date: date) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                isp.symbol,
                isp.session_type_pred,
                isp.trend_up_prob,
                isp.chop_prob,
                isp.pullback_depth_pred,
                sip.iss_score,
                NOW() AS timestamp
            FROM intraday_session_predictions isp
            LEFT JOIN symbol_intraday_profile sip ON sip.symbol = isp.symbol
            WHERE isp.prediction_date = $1
        """, prediction_date)
    return [
        {
            "symbol": row["symbol"],
            "session_type_pred": row["session_type_pred"],
            "trend_up_prob": float(row["trend_up_prob"]) if row["trend_up_prob"] is not None else None,
            "chop_prob": float(row["chop_prob"]) if row["chop_prob"] is not None else None,
            "pullback_depth_pred": float(row["pullback_depth_pred"]) if row["pullback_depth_pred"] is not None else None,
            "iss_score": float(row["iss_score"]) if row["iss_score"] is not None else None,
            "timestamp": row["timestamp"].isoformat(),
        }
        for row in rows
    ]
