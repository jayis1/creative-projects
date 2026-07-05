"""Fractal iterator functions.

Each iterator returns ``(iter_count, extra)`` where ``extra`` depends on the
fractal:

* escape-time fractals → ``|z|^2`` at escape (for smooth/DE colouring)
* Newton               → ``root_index`` (or -1)
* derivative-aware     → a ``(z2, |dz|^2)`` tuple for true DE
"""
from __future__ import annotations

import cmath
import math
from typing import Callable, Tuple

from .periodicity import iterate_with_periodicity


# --------------------------------------------------------------------------- #
# Core iterators
# --------------------------------------------------------------------------- #

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
    """
    z = 0
    dz = 1
    z2 = 0
    dz2 = 1
    for i in range(max_iter):
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


def _mandelbrot_iter_periodic(c, max_iter, bailout, power=2.0):
    """Mandelbrot with periodicity detection for interior points.

    Uses the Brent cycle-detection algorithm so that interior points can be
    identified early (before ``max_iter``), speeding up deep renders of the
    interior.
    """
    return iterate_with_periodicity(c, max_iter, bailout, power=power)


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
        z = (z.real * z.real - z.imag * z.imag
              - 2j * z.real * z.imag + c)
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
    """Phoenix fractal: ``z_{n+1} = z_n^p + c + p_c·z_{n-1}``."""
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
    """
    z = c
    tol = 1e-6
    for i in range(max_iter):
        z2 = z * z
        if variant == 1:
            num = z2 + c
            den = 2 * z2 + c - 1
        else:
            num = z2 + c
            den = 2 * z2 + c - 1
        if den == 0:
            return i + 1, float("inf")
        z = (num / den) ** 2
        mz2 = z.real * z.real + z.imag * z.imag
        if mz2 < tol:
            return i + 1, mz2
        if mz2 > bailout:
            return i + 1, mz2
    return max_iter, 0


def _newton_iter(c, max_iter, bailout, power=3, tol=1e-6, roots=None):
    """Newton's method iteration on ``z^p - 1`` with given roots.

    Returns ``(iterations, root_index)``. ``root_index`` is -1 if it did
    not converge within ``max_iter``.
    """
    z = c
    if roots is None:
        roots = [cmath.rect(1.0, 2 * math.pi * k / power)
                 for k in range(int(power))]
    for i in range(max_iter):
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
    """Generic escape-time iteration ``z_{n+1} = fn(z_n, c)``."""
    z = 0
    for i in range(max_iter):
        z = fn(z, c)
        z2 = (z.real * z.real + z.imag * z.imag)
        if z2 > bailout:
            return i + 1, z2
    return max_iter, 0


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

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
    "mandelbrot_periodic": lambda c, **kw: _mandelbrot_iter_periodic(
        c, kw.get("max_iter", 256), kw.get("bailout", 1 << 16),
        kw.get("power", 2.0)),
}

DE_CAPABLE = {"mandelbrot", "mandelbrot_periodic"}


def get_fractal(kind: str):
    """Return the iterator callable for a named fractal kind."""
    if kind not in FRACTALS:
        raise ValueError(f"Unknown fractal {kind!r}; options: {list(FRACTALS)}")
    return FRACTALS[kind]