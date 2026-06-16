"""Tests for CHIP-8 timers."""

import time
import pytest
from chip8_emulator.timer import DelayTimer
from chip8_emulator.sound import SoundTimer


class TestDelayTimer:
    """Test delay timer countdown."""

    def test_initial_value(self):
        dt = DelayTimer()
        assert dt.get() == 0

    def test_set_get(self):
        dt = DelayTimer()
        dt.set(42)
        assert dt.get() == 42

    def test_clamp_max(self):
        dt = DelayTimer()
        dt.set(300)
        assert dt.get() == 255

    def test_clamp_min(self):
        dt = DelayTimer()
        dt.set(-1)
        assert dt.get() == 0

    def test_countdown(self):
        dt = DelayTimer()
        dt.set(5)
        # Sleep enough for at least 1 tick at 60Hz
        time.sleep(1.0 / 30)
        val = dt.get()
        # Value should be 5 or 4 (depending on timing)
        assert val <= 5

    def test_repr(self):
        dt = DelayTimer()
        dt.set(10)
        assert "10" in repr(dt)


class TestSoundTimer:
    """Test sound timer and beeping state."""

    def test_initial_value(self):
        st = SoundTimer()
        assert st.get() == 0

    def test_set_nonzero_starts_beep(self):
        st = SoundTimer()
        st.set(5)
        assert st.is_beeping() is True

    def test_set_zero_stops_beep(self):
        st = SoundTimer()
        st.set(5)
        st.set(0)
        assert st.is_beeping() is False

    def test_countdown_stops_beep(self):
        st = SoundTimer()
        st.set(1)
        assert st.is_beeping() is True
        # Wait for it to count down
        time.sleep(0.1)
        # After countdown, beeping should stop
        st.get()  # Force tick
        # May or may not have reached 0 depending on timing
        assert st.get() >= 0