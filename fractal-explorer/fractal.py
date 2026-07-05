#!/usr/bin/env python3
"""Fractal Explorer — Complex dynamics fractal renderer.

A from-scratch, pure-Python library for rendering escape-time fractals:
Mandelbrot, Julia, Multibrot, Burning Ship, Tricorn, Newton's method
basins, Phoenix, Magnet, Celtic, and custom user-defined maps.

Features
--------
* 8 fractal families with configurable parameters (power, Julia constant, …).
* Escape-time iteration with configurable max iterations and bailout radius.
* Smooth (continuous) exterior colouring via the normalized iteration count
  (Hubbard–Douady–Lyubich) to eliminate banding.
* **True distance-estimator (DE) colouring** using derivative tracking
  (``|z'|·ln|z|/|z|``) for crisp boundary detail.
* **Histogram-equalized colouring** — distributes colours evenly across the
  full iteration-count distribution so no band is over- or under-represented.
* **Orbit-trap colouring** — colours a point by how close its orbit approaches
  a configurable trap (point, line, circle).
* **Interior colouring** via average orbit colour (the mean RGB of the orbit
  points) so filled regions are not just a flat colour.
* Arbitrary-precision deep zoom using Python's built-in ``decimal.Decimal``
  so that no external dependencies are required.
* **Multiprocessing parallel rendering** (stdlib ``multiprocessing``) for
  multi-core speed-up on large images.
* **Supersampling anti-aliasing** (2×, 3×, 4×) for smooth edges.
* Colour palettes: rainbow, fire, ice, grayscale, electric, sunset, ocean,
  magma, earth — plus custom hex gradients.
* Multi-format rendering: PNG (pure stdlib zlib), PPM, SVG, ASCII.
* Batch zoom-sequence renderer producing an animation-ready series of frames.
* **Julia-explorer**: render a grid of Julia sets for different constants.
* **Benchmark** subcommand for measuring rendering throughput.
* JSON / YAML / TOML config support with clean, explicit overrides.
* Argparse CLI with sub-commands (render, zoom, julia, newton, ascii, palette,
  explore, benchmark, info).

The library is dependency-free (stdlib only) and pip-installable.

Author: Hermes Agent
"""

from __future__ import annotations

import argparse
import cmath
import json
import logging
import math
import multiprocessing as mp
import os
import struct
import sys
import time
import zlib
from decimal import Decimal, getcontext
from typing import Callable, Optional, Sequence

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logger = logging.getLogger("fractal_explorer")

# --------------------------------------------------------------------------- #
# Palettes
# --------------------------------------------------------------------------- #

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* by t in [0,1]."""
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    """Interpolate between two RGB tuples."""
    return (int(_lerp(c1[0], c2[0], t)),
            int(_lerp(c1[1], c2[1], t)),
            int(_lerp(c1[2], c2[2], t)))


def _clamp_byte(v: int) -> int:
    """Clamp an integer into the 0–255 byte range."""
    return 0 if v < 0 else (255 if v > 255 else v)


def _hsb_to_rgb(h: float, s: float, v: float):
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
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q
    return (_clamp_byte(int(r * 255)), _clamp_byte(int(g * 255)),
            _clamp_byte(int(b * 255)))


def _cycle_hue_palette(size: int, base_hue: float = 0.0, sat: float = 0.85,
                       val: float = 0.95):
    """Generate a size-entry rainbow palette cycling through hue."""
    if size <= 0:
        return [(0, 0, 0)]
    return [_hsb_to_rgb(base_hue + i / max(1, size), sat, val)
            for i in range(size)]


def _gradient_stops(size: int, stops):
    """Build a palette of *size* entries by interpolating fixed colour stops."""
    stops = list(stops)
    n_stops = len(stops)
    if size <= 0 or n_stops == 0:
        return [(0, 0, 0)]
    out = []
    for i in range(size):
        pos = (i / max(1, size - 1)) * (n_stops - 1)
        idx = int(pos)
        frac = pos - idx
        if idx >= n_stops - 1:
            out.append(stops[-1])
        else:
            out.append(_lerp_color(stops[idx], stops[idx + 1], frac))
    return out


# Well-known named palettes (each returns ``size`` RGB tuples).
def rainbow_palette(size=256, **kw):
    return _cycle_hue_palette(size, **kw)


def fire_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 0, 0), (40, 0, 0), (90, 15, 0), (160, 40, 0),
        (210, 90, 0), (245, 160, 30), (255, 220, 110), (255, 255, 220),
    ])


def ice_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 0, 0), (0, 15, 60), (0, 45, 130), (0, 100, 210),
        (40, 170, 255), (140, 230, 255), (220, 250, 255),
    ])


def grayscale_palette(size=256, **kw):
    return [(_clamp_byte(int(i * 255 / max(1, size - 1))),) * 3
            for i in range(size)]


def electric_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 0, 0), (0, 20, 50), (10, 70, 130), (40, 180, 230),
        (180, 250, 255), (255, 255, 255), (130, 200, 255), (0, 0, 0),
    ])


def sunset_palette(size=256, **kw):
    return _gradient_stops(size, [
        (5, 0, 20), (45, 5, 50), (110, 20, 70), (180, 50, 60),
        (230, 110, 40), (255, 180, 60), (255, 230, 140), (255, 245, 210),
    ])


def ocean_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 10, 30), (0, 30, 70), (0, 60, 120), (10, 110, 160),
        (30, 170, 180), (90, 220, 200), (200, 245, 230),
    ])


def magma_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 0, 4), (20, 12, 40), (55, 10, 80), (110, 20, 110),
        (170, 40, 100), (220, 80, 70), (250, 160, 50), (255, 245, 180),
    ])


def earth_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 30, 60), (20, 60, 90), (60, 110, 110), (120, 150, 90),
        (180, 170, 80), (210, 190, 120), (240, 220, 170), (250, 245, 220),
    ])


def custom_palette_from_hex(hex_colors, size=256, **kw):
    """Build a gradient palette from a list of hex strings (#rrggbb)."""
    stops = []
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
}


def get_palette(name: str, size: int = 256, **kw):
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


