"""
Andrew's monotone-chain convex hull algorithm.

Runs in O(n log n) and returns the hull vertices in counter-clockwise
order, with no collinear hull-edge points (uses strict orientation).
"""

from __future__ import annotations

from typing import List

from .geometry import Point, orient2d


def convex_hull(points: List[Point]) -> List[Point]:
    """Return the convex hull of *points* as a list of vertices (CCW).

    Collinear interior points are excluded.  Fewer than 3 unique points
    returns them directly.
    """
    # Deduplicate while preserving sorted order
    unique: List[Point] = []
    seen = set()
    for p in sorted(points, key=lambda q: (q.x, q.y)):
        key = (p.x, p.y)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    if len(unique) <= 2:
        return unique

    def build_half(pts: List[Point]) -> List[Point]:
        half: List[Point] = []
        for p in pts:
            while (
                len(half) >= 2
                and orient2d(half[-2], half[-1], p) <= 0
            ):
                half.pop()
            half.append(p)
        return half

    lower = build_half(unique)
    upper = build_half(list(reversed(unique)))
    # Concatenate, dropping the last point of each (it's the first of the other)
    hull = lower[:-1] + upper[:-1]
    return hull