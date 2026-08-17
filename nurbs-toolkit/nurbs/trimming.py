"""Curve and surface trimming operations.

Provides:
- Curve–curve intersection (B-spline/NURBS)
- Trimming curves for surfaces
- Boolean trimming of surface patches
"""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple, Optional

from .bspline import BSplineCurve
from .nurbs_curve import NURBSCurve

Curve = "BSplineCurve | NURBSCurve"


def _curve_bbox(curve: Curve) -> Tuple[List[float], List[float]]:
    """Compute axis-aligned bounding box of a curve's control points."""
    cps = curve.control_points
    dim = len(cps[0])
    mn = [min(cp[d] for cp in cps) for d in range(dim)]
    mx = [max(cp[d] for cp in cps) for d in range(dim)]
    return mn, mx


def _bboxes_overlap(
    mn1: List[float], mx1: List[float],
    mn2: List[float], mx2: List[float],
    tol: float = 1e-10,
) -> bool:
    """Check if two AABBs overlap."""
    for d in range(len(mn1)):
        if mx1[d] < mn2[d] - tol or mx2[d] < mn1[d] - tol:
            return False
    return True


def intersect_curves(
    curve1,
    curve2,
    samples: int = 200,
    tol: float = 1e-8,
    max_iter: int = 50,
) -> List[Tuple[float, float, List[float]]]:
    """Find intersection points between two curves.

    Uses a recursive subdivision approach based on bounding-box
    overlap, followed by Newton refinement on the distance function
    ``f(u, v) = |C1(u) - C2(v)|^2``.

    Returns
    -------
    list of (u, v, point)
        Intersection points as (parameter on curve1, parameter on curve2,
        3-D intersection point).
    """
    dim = len(curve1.control_points[0])
    if len(curve2.control_points[0]) != dim:
        raise ValueError("Curves must have the same dimension")

    results: List[Tuple[float, float, List[float]]] = []
    u0_1, u1_1 = curve1.parameter_range
    u0_2, u1_2 = curve2.parameter_range

    # Coarse grid search.
    grid1 = [
        (u0_1 + (i / (samples - 1)) * (u1_1 - u0_1), curve1.evaluate(u0_1 + (i / (samples - 1)) * (u1_1 - u0_1)))
        for i in range(samples)
    ]
    grid2 = [
        (u0_2 + (j / (samples - 1)) * (u1_2 - u0_2), curve2.evaluate(u0_2 + (j / (samples - 1)) * (u1_2 - u0_2)))
        for j in range(samples)
    ]

    # Find candidate pairs where distance is small.
    candidates: List[Tuple[float, float]] = []
    step1 = (u1_1 - u0_1) / (samples - 1)
    step2 = (u1_2 - u0_2) / (samples - 1)
    for i in range(samples):
        p1 = grid1[i][1]
        for j in range(samples):
            p2 = grid2[j][1]
            dist2 = sum((p1[d] - p2[d]) ** 2 for d in range(dim))
            if dist2 < (max(step1, step2) * 2) ** 2:
                candidates.append((grid1[i][0], grid2[j][0]))

    # Refine each candidate with 2-D Newton on f(u,v) = C1(u) - C2(v) = 0.
    seen: List[Tuple[float, float, List[float]]] = []
    for u_guess, v_guess in candidates:
        u, v = u_guess, v_guess
        converged = False
        for _ in range(max_iter):
            p1 = curve1.evaluate(u)
            p2 = curve2.evaluate(v)
            diff = [p1[d] - p2[d] for d in range(dim)]
            err = sum(d * d for d in diff)
            if err < tol * tol:
                converged = True
                break
            d1_u = curve1.derivative(u, 1)
            d2_v = curve2.derivative(v, 1)
            # Jacobian of diff: [d1_u  -d2_v] (dim x 2)
            # Solve J [du, dv]^T = -diff using normal equations (2x2).
            J00 = sum(d1_u[d] * d1_u[d] for d in range(dim))
            J01 = sum(-d1_u[d] * d2_v[d] for d in range(dim))
            J11 = sum(d2_v[d] * d2_v[d] for d in range(dim))
            det = J00 * J11 - J01 * J01
            if abs(det) < 1e-20:
                break
            b0 = -sum(diff[d] * d1_u[d] for d in range(dim))
            b1 = sum(diff[d] * d2_v[d] for d in range(dim))
            du = (J11 * b0 - J01 * b1) / det
            dv = (-J01 * b0 + J00 * b1) / det
            u = max(u0_1, min(u1_1, u + du))
            v = max(u0_2, min(u1_2, v + dv))
        if not converged:
            continue
        p = curve1.evaluate(u)
        # Check if we already found this intersection.
        is_new = True
        for _, _, ep in seen:
            if all(abs(p[d] - ep[d]) < 1e-6 for d in range(dim)):
                is_new = False
                break
        if is_new:
            seen.append((u, v, p))

    return seen


class TrimmingLoop:
    """A closed loop of 2-D trimming curves on a surface's (u, v) domain.

    Trimming curves are 2-D B-spline curves in parameter space.
    A loop defines a boundary: the interior of the loop is kept,
    the exterior is trimmed away.
    """

    def __init__(self, curves: Sequence):
        """Create a trimming loop from a sequence of 2-D curves.

        Each curve must be 2-D.  The end of each curve should match
        the start of the next (G0 continuity).
        """
        for c in curves:
            if len(c.control_points[0]) != 2:
                raise ValueError("Trimming curves must be 2-D")
        self.curves = list(curves)

    def is_inside(self, u: float, v: float) -> bool:
        """Check if (u, v) is inside the trimming loop (winding number).

        Uses a ray-casting algorithm: count how many times a
        horizontal ray from (u, v) to (+∞, v) crosses the loop.
        Odd = inside, even = outside.
        """
        crossings = 0
        for curve in self.curves:
            u0, u1 = curve.parameter_range
            # Sample the curve.
            pts = [curve.evaluate(u0 + (i / 100) * (u1 - u0)) for i in range(101)]
            for i in range(len(pts) - 1):
                x0, y0 = pts[i][0], pts[i][1]
                x1, y1 = pts[i + 1][0], pts[i + 1][1]
                # Check if the segment crosses the horizontal ray.
                if (y0 <= v < y1) or (y1 <= v < y0):
                    # Compute x at y = v.
                    t = (v - y0) / (y1 - y0) if y1 != y0 else 0.0
                    x_at_v = x0 + t * (x1 - x0)
                    if x_at_v > u:
                        crossings += 1
        return crossings % 2 == 1


def trim_surface_points(
    surface,
    u: float,
    v: float,
    loops: Sequence[TrimmingLoop],
) -> bool:
    """Check if (u, v) on a surface is inside all trimming loops.

    Returns True if the point should be kept (inside all loops),
    False if it should be trimmed away.
    """
    for loop in loops:
        if not loop.is_inside(u, v):
            return False
    return True