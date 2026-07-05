"""Zoom-sequence batch renderer."""
from __future__ import annotations

import logging
import math
import os

from .render import render_fractal
from .hp import render_mandelbrot_hp
from .io_writers import write_png
from .viewport import Viewport

logger = logging.getLogger("fractal_explorer")


def render_zoom_sequence(kind, center, start_width, end_width, frames,
                         img_size=(400, 300), max_iter=256,
                         palette_name="fire", output_dir=".", prefix="zoom",
                         max_iter_base=None, high_precision=False, prec=60,
                         coloring="smooth", workers=1):
    """Render a zoom sequence producing *frames* frames.

    The width of the viewport shrinks exponentially from ``start_width`` to
    ``end_width``. Iteration count is scaled up as the zoom deepens so that
    detail does not wash out.
    """
    os.makedirs(output_dir, exist_ok=True)
    if frames <= 0:
        raise ValueError("frames must be positive")
    if end_width <= 0 or start_width <= 0:
        raise ValueError("widths must be positive")
    if end_width >= start_width:
        raise ValueError("end_width must be < start_width for a zoom-in")
    ratio = (end_width / start_width) ** (1.0 / max(1, frames - 1))
    files = []
    w, h = img_size
    for i in range(frames):
        width_i = start_width * (ratio ** i)
        if max_iter_base is None:
            mi = int(max_iter * (1 + 2 * math.log10(start_width / width_i + 1)))
        else:
            mi = max_iter_base
        mi = max(64, min(mi, 10000))
        vp = Viewport(center, width_i, width_i)
        if high_precision:
            pixels, stats = render_mandelbrot_hp(
                vp, w, h, max_iter=mi, prec=prec, palette_name=palette_name)
        else:
            pixels, stats = render_fractal(
                kind, vp, w, h, max_iter=mi, palette_name=palette_name,
                coloring=coloring, workers=workers)
        name = f"{prefix}_{i:04d}.png"
        write_png(os.path.join(output_dir, name), pixels, w, h,
                  text_meta={"fractal": kind, "width": str(width_i),
                             "max_iter": str(mi)})
        files.append(name)
        logger.info("frame %d/%d width=%.6g mi=%d -> %s",
                    i + 1, frames, width_i, mi, name)
    return files