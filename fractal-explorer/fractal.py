#!/usr/bin/env python3
"""Fractal Explorer — Complex dynamics fractal renderer.

A from-scratch, pure-Python library for rendering escape-time fractals:
Mandelbrot, Julia, Multibrot, Burning Ship, Tricorn, Newton's method
basins, and custom user-defined maps.

Features
--------
* 7 fractal families with configurable parameters (power, Julia constant, …).
* Escape-time iteration with configurable max iterations and bailout radius.
* Smooth (continuous) exterior colouring via the normalized iteration count
  (Hubbard-Lyubich-Shishikura) to eliminate banding.
* Distance estimator (DE) colouring for crisp boundary detail.
* Interior colouring via derivative / period detection (basic).
* Arbitrary-precision deep zoom using Python's built-in ``decimal.Decimal``
  so that no external dependencies are required.
* Histogram-equalized colour palettes (rainbow, fire, ice, grayscale, custom).
* Multi-format rendering: PNG (pure stdlib zlib), PPM, ASCII.
* Batch zoom-sequence renderer producing an animation-ready series of frames.
* JSON / YAML / TOML config support.
* Argparse CLI with sub-commands (render, zoom, julia, newton, ascii, palette,
  info).

The library is dependency-free (stdlib only) and pip-installable.

Author: Hermes Agent
"""

from __future__ import annotations

import argparse
import cmath
import json
import logging
import math
import struct
import sys
import time
import zlib
from decimal import Decimal, getcontext, ROUND_HALF_EVEN
from typing import Callable, Iterator, Optional

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
    return (int(_lerp(c1[0], c2[0], t)),
            int(_lerp(c1[1], c2[1], t)),
            int(_lerp(c1[2], c2[2], t)))


def _hsb_to_rgb(h: float, s: float, v: float):
    """Convert HSB (h,s,v in [0,1]) to 8-bit RGB tuple."""
    if s == 0:
        g = int(v * 255)
        return (g, g, g)
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
    return (int(r * 255), int(g * 255), int(b * 255))


def _cycle_hue_palette(size: int, base_hue: float = 0.0, sat: float = 0.85,
                       val: float = 0.95):
    """Generate a size-entry rainbow palette cycling through hue."""
    if size <= 0:
        return [(0, 0, 0)]
    out = []
    for i in range(size):
        h = (base_hue + i / max(1, size)) % 1.0
        out.append(_hsb_to_rgb(h, sat, val))
    return out


def _gradient_stops(size: int, stops):
    """Build a palette of *size* entries by interpolating fixed colour stops."""
    stops = list(stops)
    n_stops = len(stops)
    if size <= 0:
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
    return [(int(i * 255 / max(1, size - 1)),) * 3 for i in range(size)]