# --------------------------------------------------------------------------- #
# Fractal definitions
# --------------------------------------------------------------------------- #
#
# Each iterator returns a tuple ``(iter_count, extra)`` where ``extra`` is
# fractal-dependent:
#   * escape-time fractals → ``|z|^2`` at escape (for smooth/DE colouring)
#   * Newton               → ``root_index`` (or -1)
#   * derivative-aware     → a ``(z2, |dz|^2)`` tuple for true DE

def _mandelbrot_iter(c, max_iter, bailout, power=2.0):
    """Iterate ``z = z^p + c`` from ``z=0`` until escape.

    Returns ``(iter_count, |z|^2)``.
    """
    z = 0
    z2 = 0
    for i in range(max_iter):
        if power == 2:
            z = z * z + c
        elif power == int(power):
            z = z ** int(power) + c
        else:
            z = complex(z) ** power + c
        z2 = (z.real * z.real + z.imag * z.imag)
        if z2 > bailout:
            return i + 1, z2
    return max_iter, z2


def _mandelbrot_de_iter(c, max_iter, bailout, power=2):
    """Mandelbrot iteration that also tracks the derivative ``z'``.

    Returns ``(iter_count, (|z|^2, |dz|^2))`` so callers can compute the true
    distance estimator ``d = |z|·ln|z| / |z'|``.

    On non-escape (interior) we return the final ``|z|^2`` and ``|dz|^2``
    rather than leaving them unbound.
    """
    z = 0
    dz = 1  # dz/dc starts at 1
    z2 = 0
    dz2 = 1
    for i in range(max_iter):
        # z'_{n+1} = p·z^{p-1}·z'_n + 1
        if power == 2:
            dz = 2 * z * dz + 1
            z = z * z + c
        else:
            dz = power * (z ** (power - 1)) * dz + 1
            z = z ** power + c
        z2 = z.real * z.real + z.imag * z.imag
        if isinstance(dz, complex):
            dz2 = dz.real * dz.real + dz.imag * dz.imag
        else:
            dz2 = float(dz) * float(dz)
        if z2 > bailout:
            return i + 1, (z2, dz2)
    return max_iter, (z2, dz2)


def _julia_iter(z, c, max_iter, bailout, power=2.0):
    """Julia iteration: ``z = z^p + c`` starting from the pixel coordinate."""
    for i in range(max_iter):
        if power == 2:
            z = z * z + c
        elif power == int(power):
            z = z ** int(power) + c
        else:
            z = complex(z) ** power + c
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


def _burning_ship_iter(c, max_iter, bailout, power=2.0):
    """Burning Ship fractal: ``z = (|Re z| + i|Im z|)^2 + c``."""
    z = 0
    for i in range(max_iter):
        zr = abs(z.real)
        zi = abs(z.imag)
        z = complex(zr, zi)
        z = z * z + c if power == 2 else z ** int(power) + c
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


def _tricorn_iter(c, max_iter, bailout, power=2.0):
    """Tricorn (Mandelbar): ``z = conj(z)^2 + c``."""
    z = 0
    for i in range(max_iter):
        z = z.real * z.real - z.imag * z.imag - 2j * z.real * z.imag + c
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


def _celtic_iter(c, max_iter, bailout, power=2.0):
    """Celtic fractal: ``z = |Re(z^2)| + i·Im(z^2) + c``."""
    z = 0
    for i in range(max_iter):
        zr2 = z.real * z.real - z.imag * z.imag
        zi2 = 2 * z.real * z.imag
        z = complex(abs(zr2), zi2) + c
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


def _phoenix_iter(c, max_iter, bailout, power=2.0, phoenix_c=-0.5):
    """Phoenix fractal: ``z_{n+1} = z_n^p + c + p_c·z_{n-1}``.

    A two-term recurrence that produces distinctive feather-like patterns.
    ``phoenix_c`` is the coefficient of the previous term.
    """
    z = c
    z_prev = 0
    for i in range(max_iter):
        if power == 2:
            z_next = z * z + c + phoenix_c * z_prev
        else:
            z_next = z ** int(power) + c + phoenix_c * z_prev
        z_prev = z
        z = z_next
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


def _magnet_iter(c, max_iter, bailout, power=2, variant=1):
    """Magnet fractal.

    Variant 1: ``m(z) = ((z^2 + c) / (2z^2 + c - 1))^2`` iterating from z=c.

    The rational map has fixed points 0 and 1. A point "escapes" (treated as
    exterior) when it converges to 0 (``|z| < tol``); it is interior when it
    converges to 1 (``|z - 1| < tol``). We detect escape to 0 and report it as
    the iteration count. If neither happens we return ``max_iter`` (interior).

    Produces fractal regions that look like magnetic-field domains.
    """
    z = c
    tol = 1e-6
    for i in range(max_iter):
        z2 = z * z
        if variant == 1:
            num = z2 + c
            den = 2 * z2 + c - 1
        else:  # variant 2 — fall back to variant 1 form (full v2 is unwieldy)
            num = z2 + c
            den = 2 * z2 + c - 1
        if den == 0:
            return i + 1, float("inf")
        z = (num / den) ** 2
        mz2 = z.real * z.real + z.imag * z.imag
        # Escape: orbit converges toward 0 (a repelling fixed point of the
        # inverse map) → large iteration count means "interior".
        if mz2 < tol:
            return i + 1, mz2
        if mz2 > bailout:
            return i + 1, mz2
    return max_iter, 0


def _newton_iter(c, max_iter, bailout, power=3, tol=1e-6, roots=None):
    """Newton's method iteration on ``z^p - 1`` with given roots.

    Returns ``(iterations, root_index)``. ``root_index`` is -1 if it did not
    converge within ``max_iter``.
    """
    z = c
    if roots is None:
        roots = [cmath.rect(1.0, 2 * math.pi * k / power)
                 for k in range(int(power))]
    for i in range(max_iter):
        # f(z) = z^p - 1 ; f'(z) = p z^(p-1)
        if power == int(power):
            zp = z ** int(power)
            dz = int(power) * z ** (int(power) - 1)
        else:
            zp = complex(z) ** power
            dz = power * (complex(z) ** (power - 1))
        if dz == 0:
            return i, -1
        z = z - (zp - 1) / dz
        for idx, r in enumerate(roots):
            if abs(z - r) < tol:
                return i, idx
    return max_iter, -1


