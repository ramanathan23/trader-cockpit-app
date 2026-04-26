FEATURES = [
    "prev_rsi",
    "prev_adx",
    "prev_di_spread",
    "prev_atr_ratio",
    "prev_roc_5",
    "prev_roc_20",
    "prev_vol_ratio",
    "prev_bb_squeeze",
    "prev_squeeze_days",
    "prev_rs_vs_nifty",
    "stage_encoded",
    "day_of_week",
    "nifty_gap_pct",
    "iss_score",
    "choppiness_idx",
    "stop_hunt_rate",
    "orb_followthrough_rate",
    "pullback_depth_hist",
]

CATEGORICAL = ["day_of_week", "stage_encoded", "prev_bb_squeeze"]
SESSION_CLASSES = ["TREND_UP", "TREND_DOWN", "CHOP", "VOLATILE", "GAP_FADE", "NEUTRAL"]
