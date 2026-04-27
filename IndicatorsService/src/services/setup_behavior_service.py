from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from zoneinfo import ZoneInfo

from ..config import settings
from ..domain.snapshots import SetupBehaviorProfileSnapshot
from ..repositories.indicator_repository import IndicatorRepository
from ..repositories.price_repository import PriceRepository

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")

_HORIZON_BARS = 12
_LOOKBACK_BARS = 6
_NARROW_RANGE_PCT = 0.008
_WIDE_PIVOT_PCT = 0.028
_RETEST_BARS = 3
_FAKEOUT_R = 0.5
_TARGET_R = 1.0
_DEEP_PULLBACK_R = 0.45


@dataclass(frozen=True)
class _Bar:
    time: object
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def range(self) -> float:
        return max(0.0, self.high - self.low)

    @property
    def turnover(self) -> float:
        return self.close * self.volume


@dataclass(frozen=True)
class _Attempt:
    kind: str
    direction: int
    success: bool
    fakeout: bool
    deep_pullback: bool
    adverse_r: float
    pullback_r: float
    time_to_1r_bars: int | None
    trend_efficiency: float
    vwap_hold: bool


class SetupBehaviorService:
    def __init__(self, pool) -> None:
        self._prices = PriceRepository(pool)
        self._repo = IndicatorRepository(pool)
        self._sem = asyncio.Semaphore(settings.concurrency)

    async def compute_all(self) -> dict:
        symbols = await self._prices.fetch_1min_symbols(days=90)
        synced_symbols = await self._prices.fetch_synced_symbols()
        if not symbols:
            cleared = await self._repo.delete_setup_behavior_profiles(synced_symbols)
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
        snapshots: list[SetupBehaviorProfileSnapshot] = []
        skipped_symbols: list[str] = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.warning("Setup behavior failed for %s: %s", symbol, result)
                continue
            if result is not None:
                snapshots.append(result)
            else:
                skipped_symbols.append(symbol)

        written = await self._repo.upsert_setup_behavior_profiles_batch(snapshots)
        no_1min_symbols = sorted(set(synced_symbols) - set(symbols))
        cleared = await self._repo.delete_setup_behavior_profiles([*skipped_symbols, *no_1min_symbols])
        return {
            "symbols": len(symbols),
            "symbols_computed": written,
            "symbols_skipped_no_1min": len(no_1min_symbols),
            "symbols_skipped_incomplete_1min": len(skipped_symbols),
            "stale_profiles_cleared": cleared,
        }

    async def compute_symbol(self, symbol: str) -> SetupBehaviorProfileSnapshot | None:
        async with self._sem:
            bars = await self._prices.fetch_1min_bars(symbol, days=90)
            return await asyncio.to_thread(_compute_snapshot, symbol, bars)

    async def get_profile(self, symbol: str) -> dict | None:
        return await self._repo.fetch_setup_behavior_profile(symbol)


