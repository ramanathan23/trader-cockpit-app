from dataclasses import dataclass


@dataclass(frozen=True)
class UnifiedScoreBreakdown:
    total_score:      float
    momentum_score:   float
    trend_score:      float
    volatility_score: float
    structure_score:  float
    # Raw indicator values for symbol_metrics + display
    rsi_14:        float | None = None
    macd_hist:     float | None = None
    roc_5:         float | None = None
    roc_20:        float | None = None
    roc_60:        float | None = None
    vol_ratio_20:  float | None = None
    adx_14:        float | None = None
    plus_di:       float | None = None
    minus_di:      float | None = None
    weekly_bias:   str = "NEUTRAL"
    bb_squeeze:    bool = False
    squeeze_days:  int = 0
    nr7:           bool = False
    atr_ratio:     float | None = None
    atr_5:         float | None = None
    bb_width:      float | None = None
    kc_width:      float | None = None
    rs_vs_nifty:   float | None = None
    stage:         str = "UNKNOWN"
