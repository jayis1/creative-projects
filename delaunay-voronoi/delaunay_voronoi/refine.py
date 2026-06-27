"""
Ruppert's Delaunay refinement algorithm.

Produces a **quality mesh** — a Delaunay triangulation where no triangle
has an angle smaller than a given bound (default ~30°).  It works by
incrementally inserting circumcenters of bad triangles, splitting
segments (constrained edges) as needed.

This is a simplified 2-D implementation suitable for PSLG-like input
defined by a set of points and optional boundary segments.
"""

from __future__ import annotations

import math
from typing import List, Optional, Set, Tuple

from .delaunay import DelaunayTriangulation
from .geometry import Point, Triangle, circumcenter, orient2d


def ruppert_refine(
    points: List[Point],
    min_angle_deg: float = 30.0,
    max_points: int = 10000,
    max_area: Optional[float] = None,
) -> List[Point]:
    """Refine a point set into a quality mesh via Ruppert's algorithm.

    Parameters
    ----------
    points : initial sites.
    min_angle_deg : target minimum triangle angle (≈20-33° is practical).
    max_points : safety bound on the number of inserted points.
    max_area : if given, triangles larger than this are also split.

    Returns the refined list of points (originals + circumcenter inserts).
    """
    if len(points) < 3:
        return list(points)

    min_angle_rad = math.radians(min_angle_deg)
    current = list(points)
    # _min_angle_sin_ratio returns sin(min_angle); compare directly.
    threshold = math.sin(min_angle_rad)

    iterations = 0
    last_worst = float("inf")
    stall_count = 0
    while iterations < max_points:
        iterations += 1
        dt = DelaunayTriangulation.from_points(current)
        bad: Optional[Triangle] = None
        worst_ratio = threshold
        for t in dt.triangles:
            ratio = _min_angle_sin_ratio(t)
            if max_area is not None and t.area() > max_area:
                ratio = min(ratio, 0.0)  # force splitting large triangles
            if ratio < worst_ratio:
                worst_ratio = ratio
                bad = t
        if bad is None:
            break
        # Detect stall: if not making meaningful progress, stop to avoid
        # infinite loops (Ruppert's without constrained segments can diverge).
        if worst_ratio >= last_worst - 1e-9:
            stall_count += 1
            if stall_count >= 5:
                break
        else:
            stall_count = 0
        last_worst = worst_ratio
        # Insert circumcenter of the worst triangle
        try:
            c = circumcenter(bad.a, bad.b, bad.c)
        except ValueError:
            break
        # Guard against inserting a point essentially identical to an
        # existing one (which would create a degenerate triangle).
        if any(c.distance_to(p) < 1e-9 for p in current):
            break
        current.append(c)

    return current


def _min_angle_sin_ratio(t: Triangle) -> float:
    """Return sin(min_angle) of triangle *t* (higher = better)."""
    a, b, c = t.vertices()
    # Side lengths
    lab = a.distance_to(b)
    lbc = b.distance_to(c)
    lca = c.distance_to(a)
    # Area
    area = t.area()
    if area < 1e-18:
        return 0.0
    # sin(angle) = 2*area / (side1 * side2) for the angle between side1, side2
    s_a = 2.0 * area / (lbc * lca)  # angle at a
    s_b = 2.0 * area / (lab * lca)  # angle at b
    s_c = 2.0 * area / (lab * lbc)  # angle at c
    return min(s_a, s_b, s_c)