def _compute_snapshot(symbol: str, raw_bars: list[dict]) -> SetupBehaviorProfileSnapshot | None:
    sessions_1m = _group_sessions(raw_bars)
    sessions_5m = {
        session_date: _to_5min(session_bars)
        for session_date, session_bars in sessions_1m.items()
    }
    sessions_5m = {d: bars for d, bars in sessions_5m.items() if len(bars) >= 24}
    if len(sessions_5m) < 8:
        return None

    dates = sorted(sessions_5m)
    attempts: list[_Attempt] = []
    session_turnover_cr: list[float] = []

    for idx, session_date in enumerate(dates):
        bars = sessions_5m[session_date]
        session_turnover_cr.append(sum(b.turnover for b in bars) / 10_000_000.0)
        if idx == 0:
            continue

        prev = sessions_5m[dates[idx - 1]]
        prev_high = max(b.high for b in prev)
        prev_low = min(b.low for b in prev)
        prev_close = prev[-1].close
        prev_range = max(prev_high - prev_low, prev_close * 0.002, 1e-8)
        pivot_width_pct = prev_range / max(prev_close, 1e-8)
        h3 = prev_close + 1.1 * prev_range / 4.0
        h4 = prev_close + 1.1 * prev_range / 2.0
        s3 = prev_close - 1.1 * prev_range / 4.0
        s4 = prev_close - 1.1 * prev_range / 2.0

        attempts.extend(_camarilla_breakouts(bars, h4, s4))
        attempts.extend(_range_breakouts(bars))
        if pivot_width_pct >= _WIDE_PIVOT_PCT:
            attempts.extend(_h3_s3_reversals(bars, h3, s3))

    if not attempts:
        return None

    breakout = [a for a in attempts if a.kind == "breakout"]
    breakdown = [a for a in attempts if a.kind == "breakdown"]
    reversal = [a for a in attempts if a.kind == "reversal"]
    avg_turnover = mean(session_turnover_cr) if session_turnover_cr else 0.0
    liquidity_score = _liquidity_score(avg_turnover)

    breakout_quality = _quality_score(breakout)
    breakdown_quality = _quality_score(breakdown)
    reversal_quality = _quality_score(reversal)
    execution_score = _execution_score(attempts, liquidity_score)

    return SetupBehaviorProfileSnapshot(
        symbol=symbol,
        sessions_analyzed=len(dates),
        setups_analyzed=len(attempts),
        breakout_attempts=len(breakout),
        breakdown_attempts=len(breakdown),
        reversal_attempts=len(reversal),
        breakout_success_rate=_rate(breakout, "success"),
        breakdown_success_rate=_rate(breakdown, "success"),
        reversal_success_rate=_rate(reversal, "success"),
        fakeout_rate=_rate(attempts, "fakeout"),
        deep_pullback_rate=_rate(attempts, "deep_pullback"),
        avg_adverse_excursion_r=_avg(attempts, "adverse_r"),
        avg_pullback_depth_r=_avg(attempts, "pullback_r"),
        avg_time_to_1r_bars=_avg([a for a in attempts if a.time_to_1r_bars is not None], "time_to_1r_bars"),
        trend_efficiency=_avg(attempts, "trend_efficiency"),
        vwap_hold_rate=_rate(attempts, "vwap_hold"),
        avg_session_turnover_cr=round(avg_turnover, 2),
        liquidity_score=liquidity_score,
        breakout_quality_score=breakout_quality,
        breakdown_quality_score=breakdown_quality,
        reversal_quality_score=reversal_quality,
        execution_score=execution_score,
        execution_grade=_grade(execution_score, liquidity_score),
    )


def _group_sessions(raw_bars: list[dict]) -> dict[object, list[_Bar]]:
    sessions: dict[object, list[_Bar]] = defaultdict(list)
    for raw in raw_bars:
        ts = raw["time"]
        session_date = ts.astimezone(_IST).date() if hasattr(ts, "astimezone") else ts.date()
        sessions[session_date].append(_Bar(
            time=ts,
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
            volume=float(raw["volume"] or 0.0),
        ))
    return {date: sorted(bars, key=lambda b: b.time) for date, bars in sessions.items()}


def _to_5min(bars: list[_Bar]) -> list[_Bar]:
    out: list[_Bar] = []
    for i in range(0, len(bars), 5):
        chunk = bars[i:i + 5]
        if len(chunk) < 5:
            continue
        out.append(_Bar(
            time=chunk[-1].time,
            open=chunk[0].open,
            high=max(b.high for b in chunk),
            low=min(b.low for b in chunk),
            close=chunk[-1].close,
            volume=sum(b.volume for b in chunk),
        ))
    return out


