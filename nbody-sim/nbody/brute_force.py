"""Brute-force O(N²) N-body force evaluator — the ground truth that Barnes–Hut
approximates. Used for accuracy benchmarks and as a fallback when theta=0.

Also provides :func:`benchmark` to compare Barnes–Hut against brute force for
both speed and force error.
"""

from __future__ import annotations

import math
import time
from typing import List, Tuple

from .body import Body
from .barnes_hut import BHTree


def brute_force_accelerations(
    bodies: List[Body], G: float = 1.0, softening: float = 0.0
) -> List[Tuple[float, float]]:
    """Exact pairwise accelerations — O(N²)."""
    n = len(bodies)
    soft_sq = softening * softening
    accels = [(0.0, 0.0)] * n
    for i in range(n):
        ax = 0.0
        ay = 0.0
        for j in range(n):
            if i == j:
                continue
            dx = bodies[j].x - bodies[i].x
            dy = bodies[j].y - bodies[i].y
            r = math.sqrt(dx * dx + dy * dy + soft_sq)
            if r < 1e-12:
                r = 1e-12
            inv_r3 = 1.0 / (r * r * r)
            f = G * bodies[j].m * inv_r3
            ax += f * dx
            ay += f * dy
        accels[i] = (ax, ay)
    return accels


def barnes_hut_accelerations(
    bodies: List[Body], theta: float = 0.5, G: float = 1.0, softening: float = 0.0
) -> List[Tuple[float, float]]:
    """Barnes–Hut accelerations for the same configuration."""
    tree = BHTree(theta=theta, softening=softening, G=G)
    tree.build([(b.x, b.y, b.m) for b in bodies])
    return [tree.force_on((b.x, b.y, b.m)) for b in bodies]


def force_error(
    bh_accels: List[Tuple[float, float]],
    exact_accels: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """Return (max relative error, mean relative error) of BH vs exact."""
    max_rel = 0.0
    sum_rel = 0.0
    n = 0
    for (ax_bh, ay_bh), (ax_ex, ay_ex) in zip(bh_accels, exact_accels):
        ex_mag = math.hypot(ax_ex, ay_ex)
        if ex_mag < 1e-12:
            continue
        diff_mag = math.hypot(ax_bh - ax_ex, ay_bh - ay_ex)
        rel = diff_mag / ex_mag
        max_rel = max(max_rel, rel)
        sum_rel += rel
        n += 1
    mean_rel = sum_rel / max(n, 1)
    return (max_rel, mean_rel)


def benchmark(
    bodies: List[Body],
    theta: float = 0.5,
    G: float = 1.0,
    softening: float = 0.0,
) -> dict:
    """Compare Barnes–Hut vs brute-force for accuracy and speed.

    Returns a dict with keys: ``n``, ``theta``, ``bh_time``, ``bf_time``,
    ``max_rel_err``, ``mean_rel_err``, ``speedup``.
    """
    # Brute force.
    t0 = time.perf_counter()
    exact = brute_force_accelerations(bodies, G=G, softening=softening)
    t_bf = time.perf_counter() - t0
    # Barnes–Hut.
    t0 = time.perf_counter()
    bh = barnes_hut_accelerations(bodies, theta=theta, G=G, softening=softening)
    t_bh = time.perf_counter() - t0
    max_rel, mean_rel = force_error(bh, exact)
    return {
        "n": len(bodies),
        "theta": theta,
        "bh_time": t_bh,
        "bf_time": t_bf,
        "max_rel_err": max_rel,
        "mean_rel_err": mean_rel,
        "speedup": t_bf / t_bh if t_bh > 0 else float("inf"),
    }


__all__ = [
    "brute_force_accelerations",
    "barnes_hut_accelerations",
    "force_error",
    "benchmark",
]