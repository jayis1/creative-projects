"""Point projection and arc-length utilities."""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple

from .bspline import BSplineCurve


def project_point(
    curve: BSplineCurve,
    point: Sequence[float],
    samples: int = 100,
    tol: float = 1e-8,
    max_iter: int = 50,
) -> Tuple[float, List[float]]:
    """Find the parameter *u* on *curve* closest to *point*.

    Uses coarse sampling followed by Newton refinement.

    Returns
    -------
    u : float
        Best parameter.
    closest_point : list[float]
        Curve point at *u*.
    """
    u0, u1 = curve.parameter_range
    # Coarse search.
    best_u = u0
    best_dist2 = float("inf")
    for i in range(samples):
        t = i / (samples - 1) if samples > 1 else 0.0
        u = u0 + t * (u1 - u0)
        cp = curve.evaluate(u)
        d2 = sum((cp[k] - point[k]) ** 2 for k in range(len(point)))
        if d2 < best_dist2:
            best_dist2 = d2
            best_u = u

    # Newton refinement: minimize f(u) = |C(u) - P|^2.
    u = best_u
    for _ in range(max_iter):
        C = curve.evaluate(u)
        d1 = curve.derivative(u, 1)
        d2 = curve.derivative(u, 2)
        diff = [C[k] - point[k] for k in range(len(point))]
        f = sum(x * x for x in diff)
        # f'(u) = 2 * diff . d1
        fp = 2.0 * sum(diff[k] * d1[k] for k in range(len(point)))
        # f''(u) = 2 * (d1 . d1 + diff . d2)
        fpp = 2.0 * (
            sum(d1[k] * d1[k] for k in range(len(point)))
            + sum(diff[k] * d2[k] for k in range(len(point)))
        )
        if abs(fpp) < 1e-14:
            break
        delta = fp / fpp
        new_u = u - delta
        # Clamp to parameter range.
        new_u = max(u0, min(u1, new_u))
        if abs(new_u - u) < tol:
            u = new_u
            break
        u = new_u

    return u, curve.evaluate(u)


def arc_length(
    curve: BSplineCurve,
    u_start: float | None = None,
    u_end: float | None = None,
    samples: int = 1000,
) -> float:
    """Approximate the arc length of *curve* between two parameters.

    Uses composite Simpson's rule on the derivative magnitude.
    """
    u0, u1 = curve.parameter_range
    if u_start is None:
        u_start = u0
    if u_end is None:
        u_end = u1
    if u_start > u_end:
        u_start, u_end = u_end, u_start

    def speed(u: float) -> float:
        d = curve.derivative(u, 1)
        return math.sqrt(sum(x * x for x in d))

    # Composite Simpson's rule.
    if samples % 2 == 1:
        samples += 1
    h = (u_end - u_start) / samples
    total = speed(u_start) + speed(u_end)
    for i in range(1, samples):
        u = u_start + i * h
        w = 4.0 if i % 2 == 1 else 2.0
        total += w * speed(u)
    return total * h / 3.0


def reparameterize_arc_length(
    curve: BSplineCurve,
    num_samples: int = 100,
) -> List[Tuple[float, float]]:
    """Build an arc-length parameterization table.

    Returns a list of ``(u, s)`` pairs where *s* is cumulative arc
    length from the start of the curve.
    """
    u0, u1 = curve.parameter_range
    table: List[Tuple[float, float]] = []
    s = 0.0
    prev = curve.evaluate(u0)
    for i in range(num_samples):
        t = i / (num_samples - 1) if num_samples > 1 else 0.0
        u = u0 + t * (u1 - u0)
        if i > 0:
            pt = curve.evaluate(u)
            s += math.sqrt(sum((pt[k] - prev[k]) ** 2 for k in range(len(prev))))
            prev = pt
        else:
            prev = curve.evaluate(u0)
        table.append((u, s))
    return table