def _camarilla_breakouts(bars: list[_Bar], h4: float, s4: float) -> list[_Attempt]:
    attempts: list[_Attempt] = []
    seen_up = False
    seen_down = False
    for i, bar in enumerate(bars[:-_HORIZON_BARS]):
        if not seen_up and bar.close > h4 and bar.open <= h4:
            attempts.append(_evaluate_attempt(bars, i, h4, 1, "breakout"))
            seen_up = True
        if not seen_down and bar.close < s4 and bar.open >= s4:
            attempts.append(_evaluate_attempt(bars, i, s4, -1, "breakdown"))
            seen_down = True
        if seen_up and seen_down:
            break
    return attempts


def _range_breakouts(bars: list[_Bar]) -> list[_Attempt]:
    attempts: list[_Attempt] = []
    seen_up = False
    seen_down = False
    for i in range(_LOOKBACK_BARS, len(bars) - _HORIZON_BARS):
        lookback = bars[i - _LOOKBACK_BARS:i]
        range_high = max(b.high for b in lookback)
        range_low = min(b.low for b in lookback)
        width_pct = (range_high - range_low) / max(bars[i - 1].close, 1e-8)
        if width_pct > _NARROW_RANGE_PCT:
            continue
        bar = bars[i]
        if not seen_up and bar.close > range_high:
            attempts.append(_evaluate_attempt(bars, i, range_high, 1, "breakout"))
            seen_up = True
        if not seen_down and bar.close < range_low:
            attempts.append(_evaluate_attempt(bars, i, range_low, -1, "breakdown"))
            seen_down = True
        if seen_up and seen_down:
            break
    return attempts


def _h3_s3_reversals(bars: list[_Bar], h3: float, s3: float) -> list[_Attempt]:
    attempts: list[_Attempt] = []
    seen_h3 = False
    seen_s3 = False
    for i, bar in enumerate(bars[:-_HORIZON_BARS]):
        body = abs(bar.close - bar.open)
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low
        if not seen_h3 and bar.high >= h3 and bar.close < h3 and upper_wick >= max(body, bar.range * 0.35):
            attempts.append(_evaluate_attempt(bars, i, h3, -1, "reversal"))
            seen_h3 = True
        if not seen_s3 and bar.low <= s3 and bar.close > s3 and lower_wick >= max(body, bar.range * 0.35):
            attempts.append(_evaluate_attempt(bars, i, s3, 1, "reversal"))
            seen_s3 = True
        if seen_h3 and seen_s3:
            break
    return attempts


def _evaluate_attempt(bars: list[_Bar], trigger_idx: int, level: float, direction: int, kind: str) -> _Attempt:
    trigger = bars[trigger_idx]
    recent_ranges = [b.range for b in bars[max(0, trigger_idx - 6):trigger_idx + 1]]
    risk = max(trigger.range, mean(recent_ranges) if recent_ranges else 0.0, level * 0.003, 1e-8)
    future = bars[trigger_idx + 1:trigger_idx + 1 + _HORIZON_BARS]
    if not future:
        future = [trigger]

    best_favorable = 0.0
    worst_adverse = 0.0
    time_to_1r: int | None = None
    hit_half_adverse_at: int | None = None
    hit_half_favorable_at: int | None = None
    closed_inside_early = False

    for offset, bar in enumerate(future, start=1):
        favorable = ((bar.high - level) if direction == 1 else (level - bar.low)) / risk
        adverse = ((level - bar.low) if direction == 1 else (bar.high - level)) / risk
        best_favorable = max(best_favorable, favorable)
        worst_adverse = max(worst_adverse, adverse)
        if time_to_1r is None and favorable >= _TARGET_R:
            time_to_1r = offset
        if hit_half_adverse_at is None and adverse >= _FAKEOUT_R:
            hit_half_adverse_at = offset
        if hit_half_favorable_at is None and favorable >= _FAKEOUT_R:
            hit_half_favorable_at = offset
        if offset <= _RETEST_BARS:
            closed_inside_early = closed_inside_early or (bar.close < level if direction == 1 else bar.close > level)

    success = time_to_1r is not None and not (
        hit_half_adverse_at is not None and hit_half_adverse_at < time_to_1r
    )
    fakeout = closed_inside_early or (
        hit_half_adverse_at is not None
        and (hit_half_favorable_at is None or hit_half_adverse_at <= hit_half_favorable_at)
    )
    deep_pullback = worst_adverse >= _DEEP_PULLBACK_R
    net_move = abs(future[-1].close - trigger.close)
    path = sum(abs(future[i].close - (trigger.close if i == 0 else future[i - 1].close)) for i in range(len(future)))
    trend_efficiency = _clamp01(net_move / path) if path > 0 else 0.0
    vwap = _vwap(bars[:trigger_idx + 1])
    vwap_hold = trigger.close >= vwap if direction == 1 else trigger.close <= vwap

    return _Attempt(
        kind=kind,
        direction=direction,
        success=success,
        fakeout=fakeout,
        deep_pullback=deep_pullback,
        adverse_r=round(min(worst_adverse, 5.0), 4),
        pullback_r=round(min(worst_adverse / max(best_favorable, 1e-8), 5.0), 4),
        time_to_1r_bars=time_to_1r,
        trend_efficiency=round(trend_efficiency, 4),
        vwap_hold=vwap_hold,
    )


