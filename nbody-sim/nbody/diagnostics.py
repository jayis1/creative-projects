"""Diagnostics beyond energy/momentum: angular momentum, COM velocity,
virial ratio, and adaptive timestep estimation.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .body import Body


def total_angular_momentum(bodies: List[Body], about: Tuple[float, float] = (0.0, 0.0)) -> float:
    """Sum of ``m_i * (r_i × v_i)`` about the given point (z-component)."""
    cx, cy = about
    L = 0.0
    for b in bodies:
        rx = b.x - cx
        ry = b.y - cy
        L += b.m * (rx * b.vy - ry * b.vx)
    return L


def com_velocity(bodies: List[Body]) -> Tuple[float, float]:
    """Mass-weighted average velocity (center-of-mass velocity)."""
    M = sum(b.m for b in bodies)
    if M == 0.0:
        return (0.0, 0.0)
    return (
        sum(b.m * b.vx for b in bodies) / M,
        sum(b.m * b.vy for b in bodies) / M,
    )


def virial_ratio(bodies: List[Body], G: float = 1.0, softening: float = 0.0) -> float:
    """2T / |U| — equals 1 for a virialized self-gravitating system."""
    T = sum(0.5 * b.m * (b.vx * b.vx + b.vy * b.vy) for b in bodies)
    soft_sq = softening * softening
    U = 0.0
    n = len(bodies)
    for i in range(n):
        for j in range(i + 1, n):
            dx = bodies[j].x - bodies[i].x
            dy = bodies[j].y - bodies[i].y
            r = math.sqrt(dx * dx + dy * dy + soft_sq)
            U -= G * bodies[i].m * bodies[j].m / r
    return (2.0 * T) / max(abs(U), 1e-12)


def min_separation(bodies: List[Body]) -> float:
    """Smallest pairwise distance — used for adaptive timestep floors."""
    n = len(bodies)
    best = float("inf")
    for i in range(n):
        for j in range(i + 1, n):
            dx = bodies[j].x - bodies[i].x
            dy = bodies[j].y - bodies[i].y
            d = math.hypot(dx, dy)
            if d < best:
                best = d
    return best if best != float("inf") else 0.0


def max_acceleration(bodies: List[Body], G: float = 1.0, softening: float = 0.0) -> float:
    """Largest acceleration magnitude over all bodies (brute force)."""
    n = len(bodies)
    soft_sq = softening * softening
    best = 0.0
    for i in range(n):
        ax = ay = 0.0
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
        a = math.hypot(ax, ay)
        if a > best:
            best = a
    return best


def adaptive_dt(bodies: List[Body], G: float = 1.0, softening: float = 0.0,
                eta: float = 0.02, dt_min: float = 1e-6, dt_max: float = 0.1) -> float:
    """Estimate a stable timestep from the maximum acceleration.

    Uses ``dt = eta * sqrt(softening / a_max)`` (a common gravity-code heuristic)
    clamped to ``[dt_min, dt_max]``.
    """
    a_max = max_acceleration(bodies, G=G, softening=softening)
    if a_max <= 0.0:
        return dt_max
    dt = eta * math.sqrt(max(softening, 1e-6) / a_max)
    return max(dt_min, min(dt_max, dt))


__all__ = [
    "total_angular_momentum",
    "com_velocity",
    "virial_ratio",
    "min_separation",
    "max_acceleration",
    "adaptive_dt",
]