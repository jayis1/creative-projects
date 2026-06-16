"""CHIP-8 64×32 monochrome display with XOR drawing and sprite support."""

from __future__ import annotations

from typing import List


class Display:
    """64×32 monochrome display buffer.

    Pixels are stored as a flat list of booleans (on/off).
    Drawing sprites uses XOR mode — a pixel is toggled only when a
    sprite bit is 1.  If any set pixel collides with an already-on
    pixel, the VF collision flag is set.
    """

    WIDTH = 64
    HEIGHT = 32

    def __init__(self) -> None:
        self._pixels: List[bool] = [False] * (self.WIDTH * self.HEIGHT)

    # ------------------------------------------------------------------
    # Pixel access
    # ------------------------------------------------------------------

    def get(self, x: int, y: int) -> bool:
        """Return the pixel at (x, y), wrapping coordinates."""
        x = x % self.WIDTH
        y = y % self.HEIGHT
        return self._pixels[y * self.WIDTH + x]

    def set(self, x: int, y: int, on: bool) -> None:
        """Set the pixel at (x, y), wrapping coordinates."""
        x = x % self.WIDTH
        y = y % self.HEIGHT
        self._pixels[y * self.WIDTH + x] = on

    # ------------------------------------------------------------------
    # Sprite drawing (the core CHIP-8 drawing primitive)
    # ------------------------------------------------------------------

    def draw_sprite(self, x: int, y: int, sprite: bytes, start: int = 0, count: int | None = None) -> bool:
        """Draw an N-row sprite at (x, y) using XOR mode.

        *sprite* is a bytes-like object.  *start* is the byte offset
        within *sprite* to begin reading rows.  *count* is the number
        of rows (bytes) to draw; defaults to remaining bytes.

        Returns ``True`` if any pixel was turned off (collision).
        """
        if count is None:
            count = len(sprite) - start
        collision = False
        for row in range(count):
            byte = sprite[start + row]
            for col in range(8):
                if byte & (0x80 >> col):
                    px = (x + col) % self.WIDTH
                    py = (y + row) % self.HEIGHT
                    idx = py * self.WIDTH + px
                    if self._pixels[idx]:
                        collision = True
                    self._pixels[idx] ^= True
        return collision

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear the entire display."""
        self._pixels = [False] * (self.WIDTH * self.HEIGHT)

    def scroll_down(self, n: int) -> None:
        """Scroll the display down by *n* rows (CHIP-8 extension)."""
        for row in range(self.HEIGHT - 1, n - 1, -1):
            src = row - n
            for col in range(self.WIDTH):
                self._pixels[row * self.WIDTH + col] = self._pixels[src * self.WIDTH + col]
        for row in range(n):
            for col in range(self.WIDTH):
                self._pixels[row * self.WIDTH + col] = False

    def scroll_left(self) -> None:
        """Scroll the display left by 4 pixels (SUPER-CHIP extension)."""
        for row in range(self.HEIGHT):
            for col in range(self.WIDTH - 4):
                self._pixels[row * self.WIDTH + col] = self._pixels[row * self.WIDTH + col + 4]
            for col in range(self.WIDTH - 4, self.WIDTH):
                self._pixels[row * self.WIDTH + col] = False

    def scroll_right(self) -> None:
        """Scroll the display right by 4 pixels (SUPER-CHIP extension)."""
        for row in range(self.HEIGHT):
            for col in range(self.WIDTH - 1, 3, -1):
                self._pixels[row * self.WIDTH + col] = self._pixels[row * self.WIDTH + col - 4]
            for col in range(4):
                self._pixels[row * self.WIDTH + col] = False

    # ------------------------------------------------------------------
    # Rendering / debug
    # ------------------------------------------------------------------

    def render(self, on: str = "█", off: str = " ") -> str:
        """Return a newline-separated string representation of the display."""
        lines: List[str] = []
        for y in range(self.HEIGHT):
            line = "".join(on if self._pixels[y * self.WIDTH + x] else off for x in range(self.WIDTH))
            lines.append(line)
        return "\n".join(lines)

    def to_rows(self) -> List[str]:
        """Return the display as a list of 64-char strings (one per row)."""
        rows: List[str] = []
        for y in range(self.HEIGHT):
            row = "".join("#" if self._pixels[y * self.WIDTH + x] else "." for x in range(self.WIDTH))
            rows.append(row)
        return rows

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Display({self.WIDTH}×{self.HEIGHT})"