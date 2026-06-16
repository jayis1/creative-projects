"""CHIP-8 sound timer — beeps when non-zero, counts down at 60 Hz."""

from __future__ import annotations

import time


class SoundTimer:
    """Sound timer that beeps while non-zero.

    Like the delay timer, counts down at 60 Hz.  When the value is
    non-zero a beep should be played.
    """

    def __init__(self) -> None:
        self._value: int = 0
        self._last_tick: float = time.monotonic()
        self._beeping: bool = False

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
        self._beeping = self._value > 0

    def is_beeping(self) -> bool:
        """Return ``True`` while the timer is non-zero (beep should play)."""
        self._tick()
        return self._beeping

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
            self._beeping = self._value > 0

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"SoundTimer(value={self._value}, beeping={self._beeping})"