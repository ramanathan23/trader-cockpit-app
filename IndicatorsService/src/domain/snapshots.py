from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricsSnapshot:
    symbol: str
    week52_high: float | None = None
    week52_low: float | None = None
    atr_14: float | None = None
    adv_20_cr: float | None = None
    trading_days: int = 0
    prev_day_high: float | None = None
    prev_day_low: float | None = None
    prev_day_close: float | None = None
    prev_week_high: float | None = None
    prev_week_low: float | None = None
    prev_month_high: float | None = None
    prev_month_low: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    week_return_pct: float | None = None
    week_gain_pct: float | None = None
    week_decline_pct: float | None = None
    cam_median_range_pct: float | None = None


@dataclass(frozen=True)
class IndicatorSnapshot:
    symbol: str
    rsi_14: float | None = None
    macd_hist: float | None = None
    macd_hist_std: float | None = None
    roc_5: float | None = None
    roc_20: float | None = None
    roc_60: float | None = None
    vol_ratio_20: float | None = None
    adx_14: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None
    weekly_bias: str = "NEUTRAL"
    bb_squeeze: bool = False
    squeeze_days: int = 0
    nr7: bool = False
    atr_ratio: float | None = None
    atr_5: float | None = None
    bb_width: float | None = None
    kc_width: float | None = None
    rs_vs_nifty: float | None = None
    stage: str = "UNKNOWN"


@dataclass(frozen=True)
class PatternSnapshot:
    symbol: str
    vcp_detected: bool = False
    vcp_contractions: int = 0
    rect_breakout: bool = False
    rect_range_pct: float | None = None
    consolidation_days: int = 0
