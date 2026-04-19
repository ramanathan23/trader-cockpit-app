import logging
from datetime import datetime, time, timedelta

from shared.constants import IST
from shared.utils import ensure_utc

from ..domain.daily_action import classify_daily

logger = logging.getLogger(__name__)


async def run_daily_sync(fetcher, metrics, all_symbols: list[str], last_ts_map: dict) -> dict:
    now_ist      = datetime.now(tz=IST)
    initial:     list[str] = []
    fetch_today: list[str] = []
    fetch_gap:   list[str] = []

    for symbol in all_symbols:
        action = classify_daily(ensure_utc(last_ts_map.get(symbol)), now_ist)
        if action == "INITIAL":
            initial.append(symbol)
        elif action == "FETCH_TODAY":
            fetch_today.append(symbol)
        elif action == "FETCH_GAP":
            fetch_gap.append(symbol)

    skip_count = len(all_symbols) - len(initial) - len(fetch_today) - len(fetch_gap)
    logger.info(
        "[1d] INITIAL=%d  FETCH_TODAY=%d  FETCH_GAP=%d  SKIP=%d",
        len(initial), len(fetch_today), len(fetch_gap), skip_count,
    )

    updated = 0
    if initial:
        updated += await fetcher.fetch_full(initial)
    if fetch_today:
        since_dt = datetime.combine(
            now_ist.date() - timedelta(days=1), time.min
        ).replace(tzinfo=IST)
        updated += await fetcher.fetch_since_uniform(fetch_today, since_dt)
    if fetch_gap:
        updated += await fetcher.fetch_gap(fetch_gap, last_ts_map)

    metrics_rows = await metrics.recompute()

    return {
        "initial":      len(initial),
        "fetch_today":  len(fetch_today),
        "fetch_gap":    len(fetch_gap),
        "skip":         skip_count,
        "updated":      updated,
        "metrics_rows": metrics_rows,
    }


async def build_gap_report(prices, all_symbols: list[str]) -> dict:
    now_ist = datetime.now(tz=IST)

    logger.info("gap_report: querying price tables for %d symbols", len(all_symbols))
    daily_last = await prices.get_last_data_ts_bulk(all_symbols, "1d")
    logger.info("gap_report: done")

    gaps:    dict = {}
    summary: dict = {"1d": {"INITIAL": 0, "FETCH_TODAY": 0, "FETCH_GAP": 0, "SKIP": 0}}

    for symbol in all_symbols:
        d_ts  = ensure_utc(daily_last.get(symbol))
        d_act = classify_daily(d_ts, now_ist)
        summary["1d"][d_act] += 1
        if d_act != "SKIP":
            gaps[symbol] = {
                "1d": {"action": d_act, "last_ts": d_ts.isoformat() if d_ts else None},
            }

    return {
        "as_of_ist":     now_ist.isoformat(),
        "total_symbols": len(all_symbols),
        "gap_count":     len(gaps),
        "summary":       summary,
        "symbols":       gaps,
    }
