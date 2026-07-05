"""Benchmark rendering throughput."""
from __future__ import annotations

import time

from .iterators import FRACTALS
from .render import render_fractal
from .viewport import Viewport


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