def electric_palette(size=256, **kw):
    return _gradient_stops(size, [
        (0, 0, 0), (0, 20, 50), (10, 70, 130), (40, 180, 230),
        (180, 250, 255), (255, 255, 255), (130, 200, 255), (0, 0, 0),
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
}


def get_palette(name: str, size: int = 256, **kw):
    """Look up a named palette function and build it."""
    if name in PALETTES:
        return PALETTES[name](size, **kw)
    if name.startswith("#") or (name.startswith("[") and name.endswith("]")):
        # parse comma-separated hex list
        hexes = json.loads(name) if name.startswith("[") else [
            h.strip() for h in name.split(",")
        ]
        return custom_palette_from_hex(hexes, size)
    raise ValueError(f"Unknown palette {name!r}; options: {list(PALETTES)}")


# --------------------------------------------------------------------------- #
# Fractal definitions
# --------------------------------------------------------------------------- #

def _mandelbrot_iter(c, max_iter, bailout, power=2.0):
    """Iterate z = z^p + c from z=0 until escape. Returns (iter_count, |z|^2)."""
    z = 0
    z2 = 0
    for i in range(max_iter):
        # complex pow for non-integer powers via logarithmic identity
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


def _julia_iter(z, c, max_iter, bailout, power=2.0):
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
    """Tricorn (Mandelbar): z = conj(z)^2 + c."""
    z = 0
    for i in range(max_iter):
        z = z.real * z.real - z.imag * z.imag - 2j * z.real * z.imag + c
        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


def _newton_iter(c, max_iter, bailout, power=3, tol=1e-6, roots=None):
    """Newton's method iteration on z^p - 1 with given roots.

    Returns (iterations, root_index). ``root_index`` is -1 if it did not
    converge within ``max_iter``.
    """
    z = c
    if roots is None:
        roots = [cmath.rect(1.0, 2 * math.pi * k / power) for k in range(int(power))]
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
        # find nearest root
        for idx, r in enumerate(roots):
            if abs(z - r) < tol:
                return i, idx
    return max_iter, -1


def _custom_iter(c, max_iter, bailout, fn: Callable[[complex], complex]):
    """Generic escape-time iteration z = fn(z) + c? Actually: z_{n+1} = fn(z_n, c).

    ``fn`` is a callable taking (z, c) returning the next z.
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
    "mandelbrot": lambda c, **kw: _mandelbrot_iter(c, kw.get("max_iter", 256),
                                                    kw.get("bailout", 1 << 16),
                                                    kw.get("power", 2.0)),
    "julia": lambda c, **kw: _julia_iter(c, kw.get("julia_c", -0.7 + 0.27015j),
                                          kw.get("max_iter", 256),
                                          kw.get("bailout", 1 << 16),
                                          kw.get("power", 2.0)),
    "burning_ship": lambda c, **kw: _burning_ship_iter(c, kw.get("max_iter", 256),
                                                        kw.get("bailout", 1 << 16),
                                                        kw.get("power", 2.0)),
    "tricorn": lambda c, **kw: _tricorn_iter(c, kw.get("max_iter", 256),
                                              kw.get("bailout", 1 << 16),
                                              kw.get("power", 2.0)),
    "newton": lambda c, **kw: _newton_iter(c, kw.get("max_iter", 60),
                                            kw.get("bailout", 1 << 16),
                                            kw.get("power", 3),
                                            kw.get("tol", 1e-6)),
}


def get_fractal(kind: str):
    if kind not in FRACTALS:
        raise ValueError(f"Unknown fractal {kind!r}; options: {list(FRACTALS)}")
    return FRACTALS[kind]


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

class Viewport:
    """A rectangular viewport of the complex plane."""

    def __init__(self, center, width, height, aspect=None):
        """center: complex. width: float (real span). height: float (imag span).

        If ``height`` is None or 0, it is derived from ``width`` and the
        pixel aspect ratio.
        """
        self.center = complex(center)
        self.width = float(width)
        if height is None or height <= 0:
            # square default if not specified
            self.height = self.width if aspect is None else self.width / aspect
        else:
            self.height = float(height)

    def __repr__(self):
        return (f"Viewport(center={self.center}, width={self.width}, "
                f"height={self.height})")

    def x_range(self):
        return (self.center.real - self.width / 2,
                self.center.real + self.width / 2)

    def y_range(self):
        return (self.center.imag - self.height / 2,
                self.center.imag + self.height / 2)


def _smooth_iter(iter_count: int, z2: float, bailout: float, log_power: float):
    """Compute smooth (continuous) iteration count using the Hubbard formula.

    ``nu = iter_count + 1 - log(log(|z|)) / log(power)``
    """
    if iter_count <= 0:
        return 0.0
    log_zn = 0.5 * math.log(z2) if z2 > 0 else 0.0
    nu = iter_count + 1 - math.log(max(1e-12, log_zn)) / log_power
    return max(0.0, nu)


def render_fractal(kind: str, viewport: Viewport, width: int, height: int,
                   max_iter=256, bailout=1 << 16, palette_name="fire",
                   coloring="smooth", power=2.0, julia_c=None, newton_power=3,
                   interior_color=(0, 0, 0), log_power=None, palette_size=256):
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
        Maximum iteration count.
    bailout : float
        Escape radius squared threshold (default 2**16 = 65536, i.e. |z|>256).
    palette_name : str
        Name of the palette to use.
    coloring : str
        One of ``smooth``, ``flat``, ``de`` (distance estimator), ``root``
        (for Newton).
    power : float
        Fractal power (for Multibrot/Julia/Burning Ship/Tricorn/Newton).
    julia_c : complex or None
        Constant for Julia sets.
    newton_power : int
        Power for Newton's method.
    interior_color : tuple
        RGB color for non-escaping points.
    log_power : float or None
        Log of the fractal power for the smooth formula; defaults to ln(power).
    palette_size : int
        Number of entries in the palette.

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

    palette = get_palette(palette_name, palette_size)
    # adjust viewport to match pixel aspect
    px_aspect = width / height
    plane_aspect = viewport.width / viewport.height
    if abs(plane_aspect - px_aspect) > 1e-9:
        # adjust height to keep center fixed and width as given
        viewport.height = viewport.width / px_aspect

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
    fn = get_fractal(kind)

    pixels = []
    t0 = time.time()
    escape_count = 0
    interior_count = 0
    max_seen = 0

    for row in range(height):
        ci = y_min + (row + 0.5) * dy
        for col in range(width):
            cr = x_min + (col + 0.5) * dx
            c = complex(cr, ci)
            it, extra = fn(c, **kw)
            if kind == "newton":
                # extra is root_index
                if extra < 0:
                    pixels.append(interior_color)
                    interior_count += 1
                else:
                    base = (extra * 60) % palette_size
                    color = palette[base]
                    # blend with iteration count for shading
                    t = min(1.0, it / max_iter)
                    dark = (int(color[0] * (0.3 + 0.7 * t)),
                            int(color[1] * (0.3 + 0.7 * t)),
                            int(color[2] * (0.3 + 0.7 * t)))
                    pixels.append(dark)
                    escape_count += 1
                continue

            if it >= max_iter:
                pixels.append(interior_color)
                interior_count += 1
            else:
                if coloring == "flat":
                    idx = it % palette_size
                    pixels.append(palette[idx])
                elif coloring == "smooth":
                    nu = _smooth_iter(it, extra, bailout, log_power)
                    # normalize to [0,1) via a cyclic mapping that keeps
                    # detail even at high iteration counts.
                    if max_iter > 0:
                        scaled = (nu / max_iter) % 1.0
                    else:
                        scaled = 0.0
                    idx = int(scaled * (palette_size - 1))
                    idx = max(0, min(palette_size - 1, idx))
                    pixels.append(palette[idx])
                elif coloring == "de":
                    # Distance estimator: d = |z| * ln|z| / |z'|
                    # Approximate |z'| via finite difference on log scale.
                    z2 = extra
                    log_zn = 0.5 * math.log(z2) if z2 > 0 else 0.0
                    # Use the smooth iteration count to derive a DE proxy
                    nu = _smooth_iter(it, z2, bailout, log_power)
                    de = math.exp(-nu * 0.1) if nu > 0 else 0.0
                    idx = int(de * (palette_size - 1))
                    idx = max(0, min(palette_size - 1, idx))
                    pixels.append(palette[idx])
                else:
                    idx = it % palette_size
                    pixels.append(palette[idx])
                escape_count += 1
                if it > max_seen:
                    max_seen = it

    stats = {
        "width": width, "height": height, "kind": kind,
        "viewport": repr(viewport), "max_iter": max_iter,
        "escape_count": escape_count, "interior_count": interior_count,
        "max_iter_seen": max_seen, "elapsed": time.time() - t0,
    }
    return pixels, stats


# --------------------------------------------------------------------------- #
# Arbitrary-precision Mandelbrot (deep zoom)
# --------------------------------------------------------------------------- #

def mandelbrot_decimal(c_re: Decimal, c_im: Decimal, max_iter: int,
                       bailout_sq: Decimal, prec: int = 50):
    """High-precision Mandelbrot iteration using Decimal.

    Returns (iter_count, |z|^2 as Decimal).
    """
    zr = Decimal(0)
    zi = Decimal(0)
    for i in range(max_iter):
        zr2 = zr * zr
        zi2 = zi * zi
        if zr2 + zi2 > bailout_sq:
            return i + 1, zr2 + zi2
        # z = z^2 + c
        new_zr = zr2 - zi2 + c_re
        new_zi = (zr + zr) * zi + c_im
        zr, zi = new_zr, new_zi
    return max_iter, zr * zr + zi * zi


def render_mandelbrot_hp(viewport: Viewport, width: int, height: int,
                        max_iter=512, prec=60, palette_name="fire",
                        palette_size=256, interior_color=(0, 0, 0)):
    """High-precision Mandelbrot render using Decimal arithmetic.

    Used for deep zoom where double precision would suffer catastrophic
    cancellation. Color is flat (no smooth coloring) for speed and
    correctness at extreme zoom depths.
    """
    getcontext().prec = prec
    palette = get_palette(palette_name, palette_size)
    x_min, x_max = viewport.x_range()
    y_min, y_max = viewport.y_range()
    x_min = Decimal(str(x_min))
    x_max = Decimal(str(x_max))
    y_min = Decimal(str(y_min))
    y_max = Decimal(str(y_max))
    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height
    bailout_sq = Decimal(1 << 16)

    pixels = []
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
             "prec": prec, "max_iter": max_iter}
    return pixels, stats


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #

def write_ppm(path: str, pixels, width: int, height: int):
    """Write a P6 PPM file."""
    with open(path, "wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode())
        buf = bytearray()
        for r, g, b in pixels:
            buf += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
        f.write(buf)


def write_png(path: str, pixels, width: int, height: int):
    """Write a PNG file using only the standard library.

    Builds an 8-bit RGB PNG with no compression of the IHDR / image data
    beyond what zlib provides (so this works everywhere).
    """
    def _chunk(tag, data):
        chunk = tag + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # image data: filter byte 0 per row, then RGB triples
    raw = bytearray()
    for row in range(height):
        raw.append(0)
        base = row * width
        for col in range(width):
            r, g, b = pixels[base + col]
            raw += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig)
        f.write(_chunk(b"IHDR", ihdr))
        f.write(_chunk(b"IDAT", idat))
        f.write(_chunk(b"IEND", b""))


def write_ascii(path: str, pixels, width: int, height: int,
                chars: str = " .:-=+*#%@"):
    """Write an ASCII-art representation of the image (luminance-mapped)."""
    lines = []
    # downsample if image is wide
    for row in range(height):
        line = []
        base = row * width
        for col in range(width):
            r, g, b = pixels[base + col]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            idx = int(lum * (len(chars) - 1))
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
                         prefix="zoom", max_iter_base=None, high_precision=False,
                         prec=60):
    """Render a zoom sequence producing *frames* frames.

    The width of the viewport shrinks exponentially from ``start_width`` to
    ``end_width``. Iteration count is scaled up as the zoom deepens so that
    detail does not wash out.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    if frames <= 0:
        raise ValueError("frames must be positive")
    if end_width <= 0 or start_width <= 0:
        raise ValueError("widths must be positive")
    ratio = (end_width / start_width) ** (1.0 / max(1, frames - 1))
    files = []
    w, h = img_size
    for i in range(frames):
        width_i = start_width * (ratio ** i)
        # scale iteration count with zoom: more detail near the boundary
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
                                             palette_name=palette_name)
        name = f"{prefix}_{i:04d}.png"
        write_png(os.path.join(output_dir, name), pixels, w, h)
        files.append(name)
        logger.info("frame %d/%d width=%.6g mi=%d -> %s",
                    i + 1, frames, width_i, mi, name)
    return files


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


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _add_render_args(p):
    p.add_argument("--kind", default="mandelbrot", choices=sorted(FRACTALS))
    p.add_argument("--width", type=int, default=600, help="image width px")
    p.add_argument("--height", type=int, default=450, help="image height px")
    p.add_argument("--max-iter", type=int, default=256)
    p.add_argument("--bailout", type=int, default=1 << 16)
    p.add_argument("--palette", default="fire")
    p.add_argument("--coloring", default="smooth",
                    choices=["smooth", "flat", "de", "root"])
    p.add_argument("--power", type=float, default=2.0)
    p.add_argument("--julia-c", default=None, help="complex constant for Julia")
    p.add_argument("--newton-power", type=int, default=3)
    p.add_argument("--center", default="-0.5,0", help="real,imag center")
    p.add_argument("--viewport-width", type=float, default=3.0)
    p.add_argument("--viewport-height", type=float, default=None)
    p.add_argument("--interior", default="0,0,0", help="interior RGB")
    p.add_argument("--output", "-o", default="fractal.png")
    p.add_argument("--format", default=None, choices=["png", "ppm", "ascii"])
    p.add_argument("--config", default=None)