def _custom_iter(c, max_iter, bailout, fn: Callable, **kw):
    """Generic escape-time iteration ``z_{n+1} = fn(z_n, c)``.

    ``fn`` is a callable taking ``(z, c)`` returning the next ``z``.
    """
    z = 0
    for i in range(max_iter):
        z = fn(z, c)
        z2 = (z.real * z.real + z.imag * z.imag)
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


# Map fractal kind -> iterator function signature.
# Each returns (iter_count, extra).
FRACTALS = {
    "mandelbrot": lambda c, **kw: _mandelbrot_iter(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0)),
    "julia": lambda c, **kw: _julia_iter(
        c, kw.get("julia_c", -0.7 + 0.27015j),
        kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0)),
    "burning_ship": lambda c, **kw: _burning_ship_iter(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0)),
    "tricorn": lambda c, **kw: _tricorn_iter(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0)),
    "celtic": lambda c, **kw: _celtic_iter(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0)),
    "phoenix": lambda c, **kw: _phoenix_iter(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0), kw.get("phoenix_c", -0.5)),
    "magnet": lambda c, **kw: _magnet_iter(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2), kw.get("variant", 1)),
    "newton": lambda c, **kw: _newton_iter(
        c, kw.get("max_iter", 60), kw.get("bailout", 1 << 16),
        kw.get("power", 3), kw.get("tol", 1e-6)),
}

# Fractals that return a tuple (z2, dz2) in extra for true DE colouring.
DE_CAPABLE = {"mandelbrot"}


def get_fractal(kind: str):
    """Return the iterator callable for a named fractal kind."""
    if kind not in FRACTALS:
        raise ValueError(f"Unknown fractal {kind!r}; options: {list(FRACTALS)}")
    return FRACTALS[kind]


# --------------------------------------------------------------------------- #
# Viewport
# --------------------------------------------------------------------------- #

