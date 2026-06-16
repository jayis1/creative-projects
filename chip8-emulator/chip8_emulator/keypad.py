"""CHIP-8 hex keypad (16 keys, 0–F)."""

from __future__ import annotations

from typing import Dict, Optional


class Keypad:
    """16-key hex keypad for CHIP-8 input.

    Keys are numbered 0x0 through 0xF.  The mapping from physical
    keys to hex keys is configurable; the default follows the common
    QWERTY layout:

        1 2 3 C        1 2 3 4
        4 5 6 D   ←→   Q W E R
        7 8 9 E        A S D F
        A 0 B F        Z X C V
    """

    DEFAULT_MAP: Dict[str, int] = {
        "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
        "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
        "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
        "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
    }

    def __init__(self, keymap: Optional[Dict[str, int]] = None) -> None:
        self._keymap = keymap if keymap is not None else dict(self.DEFAULT_MAP)
        self._pressed: Dict[int, bool] = {k: False for k in range(16)}

    # ------------------------------------------------------------------
    # Key press / release
    # ------------------------------------------------------------------

    def press(self, key: int) -> None:
        """Mark hex *key* (0–F) as pressed."""
        self._check(key)
        self._pressed[key] = True

    def release(self, key: int) -> None:
        """Mark hex *key* (0–F) as released."""
        self._check(key)
        self._pressed[key] = False

    def release_all(self) -> None:
        """Release all keys."""
        for k in self._pressed:
            self._pressed[k] = False

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def is_pressed(self, key: int) -> bool:
        """Return whether hex *key* is currently pressed."""
        self._check(key)
        return self._pressed[key]

    def wait_for_key(self) -> int:
        """Block (busy-wait) until a key is pressed, then return its index.

        This is used by the Fx0A (LD Vx, K) instruction.  In a real
        emulator loop, you'd poll this from the event system instead.
        """
        import select
        import sys
        import tty
        import termios

        old = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1).lower()
                    if ch in self._keymap:
                        hex_key = self._keymap[ch]
                        self._pressed[hex_key] = True
                        return hex_key
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def map_key(self, physical: str, hex_key: int) -> None:
        """Add or update a physical key → hex key mapping."""
        if not 0 <= hex_key <= 0xF:
            raise ValueError(f"Hex key {hex_key:#x} out of range 0–F")
        self._keymap[physical.lower()] = hex_key

    def physical_to_hex(self, physical: str) -> Optional[int]:
        """Map a physical keypress string to its hex key, or ``None``."""
        return self._keymap.get(physical.lower())

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _check(key: int) -> None:
        if not 0 <= key <= 0xF:
            raise ValueError(f"Key {key:#x} out of range 0–F")

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return "Keypad()"