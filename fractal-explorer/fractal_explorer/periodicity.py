"""Periodicity (Brent cycle) detection for interior points.

Many interior points of the Mandelbrot set never escape, so iteration runs
all the way to ``max_iter``. Brent's cycle detection finds a repeating
orbit early, so we can bail out *before* ``max_iter`` and save a large
amount of computation on the interior.
"""
from __future__ import annotations

from typing import Tuple


def iterate_with_periodicity(c: complex, max_iter: int, bailout: float,
                             power: float = 2.0) -> Tuple[int, float]:
    """Mandelbrot iteration with Brent cycle detection.

    Returns ``(iter_count, |z|^2)`` just like :func:`_mandelbrot_iter`,
    but uses Brent's algorithm to detect periodic orbits and return
    ``max_iter`` early when a cycle is found.
    """
    z = 0
    z2 = 0.0
    # Brent's cycle detection: track a "snapshot" point and a power-of-two
    # period bound. When z matches the snapshot, a cycle is confirmed.
    tortoise = 0  # snapshot of z at the last power-of-two step
    period = 1
    step_limit = 1

    for i in range(max_iter):
        # Advance z
        if power == 2:
            z = z * z + c
        elif power == int(power):
            z = z ** int(power) + c
        else:
            z = complex(z) ** power + c

        z2 = z.real * z.real + z.imag * z.imag
        if z2 > bailout:
            return i + 1, z2

        # Check for cycle: compare z to tortoise
        if z == tortoise:
            return max_iter, z2

        if i + 1 >= step_limit:
            tortoise = z
            step_limit = period * 2
            period = i + 1

    return max_iter, z2