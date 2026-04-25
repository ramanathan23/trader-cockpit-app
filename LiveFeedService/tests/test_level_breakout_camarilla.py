from src.domain.signal_type import SignalType
from src.signals.level_breakout import CamarillaLevels, compute_camarilla, detect_camarilla

def history(make_candle):
    return [make_candle(100.0, 100.2, high=100.5, low=99.8, volume=100, minute=15+i*5) for i in range(5)]

# Narrow range: (h4-l4)/prev_close ≤ 0.03 → breakout/breakdown mode
_NARROW_LEVELS  = CamarillaLevels(h4=100.55, h3=100.275, l3=99.725, l4=99.45)
_NARROW_PDC     = 100.0   # range 1.1/100 = 1.1% → narrow

# Wide range: (h4-l4)/prev_close > 0.03 → pin-bar reversal mode
_WIDE_LEVELS    = CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
_WIDE_PDC       = 105.0   # range 11/105 = 10.5% → wide


def test_h4_breakout_fires_in_narrow_mode(make_candle):
    prior = history(make_candle)
    prev  = make_candle(100.0, 100.4, high=100.5, low=99.9, volume=120, minute=40)
    sigs  = detect_camarilla(
        make_candle(100.0, 100.7, high=100.8, low=99.9, volume=140, minute=45),
        _NARROW_LEVELS, prev, prior, _NARROW_PDC, min_vol_ratio=1.2,
    )
    assert any(s.signal_type == SignalType.CAM_H4_BREAKOUT for s in sigs)


def test_h4_breakout_no_signal_when_prev_already_above(make_candle):
    prior = history(make_candle)
    prev_above = make_candle(100.6, 100.8, high=101.0, low=100.5, volume=120, minute=40)
    sigs = detect_camarilla(
        make_candle(100.6, 100.9, high=101.0, low=100.5, volume=140, minute=45),
        _NARROW_LEVELS, prev_above, prior, _NARROW_PDC, min_vol_ratio=1.2,
    )
    assert len([s for s in sigs if s.signal_type == SignalType.CAM_H4_BREAKOUT]) == 0


def test_l4_breakdown_fires_in_narrow_mode(make_candle):
    prior = history(make_candle)
    prev_above_l4 = make_candle(100.0, 99.5, high=100.2, low=99.4, volume=120, minute=40)
    breakdown = make_candle(100.0, 99.3, high=100.2, low=99.2, volume=140, minute=45)
    assert any(s.signal_type == SignalType.CAM_L4_BREAKDOWN for s in
               detect_camarilla(breakdown, _NARROW_LEVELS, prev_above_l4, prior, _NARROW_PDC, min_vol_ratio=1.2))


def test_l4_breakdown_no_signal_when_prev_already_below(make_candle):
    prior = history(make_candle)
    prev_below_l4 = make_candle(99.3, 99.2, high=99.4, low=99.0, volume=120, minute=40)
    breakdown = make_candle(100.0, 99.3, high=100.2, low=99.2, volume=140, minute=45)
    assert len([s for s in
                detect_camarilla(breakdown, _NARROW_LEVELS, prev_below_l4, prior, _NARROW_PDC, min_vol_ratio=1.2)
                if s.signal_type == SignalType.CAM_L4_BREAKDOWN]) == 0


def test_h3_reversal_fires_in_wide_mode(make_candle):
    prior = history(make_candle)
    # bearish pin bar: open=107.0 close=106.8 body=0.2, upper_wick=107.9-107.0=0.9 (4.5x body ≥ 2x)
    candle = make_candle(107.0, 106.8, high=107.9, low=106.7, volume=140, minute=45)
    sigs = detect_camarilla(candle, _WIDE_LEVELS, prior[-1], prior, _WIDE_PDC, min_vol_ratio=1.2)
    assert any(s.signal_type == SignalType.CAM_H3_REVERSAL for s in sigs)


def test_l3_reversal_fires_in_wide_mode(make_candle):
    prior = history(make_candle)
    # bullish pin bar: open=103.0 close=103.2 body=0.2, lower_wick=103.0-102.1=0.9 (4.5x body ≥ 2x)
    candle = make_candle(103.0, 103.2, high=103.3, low=102.1, volume=140, minute=45)
    sigs = detect_camarilla(candle, _WIDE_LEVELS, prior[-1], prior, _WIDE_PDC, min_vol_ratio=1.2)
    assert any(s.signal_type == SignalType.CAM_L3_REVERSAL for s in sigs)
