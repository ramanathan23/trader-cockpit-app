import dataclasses as dc
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo
import pytest
from src.domain.direction import Direction
from src.domain.signal import Signal
from src.domain.signal_type import SignalType
from src.domain.strength import Strength
from src.core.session_manager import SessionManager
from src.domain.session_phase import SessionPhase

IST = ZoneInfo("Asia/Kolkata")

def _make_signal(direction=Direction.BULLISH, signal_type=SignalType.RANGE_BREAKOUT,
                 strength=Strength.MEDIUM, score=5.0):
    return Signal(symbol="TEST", signal_type=signal_type, direction=direction,
                  strength=strength, score=score, price=100.0, session_phase=SessionPhase.EXECUTION)

class TestFrozenSignal:
    def test_signal_is_immutable(self):
        sig = _make_signal()
        with pytest.raises(dc.FrozenInstanceError):
            sig.score = 10.0

    def test_signal_replace_creates_new_instance(self):
        sig = _make_signal(score=7.5)
        new_sig = dc.replace(sig, score=10.0)
        assert new_sig.score == 10.0
        assert sig.score == 7.5
        assert new_sig is not sig


class TestConfluenceFilter:
    def test_opposing_15m_blocks_signal(self):
        from src.core import mtf_bias
        from src.signals._confluence_filter import apply_confluence
        bias = mtf_bias.MTFBias(bias_15m=Direction.BEARISH, bias_1h=Direction.NEUTRAL)
        sig  = _make_signal(direction=Direction.BULLISH, signal_type=SignalType.RANGE_BREAKOUT)
        assert len(apply_confluence([sig], bias)) == 0

    def test_aligned_15m_and_1h_upgrades_strength(self):
        from src.core import mtf_bias
        from src.signals._confluence_filter import apply_confluence
        bias = mtf_bias.MTFBias(bias_15m=Direction.BULLISH, bias_1h=Direction.BULLISH)
        sig  = _make_signal(direction=Direction.BULLISH, signal_type=SignalType.RANGE_BREAKOUT, strength=Strength.MEDIUM)
        result = apply_confluence([sig], bias)
        assert len(result) == 1
        assert result[0].strength == Strength.HIGH

    def test_exempt_cam_types_pass_through_opposing_bias(self):
        from src.core import mtf_bias
        from src.signals._confluence_filter import apply_confluence
        bias = mtf_bias.MTFBias(bias_15m=Direction.BEARISH, bias_1h=Direction.BEARISH)
        sig  = _make_signal(direction=Direction.BULLISH, signal_type=SignalType.CAM_H4_BREAKOUT)
        assert len(apply_confluence([sig], bias)) == 1