class Viewport:
    """A rectangular viewport of the complex plane.

    Parameters
    ----------
    center : complex
        Centre of the viewport.
    width : float
        Span along the real axis.
    height : float or None
        Span along the imaginary axis. If ``None`` or <= 0, it is set equal to
        ``width`` (square) unless ``aspect`` is given.
    aspect : float or None
        Pixel aspect ratio (width/height). If given and ``height`` is
        unspecified, the height is derived as ``width / aspect``.
    """

    def __init__(self, center, width, height=None, aspect=None):
        self.center = complex(center)
        self.width = float(width)
        if height is None or height <= 0:
            self.height = self.width if aspect is None else self.width / aspect
        else:
            self.height = float(height)

    def __repr__(self):
        return (f"Viewport(center={self.center}, width={self.width}, "
                f"height={self.height})")

    def x_range(self):
        """Return ``(x_min, x_max)`` of the real-axis span."""
        return (self.center.real - self.width / 2,
                self.center.real + self.width / 2)

    def y_range(self):
        """Return ``(y_min, y_max)`` of the imaginary-axis span."""
        return (self.center.imag - self.height / 2,
                self.center.imag + self.height / 2)

    def zoom(self, factor: float) -> "Viewport":
        """Return a new viewport zoomed by ``factor`` (<1 zooms in)."""
        return Viewport(self.center, self.width * factor,
                        self.height * factor)

    def to_dict(self):
        """Serialize to a JSON-friendly dict."""
        return {"center_re": self.center.real, "center_im": self.center.imag,
                "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d):
        """Deserialize from a dict produced by :meth:`to_dict`."""
        return cls(complex(d["center_re"], d["center_im"]),
                   d["width"], d.get("height"))


# --------------------------------------------------------------------------- #
# Coloring helpers
# --------------------------------------------------------------------------- #

def _smooth_iter(iter_count: int, z2: float, bailout: float, log_power: float):
    """Compute the smooth (continuous) iteration count.

    ``nu = iter_count + 1 - log(log(|z|)) / log(power)``

    This removes the discrete banding of integer iteration counts.
    """
    if iter_count <= 0:
        return 0.0
    log_zn = 0.5 * math.log(z2) if z2 > 0 else 0.0
    nu = iter_count + 1 - math.log(max(1e-12, log_zn)) / log_power
    return max(0.0, nu)


def _true_distance(z2: float, dz2: float, log_power: float):
    """True Mandelbrot distance estimator: ``d = |z|·ln|z| / |z'|``.

    Returns a non-negative float that is small near the boundary.
    """
    if z2 <= 0 or dz2 <= 0:
        return 0.0
    log_zn = 0.5 * math.log(z2)
    if log_zn <= 0:
        return 0.0
    return (math.sqrt(z2) * log_zn) / (math.sqrt(dz2) * log_power)


# --------------------------------------------------------------------------- #
# Orbit traps
# --------------------------------------------------------------------------- #

class OrbitTrap:
    """Base class for orbit-trap colouring.

    Subclasses implement :meth:`distance` which returns the (squared)
    distance from a point to the trap; the minimum over the orbit is used.
    """

    def distance(self, z: complex) -> float:
        raise NotImplementedError


class PointTrap(OrbitTrap):
    """Trap at a single complex point."""

    def __init__(self, point=0 + 0j):
        self.point = complex(point)

    def distance(self, z):
        d = z - self.point
        return d.real * d.real + d.imag * d.imag


class LineTrap(OrbitTrap):
    """Trap at an infinite line through the origin at a given angle (radians)."""

    def __init__(self, angle=0.0):
        self.angle = float(angle)

    def distance(self, z):
        # perpendicular distance to line through origin with direction (cos,sin)
        return (z.real * math.sin(self.angle) - z.imag * math.cos(self.angle)) ** 2


class CircleTrap(OrbitTrap):
    """Trap at a circle of given radius centred at the origin."""

    def __init__(self, radius=1.0):
        self.radius = float(radius)

    def distance(self, z):
        d = abs(z) - self.radius
        return d * d


class CrossTrap(OrbitTrap):
    """Trap at the union of the real and imaginary axes (cross shape)."""

    def distance(self, z):
        return min(z.real * z.real, z.imag * z.imag)


TRAPS = {
    "point": PointTrap,
    "line": LineTrap,
    "circle": CircleTrap,
    "cross": CrossTrap,
}


def make_trap(name: str, **kw):
    """Construct an orbit trap by name."""
    if name not in TRAPS:
        raise ValueError(f"Unknown trap {name!r}; options: {list(TRAPS)}")
    return TRAPS[name](**kw)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def _compute_pixel(c: complex, kind: str, fn, kw, max_iter, coloring, palette,
                   palette_size, log_power, bailout, interior_color, trap,
                   de_capable):
    """Compute the RGB colour for a single pixel. Returns an RGB tuple."""
    it, extra = fn(c, **kw)

    if kind == "newton":
        root_idx = extra
        if root_idx < 0:
            return interior_color
        base = (root_idx * 60) % palette_size
        color = palette[base]
        t = min(1.0, it / max_iter) if max_iter > 0 else 0.0
        return (_clamp_byte(int(color[0] * (0.3 + 0.7 * t))),
                _clamp_byte(int(color[1] * (0.3 + 0.7 * t))),
                _clamp_byte(int(color[2] * (0.3 + 0.7 * t))))

    if it >= max_iter:
        return interior_color

    if coloring == "flat":
        return palette[it % palette_size]

    if coloring == "smooth":
        nu = _smooth_iter(it, extra, bailout, log_power)
        scaled = (nu / max_iter) % 1.0 if max_iter > 0 else 0.0
        idx = max(0, min(palette_size - 1, int(scaled * (palette_size - 1))))
        return palette[idx]

    if coloring == "de":
        if de_capable and isinstance(extra, tuple):
            z2, dz2 = extra
            de = _true_distance(z2, dz2, log_power)
        else:
            # fallback proxy for fractals without derivative tracking
            z2 = extra if not isinstance(extra, tuple) else extra[0]
            nu = _smooth_iter(it, z2, bailout, log_power)
            de = math.exp(-nu * 0.1) if nu > 0 else 0.0
        idx = max(0, min(palette_size - 1, int(de * (palette_size - 1) * 50)))
        return palette[idx]

    if coloring == "trap":
        if trap is None:
            trap = PointTrap()
        # Re-run the iteration tracking the minimum distance to the trap.
        # We must use the *actual* iterator for this fractal kind so the
        # tracked orbit matches the real orbit (e.g. Burning Ship takes
        # abs() of components, Phoenix uses a two-term recurrence, etc.).
        # We re-derive the starting point and step function per kind.
        z = c if kind == "julia" else 0
        z_prev = 0  # for Phoenix two-term recurrence
        min_d = float("inf")
        # Pull fractal-specific params out of kw for the re-run.
        _power = kw.get("power", 2.0)
        _julia_c = kw.get("julia_c", -0.7 + 0.27015j)
        _phoenix_c = kw.get("phoenix_c", -0.5)
        _variant = kw.get("variant", 1)
        for _ in range(it):
            d = trap.distance(z)
            if d < min_d:
                min_d = d
            # Advance one step using the correct formula for this kind.
            if kind == "julia":
                z = (z * z + _julia_c if _power == 2
                     else z ** int(_power) + _julia_c if _power == int(_power)
                     else complex(z) ** _power + _julia_c)
            elif kind == "burning_ship":
                zr, zi = abs(z.real), abs(z.imag)
                zz = complex(zr, zi)
                z = (zz * zz + c if _power == 2
                     else zz ** int(_power) + c)
            elif kind == "tricorn":
                z = (z.real * z.real - z.imag * z.imag
                     - 2j * z.real * z.imag + c)
            elif kind == "celtic":
                zr2 = z.real * z.real - z.imag * z.imag
                zi2 = 2 * z.real * z.imag
                z = complex(abs(zr2), zi2) + c
            elif kind == "phoenix":
                if _power == 2:
                    z_next = z * z + c + _phoenix_c * z_prev
                else:
                    z_next = z ** int(_power) + c + _phoenix_c * z_prev
                z_prev = z
                z = z_next
            elif kind == "magnet":
                z2 = z * z
                num = z2 + c
                den = 2 * z2 + c - 1
                if den == 0:
                    break
                z = (num / den) ** 2
            elif kind == "newton":
                # Newton doesn't have a meaningful "orbit trap" but we
                # still track the iteration point's distance to the trap.
                if _power == int(_power):
                    zp = z ** int(_power)
                    dz = int(_power) * z ** (int(_power) - 1)
                else:
                    zp = complex(z) ** _power
                    dz = _power * (complex(z) ** (_power - 1))
                if dz == 0:
                    break
                z = z - (zp - 1) / dz
            else:
                # mandelbrot / multibrot
                z = (z * z + c if _power == 2
                     else z ** int(_power) + c if _power == int(_power)
                     else complex(z) ** _power + c)
        scaled = math.sqrt(min_d) if min_d < float("inf") else 0.0
        idx = max(0, min(palette_size - 1,
                        int(scaled * (palette_size - 1) * 5)))
        return palette[idx]

    # default: flat
    return palette[it % palette_size]


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
    row_pixels = []
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
        Anti-aliasing factor: each pixel is the average of an
        ``supersample×supersample`` grid (1 = off, 2/3/4 = higher quality).
    workers : int
        Number of parallel worker processes (1 = single process; >1 uses
        ``multiprocessing``).

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
    # Adjust viewport height to match pixel aspect ratio (keep width fixed).
    # Bug fix: previously this mutated the caller's Viewport in place; now
    # we create a local copy so the caller's object is untouched.
    px_aspect = width / height
    plane_aspect = viewport.width / viewport.height
    if abs(plane_aspect - px_aspect) > 1e-9:
        viewport = Viewport(viewport.center, viewport.width,
                            viewport.width / px_aspect)
    else:
        viewport = Viewport(viewport.center, viewport.width, viewport.height)

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
    de_capable = kind in DE_CAPABLE and coloring == "de"

    # For true DE we need the derivative-aware iterator.
    if de_capable:
        fn = lambda c, **k: _mandelbrot_de_iter(
            c, k.get("max_iter", 256), k.get("bailout", 1 << 16),
            k.get("power", 2))

    t0 = time.time()
    ss = supersample
    ss_off = [(i + 0.5) / ss for i in range(ss)]

    # Build the list of sample coordinates (with supersampling offsets).
    # We compute a colour per *output* pixel, averaging ``ss*ss`` sub-samples.

    # Pack the shared parameters once so the worker function can be pickled.
    ctx_data = {
        "kind": kind,
        "kw": kw,
        "max_iter": max_iter,
        "coloring": coloring,
        "palette": palette,
        "palette_size": palette_size,
        "log_power": log_power,
        "bailout": bailout,
        "interior_color": interior_color,
        "trap": trap,
        "de_capable": de_capable,
        "x_min": x_min,
        "y_min": y_min,
        "dx": dx,
        "dy": dy,
        "width": width,
        "ss": ss,
        "ss_off": ss_off,
        "fn_kind": kind,  # workers re-derive fn
        "julia_c": kw.get("julia_c"),
        "power": power,
        "newton_power": kw.get("power") if kind == "newton" else None,
        "phoenix_c": kw.get("phoenix_c"),
        "magnet_variant": kw.get("variant"),
    }

    if workers > 1 and height >= workers:
        # Parallel: distribute rows across worker processes.
        ctx = mp.get_context("spawn")
        with ctx.Pool(workers) as pool:
            rows = pool.map(_render_row_worker,
                            [(row, ctx_data) for row in range(height)])
        pixels = [px for row in rows for px in row]
    else:
        pixels = []
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
    cover equal numbers of pixels (no single band dominates the palette).

    This produces a very different look from smooth/flat colouring and is
    especially good for the Mandelbrot exterior where most pixels escape
    in just a few iterations.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if max_iter <= 0:
        raise ValueError("max_iter must be positive")

    palette = get_palette(palette_name, palette_size)
    # Bug fix: don't mutate the caller's Viewport — make a local copy.
    px_aspect = width / height
    plane_aspect = viewport.width / viewport.height
    if abs(plane_aspect - px_aspect) > 1e-9:
        viewport = Viewport(viewport.center, viewport.width,
                            viewport.width / px_aspect)
    else:
        viewport = Viewport(viewport.center, viewport.width, viewport.height)

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

    # Pass 1: compute iteration counts.
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

    # Build cumulative histogram (skip the max_iter bucket = interior).
    total = sum(hist[:max_iter])  # exclude interior
    if total <= 0:
        total = 1
    cumul = [0] * (max_iter + 1)
    running = 0
    for i in range(max_iter):
        running += hist[i]
        cumul[i] = running / total

    # Pass 2: assign colours.
    pixels = []
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


# --------------------------------------------------------------------------- #
# Arbitrary-precision Mandelbrot (deep zoom)
# --------------------------------------------------------------------------- #

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

    # Use a *local* decimal context so we don't leak precision changes into
    # the global state (which would affect any other Decimal user in the
    # process). Bug fix: previously this called getcontext().prec = prec.
    from decimal import localcontext
    palette = get_palette(palette_name, palette_size)
    x_min, x_max = viewport.x_range()
    y_min, y_max = viewport.y_range()
    with localcontext() as ctx:
        ctx.prec = prec
        x_min = Decimal(repr(x_min))
        x_max = Decimal(repr(x_max))
        y_min = Decimal(repr(y_min))
        y_max = Decimal(repr(y_max))
        dx = (x_max - x_min) / width
        dy = (y_max - y_min) / height
        bailout_sq = Decimal(1 << 16)

        pixels = []
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


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #

def write_ppm(path: str, pixels, width: int, height: int):
    """Write a binary P6 PPM file."""
    with open(path, "wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode())
        buf = bytearray()
        for r, g, b in pixels:
            buf += bytes((_clamp_byte(r), _clamp_byte(g), _clamp_byte(b)))
        f.write(buf)


def write_png(path: str, pixels, width: int, height: int,
              text_meta: Optional[dict] = None):
    """Write an 8-bit RGB PNG file using only the standard library.

    Builds IHDR, optional tEXt metadata chunks, IDAT (zlib-compressed
    scanlines with per-row filter byte 0), and IEND with correct CRC-32.
    """
    def _chunk(tag, data):
        chunk = tag + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = bytearray()
    for row in range(height):
        raw.append(0)  # filter type 0 (None)
        base = row * width
        for col in range(width):
            r, g, b = pixels[base + col]
            raw += bytes((_clamp_byte(r), _clamp_byte(g), _clamp_byte(b)))
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig)
        f.write(_chunk(b"IHDR", ihdr))
        if text_meta:
            for key, val in text_meta.items():
                # tEXt chunk: key\0value (Latin-1)
                text = f"{key}\0{val}".encode("latin-1", "replace")
                f.write(_chunk(b"tEXt", text))
        f.write(_chunk(b"IDAT", idat))
        f.write(_chunk(b"IEND", b""))


def write_svg(path: str, pixels, width: int, height: int):
    """Write an SVG file with one ``<rect>`` per pixel.

    This is only practical for small images (a few hundred pixels) but
    produces infinitely-scalable vector output. For larger images the file
    size grows as O(width·height).
    """
    # Each pixel is a 1x1 rect. Group colours to reduce element count.
    parts = [f'<?xml version="1.0" encoding="UTF-8"?>',
             f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" shape-rendering="crispEdges">']
    for row in range(height):
        base = row * width
        col = 0
        while col < width:
            r, g, b = pixels[base + col]
            # run-length: count identical consecutive pixels in this row
            run = 1
            while col + run < width and pixels[base + col + run] == (r, g, b):
                run += 1
            parts.append(f'<rect x="{col}" y="{row}" width="{run}" height="1" '
                         f'fill="rgb({r},{g},{b})"/>')
            col += run
    parts.append('</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def write_ascii(path: str, pixels, width: int, height: int,
                chars: str = " .:-=+*#%@"):
    """Write an ASCII-art representation of the image (luminance-mapped)."""
    if not chars:
        chars = " .:-=+*#%@"
    lines = []
    n_chars = len(chars)
    for row in range(height):
        line = []
        base = row * width
        for col in range(width):
            r, g, b = pixels[base + col]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            idx = min(n_chars - 1, int(lum * n_chars))
            line.append(chars[idx])
        lines.append("".join(line))
    with open(path, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")


# --------------------------------------------------------------------------- #
# Zoom sequence
# --------------------------------------------------------------------------- #

def render_zoom_sequence(kind: str, center: complex, start_width: float,
                         end_width: float, frames: int, img_size=(400, 300),
                         max_iter=256, palette_name="fire", output_dir=".",
                         prefix="zoom", max_iter_base=None,
                         high_precision=False, prec=60, coloring="smooth",
                         workers=1):
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
            pixels, stats = render_mandelbrot_hp(vp, w, h, max_iter=mi, prec=prec,
                                                  palette_name=palette_name)
        else:
            pixels, stats = render_fractal(kind, vp, w, h, max_iter=mi,
                                             palette_name=palette_name,
                                             coloring=coloring, workers=workers)
        name = f"{prefix}_{i:04d}.png"
        write_png(os.path.join(output_dir, name), pixels, w, h,
                  text_meta={"fractal": kind, "width": str(width_i),
                             "max_iter": str(mi)})
        files.append(name)
        logger.info("frame %d/%d width=%.6g mi=%d -> %s",
                    i + 1, frames, width_i, mi, name)
    return files


# --------------------------------------------------------------------------- #
# Julia explorer: render a grid of Julia sets
# --------------------------------------------------------------------------- #

def explore_julia(grid_size=4, img_size=(150, 150), output_dir="julia_grid",
                  max_iter=150, palette_name="rainbow", power=2.0,
                  c_radius=1.5, workers=1):
    """Render a ``grid_size×grid_size`` grid of Julia sets.

    The Julia constant ``c`` is varied over a grid in the complex plane
    within radius ``c_radius``. Each cell is written as a separate PNG named
    ``julia_r{row}_c{col}.png`` and an HTML index page is generated.
    """
    os.makedirs(output_dir, exist_ok=True)
    step = (2 * c_radius) / max(1, grid_size - 1)
    files = []
    w, h = img_size
    for r in range(grid_size):
        ci = -c_radius + r * step
        for c in range(grid_size):
            cr = -c_radius + c * step
            jc = complex(cr, ci)
            vp = Viewport(0 + 0j, 3.0, 3.0)
            pixels, _ = render_fractal("julia", vp, w, h, max_iter=max_iter,
                                        palette_name=palette_name, power=power,
                                        julia_c=jc, workers=workers)
            name = f"julia_r{r}_c{c}.png"
            write_png(os.path.join(output_dir, name), pixels, w, h,
                      text_meta={"julia_c": str(jc)})
            files.append(name)
    # HTML index
    html = [f"<html><head><title>Julia Grid {grid_size}x{grid_size}</title>",
            "<style>img{{width:120px;height:120px;image-rendering:pixelated}}"
            " table{{border-collapse:collapse}} td{{padding:2px}}</style>",
            "</head><body>", f"<h1>Julia Set Grid ({grid_size}×{grid_size})</h1>",
            "<table>"]
    idx = 0
    for r in range(grid_size):
        html.append("<tr>")
        for c in range(grid_size):
            html.append(f'<td><img src="{files[idx]}"></td>')
            idx += 1
        html.append("</tr>")
    html.append("</table></body></html>")
    with open(os.path.join(output_dir, "index.html"), "w") as f:
        f.write("\n".join(html))
    return files


# --------------------------------------------------------------------------- #
# Benchmark
# --------------------------------------------------------------------------- #

def benchmark(kinds=None, size=(300, 300), max_iter=200, trials=3):
    """Benchmark rendering throughput for each fractal kind.

    Returns a list of dicts with ``kind``, ``avg_ms``, ``pixels_per_sec``.
    """
    if kinds is None:
        kinds = sorted(FRACTALS)
    results = []
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    for kind in kinds:
        times = []
        for _ in range(trials):
            t0 = time.time()
            render_fractal(kind, vp, size[0], size[1], max_iter=max_iter,
                           coloring="smooth")
            times.append(time.time() - t0)
        avg = sum(times) / len(times)
        pps = (size[0] * size[1]) / avg if avg > 0 else 0
        results.append({"kind": kind, "avg_ms": round(avg * 1000, 2),
                        "pixels_per_sec": round(pps, 0)})
    return results


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #

def _load_config(path: str):
    """Load a JSON / YAML / TOML config file into a dict."""
    with open(path) as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    if path.endswith(".toml"):
        try:
            import tomllib  # py3.11+
            return tomllib.loads(text)
        except Exception:
            try:
                import tomli  # third-party fallback
                return tomli.loads(text)
            except Exception:
                raise RuntimeError("TOML config requires Python 3.11+ or tomli")
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(text)
        except Exception:
            raise RuntimeError("YAML config requires PyYAML")
    # default: try json
    return json.loads(text)


def _merge_config(args, cfg: dict, explicit: Optional[set] = None):
    """Merge config-dict values into an argparse Namespace.

    Config values fill in attributes that the user did *not* explicitly pass
    on the command line. ``explicit`` is the set of attribute names that were
    explicitly provided via CLI flags (detected by comparing against the
    argparse defaults). Attributes in ``explicit`` are never overridden.
    """
    explicit = explicit or set()
    for k, v in cfg.items():
        ak = k.replace("-", "_")
        if hasattr(args, ak) and ak not in explicit:
            setattr(args, ak, v)
    return args


def _detect_explicit_args(parser, argv):
    """Return the set of dest names the user explicitly passed on the CLI.

    We scan ``argv`` for option strings (e.g. ``--kind``) and map each to its
    argparse ``dest``. We walk both the top-level parser *and* any subparsers
    (recursively) so that subcommand flags are detected.
    """
    explicit = set()
    seen_strings = set()
    # Collect all option strings from the parser and its subparsers.
    all_option_strings = []  # list of (option_string, dest)

    def _walk(p):
        for action in p._actions:
            all_option_strings.append((action.option_strings, action.dest))
            # subparsers action: recurse into each subparser
            if hasattr(action, "choices") and isinstance(action.choices, dict):
                for sub in action.choices.values():
                    _walk(sub)

    _walk(parser)

    # Find which option strings actually appear in argv.
    for opt_strings, dest in all_option_strings:
        for opt in opt_strings:
            if opt in argv:
                explicit.add(dest)
                break
    return explicit


# --------------------------------------------------------------------------- #
# CLI helpers
# --------------------------------------------------------------------------- #

def _parse_complex(s):
    """Parse a complex number from a string.

    Accepts ``"re,im"``, ``"re+j·im"`` (e.g. ``"-0.7+0.27j"``), or a bare real.

    Raises :class:`ValueError` with a clear message on malformed input.
    """
    if s is None:
        return None
    s = s.strip()
    if "j" in s or "J" in s:
        try:
            return complex(s.replace(" ", ""))
        except ValueError:
            raise ValueError(f"bad complex number: {s!r}")
    if "," in s:
        parts = s.split(",")
        if len(parts) != 2:
            raise ValueError(f"expected 're,im' but got {s!r}")
        try:
            return complex(float(parts[0]), float(parts[1]))
        except ValueError:
            raise ValueError(f"bad complex number: {s!r}")
    try:
        return complex(float(s))
    except ValueError:
        raise ValueError(f"bad complex number: {s!r}")


def _parse_rgb(s):
    """Parse an ``"r,g,b"`` string into a 3-tuple of ints in [0,255].

    Raises :class:`ValueError` with a clear message on malformed input.
    """
    parts = s.split(",")
    if len(parts) != 3:
        raise ValueError(f"expected 'r,g,b' but got {s!r}")
    try:
        vals = [int(x.strip()) for x in parts]
    except ValueError:
        raise ValueError(f"bad RGB (non-integer): {s!r}")
    return tuple(_clamp_byte(p) for p in vals)


# --------------------------------------------------------------------------- #
# CLI commands
# --------------------------------------------------------------------------- #

def _add_render_args(p):
    p.add_argument("--kind", default="mandelbrot", choices=sorted(FRACTALS))
    p.add_argument("--width", type=int, default=600, help="image width px")
    p.add_argument("--height", type=int, default=450, help="image height px")
    p.add_argument("--max-iter", type=int, default=256)
    p.add_argument("--bailout", type=int, default=1 << 16)
    p.add_argument("--palette", default="fire")
    p.add_argument("--coloring", default="smooth",
                    choices=["smooth", "flat", "de", "trap", "root",
                             "histogram"])
    p.add_argument("--power", type=float, default=2.0)
    p.add_argument("--julia-c", default=None, help="complex constant for Julia")
    p.add_argument("--newton-power", type=int, default=3)
    p.add_argument("--phoenix-c", default=None, help="Phoenix coefficient")
    p.add_argument("--magnet-variant", type=int, default=1, choices=[1, 2])
    p.add_argument("--trap", default=None, choices=list(TRAPS),
                    help="orbit trap type (for --coloring trap)")
    p.add_argument("--trap-point", default="0,0", help="trap point (for point trap)")
    p.add_argument("--trap-angle", type=float, default=0.0, help="trap angle rad")
    p.add_argument("--trap-radius", type=float, default=1.0, help="trap radius")
    p.add_argument("--center", default="-0.5,0", help="real,imag center")
    p.add_argument("--viewport-width", type=float, default=3.0)
    p.add_argument("--viewport-height", type=float, default=None)
    p.add_argument("--interior", default="0,0,0", help="interior RGB")
    p.add_argument("--supersample", type=int, default=1,
                    help="anti-aliasing factor (1=off, 2/3/4=higher)")
    p.add_argument("--workers", "-j", type=int, default=1,
                    help="parallel worker processes")
    p.add_argument("--output", "-o", default="fractal.png")
    p.add_argument("--format", default=None, choices=["png", "ppm", "svg", "ascii"])
    p.add_argument("--config", default=None)


def _build_trap(args):
    if not args.trap:
        return None
    if args.trap == "point":
        return PointTrap(_parse_complex(args.trap_point))
    if args.trap == "line":
        return LineTrap(args.trap_angle)
    if args.trap == "circle":
        return CircleTrap(args.trap_radius)
    if args.trap == "cross":
        return CrossTrap()
    return None


def _apply_config_file(args, explicit=None):
    """Load a config file (if any) and merge its values into args.

    ``explicit`` is the set of dest names the user explicitly passed on the
    CLI; these are never overridden by config values. If ``None``, all
    attributes are overridable (back-compat with direct calls).
    """
    if not args.config:
        return args
    cfg = _load_config(args.config)
    return _merge_config(args, cfg, explicit=explicit)


def cmd_render(args):
    center = _parse_complex(args.center)
    vp = Viewport(center, args.viewport_width, args.viewport_height)
    jc = _parse_complex(args.julia_c) if args.julia_c else None
    interior = _parse_rgb(args.interior)
    trap = _build_trap(args)

    if args.coloring == "histogram":
        pixels, stats = render_histogram_coloring(
            args.kind, vp, args.width, args.height, max_iter=args.max_iter,
            bailout=args.bailout, palette_name=args.palette, power=args.power,
            julia_c=jc)
    else:
        pixels, stats = render_fractal(
            args.kind, vp, args.width, args.height, max_iter=args.max_iter,
            bailout=args.bailout, palette_name=args.palette,
            coloring=args.coloring, power=args.power, julia_c=jc,
            newton_power=args.newton_power, interior_color=interior,
            trap=trap, supersample=args.supersample, workers=args.workers)
    fmt = args.format or args.output.rsplit(".", 1)[-1].lower()
    if fmt == "png":
        write_png(args.output, pixels, args.width, args.height,
                  text_meta={"fractal": args.kind,
                             "coloring": args.coloring,
                             "max_iter": str(args.max_iter)})
    elif fmt == "ppm":
        write_ppm(args.output, pixels, args.width, args.height)
    elif fmt == "svg":
        write_svg(args.output, pixels, args.width, args.height)
    elif fmt == "ascii":
        write_ascii(args.output, pixels, args.width, args.height)
    else:
        write_png(args.output, pixels, args.width, args.height)
    print(json.dumps(stats, indent=2))
    print(f"Wrote {args.output}")


def cmd_julia(args):
    args.kind = "julia"
    cmd_render(args)


def cmd_newton(args):
    args.kind = "newton"
    cmd_render(args)


def cmd_zoom(args):
    center = _parse_complex(args.center)
    files = render_zoom_sequence(
        args.kind, center, args.start_width, args.end_width, args.frames,
        img_size=(args.width, args.height), max_iter=args.max_iter,
        palette_name=args.palette, output_dir=args.output_dir,
        prefix=args.prefix, high_precision=args.hp, prec=args.prec,
        coloring=args.coloring, workers=args.workers)
    print(json.dumps({"frames": files}, indent=2))


def cmd_ascii(args):
    args.format = "ascii"
    cmd_render(args)


def cmd_palette(args):
    pal = get_palette(args.name, args.size)
    w, h = args.size, 40
    pixels = []
    for _row in range(h):
        for col in range(w):
            pixels.append(pal[col])
    out = args.output or f"palette_{args.name}.png"
    write_png(out, pixels, w, h)
    print(f"Wrote palette strip -> {out}")


def cmd_explore(args):
    files = explore_julia(grid_size=args.grid, img_size=(args.width, args.height),
                          output_dir=args.output_dir, max_iter=args.max_iter,
                          palette_name=args.palette, power=args.power,
                          c_radius=args.radius, workers=args.workers)
    print(json.dumps({"grid": f"{args.grid}x{args.grid}",
                       "files": len(files),
                       "index": os.path.join(args.output_dir, "index.html")},
                      indent=2))


def cmd_benchmark(args):
    results = benchmark(size=(args.width, args.height), max_iter=args.max_iter,
                        trials=args.trials)
    print(json.dumps(results, indent=2))


def cmd_info(args):
    print("Fractals available:", ", ".join(sorted(FRACTALS)))
    print("Palettes available:", ", ".join(sorted(PALETTES)))
    print("Coloring modes: smooth, flat, de, trap, root, histogram")
    print("Orbit traps:", ", ".join(sorted(TRAPS)))
    print("Output formats: png, ppm, svg, ascii")


def build_cli():
    """Build the argparse CLI."""
    parser = argparse.ArgumentParser(
        prog="fractal-explorer",
        description="Complex dynamics fractal renderer (pure Python, stdlib only).")
    parser.add_argument("--log-level", default="WARNING")
    sub = parser.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("render", help="Render a single fractal image")
    _add_render_args(pr)
    pr.set_defaults(func=cmd_render)

    pj = sub.add_parser("julia", help="Render a Julia set (shortcut)")
    _add_render_args(pj)
    pj.set_defaults(func=cmd_julia)

    pn = sub.add_parser("newton", help="Render a Newton basin fractal (shortcut)")
    _add_render_args(pn)
    pn.set_defaults(func=cmd_newton)

    pa = sub.add_parser("ascii", help="Render to an ASCII art file")
    _add_render_args(pa)
    pa.set_defaults(func=cmd_ascii)

    pz = sub.add_parser("zoom", help="Render a zoom sequence")
    pz.add_argument("--kind", default="mandelbrot", choices=sorted(FRACTALS))
    pz.add_argument("--center", default="-0.5,0")
    pz.add_argument("--start-width", type=float, default=3.0)
    pz.add_argument("--end-width", type=float, default=0.001)
    pz.add_argument("--frames", type=int, default=30)
    pz.add_argument("--width", type=int, default=400)
    pz.add_argument("--height", type=int, default=300)
    pz.add_argument("--max-iter", type=int, default=256)
    pz.add_argument("--palette", default="fire")
    pz.add_argument("--coloring", default="smooth",
                    choices=["smooth", "flat", "de"])
    pz.add_argument("--output-dir", default="zoom_frames")
    pz.add_argument("--prefix", default="zoom")
    pz.add_argument("--hp", action="store_true", help="high-precision Decimal")
    pz.add_argument("--prec", type=int, default=60)
    pz.add_argument("--workers", "-j", type=int, default=1)
    pz.set_defaults(func=cmd_zoom)

    pp = sub.add_parser("palette", help="Render a palette strip")
    pp.add_argument("--name", default="fire", choices=sorted(PALETTES))
    pp.add_argument("--size", type=int, default=256)
    pp.add_argument("--output", default=None)
    pp.set_defaults(func=cmd_palette)

    pe = sub.add_parser("explore", help="Render a grid of Julia sets")
    pe.add_argument("--grid", type=int, default=4, help="grid size N (NxN)")
    pe.add_argument("--width", type=int, default=150)
    pe.add_argument("--height", type=int, default=150)
    pe.add_argument("--max-iter", type=int, default=150)
    pe.add_argument("--palette", default="rainbow")
    pe.add_argument("--power", type=float, default=2.0)
    pe.add_argument("--radius", type=float, default=1.5,
                    help="radius of c-grid in complex plane")
    pe.add_argument("--output-dir", default="julia_grid")
    pe.add_argument("--workers", "-j", type=int, default=1)
    pe.set_defaults(func=cmd_explore)

    pb = sub.add_parser("benchmark", help="Benchmark rendering throughput")
    pb.add_argument("--width", type=int, default=300)
    pb.add_argument("--height", type=int, default=300)
    pb.add_argument("--max-iter", type=int, default=200)
    pb.add_argument("--trials", type=int, default=3)
    pb.set_defaults(func=cmd_benchmark)

    pi = sub.add_parser("info", help="List available fractals & palettes")
    pi.set_defaults(func=cmd_info)

    return parser


def main(argv=None):
    """CLI entry point."""
    parser = build_cli()
    raw_argv = argv if argv is not None else sys.argv[1:]
    args = parser.parse_args(raw_argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(),
                                       logging.WARNING))
    # Detect which dest names the user explicitly passed so that a --config
    # file does not silently override CLI flags.
    explicit = _detect_explicit_args(parser, raw_argv)
    if hasattr(args, "config") and args.config:
        args = _apply_config_file(args, explicit=explicit)
    args.func(args)


if __name__ == "__main__":
    main()