from unittest.mock import MagicMock
from src.domain.direction import Direction
from src.domain.signal import Signal
from src.domain.signal_type import SignalType
from src.domain.strength import Strength
from src.core.session_manager import SessionManager
from src.domain.session_phase import SessionPhase


class TestEngineReset:
    def test_reset_clears_cam_state(self):
        from src.signals.engine import SignalEngine
        builder = MagicMock(); builder.get_history.return_value = []
        engine = SignalEngine("TEST", builder, MagicMock(spec=SessionManager))
        engine._state.cam_h4_signalled = True
        engine._state.cam_l4_signalled = True
        engine._state.cam_h4r_signalled = True
        engine._state.cam_l4r_signalled = True
        engine._state.range_signalled_at = "2024-01-01T10:00:00"
        engine.reset()
        assert engine._state.cam_h4_signalled is False
        assert engine._state.cam_l4_signalled is False
        assert engine._state.cam_h4r_signalled is False
        assert engine._state.cam_l4r_signalled is False
        assert engine._state.range_signalled_at is None
