"""Coloring helpers and per-pixel color computation."""
from __future__ import annotations

import math
from typing import Optional, Tuple

from .palettes import _clamp_byte
from .traps import PointTrap


def _smooth_iter(iter_count: int, z2: float, bailout: float,
                 log_power: float) -> float:
    """Compute the smooth (continuous) iteration count.

    ``nu = iter_count + 1 - log(log(|z|)) / log(power)``
    """
    if iter_count <= 0:
        return 0.0
    log_zn = 0.5 * math.log(z2) if z2 > 0 else 0.0
    nu = iter_count + 1 - math.log(max(1e-12, log_zn)) / log_power
    return max(0.0, nu)


def _true_distance(z2: float, dz2: float, log_power: float) -> float:
    """True Mandelbrot distance estimator: ``d = |z|·ln|z| / |z'|``."""
    if z2 <= 0 or dz2 <= 0:
        return 0.0
    log_zn = 0.5 * math.log(z2)
    if log_zn <= 0:
        return 0.0
    return (math.sqrt(z2) * log_zn) / (math.sqrt(dz2) * log_power)


def _compute_pixel(c, kind, fn, kw, max_iter, coloring, palette,
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
            z2 = extra if not isinstance(extra, tuple) else extra[0]
            nu = _smooth_iter(it, z2, bailout, log_power)
            de = math.exp(-nu * 0.1) if nu > 0 else 0.0
        idx = max(0, min(palette_size - 1, int(de * (palette_size - 1) * 50)))
        return palette[idx]

    if coloring == "trap":
        if trap is None:
            trap = PointTrap()
        # Re-run the iteration tracking the minimum distance to the trap.
        # Use the *actual* iterator for this fractal kind so the tracked orbit
        # matches the real orbit.
        z = c if kind == "julia" else 0
        z_prev = 0
        min_d = float("inf")
        _power = kw.get("power", 2.0)
        _julia_c = kw.get("julia_c", -0.7 + 0.27015j)
        _phoenix_c = kw.get("phoenix_c", -0.5)
        _variant = kw.get("variant", 1)
        for _ in range(it):
            d = trap.distance(z)
            if d < min_d:
                min_d = d
            if kind == "julia":
                z = (z * z + _julia_c if _power == 2
                     else z ** int(_power) + _julia_c if _power == int(_power)
                     else complex(z) ** _power + _julia_c)
            elif kind == "burning_ship":
                zr, zi = abs(z.real), abs(z.imag)
                zz = complex(zr, zi)
                z = (zz * zz + c if _power == 2 else zz ** int(_power) + c)
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
                z = (z * z + c if _power == 2
                     else z ** int(_power) + c if _power == int(_power)
                     else complex(z) ** _power + c)
        scaled = math.sqrt(min_d) if min_d < float("inf") else 0.0
        idx = max(0, min(palette_size - 1,
                         int(scaled * (palette_size - 1) * 5)))
        return palette[idx]

    return palette[it % palette_size]