from src.domain.signal_type import SignalType
from src.signals.level_breakout import CamarillaLevels, compute_camarilla

def test_compute_camarilla_levels_matches_formula():
    assert compute_camarilla(110.0, 100.0, 105.0) == CamarillaLevels(h4=110.5, h3=107.75, l3=102.25, l4=99.5)
