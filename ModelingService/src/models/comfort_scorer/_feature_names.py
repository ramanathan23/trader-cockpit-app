"""Feature name constants for ComfortScorer."""

# 22 features — all sourced from daily_scores (no symbol_metrics join needed).
FEATURE_NAMES = [
    # Scores (5)
    'total_score', 'momentum_score', 'trend_score', 'volatility_score', 'structure_score',
    # Momentum indicators (6)
    'rsi_14', 'macd_hist', 'roc_5', 'roc_20', 'roc_60', 'vol_ratio_20',
    # Trend indicators (3)
    'adx_14', 'plus_di', 'minus_di',
    # Volatility (7)
    'bb_squeeze', 'squeeze_days', 'nr7', 'atr_ratio', 'atr_5', 'bb_width', 'kc_width',
    # Structure (1)
    'rs_vs_nifty',
]
