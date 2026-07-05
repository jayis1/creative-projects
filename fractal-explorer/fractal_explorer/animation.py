"""Animation renderers — produce sequences of frames for GIF/video assembly."""
from __future__ import annotations

import os
from typing import List

from .render import render_fractal
from .io_writers import write_png
from .viewport import Viewport


def render_julia_morph(c_start, c_end, frames: int, width: int = 400,
                       height: int = 300, max_iter: int = 200,
                       palette_name: str = "rainbow",
                       output_dir: str = "julia_morph",
                       prefix: str = "morph") -> List[str]:
    """Render a Julia-set morph: interpolate ``c`` from ``c_start`` to ``c_end``.

    Produces a sequence of PNG frames suitable for assembling into a video
    or animated GIF with external tools (ffmpeg, ImageMagick).
    """
    os.makedirs(output_dir, exist_ok=True)
    files = []
    vp = Viewport(0 + 0j, 3.0, 2.0)
    for i in range(frames):
        t = i / max(1, frames - 1)
        c = complex(c_start.real + (c_end.real - c_start.real) * t,
                    c_start.imag + (c_end.imag - c_start.imag) * t)
        pixels, _ = render_fractal("julia", vp, width, height,
                                    max_iter=max_iter,
                                    palette_name=palette_name, julia_c=c)
        name = f"{prefix}_{i:04d}.png"
        write_png(os.path.join(output_dir, name), pixels, width, height,
                  text_meta={"julia_c": str(c), "frame": str(i)})
        files.append(name)
    return files


def render_color_cycle(kind: str, viewport: Viewport, frames: int,
                        width: int = 400, height: int = 300,
                        max_iter: int = 200,
                        palette_name: str = "rainbow",
                        output_dir: str = "color_cycle",
                        prefix: str = "cycle") -> List[str]:
    """Render a colour-cycling animation.

    The fractal is rendered once with flat coloring; each frame shifts the
    palette index by a fixed amount, producing a "flowing colours" effect
    without re-rendering the iteration data. The raw iteration counts are
    stored and re-mapped per frame.
    """
    os.makedirs(output_dir, exist_ok=True)
    from .palettes import get_palette
    from .iterators import get_fractal

    palette = get_palette(palette_name, 256)
    palette_size = len(palette)

    # Render with flat coloring, but capture raw iteration counts.
    px_aspect = width / height
    vp = viewport.fit_aspect(px_aspect)
    x_min, x_max = vp.x_range()
    y_min, y_max = vp.y_range()
    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height
    fn = get_fractal(kind)
    kw = dict(max_iter=max_iter, bailout=1 << 16, power=2.0)
    if kind == "julia":
        kw["julia_c"] = -0.7 + 0.27015j
    elif kind == "newton":
        kw["power"] = 3

    iters: List[int] = []
    for row in range(height):
        ci = y_min + (row + 0.5) * dy
        for col in range(width):
            cr = x_min + (col + 0.5) * dx
            it, _ = fn(complex(cr, ci), **kw)
            iters.append(int(it) if it < max_iter else -1)

    files = []
    for i in range(frames):
        shift = int(i * palette_size / frames)
        out_pixels = []
        for it in iters:
            if it < 0:
                out_pixels.append((0, 0, 0))
            else:
                out_pixels.append(palette[(it + shift) % palette_size])
        name = f"{prefix}_{i:04d}.png"
        write_png(os.path.join(output_dir, name), out_pixels, width, height)
        files.append(name)
    return files