def _vwap(bars: list[_Bar]) -> float:
    total_volume = sum(b.volume for b in bars)
    if total_volume <= 0:
        return bars[-1].close
    return sum(b.close * b.volume for b in bars) / total_volume


def _quality_score(attempts: list[_Attempt]) -> float | None:
    if not attempts:
        return None
    success = _rate(attempts, "success") or 0.0
    fakeout = _rate(attempts, "fakeout") or 0.0
    deep = _rate(attempts, "deep_pullback") or 0.0
    efficiency = _avg(attempts, "trend_efficiency") or 0.0
    vwap = _rate(attempts, "vwap_hold") or 0.0
    adverse = min(_avg(attempts, "adverse_r") or 1.0, 1.5)
    score = (
        35.0 * success
        + 20.0 * (1.0 - fakeout)
        + 20.0 * (1.0 - deep)
        + 12.5 * efficiency
        + 7.5 * vwap
        + 5.0 * (1.0 - adverse / 1.5)
    )
    return round(_clamp(score), 2)


def _execution_score(attempts: list[_Attempt], liquidity_score: float) -> float:
    setup_score = _quality_score(attempts) or 0.0
    return round(_clamp(0.82 * setup_score + 0.18 * liquidity_score), 2)


def _liquidity_score(avg_turnover_cr: float) -> float:
    if avg_turnover_cr <= 0:
        return 0.0
    if avg_turnover_cr < 5:
        return round(avg_turnover_cr / 5.0 * 35.0, 2)
    if avg_turnover_cr < 25:
        return round(35.0 + (avg_turnover_cr - 5.0) / 20.0 * 35.0, 2)
    if avg_turnover_cr < 100:
        return round(70.0 + (avg_turnover_cr - 25.0) / 75.0 * 25.0, 2)
    return 100.0


def _grade(execution_score: float, liquidity_score: float) -> str:
    if liquidity_score < 35:
        return "LIQUIDITY_RISK"
    if execution_score >= 80:
        return "A"
    if execution_score >= 68:
        return "B"
    if execution_score >= 52:
        return "C"
    if execution_score >= 38:
        return "D"
    return "AVOID"


def _rate(attempts: list[_Attempt], attr: str) -> float | None:
    if not attempts:
        return None
    return round(sum(1 for a in attempts if bool(getattr(a, attr))) / len(attempts), 4)


def _avg(attempts: list[_Attempt], attr: str) -> float | None:
    vals = [float(getattr(a, attr)) for a in attempts if getattr(a, attr) is not None]
    return round(mean(vals), 4) if vals else None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
