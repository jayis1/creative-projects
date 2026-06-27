"""
Spatial query utilities built on top of a Delaunay triangulation.

Provides:

* **Nearest-neighbour** lookup via walking (no grid needed).
* **Point location** — which triangle contains a given query point.
* **k-nearest neighbours** by graph distance in the triangulation.

These are O(n) walking strategies; good enough for interactive use and
avoid the machinery of a dedicated spatial index.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .geometry import Edge, Point, Triangle, orient2d
from .delaunay import DelaunayTriangulation


def nearest_neighbor(
    dt: DelaunayTriangulation, query: Point, start: Optional[Point] = None
) -> Point:
    """Return the input site closest to *query*.

    Uses a straight-line walk: from *start* (or the first point) it moves
    to adjacent sites that are closer until no improvement is possible.
    """
    sites = dt.points
    if not sites:
        raise ValueError("No sites in triangulation")
    if start is None:
        start = sites[0]

    adjacency = _site_adjacency(dt)
    current = start
    best_d = current.distance_to(query)
    improved = True
    while improved:
        improved = False
        for nb in adjacency.get(current, []):
            d = nb.distance_to(query)
            if d < best_d:
                best_d = d
                current = nb
                improved = True
    return current


def k_nearest_neighbors(
    dt: DelaunayTriangulation, query: Point, k: int
) -> List[Point]:
    """Return the *k* sites nearest to *query* by graph distance (hops)."""
    sites = dt.points
    if not sites or k <= 0:
        return []
    adjacency = _site_adjacency(dt)
    start = nearest_neighbor(dt, query)

    # BFS from start
    visited: Set[Point] = {start}
    order: List[Point] = [start]
    frontier: List[Point] = [start]
    while frontier and len(order) < k:
        nxt: List[Point] = []
        for node in frontier:
            for nb in adjacency.get(node, []):
                if nb not in visited:
                    visited.add(nb)
                    order.append(nb)
                    nxt.append(nb)
                    if len(order) >= k:
                        break
            if len(order) >= k:
                break
        frontier = nxt
    return order[:k]


def locate_point(
    dt: DelaunayTriangulation, query: Point
) -> Optional[Triangle]:
    """Return the triangle containing *query*, or None if outside the hull.

    Uses a visibility-walk: from a random triangle, move across the edge
    whose opposite vertex is "behind" the query relative to the current
    triangle, until no such crossing remains.
    """
    triangles = dt.triangles
    if not triangles:
        return None

    current = triangles[0]
    visited: Set[int] = set()
    # Build edge -> triangle map for adjacency
    edge_to_tris: Dict[Edge, List[Triangle]] = {}
    for t in triangles:
        for e in t.edges():
            edge_to_tris.setdefault(e, []).append(t)

    import random
    rng = random.Random(42)
    while id(current) not in visited:
        visited.add(id(current))
        a, b, c = current.vertices()
        # Check if query is inside this triangle
        if (
            orient2d(a, b, query) >= 0
            and orient2d(b, c, query) >= 0
            and orient2d(c, a, query) >= 0
        ):
            return current
        # Find an edge to cross: the one whose half-plane excludes query
        moved = False
        for e in current.edges():
            opp = current.vertices()
            # The vertex opposite to edge e
            opp_vertex = [v for v in opp if v != e.a and v != e.b]
            if len(opp_vertex) != 1:
                continue
            ov = opp_vertex[0]
            # If query and opp are on opposite sides of e, cross it
            q_side = orient2d(e.a, e.b, query)
            o_side = orient2d(e.a, e.b, ov)
            if q_side * o_side < 0:
                # Cross to the neighbour
                nbrs = edge_to_tris.get(e, [])
                other = None
                for n in nbrs:
                    if n is not current:
                        other = n
                        break
                if other is not None:
                    current = other
                    moved = True
                    break
        if not moved:
            # Stuck — query is outside the convex hull
            return None
    return None


def _site_adjacency(dt: DelaunayTriangulation) -> Dict[Point, List[Point]]:
    """Map each site to its neighbouring sites (via shared Delaunay edges)."""
    adj: Dict[Point, List[Point]] = {}
    for e in dt.edges():
        adj.setdefault(e.a, []).append(e.b)
        adj.setdefault(e.b, []).append(e.a)
    return adj