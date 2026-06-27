"""
Bowyer-Watson incremental Delaunay triangulation.

The algorithm:

1. Start with a super-triangle large enough to contain all input points.
2. For each input point:
   a. Find all triangles whose circumcircle contains the point ("bad triangles").
   b. Compute the boundary of the bad-triangle region (edges that appear once).
   c. Remove the bad triangles.
   d. Create new triangles from each boundary edge to the new point.
3. Remove any triangle that still references a super-triangle vertex.

The implementation uses the robust ``incircle`` predicate from
``geometry`` so cocircular degeneracies are handled exactly.
"""

from __future__ import annotations

from typing import Dict, List, Set

from .geometry import Edge, Point, Triangle, bounding_box, orient2d


class DelaunayTriangulation:
    """Incremental Delaunay triangulation of a 2-D point set."""

    def __init__(self) -> None:
        self._triangles: List[Triangle] = []
        self._points: List[Point] = []
        self._super_vertices: Set[Point] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def from_points(cls, points: List[Point]) -> "DelaunayTriangulation":
        """Build a Delaunay triangulation from a list of points."""
        if len(points) < 3:
            raise ValueError("Need at least 3 points for a triangulation")
        dt = cls()
        dt._build(points)
        return dt

    @property
    def triangles(self) -> List[Triangle]:
        """All real triangles (super-triangle remnants removed)."""
        return list(self._triangles)

    @property
    def points(self) -> List[Point]:
        """Input points (no super-triangle vertices)."""
        return list(self._points)

    def edges(self) -> List[Edge]:
        """Unique edges across all triangles."""
        seen: Set[Edge] = set()
        for t in self._triangles:
            for e in t.edges():
                seen.add(e)
        return list(seen)

    def neighbors(self) -> Dict[Edge, List[Triangle]]:
        """Map each edge to the (1 or 2) triangles sharing it."""
        nbrs: Dict[Edge, List[Triangle]] = {}
        for t in self._triangles:
            for e in t.edges():
                nbrs.setdefault(e, []).append(t)
        return nbrs

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self, points: List[Point]) -> None:
        pts = list(points)
        self._points = list(pts)

        min_p, max_p = bounding_box(pts)
        dx = max_p.x - min_p.x or 1.0
        dy = max_p.y - min_p.y or 1.0
        midx = (min_p.x + max_p.x) / 2.0
        midy = (min_p.y + max_p.y) / 2.0
        # Large enough that no input point can be inside its circumcircle
        # in a way that breaks the algorithm. 20× the span is safe.
        span = 20.0 * max(dx, dy)
        sa = Point(midx - span, midy - span)
        sb = Point(midx + span, midy - span)
        sc = Point(midx, midy + span)
        self._super_vertices = {sa, sb, sc}

        super_tri = Triangle(sa, sb, sc)
        self._triangles = [super_tri]

        for p in pts:
            self._insert_point(p)

        self._triangles = [
            t for t in self._triangles if not self._has_super_vertex(t)
        ]

    def _insert_point(self, p: Point) -> None:
        bad: List[Triangle] = []
        for t in self._triangles:
            if t.contains_point_in_circumcircle(p):
                bad.append(t)

        # Boundary edges = edges that appear in exactly one bad triangle.
        edge_count: Dict[Edge, int] = {}
        for t in bad:
            for e in t.edges():
                edge_count[e] = edge_count.get(e, 0) + 1
        boundary = [e for e, c in edge_count.items() if c == 1]

        # Remove bad triangles
        bad_ids = {id(t) for t in bad}
        self._triangles = [t for t in self._triangles if id(t) not in bad_ids]

        # Create new triangles from boundary edges to p (ensuring CCW)
        for e in boundary:
            if orient2d(e.a, e.b, p) >= 0:
                tri = Triangle(e.a, e.b, p)
            else:
                tri = Triangle(e.a, p, e.b)
            self._triangles.append(tri)

    def _has_super_vertex(self, t: Triangle) -> bool:
        return any(v in self._super_vertices for v in t.vertices())