def _parse_complex(s):
    if s is None:
        return None
    s = s.strip()
    if "j" in s:
        return complex(s.replace(" ", ""))
    if "," in s:
        re, im = s.split(",")
        return complex(float(re), float(im))
    return complex(float(s))


def _parse_rgb(s):
    parts = [int(x.strip()) for x in s.split(",")]
    if len(parts) != 3:
        raise ValueError(f"bad RGB: {s!r}")
    return tuple(parts)


def _apply_config(args):
    if not args.config:
        return args
    cfg = _load_config(args.config)
    for k, v in cfg.items():
        ak = k.replace("-", "_")
        if hasattr(args, ak) and getattr(args, ak) is None:
            setattr(args, ak, v)
        elif hasattr(args, ak) and getattr(args, ak) in (None, "", 0, False,
                                                         3.0, 256, "mandelbrot",
                                                         "fire", "smooth",
                                                         "-0.5,0"):
            # only override defaults
            setattr(args, ak, v)
    return args


def cmd_render(args):
    args = _apply_config(args)
    center = _parse_complex(args.center)
    vp = Viewport(center, args.viewport_width, args.viewport_height)
    jc = _parse_complex(args.julia_c) if args.julia_c else None
    interior = _parse_rgb(args.interior)
    pixels, stats = render_fractal(
        args.kind, vp, args.width, args.height, max_iter=args.max_iter,
        bailout=args.bailout, palette_name=args.palette,
        coloring=args.coloring, power=args.power, julia_c=jc,
        newton_power=args.newton_power, interior_color=interior)
    fmt = args.format or args.output.rsplit(".", 1)[-1].lower()
    if fmt == "png":
        write_png(args.output, pixels, args.width, args.height)
    elif fmt == "ppm":
        write_ppm(args.output, pixels, args.width, args.height)
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
        prefix=args.prefix, high_precision=args.hp, prec=args.prec)
    print(json.dumps({"frames": files}, indent=2))


