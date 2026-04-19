from src.domain.signal_type import SignalType
from src.signals.level_breakout import CamarillaLevels, compute_camarilla, detect_camarilla, detect_orb, detect_pdh_pdl, detect_week52

def history(make_candle):
    return [make_candle(100.0, 100.2, high=100.5, low=99.8, volume=100, minute=15+i*5) for i in range(5)]

def test_detect_orb_requires_volume_confirmation(make_candle):
    prior = history(make_candle)
    assert detect_orb(make_candle(100.0, 102.0, high=102.2, low=99.9, volume=150, minute=45), 101.0, 99.0, prior, min_vol_ratio=1.3) == SignalType.ORB_BREAKOUT
    assert detect_orb(make_candle(100.0, 102.0, high=102.2, low=99.9, volume=110, minute=45), 101.0, 99.0, prior, min_vol_ratio=1.3) is None

def test_detect_week52_breakdown(make_candle):
    assert detect_week52(make_candle(100.0, 94.0, high=100.0, low=93.5, volume=250, minute=45), 120.0, 95.0, history(make_candle), min_vol_ratio=2.0) == SignalType.WEEK52_BREAKDOWN

def test_detect_pdh_and_pdl_use_crossing_logic(make_candle):
    prior = history(make_candle)
    assert detect_pdh_pdl(make_candle(100.0, 106.0, high=106.2, low=99.8, volume=160, minute=45), 105.0, 95.0, prior, min_vol_ratio=1.3) == SignalType.PDH_BREAKOUT
    assert detect_pdh_pdl(make_candle(100.0, 94.0, high=100.0, low=93.5, volume=160, minute=45), 105.0, 95.0, prior, min_vol_ratio=1.3) == SignalType.PDL_BREAKDOWN

def test_compute_camarilla_levels_matches_formula():
    assert compute_camarilla(110.0, 100.0, 105.0) == CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
