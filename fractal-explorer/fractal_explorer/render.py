"""Rendering engine — single-threaded and multiprocessing parallel."""
from __future__ import annotations

import logging
import math
import multiprocessing as mp
import time
from typing import List, Optional, Tuple

from .palettes import get_palette
from .iterators import get_fractal, _mandelbrot_de_iter
from .viewport import Viewport
from .coloring import _compute_pixel

logger = logging.getLogger("fractal_explorer")


def _render_row_worker(task):
    """Module-level worker function for parallel row rendering.

    Receives ``(row_index, ctx_data)`` and returns the list of RGB tuples for
    that row. Must be module-level (not a closure) so it can be pickled by
    ``multiprocessing.spawn``.
    """
    row, cd = task
    kind = cd["kind"]
    max_iter = cd["max_iter"]
    coloring = cd["coloring"]
    palette = cd["palette"]
    palette_size = cd["palette_size"]
    log_power = cd["log_power"]
    bailout = cd["bailout"]
    interior_color = cd["interior_color"]
    trap = cd["trap"]
    de_capable = cd["de_capable"]
    x_min = cd["x_min"]
    y_min = cd["y_min"]
    dx = cd["dx"]
    dy = cd["dy"]
    width = cd["width"]
    ss = cd["ss"]
    ss_off = cd["ss_off"]

    # Rebuild the iterator fn and kwargs for this worker.
    kw = dict(max_iter=max_iter, bailout=bailout, power=cd["power"])
    if cd["julia_c"] is not None:
        kw["julia_c"] = cd["julia_c"]
    if kind == "newton" and cd["newton_power"] is not None:
        kw["power"] = cd["newton_power"]
    if kind == "phoenix" and cd["phoenix_c"] is not None:
        kw["phoenix_c"] = cd["phoenix_c"]
    if kind == "magnet" and cd["magnet_variant"] is not None:
        kw["variant"] = cd["magnet_variant"]
    fn = get_fractal(kind)
    if de_capable:
        fn = lambda c, **k: _mandelbrot_de_iter(
            c, k.get("max_iter", 256), k.get("bailout", 1 << 16),
            k.get("power", 2))

    ci_base = y_min + (row + 0.5) * dy
    row_pixels: List[Tuple[int, int, int]] = []
    for col in range(width):
        cr_base = x_min + (col + 0.5) * dx
        if ss == 1:
            c = complex(cr_base, ci_base)
            row_pixels.append(_compute_pixel(
                c, kind, fn, kw, max_iter, coloring, palette,
                palette_size, log_power, bailout, interior_color,
                trap, de_capable))
        else:
            r_sum = g_sum = b_sum = 0
            for sy in ss_off:
                ci = ci_base + (sy - 0.5) * dy / ss
                for sx in ss_off:
                    cr = cr_base + (sx - 0.5) * dx / ss
                    c = complex(cr, ci)
                    r, g, b = _compute_pixel(
                        c, kind, fn, kw, max_iter, coloring, palette,
                        palette_size, log_power, bailout, interior_color,
                        trap, de_capable)
                    r_sum += r
                    g_sum += g
                    b_sum += b
            n = ss * ss
            row_pixels.append((r_sum // n, g_sum // n, b_sum // n))
    return row_pixels


def render_fractal(kind: str, viewport: Viewport, width: int, height: int,
                   max_iter=256, bailout=1 << 16, palette_name="fire",
                   coloring="smooth", power=2.0, julia_c=None, newton_power=3,
                   interior_color=(0, 0, 0), log_power=None, palette_size=256,
                   trap=None, supersample=1, workers=1):
    """Render an escape-time fractal to a flat list of RGB pixels.

    Parameters
    ----------
    kind : str
        Fractal family — one of the keys of :data:`FRACTALS`.
    viewport : Viewport
        Complex-plane region to render.
    width, height : int
        Output image dimensions in pixels.
    max_iter : int
        Maximum iteration count (must be > 0).
    bailout : float
        Escape radius squared threshold.
    palette_name : str
        Name of the palette to use.
    coloring : str
        One of ``smooth``, ``flat``, ``de``, ``trap``, ``root`` (Newton only).
    power : float
        Fractal power.
    julia_c : complex or None
        Constant for Julia sets.
    newton_power : int
        Power for Newton's method.
    interior_color : tuple
        RGB color for non-escaping points.
    log_power : float or None
        Log of the fractal power for the smooth formula; defaults to ln(power).
    palette_size : int
        Number of entries in the palette (must be > 0).
    trap : OrbitTrap or None
        Orbit trap for ``coloring="trap"``.
    supersample : int
        Anti-aliasing factor.
    workers : int
        Number of parallel worker processes.

    Returns
    -------
    pixels : list[tuple[int,int,int]]
        Flat list of ``width*height`` RGB tuples, row-major top-to-bottom.
    stats : dict
        Render statistics.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if max_iter <= 0:
        raise ValueError("max_iter must be positive")
    if palette_size <= 0:
        raise ValueError("palette_size must be positive")
    if supersample < 1:
        raise ValueError("supersample must be >= 1")
    if workers < 1:
        raise ValueError("workers must be >= 1")

    palette = get_palette(palette_name, palette_size)
    # Adjust viewport height to match pixel aspect ratio (don't mutate caller).
    px_aspect = width / height
    viewport = viewport.fit_aspect(px_aspect)

    x_min, x_max = viewport.x_range()
    y_min, y_max = viewport.y_range()
    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height

    if log_power is None:
        log_power = math.log(power) if power > 1 else math.log(2)

    kw = dict(max_iter=max_iter, bailout=bailout, power=power)
    if julia_c is not None:
        kw["julia_c"] = julia_c
    if kind == "newton":
        kw["power"] = newton_power
    if kind == "phoenix":
        kw.setdefault("phoenix_c", -0.5)
    if kind == "magnet":
        kw.setdefault("variant", 1)
    fn = get_fractal(kind)
    de_capable = kind in ("mandelbrot", "mandelbrot_periodic") and coloring == "de"

    if de_capable:
        fn = lambda c, **k: _mandelbrot_de_iter(
            c, k.get("max_iter", 256), k.get("bailout", 1 << 16),
            k.get("power", 2))

    t0 = time.time()
    ss = supersample
    ss_off = [(i + 0.5) / ss for i in range(ss)]

    ctx_data = {
        "kind": kind, "max_iter": max_iter, "coloring": coloring,
        "palette": palette, "palette_size": palette_size,
        "log_power": log_power, "bailout": bailout,
        "interior_color": interior_color, "trap": trap,
        "de_capable": de_capable, "x_min": x_min, "y_min": y_min,
        "dx": dx, "dy": dy, "width": width, "ss": ss, "ss_off": ss_off,
        "julia_c": kw.get("julia_c"), "power": power,
        "newton_power": kw.get("power") if kind == "newton" else None,
        "phoenix_c": kw.get("phoenix_c"),
        "magnet_variant": kw.get("variant"),
    }

    if workers > 1 and height >= workers:
        ctx = mp.get_context("spawn")
        with ctx.Pool(workers) as pool:
            rows = pool.map(_render_row_worker,
                            [(row, ctx_data) for row in range(height)])
        pixels = [px for row in rows for px in row]
    else:
        pixels: List[Tuple[int, int, int]] = []
        for row in range(height):
            pixels.extend(_render_row_worker((row, ctx_data)))

    elapsed = time.time() - t0
    stats = {
        "width": width, "height": height, "kind": kind,
        "viewport": repr(viewport), "max_iter": max_iter,
        "coloring": coloring, "palette": palette_name,
        "supersample": supersample, "workers": workers,
        "elapsed": round(elapsed, 4),
    }
    return pixels, stats


def render_histogram_coloring(kind: str, viewport: Viewport, width: int,
                              height: int, max_iter=256, bailout=1 << 16,
                              power=2.0, julia_c=None, palette_name="fire",
                              palette_size=256, interior_color=(0, 0, 0)):
    """Render with histogram-equalized colouring.

    First pass: compute the integer iteration count for every pixel.
    Second pass: map each count to a colour so that equal colour ranges
    cover equal numbers of pixels.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if max_iter <= 0:
        raise ValueError("max_iter must be positive")

    palette = get_palette(palette_name, palette_size)
    px_aspect = width / height
    viewport = viewport.fit_aspect(px_aspect)

    x_min, x_max = viewport.x_range()
    y_min, y_max = viewport.y_range()
    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height

    kw = dict(max_iter=max_iter, bailout=bailout, power=power)
    if julia_c is not None:
        kw["julia_c"] = julia_c
    if kind == "newton":
        kw["power"] = 3
    fn = get_fractal(kind)

    iters = [0] * (width * height)
    hist = [0] * (max_iter + 1)
    for row in range(height):
        ci = y_min + (row + 0.5) * dy
        base = row * width
        for col in range(width):
            cr = x_min + (col + 0.5) * dx
            it, _ = fn(complex(cr, ci), **kw)
            iters[base + col] = it
            hist[it] += 1

    total = sum(hist[:max_iter])
    if total <= 0:
        total = 1
    cumul = [0.0] * (max_iter + 1)
    running = 0
    for i in range(max_iter):
        running += hist[i]
        cumul[i] = running / total

    pixels: List[Tuple[int, int, int]] = []
    for it in iters:
        if it >= max_iter:
            pixels.append(interior_color)
        else:
            frac = cumul[it]
            idx = max(0, min(palette_size - 1,
                             int(frac * (palette_size - 1))))
            pixels.append(palette[idx])
    return pixels, {"width": width, "height": height, "kind": kind,
                     "coloring": "histogram"}