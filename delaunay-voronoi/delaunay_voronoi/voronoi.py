"""
Voronoi diagram construction via the dual of a Delaunay triangulation.

Each Voronoi vertex is the circumcenter of a Delaunay triangle.  Each
Voronoi edge connects the circumcenters of two adjacent Delaunay triangles
(those sharing a Delaunay edge).  Boundary edges, which have only one
neighbouring triangle, are extended to the clipping boundary.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .delaunay import DelaunayTriangulation
from .geometry import Edge, Point, Triangle, bounding_box, circumcenter


class VoronoiCell:
    """A Voronoi cell: a site plus the polygon of points closest to it."""

    def __init__(self, site: Point, vertices: List[Point]):
        self.site = site
        self.vertices = vertices

    def area(self) -> float:
        """Polygon area via the shoelace formula (assumes simple polygon)."""
        v = self.vertices
        n = len(v)
        if n < 3:
            return 0.0
        s = 0.0
        for i in range(n):
            j = (i + 1) % n
            s += v[i].x * v[j].y - v[j].x * v[i].y
        return abs(s) / 2.0

    def centroid(self) -> Point:
        """Centroid of the polygon (area-weighted)."""
        v = self.vertices
        n = len(v)
        if n == 0:
            return self.site
        if n < 3:
            return Point(sum(p.x for p in v) / n, sum(p.y for p in v) / n)
        cx = 0.0
        cy = 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            cross = v[i].x * v[j].y - v[j].x * v[i].y
            cx += (v[i].x + v[j].x) * cross
            cy += (v[i].y + v[j].y) * cross
            area += cross
        area *= 0.5
        if abs(area) < 1e-18:
            return Point(sum(p.x for p in v) / n, sum(p.y for p in v) / n)
        return Point(cx / (6.0 * area), cy / (6.0 * area))


class VoronoiDiagram:
    """Voronoi diagram derived from a Delaunay triangulation."""

    def __init__(
        self,
        vertices: List[Point],
        edges: List[Edge],
        cells: Dict[Point, VoronoiCell],
        sites: List[Point],
    ):
        self.vertices = vertices
        self.edges = edges
        self.cells = cells
        self.sites = sites

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def from_delaunay(
        cls,
        dt: DelaunayTriangulation,
        clip_box: Optional[Tuple[Point, Point]] = None,
    ) -> "VoronoiDiagram":
        """Build a Voronoi diagram from a Delaunay triangulation.

        If *clip_box* is given as (min, max) the infinite boundary edges
        are clipped to that rectangle; otherwise they are omitted.
        """
        triangles = dt.triangles
        sites = dt.points

        # Circumcenter of each triangle → Voronoi vertex
        circumcenters: Dict[int, Point] = {}
        for i, t in enumerate(triangles):
            try:
                circumcenters[i] = circumcenter(t.a, t.b, t.c)
            except ValueError:
                circumcenters[i] = t.centroid()

        # For each Delaunay edge, find the 1 or 2 adjacent triangles.
        edge_to_tris: Dict[Edge, List[int]] = {}
        for i, t in enumerate(triangles):
            for e in t.edges():
                edge_to_tris.setdefault(e, []).append(i)

        voronoi_edges: List[Edge] = []
        for e, tri_ids in edge_to_tris.items():
            if len(tri_ids) == 2:
                # Interior edge: connect the two circumcenters
                c1 = circumcenters[tri_ids[0]]
                c2 = circumcenters[tri_ids[1]]
                voronoi_edges.append(Edge(c1, c2))
            elif len(tri_ids) == 1:
                # Boundary edge: a ray from the circumcenter outward,
                # perpendicular to the Delaunay edge.
                if clip_box is not None:
                    ray_edge = _clip_ray(
                        circumcenters[tri_ids[0]], e, clip_box
                    )
                    if ray_edge is not None:
                        voronoi_edges.append(ray_edge)
                # else: omit infinite edges

        # Build cells: for each site, collect ordered circumcenters of
        # triangles touching that site.
        cells: Dict[Point, VoronoiCell] = {}
        for site in sites:
            touching: List[Tuple[int, Triangle]] = []
            for i, t in enumerate(triangles):
                if t.shares_vertex(site):
                    touching.append((i, t))
            if len(touching) < 3:
                cells[site] = VoronoiCell(site, [])
                continue
            # Order triangles around the site by angle of circumcenter.
            centers = [circumcenters[i] for i, _ in touching]
            centers.sort(
                key=lambda c: _angle(site, c)
            )
            cells[site] = VoronoiCell(site, centers)

        return cls(
            vertices=list(circumcenters.values()),
            edges=voronoi_edges,
            cells=cells,
            sites=sites,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _angle(origin: Point, p: Point) -> float:
    """Polar angle of *p* around *origin*, in [0, 2π)."""
    import math

    a = math.atan2(p.y - origin.y, p.x - origin.x)
    if a < 0:
        a += 2.0 * math.pi
    return a


def _clip_ray(
    center: Point, delaunay_edge: Edge, clip_box: Tuple[Point, Point]
) -> Optional[Edge]:
    """Clip a Voronoi ray to the bounding box.

    The ray starts at *center* and goes perpendicular to *delaunay_edge*,
    away from the edge midpoint (outward from the triangulation).
    """
    import math

    mid = delaunay_edge.midpoint()
    dx = mid.x - center.x
    dy = mid.y - center.y
    # The ray direction is from center away from the interior, i.e. along
    # (mid - center) normalised. But the Voronoi ray is actually perpendicular
    # to the Delaunay edge, pointing outward.  The direction from circumcenter
    # to edge-midpoint is along the Delaunay edge's perpendicular, so the
    # outward ray direction is the same as (mid - center).
    length = math.hypot(dx, dy)
    if length < 1e-18:
        return None
    nx = dx / length
    ny = dy / length

    min_p, max_p = clip_box
    # Find intersection with the box boundary (extend ray far)
    far = 1e6
    target = Point(center.x + nx * far, center.y + ny * far)

    # Clip the line segment center→target to the box via Liang-Barsky
    clipped = _liang_barsky(center, target, min_p, max_p)
    if clipped is None:
        return None
    return Edge(center, clipped)


def _liang_barsky(
    p1: Point, p2: Point, min_p: Point, max_p: Point
) -> Optional[Point]:
    """Liang-Barsky line clipping; returns the far intersection with the box."""
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    dx = x2 - x1
    dy = y2 - y1

    t_enter = 0.0
    t_exit = 1.0

    for p, q in [
        (-dx, x1 - min_p.x),
        (dx, max_p.x - x1),
        (-dy, y1 - min_p.y),
        (dy, max_p.y - y1),
    ]:
        if abs(p) < 1e-18:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                if t > t_exit:
                    return None
                if t > t_enter:
                    t_enter = t
            else:
                if t < t_enter:
                    return None
                if t < t_exit:
                    t_exit = t

    return Point(x1 + t_exit * dx, y1 + t_exit * dy)