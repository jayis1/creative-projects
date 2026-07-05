"""High-precision Mandelbrot rendering using decimal.Decimal."""
from __future__ import annotations

import logging
import time
from decimal import Decimal, localcontext
from typing import List, Tuple

from .palettes import get_palette
from .viewport import Viewport

logger = logging.getLogger("fractal_explorer")


def mandelbrot_decimal(c_re: Decimal, c_im: Decimal, max_iter: int,
                       bailout_sq: Decimal, prec: int = 50):
    """High-precision Mandelbrot iteration using ``Decimal``.

    Returns ``(iter_count, |z|^2 as Decimal)``.
    """
    zr = Decimal(0)
    zi = Decimal(0)
    for i in range(max_iter):
        zr2 = zr * zr
        zi2 = zi * zi
        if zr2 + zi2 > bailout_sq:
            return i + 1, zr2 + zi2
        new_zr = zr2 - zi2 + c_re
        new_zi = (zr + zr) * zi + c_im
        zr, zi = new_zr, new_zi
    return max_iter, zr * zr + zi * zi


def render_mandelbrot_hp(viewport: Viewport, width: int, height: int,
                        max_iter=512, prec=60, palette_name="fire",
                        palette_size=256, interior_color=(0, 0, 0)):
    """High-precision Mandelbrot render using ``Decimal`` arithmetic.

    Used for deep zoom where double precision would suffer catastrophic
    cancellation. Colour is flat (no smooth coloring) for speed and
    correctness at extreme zoom depths.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if max_iter <= 0:
        raise ValueError("max_iter must be positive")
    if prec < 10:
        raise ValueError("prec must be >= 10")

    palette = get_palette(palette_name, palette_size)
    x_min, x_max = viewport.x_range()
    y_min, y_max = viewport.y_range()

    # Use a *local* decimal context so we don't leak precision changes.
    with localcontext() as ctx:
        ctx.prec = prec
        x_min = Decimal(repr(x_min))
        x_max = Decimal(repr(x_max))
        y_min = Decimal(repr(y_min))
        y_max = Decimal(repr(y_max))
        dx = (x_max - x_min) / width
        dy = (y_max - y_min) / height
        bailout_sq = Decimal(1 << 16)

        pixels: List[Tuple[int, int, int]] = []
        t0 = time.time()
        for row in range(height):
            ci = y_min + (Decimal(row) + Decimal("0.5")) * dy
            for col in range(width):
                cr = x_min + (Decimal(col) + Decimal("0.5")) * dx
                it, z2 = mandelbrot_decimal(cr, ci, max_iter, bailout_sq, prec)
                if it >= max_iter:
                    pixels.append(interior_color)
                else:
                    idx = it % palette_size
                    pixels.append(palette[idx])
    stats = {"width": width, "height": height, "kind": "mandelbrot-hp",
             "prec": prec, "max_iter": max_iter,
             "elapsed": round(time.time() - t0, 4)}
    return pixels, stats