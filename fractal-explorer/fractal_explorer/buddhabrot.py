"""Buddhabrot rendering — a different kind of fractal image.

The Buddhabrot traces the *orbits* of escaping points and accumulates a
histogram of how often each pixel is visited. Points that escape quickly
contribute little; points that take many iterations to escape travel far
and contribute the most. The result is a haunting, nebula-like image of
the Mandelbrot set's escape dynamics.
"""
from __future__ import annotations

import logging
import math
import random
from typing import List, Optional, Tuple

from .palettes import get_palette, _clamp_byte
from .viewport import Viewport

logger = logging.getLogger("fractal_explorer")

RGB = Tuple[int, int, int]


def _escape_orbit(c: complex, max_iter: int, bailout: float, power: float = 2.0):
    """Return the orbit (list of complex points) if *c* escapes, else None."""
    z = 0
    orbit = []
    for i in range(max_iter):
        if power == 2:
            z = z * z + c
        elif power == int(power):
            z = z ** int(power) + c
        else:
            z = complex(z) ** power + c
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            orbit.append(z)
            return orbit
        orbit.append(z)
    return None  # didn't escape


class AntiBuddhabrot:
    """Anti-Buddhabrot: traces orbits of *non-escaping* (interior) points.

    This is the complement of the standard Buddhabrot — it accumulates
    visits from points that stay bounded, producing the inverse image.
    """

    @staticmethod
    def render(viewport: Viewport, width: int, height: int,
               samples: int = 100000, max_iter: int = 500,
               bailout: float = 1 << 16, power: float = 2.0,
               palette_name: str = "magma", palette_size: int = 256,
               seed: Optional[int] = None):
        return render_buddhabrot(viewport, width, height, samples=samples,
                                  max_iter=max_iter, bailout=bailout,
                                  power=power, palette_name=palette_name,
                                  palette_size=palette_size, seed=seed,
                                  anti=True)


def render_buddhabrot(viewport: Viewport, width: int, height: int,
                      samples: int = 200000, max_iter: int = 500,
                      bailout: float = 1 << 16, power: float = 2.0,
                      palette_name: str = "fire", palette_size: int = 256,
                      seed: Optional[int] = None,
                      anti: bool = False) -> Tuple[List[RGB], dict]:
    """Render a Buddhabrot image.

    Parameters
    ----------
    viewport : Viewport
        Region of the complex plane to render.
    width, height : int
        Output image dimensions.
    samples : int
        Number of random sample points to try.
    max_iter : int
        Maximum iterations per sample.
    anti : bool
        If True, trace non-escaping orbits instead (Anti-Buddhabrot).

    Returns
    -------
    pixels : list of RGB tuples
    stats : dict
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if samples <= 0:
        raise ValueError("samples must be positive")

    rng = random.Random(seed)
    x_min, x_max = viewport.x_range()
    y_min, y_max = viewport.y_range()

    # Accumulation grid (one per channel for RGB separation by iteration depth).
    grid = [0.0] * (width * height)
    max_val = 0.0

    for _ in range(samples):
        cr = rng.uniform(x_min, x_max)
        ci = rng.uniform(y_min, y_max)
        c = complex(cr, ci)
        orbit = _escape_orbit(c, max_iter, bailout, power)
        escaped = orbit is not None
        if anti:
            if escaped:
                continue
            # Non-escaping: trace the full orbit
            z = 0
            for _i in range(max_iter):
                if power == 2:
                    z = z * z + c
                else:
                    z = complex(z) ** power + c
                px = int((z.real - x_min) / (x_max - x_min) * width)
                py = int((z.imag - y_min) / (y_max - y_min) * height)
                if 0 <= px < width and 0 <= py < height:
                    idx = py * width + px
                    grid[idx] += 1.0
                    if grid[idx] > max_val:
                        max_val = grid[idx]
        else:
            if not escaped:
                continue
            assert orbit is not None
            for z in orbit:
                px = int((z.real - x_min) / (x_max - x_min) * width)
                py = int((z.imag - y_min) / (y_max - y_min) * height)
                if 0 <= px < width and 0 <= py < height:
                    idx = py * width + px
                    grid[idx] += 1.0
                    if grid[idx] > max_val:
                        max_val = grid[idx]

    if max_val <= 0:
        max_val = 1.0

    # Map the grid to colours via the palette using log scaling for contrast.
    palette = get_palette(palette_name, palette_size)
    pixels: List[RGB] = []
    for v in grid:
        if v <= 0:
            pixels.append((0, 0, 0))
            continue
        # Log-scale normalisation brings out the faint structure
        t = math.log1p(v) / math.log1p(max_val)
        idx = max(0, min(palette_size - 1, int(t * (palette_size - 1))))
        pixels.append(palette[idx])

    stats = {"width": width, "height": height, "kind": "buddhabrot",
             "samples": samples, "max_iter": max_iter,
             "anti": anti, "max_val": max_val}
    return pixels, stats