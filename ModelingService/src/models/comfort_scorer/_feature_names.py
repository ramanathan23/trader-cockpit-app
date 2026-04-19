"""Feature name constants for ComfortScorer."""

FEATURE_NAMES = [
    # Scores (5)
    'total_score', 'momentum_score', 'trend_score', 'volatility_score', 'structure_score',
    # RSI/MACD/ROC (6)
    'rsi_14', 'macd_hist', 'roc_5', 'roc_20', 'roc_60', 'vol_ratio_20',
    # Trend indicators (4)
    'adx_14', 'plus_di', 'minus_di', 'weekly_bias_encoded',
    # Volatility (7)
    'bb_squeeze', 'squeeze_days', 'nr7', 'atr_ratio', 'atr_5', 'bb_width', 'kc_width',
    # Structure (1)
    'rs_vs_nifty',
    # Additional context (5)
    'price_52w_proximity', 'sector_encoded', 'market_cap_log',
    'avg_volume_log', 'liquidity_score',
]