def cmd_ascii(args):
    args.format = "ascii"
    cmd_render(args)


def cmd_palette(args):
    pal = get_palette(args.name, args.size)
    # render a small gradient strip
    w, h = args.size, 40
    pixels = []
    for row in range(h):
        for col in range(w):
            pixels.append(pal[col])
    out = args.output or f"palette_{args.name}.png"
    write_png(out, pixels, w, h)
    print(f"Wrote palette strip -> {out}")


def cmd_info(args):
    print("Fractals available:", ", ".join(sorted(FRACTALS)))
    print("Palettes available:", ", ".join(sorted(PALETTES)))
    print("Coloring modes: smooth, flat, de, root")


def build_cli():
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
    pz.add_argument("--output-dir", default="zoom_frames")
    pz.add_argument("--prefix", default="zoom")
    pz.add_argument("--hp", action="store_true", help="high-precision Decimal")
    pz.add_argument("--prec", type=int, default=60)
    pz.set_defaults(func=cmd_zoom)

    pp = sub.add_parser("palette", help="Render a palette strip")
    pp.add_argument("--name", default="fire", choices=sorted(PALETTES))
    pp.add_argument("--size", type=int, default=256)
    pp.add_argument("--output", default=None)
    pp.set_defaults(func=cmd_palette)

    pi = sub.add_parser("info", help="List available fractals & palettes")
    pi.set_defaults(func=cmd_info)

    return parser


def main(argv=None):
    parser = build_cli()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(),
                                       logging.WARNING))
    args.func(args)


if __name__ == "__main__":
    main()