from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from statistics import mean
from zoneinfo import ZoneInfo

from ..config import settings
from ..domain.snapshots import IntradayProfileSnapshot
from ..repositories.indicator_repository import IndicatorRepository
from ..repositories.price_repository import PriceRepository

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")


class IntradayProfileService:
    def __init__(self, pool) -> None:
        self._prices = PriceRepository(pool)
        self._repo = IndicatorRepository(pool)
        self._sem = asyncio.Semaphore(settings.concurrency)

    async def compute_all(self) -> dict:
        symbols = await self._prices.fetch_1min_symbols(days=90)
        synced_symbols = await self._prices.fetch_synced_symbols()
        if not symbols:
            cleared = await self._repo.delete_intraday_profiles(synced_symbols)
            return {
                "symbols": 0,
                "symbols_computed": 0,
                "symbols_skipped_no_1min": len(synced_symbols),
                "stale_profiles_cleared": cleared,
            }

        results = await asyncio.gather(
            *[self.compute_symbol(symbol) for symbol in symbols],
            return_exceptions=True,
        )
        snapshots: list[IntradayProfileSnapshot] = []
        skipped_symbols: list[str] = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.warning("Intraday profile failed for %s: %s", symbol, result)
                continue
            if result is not None:
                snapshots.append(result)
            else:
                skipped_symbols.append(symbol)
        written = await self._repo.upsert_intraday_profiles_batch(snapshots)
        no_1min_symbols = sorted(set(synced_symbols) - set(symbols))
        cleared = await self._repo.delete_intraday_profiles([*skipped_symbols, *no_1min_symbols])
        return {
            "symbols": len(symbols),
            "symbols_computed": written,
            "symbols_skipped_no_1min": len(no_1min_symbols),
            "symbols_skipped_incomplete_1min": len(skipped_symbols),
            "stale_profiles_cleared": cleared,
        }

    async def compute_symbol(self, symbol: str) -> IntradayProfileSnapshot | None:
        async with self._sem:
            bars = await self._prices.fetch_1min_bars(symbol, days=90)
            daily_atr = await self._prices.fetch_daily_atr(symbol)
            return await asyncio.to_thread(_compute_snapshot, symbol, bars, daily_atr)

    async def get_profile(self, symbol: str) -> dict | None:
        return await self._repo.fetch_intraday_profile(symbol)


def _compute_snapshot(
    symbol: str,
    bars: list[dict],
    daily_atr: float | None,
) -> IntradayProfileSnapshot | None:
    sessions: dict[object, list[dict]] = defaultdict(list)
    for bar in bars:
        ts = bar["time"]
        session_date = ts.astimezone(_IST).date() if hasattr(ts, "astimezone") else ts.date()
        sessions[session_date].append(bar)

    chop_vals: list[float] = []
    stop_hunt_vals: list[float] = []
    orb_vals: list[float] = []
    opening_drive_vals: list[float] = []
    pullback_up_vals: list[float] = []
    autocorr_vals: list[float] = []
    daily_ranges: list[float] = []

    for session_bars in sessions.values():
        if len(session_bars) < 60:
            continue

        closes = [float(b["close"]) for b in session_bars]
        highs = [float(b["high"]) for b in session_bars]
        lows = [float(b["low"]) for b in session_bars]
        session_high = max(highs)
        session_low = min(lows)
        session_range = max(session_high - session_low, 1e-8)

        true_ranges: list[float] = []
        for i in range(1, min(15, len(session_bars))):
            true_ranges.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            ))
        if true_ranges:
            chop = sum(true_ranges) * 14 / session_range
            chop_vals.append(min(100.0, max(0.0, chop)))

        open_px = float(session_bars[0]["open"])
        threshold = open_px * 0.004
        tagged_up = session_high - open_px > threshold
        tagged_down = open_px - session_low > threshold
        stop_hunt_vals.append(1.0 if tagged_up and tagged_down else 0.0)

        if len(session_bars) >= 75:
            orb_high = max(float(b["high"]) for b in session_bars[:15])
            orb_low = min(float(b["low"]) for b in session_bars[:15])
            orb_range = orb_high - orb_low
            if orb_range > 0:
                mid = (orb_high + orb_low) / 2
                direction = 1 if closes[14] > mid else -1
                target = orb_high + 0.5 * orb_range if direction == 1 else orb_low - 0.5 * orb_range
                next_highs = [float(b["high"]) for b in session_bars[15:75]]
                next_lows = [float(b["low"]) for b in session_bars[15:75]]
                extended = max(next_highs) > target if direction == 1 else min(next_lows) < target
                orb_vals.append(1.0 if extended else 0.0)

        first30_dir = 1 if closes[29] > open_px else -1
        eod_dir = 1 if closes[-1] > open_px else -1
        opening_drive_vals.append(1.0 if first30_dir == eod_dir else 0.0)

        day_close = closes[-1]
        if day_close > open_px * 1.005 and session_high > open_px:
            depth = (session_high - day_close) / (session_high - open_px + 1e-8)
            pullback_up_vals.append(min(1.0, max(0.0, depth)))

        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1] != 0
        ]
        if len(returns) > 10:
            autocorr_vals.append(_lag1_autocorr(returns))

        daily_ranges.append(session_high - session_low)

    if not daily_ranges or len(chop_vals) == 0:
        return None

    avg_1min_range = mean(daily_ranges) if daily_ranges else 0.0
    vol_compression = avg_1min_range / daily_atr if daily_atr and daily_atr > 0 else 1.0
    avg_chop = mean(chop_vals) if chop_vals else 61.8
    avg_stop_hunt = mean(stop_hunt_vals) if stop_hunt_vals else 0.5
    avg_orb = mean(orb_vals) if orb_vals else 0.5
    avg_drive = mean(opening_drive_vals) if opening_drive_vals else 0.5
    avg_pullback = mean(pullback_up_vals) if pullback_up_vals else 0.5
    avg_autocorr = mean(autocorr_vals) if autocorr_vals else 0.0

    chop_score = max(0.0, (61.8 - avg_chop) / 61.8)
    vol_comp_score = max(0.0, 1 - abs(vol_compression - 1) / 1.5)
    iss = (
        0.25 * chop_score * 100
        + 0.20 * (1 - avg_stop_hunt) * 100
        + 0.20 * avg_orb * 100
        + 0.15 * avg_drive * 100
        + 0.15 * (1 - avg_pullback) * 100
        + 0.05 * vol_comp_score * 100
    )

    return IntradayProfileSnapshot(
        symbol=symbol,
        sessions_analyzed=len(chop_vals),
        choppiness_idx=round(avg_chop, 4),
        stop_hunt_rate=round(avg_stop_hunt, 4),
        orb_followthrough_rate=round(avg_orb, 4),
        opening_drive_rate=round(avg_drive, 4),
        pullback_depth_on_up_days=round(avg_pullback, 4),
        volatility_compression_ratio=round(vol_compression, 4),
        trend_autocorr=round(avg_autocorr, 4),
        iss_score=round(max(0.0, min(100.0, iss)), 2),
    )


def _lag1_autocorr(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    x = values[:-1]
    y = values[1:]
    mx = mean(x)
    my = mean(y)
    denom_x = sum((v - mx) ** 2 for v in x)
    denom_y = sum((v - my) ** 2 for v in y)
    denom = (denom_x * denom_y) ** 0.5
    if denom <= 1e-12:
        return 0.0
    return max(-1.0, min(1.0, sum((a - mx) * (b - my) for a, b in zip(x, y)) / denom))
