"""
Technical indicator computation using pandas-ta.

All functions accept a DataFrame with columns (time, open, high, low, close, volume)
sorted ascending by time. Returns domain snapshots for persistence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta

from ..domain.snapshots import IndicatorSnapshot, MetricsSnapshot

_SMA_PERIOD = 150
_SLOPE_WINDOW = 20
_PRIOR_WINDOW = 50
_PRIOR_COMPARE = 30
_FLAT_THRESHOLD = 1.5


def compute_metrics(symbol: str, df: pd.DataFrame) -> MetricsSnapshot | None:
    if len(df) < 5:
        return None

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)
    times = df["time"]

    n = len(df)
    week52_high = float(high.max())
    week52_low = float(low.min())
    trading_days = n

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr_14 = float(tr.iloc[-14:].mean()) if n >= 14 else float(tr.mean())

    turnover = close * volume / 1e7
    adv_20_cr = float(turnover.iloc[-20:].mean()) if n >= 20 else float(turnover.mean())

    ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    ema_200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if n >= 50 else ema_50

    prev_day_close = float(close.iloc[-1])
    prev_day_high = float(high.iloc[-1])
    prev_day_low = float(low.iloc[-1])

    prev_week_high = prev_week_low = None
    prev_month_high = prev_month_low = None

    if len(times) >= 6:
        week_slice = df.iloc[-6:-1]
        prev_week_high = float(week_slice["high"].max())
        prev_week_low = float(week_slice["low"].min())

    if n >= 22:
        month_slice = df.iloc[-22:-1]
        prev_month_high = float(month_slice["high"].max())
        prev_month_low = float(month_slice["low"].min())

    week_return_pct = week_gain_pct = week_decline_pct = None
    if n >= 6:
        base_close = float(close.iloc[-6])
        if base_close > 0:
            week_return_pct = round((prev_day_close - base_close) / base_close * 100, 4)
        week_high_5 = float(high.iloc[-5:].max())
        week_low_5 = float(low.iloc[-5:].min())
        if week_low_5 > 0:
            week_gain_pct = round((prev_day_close - week_low_5) / week_low_5 * 100, 4)
        if week_high_5 > 0:
            week_decline_pct = round((week_high_5 - prev_day_close) / week_high_5 * 100, 4)

    # Per-stock camarilla range baseline: median of (H-L)*1.1/close over last 60 days.
    # LiveFeedService uses this as the narrow-vs-wide pivot threshold for each symbol.
    lookback_60 = df.iloc[-60:] if n >= 60 else df
    _cam_ranges = (lookback_60["high"].astype(float) - lookback_60["low"].astype(float)) * 1.1 / lookback_60["close"].astype(float).replace(0, float("nan"))
    cam_median_range_pct = round(float(_cam_ranges.median()), 6) if not _cam_ranges.empty else None

    return MetricsSnapshot(
        symbol=symbol,
        week52_high=round(week52_high, 4),
        week52_low=round(week52_low, 4),
        atr_14=round(atr_14, 4),
        adv_20_cr=round(adv_20_cr, 2),
        trading_days=trading_days,
        prev_day_high=round(prev_day_high, 4),
        prev_day_low=round(prev_day_low, 4),
        prev_day_close=round(prev_day_close, 4),
        prev_week_high=round(prev_week_high, 4) if prev_week_high else None,
        prev_week_low=round(prev_week_low, 4) if prev_week_low else None,
        prev_month_high=round(prev_month_high, 4) if prev_month_high else None,
        prev_month_low=round(prev_month_low, 4) if prev_month_low else None,
        ema_20=round(ema_20, 4),
        ema_50=round(ema_50, 4),
        ema_200=round(ema_200, 4),
        week_return_pct=week_return_pct,
        week_gain_pct=week_gain_pct,
        week_decline_pct=week_decline_pct,
        cam_median_range_pct=cam_median_range_pct,
    )


def compute_indicators(
    symbol: str,
    df: pd.DataFrame,
    *,
    nifty500_roc_60: float | None = None,
) -> IndicatorSnapshot | None:
    if len(df) < 30:
        return None

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)

    rsi_s = ta.rsi(close, length=14)
    rsi_14 = _last(rsi_s)

    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is None or macd_df.empty:
        macd_hist = macd_hist_std = None
    else:
        hist_col = [c for c in macd_df.columns if "h" in c.lower()]
        hist = macd_df[hist_col[0]] if hist_col else None
        if hist is not None:
            macd_hist = _last(hist)
            std = float(hist.std())
            macd_hist_std = round(std, 6) if not np.isnan(std) else None
        else:
            macd_hist = macd_hist_std = None

    roc_5 = _last(ta.roc(close, length=5))
    roc_20 = _last(ta.roc(close, length=20))
    roc_60 = _last(ta.roc(close, length=60)) if len(close) > 60 else None

    avg_vol = volume.rolling(20, min_periods=1).mean()
    vol_ratio_s = volume / avg_vol.replace(0, np.nan)
    vol_ratio_20 = _last(vol_ratio_s)

    adx_df = ta.adx(high, low, close, length=14)
    adx_14 = plus_di = minus_di = None
    if adx_df is not None and not adx_df.empty:
        adx_14 = _last(adx_df.get("ADX_14"))
        plus_di = _last(adx_df.get("DMP_14"))
        minus_di = _last(adx_df.get("DMN_14"))

    roc_5_val = roc_5 or 0.0
    weekly_bias = "BULLISH" if roc_5_val > 0 else ("BEARISH" if roc_5_val < 0 else "NEUTRAL")

    bbands = ta.bbands(close, length=20, std=2.0)
    kc = ta.kc(high, low, close, length=20, scalar=1.5)
    bb_width = kc_width = None
    bb_squeeze = False

    if bbands is not None and not bbands.empty:
        bbu = bbands.get("BBU_20_2.0")
        bbl = bbands.get("BBL_20_2.0")
        bbm = bbands.get("BBM_20_2.0")
        if bbu is not None and bbl is not None and bbm is not None:
            mid = float(bbm.iloc[-1])
            if mid > 0:
                bb_width = round(float((bbu.iloc[-1] - bbl.iloc[-1]) / mid), 6)

    if kc is not None and not kc.empty:
        kcu_col = [c for c in kc.columns if "U" in c]
        kcl_col = [c for c in kc.columns if "L" in c]
        kcb_col = [c for c in kc.columns if "B" in c or "M" in c]
        if kcu_col and kcl_col and kcb_col:
            mid = float(kc[kcb_col[0]].iloc[-1])
            if mid > 0:
                kc_width = round(float((kc[kcu_col[0]].iloc[-1] - kc[kcl_col[0]].iloc[-1]) / mid), 6)

    if bb_width is not None and kc_width is not None:
        bb_squeeze = bb_width < kc_width

    sq_days = 0
    if bb_squeeze and bbands is not None and not bbands.empty:
        bbu_s = bbands.get("BBU_20_2.0")
        bbl_s = bbands.get("BBL_20_2.0")
        bbm_s = bbands.get("BBM_20_2.0")
        if bbu_s is not None and kc is not None and not kc.empty and kcu_col:
            bb_w_s = (bbu_s - bbl_s) / bbm_s.replace(0, np.nan)
            kc_w_s = (kc[kcu_col[0]] - kc[kcl_col[0]]) / kc[kcb_col[0]].replace(0, np.nan)
            squeeze_s = bb_w_s < kc_w_s
            vals = squeeze_s.values
            for i in range(len(vals) - 1, -1, -1):
                if vals[i]:
                    sq_days += 1
                else:
                    break

    atr5_s = ta.atr(high, low, close, length=5)
    atr14_s = ta.atr(high, low, close, length=14)
    atr_5_val = _last(atr5_s)
    atr_14_val = _last(atr14_s)
    atr_ratio = None
    if atr_5_val is not None and atr_14_val is not None and atr_14_val > 0:
        atr_ratio = round(atr_5_val / atr_14_val, 4)

    nr7 = False
    if len(high) >= 7:
        ranges = (high - low).iloc[-7:]
        nr7 = bool(ranges.iloc[-1] < ranges.iloc[:-1].min())

    rs_vs_nifty = None
    if roc_60 is not None and nifty500_roc_60 is not None:
        rs_vs_nifty = round(roc_60 - nifty500_roc_60, 4)

    stage = _detect_stage(close)

    return IndicatorSnapshot(
        symbol=symbol,
        rsi_14=_r(rsi_14, 2),
        macd_hist=_r(macd_hist, 6),
        macd_hist_std=_r(macd_hist_std, 6),
        roc_5=_r(roc_5, 4),
        roc_20=_r(roc_20, 4),
        roc_60=_r(roc_60, 4),
        vol_ratio_20=_r(vol_ratio_20, 4),
        adx_14=_r(adx_14, 2),
        plus_di=_r(plus_di, 2),
        minus_di=_r(minus_di, 2),
        weekly_bias=weekly_bias,
        bb_squeeze=bb_squeeze,
        squeeze_days=sq_days,
        nr7=nr7,
        atr_ratio=atr_ratio,
        atr_5=_r(atr_5_val, 4),
        bb_width=bb_width,
        kc_width=kc_width,
        rs_vs_nifty=rs_vs_nifty,
        stage=stage,
    )


def _detect_stage(close: pd.Series) -> str:
    if len(close) < 200:
        return "UNKNOWN"

    sma = close.rolling(_SMA_PERIOD).mean()
    sma_now = float(sma.iloc[-1])
    sma_prev = float(sma.iloc[-(_SLOPE_WINDOW + 1)])
    if sma_prev <= 0:
        return "UNKNOWN"

    slope_pct = (sma_now / sma_prev - 1.0) * 100.0
    is_rising = slope_pct > _FLAT_THRESHOLD
    is_falling = slope_pct < -_FLAT_THRESHOLD
    price_above = float(close.iloc[-1]) > sma_now

    if is_rising and price_above:
        return "STAGE_2"
    if is_falling and not price_above:
        return "STAGE_4"
    if is_rising and not price_above:
        return "STAGE_1"
    if is_falling and price_above:
        return "STAGE_3"

    sma_prior_end = float(sma.iloc[-(_PRIOR_COMPARE + 1)])
    sma_prior_start = float(sma.iloc[-(_PRIOR_WINDOW + 1)])
    if sma_prior_start <= 0:
        return "UNKNOWN"
    prior_slope = (sma_prior_end / sma_prior_start - 1.0) * 100.0
    if prior_slope > _FLAT_THRESHOLD:
        return "STAGE_3"
    if prior_slope < -_FLAT_THRESHOLD:
        return "STAGE_1"
    return "STAGE_2" if price_above else "STAGE_1"


def _last(s: pd.Series | None) -> float | None:
    if s is None or s.empty:
        return None
    v = s.iloc[-1]
    return None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)


def _r(v: float | None, decimals: int) -> float | None:
    return round(v, decimals) if v is not None else None
