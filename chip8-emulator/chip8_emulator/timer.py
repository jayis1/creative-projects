"""CHIP-8 delay timer — counts down at 60 Hz."""

from __future__ import annotations

import time


class DelayTimer:
    """Delay timer that counts down at 60 Hz.

    The CHIP-8 delay timer is a single byte (0–255) that automatically
    decrements at 60 Hz until it reaches zero.  It's used for timing
    in games and programs.
    """

    def __init__(self) -> None:
        self._value: int = 0
        self._last_tick: float = time.monotonic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> int:
        """Return the current timer value, decrementing as needed."""
        self._tick()
        return self._value

    def set(self, value: int) -> None:
        """Set the timer to *value* (clamped to 0–255)."""
        self._value = max(0, min(255, value))
        self._last_tick = time.monotonic()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Decrement timer based on elapsed wall-clock time (60 Hz)."""
        now = time.monotonic()
        elapsed = now - self._last_tick
        ticks = int(elapsed * 60)
        if ticks > 0:
            self._value = max(0, self._value - ticks)
            self._last_tick = now

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"DelayTimer(value={self._value})"