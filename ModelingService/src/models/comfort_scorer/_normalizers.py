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
    """Extract features from DB row (simplified, matches features.py order)."""
    return [
        float(row['total_score']),
        float(row['momentum_score']),
        float(row['trend_score']),
        float(row['volatility_score']),
        float(row['structure_score']),
        float(row['rsi_14'] or 50.0),
        float(row['macd_hist'] or 0.0),
        float(row['roc_5'] or 0.0),
        float(row['roc_20'] or 0.0),
        float(row['roc_60'] or 0.0),
        float(row['vol_ratio_20'] or 1.0),
        float(row['adx_14'] or 20.0),
        float(row['plus_di'] or 20.0),
        float(row['minus_di'] or 20.0),
        1.0 if row['weekly_bias'] == 'BULLISH' else (
            -1.0 if row['weekly_bias'] == 'BEARISH' else 0.0
        ),
        float(row['bb_squeeze'] or False),
        float(row['squeeze_days'] or 0),
        float(row['nr7'] or False),
        float(row['atr_ratio'] or 1.0),
        float(row['atr_5'] or 0.0),
        float(row['bb_width'] or 0.0),
        float(row['kc_width'] or 0.0),
        float(row['rs_vs_nifty'] or 0.0),
        0.8, 0.0, 20.0, 15.0, 50.0,
    ]
