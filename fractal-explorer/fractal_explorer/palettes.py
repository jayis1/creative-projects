"""Colour palettes for the Fractal Explorer.

All palette functions take a ``size`` argument and return a list of
``size`` RGB tuples with components clamped to ``[0, 255]``.  Built-in
palettes can be looked up by name via :data:`PALETTES`.
"""
from __future__ import annotations

import json
import math
from typing import Callable, List, Sequence, Tuple

RGB = Tuple[int, int, int]


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* by t in [0,1]."""
    return a + (b - a) * t


def _lerp_color(c1: RGB, c2: RGB, t: float) -> RGB:
    """Interpolate between two RGB tuples."""
    return (int(_lerp(c1[0], c2[0], t)),
            int(_lerp(c1[1], c2[1], t)),
            int(_lerp(c1[2], c2[2], t)))


def _clamp_byte(v: int) -> int:
    """Clamp an integer into the 0–255 byte range."""
    return 0 if v < 0 else (255 if v > 255 else v)


def _hsb_to_rgb(h: float, s: float, v: float) -> RGB:
    """Convert HSB (h,s,v in [0,1]) to an 8-bit RGB tuple."""
    if s <= 0:
        g = int(v * 255)
        return (g, g, g)
    h = h % 1.0
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i %= 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (_clamp_byte(int(r * 255)), _clamp_byte(int(g * 255)),
            _clamp_byte(int(b * 255)))


def _cycle_hue_palette(size: int, base_hue: float = 0.0, sat: float = 0.85,
                       val: float = 0.95) -> List[RGB]:
    """Generate a size-entry rainbow palette cycling through hue."""
    if size <= 0:
        return [(0, 0, 0)]
    return [_hsb_to_rgb(base_hue + i / max(1, size), sat, val)
            for i in range(size)]


def _gradient_stops(size: int, stops: Sequence[RGB]) -> List[RGB]:
    """Build a palette of *size* entries by interpolating fixed colour stops."""
    stops = list(stops)
    n_stops = len(stops)
    if size <= 0 or n_stops == 0:
        return [(0, 0, 0)]
    out: List[RGB] = []
    for i in range(size):
        pos = (i / max(1, size - 1)) * (n_stops - 1)
        idx = int(pos)
        frac = pos - idx
        if idx >= n_stops - 1:
            out.append(stops[-1])
        else:
            out.append(_lerp_color(stops[idx], stops[idx + 1], frac))
    return out


# --------------------------------------------------------------------------- #
# Named palettes
# --------------------------------------------------------------------------- #

def rainbow_palette(size: int = 256, **kw) -> List[RGB]:
    return _cycle_hue_palette(size, **kw)


def fire_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (0, 0, 0), (40, 0, 0), (90, 15, 0), (160, 40, 0),
        (210, 90, 0), (245, 160, 30), (255, 220, 110), (255, 255, 220),
    ])


def ice_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (0, 0, 0), (0, 15, 60), (0, 45, 130), (0, 100, 210),
        (40, 170, 255), (140, 230, 255), (220, 250, 255),
    ])


def grayscale_palette(size: int = 256, **kw) -> List[RGB]:
    return [(_clamp_byte(int(i * 255 / max(1, size - 1))),) * 3  # type: ignore[misc]
            for i in range(size)]


def electric_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (0, 0, 0), (0, 20, 50), (10, 70, 130), (40, 180, 230),
        (180, 250, 255), (255, 255, 255), (130, 200, 255), (0, 0, 0),
    ])


def sunset_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (5, 0, 20), (45, 5, 50), (110, 20, 70), (180, 50, 60),
        (230, 110, 40), (255, 180, 60), (255, 230, 140), (255, 245, 210),
    ])


def ocean_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (0, 10, 30), (0, 30, 70), (0, 60, 120), (10, 110, 160),
        (30, 170, 180), (90, 220, 200), (200, 245, 230),
    ])


def magma_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (0, 0, 4), (20, 12, 40), (55, 10, 80), (110, 20, 110),
        (170, 40, 100), (220, 80, 70), (250, 160, 50), (255, 245, 180),
    ])


def earth_palette(size: int = 256, **kw) -> List[RGB]:
    return _gradient_stops(size, [
        (0, 30, 60), (20, 60, 90), (60, 110, 110), (120, 150, 90),
        (180, 170, 80), (210, 190, 120), (240, 220, 170), (250, 245, 220),
    ])


def neon_palette(size: int = 256, **kw) -> List[RGB]:
    """Bright neon palette — pink/cyan/yellow on black."""
    return _gradient_stops(size, [
        (0, 0, 0), (10, 0, 20), (255, 0, 128), (50, 0, 80),
        (0, 255, 200), (0, 60, 80), (255, 255, 0), (200, 0, 255),
        (0, 0, 0),
    ])


def forest_palette(size: int = 256, **kw) -> List[RGB]:
    """Forest greens palette."""
    return _gradient_stops(size, [
        (0, 0, 0), (0, 20, 0), (10, 50, 10), (20, 90, 30),
        (60, 140, 60), (120, 180, 80), (200, 220, 140), (250, 250, 200),
    ])


def custom_palette_from_hex(hex_colors: Sequence[str], size: int = 256,
                            **kw) -> List[RGB]:
    """Build a gradient palette from a list of hex strings (#rrggbb)."""
    stops: List[RGB] = []
    for hx in hex_colors:
        hx = hx.lstrip("#")
        if len(hx) != 6:
            raise ValueError(f"Bad hex color: {hx!r}")
        stops.append((int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)))
    return _gradient_stops(size, stops)


PALETTES = {
    "rainbow": rainbow_palette,
    "fire": fire_palette,
    "ice": ice_palette,
    "grayscale": grayscale_palette,
    "electric": electric_palette,
    "sunset": sunset_palette,
    "ocean": ocean_palette,
    "magma": magma_palette,
    "earth": earth_palette,
    "neon": neon_palette,
    "forest": forest_palette,
}


def get_palette(name: str, size: int = 256, **kw) -> List[RGB]:
    """Look up a named palette function and build it.

    ``name`` may be a built-in name, a JSON array of hex strings, or a
    comma-separated list of hex strings.
    """
    if name in PALETTES:
        return PALETTES[name](size, **kw)
    if name.startswith("#") or (name.startswith("[") and name.endswith("]")):
        hexes = json.loads(name) if name.startswith("[") else [
            h.strip() for h in name.split(",") if h.strip()
        ]
        return custom_palette_from_hex(hexes, size)
    raise ValueError(f"Unknown palette {name!r}; options: {list(PALETTES)}")