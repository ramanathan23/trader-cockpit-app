from src.domain.signal_type import SignalType
from src.signals.level_breakout import (
    CamarillaLevels,
    compute_camarilla,
    detect_camarilla,
    detect_orb,
    detect_pdh_pdl,
    detect_week52,
)


def history(make_candle):
    return [
        make_candle(100.0, 100.2, high=100.5, low=99.8, volume=100, minute=15 + idx * 5)
        for idx in range(5)
    ]


def test_detect_orb_requires_volume_confirmation(make_candle) -> None:
    prior = history(make_candle)
    breakout = make_candle(100.0, 102.0, high=102.2, low=99.9, volume=150, minute=45)
    quiet = make_candle(100.0, 102.0, high=102.2, low=99.9, volume=110, minute=45)

    assert detect_orb(breakout, 101.0, 99.0, prior, min_vol_ratio=1.3) == SignalType.ORB_BREAKOUT
    assert detect_orb(quiet, 101.0, 99.0, prior, min_vol_ratio=1.3) is None


def test_detect_week52_breakdown(make_candle) -> None:
    prior = history(make_candle)
    candle = make_candle(100.0, 94.0, high=100.0, low=93.5, volume=250, minute=45)

    assert detect_week52(candle, 120.0, 95.0, prior, min_vol_ratio=2.0) == SignalType.WEEK52_BREAKDOWN


def test_detect_pdh_and_pdl_use_crossing_logic(make_candle) -> None:
    prior = history(make_candle)
    pdh = make_candle(100.0, 106.0, high=106.2, low=99.8, volume=160, minute=45)
    pdl = make_candle(100.0, 94.0, high=100.0, low=93.5, volume=160, minute=45)

    assert detect_pdh_pdl(pdh, 105.0, 95.0, prior, min_vol_ratio=1.3) == SignalType.PDH_BREAKOUT
    assert detect_pdh_pdl(pdl, 105.0, 95.0, prior, min_vol_ratio=1.3) == SignalType.PDL_BREAKDOWN


def test_compute_camarilla_levels_matches_formula() -> None:
    levels = compute_camarilla(110.0, 100.0, 105.0)

    assert levels == CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)


def test_detect_camarilla_returns_breakout_and_reversal_signals(make_candle) -> None:
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)

    # Prev candle must close below H4 for cross to fire
    prev_below_h4 = make_candle(108.0, 109.0, high=110.0, low=107.5, volume=120, minute=40)
    breakout = make_candle(108.0, 111.0, high=111.2, low=107.9, volume=140, minute=45)
    reversal = make_candle(106.0, 107.0, high=107.8, low=105.8, volume=140, minute=45)

    breakout_signals = detect_camarilla(breakout, levels, prev_below_h4, prior, min_vol_ratio=1.2)
    reversal_signals = detect_camarilla(reversal, levels, prior[-1], prior, min_vol_ratio=1.2)

    assert breakout_signals[0].signal_type == SignalType.CAM_H4_BREAKOUT
    assert reversal_signals[0].signal_type == SignalType.CAM_H3_REVERSAL


def test_detect_camarilla_h4_no_signal_when_already_above(make_candle) -> None:
    """H4 cross should NOT fire when prev candle already closed above H4."""
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)

    prev_above_h4 = make_candle(111.0, 111.5, high=112.0, low=110.8, volume=120, minute=40)
    candle = make_candle(111.0, 112.0, high=112.5, low=110.9, volume=140, minute=45)

    signals = detect_camarilla(candle, levels, prev_above_h4, prior, min_vol_ratio=1.2)
    h4_sigs = [s for s in signals if s.signal_type == SignalType.CAM_H4_BREAKOUT]
    assert len(h4_sigs) == 0


def test_detect_camarilla_l4_cross_requires_prev_above(make_candle) -> None:
    """L4 cross needs prev close >= L4 and current close < L4."""
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)

    prev_above_l4 = make_candle(100.0, 100.5, high=101.0, low=99.8, volume=120, minute=40)
    breakdown = make_candle(100.0, 98.0, high=100.2, low=97.5, volume=140, minute=45)

    signals = detect_camarilla(breakdown, levels, prev_above_l4, prior, min_vol_ratio=1.2)
    assert any(s.signal_type == SignalType.CAM_L4_BREAKDOWN for s in signals)

    # Already below L4 — no cross
    prev_below_l4 = make_candle(99.0, 98.5, high=99.5, low=98.0, volume=120, minute=40)
    signals2 = detect_camarilla(breakdown, levels, prev_below_l4, prior, min_vol_ratio=1.2)
    l4_sigs = [s for s in signals2 if s.signal_type == SignalType.CAM_L4_BREAKDOWN]
    assert len(l4_sigs) == 0


def test_detect_camarilla_l3_reversal(make_candle) -> None:
    """L3 rejection: low touches L3 zone but close stays above."""
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)

    # Low wicks into L3 zone, close above L3
    bounce = make_candle(103.0, 103.5, high=104.0, low=102.1, volume=140, minute=45)
    signals = detect_camarilla(bounce, levels, prior[-1], prior, min_vol_ratio=1.2)
    assert any(s.signal_type == SignalType.CAM_L3_REVERSAL for s in signals)