"""imageio.py — Write rendered frames to PPM / PNG / plain ASCII art."""

from __future__ import annotations

import os
from typing import Iterable

from .vec import Vec3
from .renderer import Renderer

__all__ = ["write_ppm", "write_png", "write_ascii", "write_array"]


def write_ppm(path: str, pixels: "list[list[Vec3]]", gamma: float = 2.0) -> None:
    """Write a 24-bit binary PPM (P6) file."""
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    with open(path, "wb") as f:
        header = f"P6\n{width} {height}\n255\n".encode("ascii")
        f.write(header)
        for row in pixels:
            for px in row:
                r, g, b = Renderer.to_rgb(px, gamma)
                f.write(bytes((r, g, b)))


def write_png(path: str, pixels: "list[list[Vec3]]", gamma: float = 2.0) -> None:
    """Write a PNG file using Pillow (falls back to PPM if Pillow missing)."""
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover - exercised in tests when PIL present
        raise ImportError("Pillow is required for PNG output") from e
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    buf = bytearray()
    for row in pixels:
        for px in row:
            r, g, b = Renderer.to_rgb(px, gamma)
            buf += bytes((r, g, b))
    img = Image.frombytes("RGB", (width, height), bytes(buf))
    img.save(path)


def write_ascii(path: str, pixels: "list[list[Vec3]]", width: int = 80) -> None:
    """Write a luminance-mapped ASCII art preview, scaled to *width* columns."""
    ramp = " .:-=+*#%@"
    height = len(pixels)
    src_w = len(pixels[0]) if height else 0
    if src_w == 0:
        with open(path, "w") as f:
            f.write("")
        return
    cols = width
    rows = max(1, int(height * cols / src_w * 0.5))
    lines: list[str] = []
    for ry in range(rows):
        sy0 = int(ry * height / rows)
        sy1 = max(sy0 + 1, int((ry + 1) * height / rows))
        line = []
        for cx in range(cols):
            sx0 = int(cx * src_w / cols)
            sx1 = max(sx0 + 1, int((cx + 1) * src_w / cols))
            lum = 0.0
            cnt = 0
            for yy in range(sy0, sy1):
                for xx in range(sx0, sx1):
                    p = pixels[yy][xx]
                    lum += 0.2126 * p.x + 0.7152 * p.y + 0.0722 * p.z
                    cnt += 1
            lum = lum / max(1, cnt)
            idx = min(len(ramp) - 1, int(lum * (len(ramp))))
            line.append(ramp[idx])
        lines.append("".join(line))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_array(pixels: "list[list[Vec3]]", gamma: float = 2.0):
    """Return a flat ``bytes`` RGB buffer (handy for tests / streaming)."""
    buf = bytearray()
    for row in pixels:
        for px in row:
            r, g, b = Renderer.to_rgb(px, gamma)
            buf += bytes((r, g, b))
    return bytes(buf)