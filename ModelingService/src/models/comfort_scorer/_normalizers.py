"""Score normalization and feature extraction helpers for comfort training."""

from typing import Optional


def normalize_return(ret: float) -> float:
    """Map return % to 0-100 quality score."""
    if ret > 3.0:
        return 100.0
    elif ret > 0.0:
        return 50.0 + (ret / 3.0) * 50.0
    elif ret > -2.0:
        return 25.0 + (ret / -2.0) * 25.0
    return 0.0


def normalize_drawdown(dd_pct: float) -> float:
    """Map drawdown % to 0-100 quality score (lower DD = higher score)."""
    if dd_pct < 1.0:
        return 100.0
    elif dd_pct < 3.0:
        return 100.0 - (dd_pct - 1.0) / 2.0 * 30.0
    elif dd_pct < 5.0:
        return 70.0 - (dd_pct - 3.0) / 2.0 * 30.0
    return max(0.0, 40.0 - (dd_pct - 5.0) * 8.0)


def normalize_volatility(vol_pct: float) -> float:
    """Map daily volatility % to 0-100 quality score (lower vol = higher score)."""
    if vol_pct < 1.5:
        return 100.0
    elif vol_pct < 3.0:
        return 100.0 - (vol_pct - 1.5) / 1.5 * 50.0
    return max(0.0, 50.0 - (vol_pct - 3.0) * 16.0)


def extract_features_from_row(row) -> list:
    """Extract 22 features from daily_scores DB row."""
    def _f(v, default=0.0):
        return default if v is None else float(v)
    return [
        _f(row['total_score']),       _f(row['momentum_score']),
        _f(row['trend_score']),       _f(row['volatility_score']),
        _f(row['structure_score']),
        _f(row['rsi_14'], 50.0),      _f(row['macd_hist']),
        _f(row['roc_5']),             _f(row['roc_20']),
        _f(row['roc_60']),            _f(row['vol_ratio_20'], 1.0),
        _f(row['adx_14']),            _f(row['plus_di']),    _f(row['minus_di']),
        1.0 if row['bb_squeeze'] else 0.0,
        _f(row['squeeze_days']),      1.0 if row['nr7'] else 0.0,
        _f(row['atr_ratio'], 1.0),    _f(row['atr_5']),
        _f(row['bb_width']),          _f(row['kc_width']),   _f(row['rs_vs_nifty']),
    ]
