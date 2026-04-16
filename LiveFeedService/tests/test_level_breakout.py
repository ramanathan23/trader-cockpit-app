from src.domain.enums import SignalType
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

    breakout = make_candle(108.0, 111.0, high=111.2, low=107.9, volume=140, minute=45)
    reversal = make_candle(106.0, 107.0, high=107.8, low=105.8, volume=140, minute=45)

    breakout_signals = detect_camarilla(breakout, levels, prior[-1], prior, min_vol_ratio=1.2)
    reversal_signals = detect_camarilla(reversal, levels, prior[-1], prior, min_vol_ratio=1.2)

    assert breakout_signals[0].signal_type == SignalType.CAM_H4_BREAKOUT
    assert reversal_signals[0].signal_type == SignalType.CAM_H3_REVERSAL