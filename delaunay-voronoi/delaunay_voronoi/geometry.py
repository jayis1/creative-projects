"""
Core geometry primitives and robust predicates.

Uses Python's arbitrary-precision integers and ``fractions.Fraction`` for the
incircle test so that cocircular degeneracies are classified exactly rather
than by fragile floating-point comparisons.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Iterator, Tuple


@dataclass(frozen=True)
class Point:
    """A 2-D point with float coordinates."""

    x: float
    y: float

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def scale(self, s: float) -> "Point":
        return Point(self.x * s, self.y * s)

    def distance_to(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Point({self.x:.6g}, {self.y:.6g})"


@dataclass(frozen=True)
class Edge:
    """An undirected edge between two points."""

    a: Point
    b: Point

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.a == other.a and self.b == other.b) or (
            self.a == other.b and self.b == other.a
        )

    def __hash__(self) -> int:
        lo, hi = sorted([(self.a.x, self.a.y), (self.b.x, self.b.y)])
        return hash((lo, hi))

    def midpoint(self) -> Point:
        return Point((self.a.x + self.b.x) / 2.0, (self.a.y + self.b.y) / 2.0)


@dataclass(frozen=True)
class Triangle:
    """A triangle referencing three ``Point`` objects."""

    a: Point
    b: Point
    c: Point

    def vertices(self) -> Tuple[Point, Point, Point]:
        return (self.a, self.b, self.c)

    def edges(self) -> Tuple[Edge, Edge, Edge]:
        return (Edge(self.a, self.b), Edge(self.b, self.c), Edge(self.c, self.a))

    def contains_point_in_circumcircle(self, p: Point) -> bool:
        """True when *p* lies strictly inside this triangle's circumcircle."""
        return incircle(self.a, self.b, self.c, p) > 0

    def shares_vertex(self, p: Point) -> bool:
        return p in (self.a, self.b, self.c)

    def area(self) -> float:
        """Signed area (positive if CCW)."""
        return 0.5 * abs(orient2d(self.a, self.b, self.c))

    def centroid(self) -> Point:
        return Point(
            (self.a.x + self.b.x + self.c.x) / 3.0,
            (self.a.y + self.b.y + self.c.y) / 3.0,
        )

    def circumcircle(self) -> "Circle":
        """Return the circumscribed circle of this triangle."""
        ax, ay = self.a.x, self.a.y
        bx, by = self.b.x, self.b.y
        cx, cy = self.c.x, self.c.y
        d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0.0:
            # Degenerate (collinear) - return a huge circle
            return Circle(Point(0.0, 0.0), float("inf"))
        ux = (
            (ax * ax + ay * ay) * (by - cy)
            + (bx * bx + by * by) * (cy - ay)
            + (cx * cx + cy * cy) * (ay - by)
        ) / d
        uy = (
            (ax * ax + ay * ay) * (cx - bx)
            + (bx * bx + by * by) * (ax - cx)
            + (cx * cx + cy * cy) * (bx - ax)
        ) / d
        center = Point(ux, uy)
        radius = math.hypot(ax - ux, ay - uy)
        return Circle(center, radius)


@dataclass(frozen=True)
class Circle:
    center: Point
    radius: float


# ---------------------------------------------------------------------------
# Robust geometric predicates
# ---------------------------------------------------------------------------

def orient2d(a: Point, b: Point, c: Point) -> float:
    """Orientation test.

    Returns a positive value if ``a,b,c`` are in counter-clockwise order,
    negative if clockwise, and zero if collinear.

    The computation uses ``Fraction`` when the float result is suspiciously
    close to zero (within an epsilon), guaranteeing an exact answer in
    degenerate / near-degenerate cases.
    """
    # Fast float path
    det = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    # Scale relative to the coordinate magnitude for the tolerance.
    extent = abs(b.x - a.x) + abs(b.y - a.y) + abs(c.x - a.x) + abs(c.y - a.y)
    tol = 1e-12 * max(1.0, extent)
    if abs(det) > tol:
        return det
    # Exact fallback using Fraction on the original float values.
    ax, ay = Fraction(a.x), Fraction(a.y)
    bx, by = Fraction(b.x), Fraction(b.y)
    cx, cy = Fraction(c.x), Fraction(c.y)
    exact = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    return float(exact)


def incircle(a: Point, b: Point, c: Point, d: Point) -> float:
    """In-circle predicate.

    Returns positive if *d* lies inside the circumcircle of triangle ``a,b,c``
    (assumed CCW), negative if outside, zero if exactly on it.

    Uses ``Fraction`` arithmetic for exactness; the determinant scales with the
    coordinate magnitudes so a float-only test is unreliable near degeneracy.
    """
    ax, ay = Fraction(a.x), Fraction(a.y)
    bx, by = Fraction(b.x), Fraction(b.y)
    cx, cy = Fraction(c.x), Fraction(c.y)
    dx, dy = Fraction(d.x), Fraction(d.y)

    adx = ax - dx
    ady = ay - dy
    bdx = bx - dx
    bdy = by - dy
    cdx = cx - dx
    cdy = cy - dy

    det = (
        adx * (bdy * (cdx * cdx + cdy * cdy) - cdy * (bdx * bdx + bdy * bdy))
        - ady * (bdx * (cdx * cdx + cdy * cdy) - cdx * (bdx * bdx + bdy * bdy))
        + (adx * adx + ady * ady)
        * (bdx * cdy - bdy * cdx)
    )
    return float(det)


def circumcenter(a: Point, b: Point, c: Point) -> Point:
    """Compute the circumcenter of three points."""
    ax, ay = a.x, a.y
    bx, by = b.x, b.y
    cx, cy = c.x, c.y
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-18:
        raise ValueError("Collinear points have no finite circumcenter")
    ux = (
        (ax * ax + ay * ay) * (by - cy)
        + (bx * bx + by * by) * (cy - ay)
        + (cx * cx + cy * cy) * (ay - by)
    ) / d
    uy = (
        (ax * ax + ay * ay) * (cx - bx)
        + (bx * bx + by * by) * (ax - cx)
        + (cx * cx + cy * cy) * (bx - ax)
    ) / d
    return Point(ux, uy)


def segment_intersection(
    p1: Point, p2: Point, p3: Point, p4: Point
) -> Point | None:
    """Return the intersection point of segments p1p2 and p3p4, or None."""
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    x3, y3 = p3.x, p3.y
    x4, y4 = p4.x, p4.y

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-18:
        return None  # parallel or collinear

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return Point(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def bounding_box(points: Iterable[Point]) -> Tuple[Point, Point]:
    """Return (min-corner, max-corner) of an axis-aligned bounding box."""
    pts = list(points)
    if not pts:
        raise ValueError("Cannot compute bounding box of empty point set")
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (Point(min(xs), min(ys)), Point(max(xs), max(ys)))