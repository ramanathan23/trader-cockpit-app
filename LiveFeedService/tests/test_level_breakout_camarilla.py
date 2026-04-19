from src.domain.signal_type import SignalType
from src.signals.level_breakout import CamarillaLevels, compute_camarilla, detect_camarilla, detect_orb, detect_pdh_pdl, detect_week52

def history(make_candle):
    return [make_candle(100.0, 100.2, high=100.5, low=99.8, volume=100, minute=15+i*5) for i in range(5)]

def test_detect_camarilla_returns_breakout_and_reversal_signals(make_candle):
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
    prev_below_h4 = make_candle(108.0, 109.0, high=110.0, low=107.5, volume=120, minute=40)
    assert detect_camarilla(make_candle(108.0, 111.0, high=111.2, low=107.9, volume=140, minute=45), levels, prev_below_h4, prior, min_vol_ratio=1.2)[0].signal_type == SignalType.CAM_H4_BREAKOUT
    assert detect_camarilla(make_candle(106.0, 107.0, high=107.8, low=105.8, volume=140, minute=45), levels, prior[-1], prior, min_vol_ratio=1.2)[0].signal_type == SignalType.CAM_H3_REVERSAL

def test_detect_camarilla_h4_no_signal_when_already_above(make_candle):
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
    prev_above_h4 = make_candle(111.0, 111.5, high=112.0, low=110.8, volume=120, minute=40)
    signals = detect_camarilla(make_candle(111.0, 112.0, high=112.5, low=110.9, volume=140, minute=45), levels, prev_above_h4, prior, min_vol_ratio=1.2)
    assert len([s for s in signals if s.signal_type == SignalType.CAM_H4_BREAKOUT]) == 0

def test_detect_camarilla_l4_cross_requires_prev_above(make_candle):
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
    prev_above_l4 = make_candle(100.0, 100.5, high=101.0, low=99.8, volume=120, minute=40)
    breakdown = make_candle(100.0, 98.0, high=100.2, low=97.5, volume=140, minute=45)
    assert any(s.signal_type == SignalType.CAM_L4_BREAKDOWN for s in detect_camarilla(breakdown, levels, prev_above_l4, prior, min_vol_ratio=1.2))
    prev_below_l4 = make_candle(99.0, 98.5, high=99.5, low=98.0, volume=120, minute=40)
    assert len([s for s in detect_camarilla(breakdown, levels, prev_below_l4, prior, min_vol_ratio=1.2) if s.signal_type == SignalType.CAM_L4_BREAKDOWN]) == 0

def test_detect_camarilla_l3_reversal(make_candle):
    prior = history(make_candle)
    levels = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
    signals = detect_camarilla(make_candle(103.0, 103.5, high=104.0, low=102.1, volume=140, minute=45), levels, prior[-1], prior, min_vol_ratio=1.2)
    assert any(s.signal_type == SignalType.CAM_L3_REVERSAL for s in signals)
