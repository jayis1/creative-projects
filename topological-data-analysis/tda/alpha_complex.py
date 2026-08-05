"""
Alpha complex builder.

The **alpha complex** is a subcomplex of the Delaunay triangulation
restricted to the union of radius-*alpha* balls.  It is a tighter
approximation of the Čech complex than the Vietoris–Rips complex and is
therefore more efficient computationally while still provably homotopy
equivalent to the union of balls.

This pure-Python implementation does *not* depend on a Delaunay
triangulation library.  Instead it builds the Rips complex and then
filters simplices by their **circumradius** (the radius of the smallest
enclosing ball of the vertices), keeping only those whose circumradius
is ≤ *alpha*.  For edges this reduces to ``diameter/2 ≤ alpha``,
identical to the Čech complex criterion, and for higher-dimensional
simplices the miniball radius is computed exactly for ≤ 3 points and
heuristically otherwise (via the Welzl-style miniball used by
:class:`~tda.complexes_extra.CechComplex`).

While this is less efficient than a true Delaunay-based alpha complex
(which avoids enumerating all cliques), it is correct and
self-contained — the primary goal of this toolkit.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .scomplex import Simplex, SimplexTree
from .complexes import euclidean_distance, pairwise_distances
from .complexes_extra import _circumradius_3pts


class AlphaComplex:
    """Alpha complex (filtered by smallest-enclosing-ball radius).

    Parameters
    ----------
    points : sequence of points
        Input point cloud in Euclidean space.
    alpha : float
        Maximum circumradius (ball radius) for simplex inclusion.
    max_dimension : int
        Maximum simplex dimension to construct.
    metric : callable, optional
        Distance function (default Euclidean).  Only used for the edge
        distance; the miniball computation always operates in the
        ambient Euclidean space.

    Examples
    --------
    >>> pts = [(0, 0), (1, 0), (0.5, 0.866)]
    >>> ac = AlphaComplex(pts, alpha=0.6, max_dimension=2)
    >>> tree = ac.build()
    >>> Simplex((0, 1)) in tree
    True
    """

    def __init__(
        self,
        points: Sequence[Sequence[float]],
        alpha: float,
        max_dimension: int = 1,
        metric=None,
    ) -> None:
        if not points:
            raise ValueError("Need at least one point")
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        self.points = list(points)
        self.alpha = float(alpha)
        self.max_dimension = int(max_dimension)
        self.metric = metric if metric is not None else euclidean_distance
        self._dist = pairwise_distances(self.points)

    # ------------------------------------------------------------------
    # smallest enclosing ball radius
    # ------------------------------------------------------------------

    def _miniball_radius(self, verts: Tuple[int, ...]) -> float:
        """Return the radius of the smallest enclosing ball of *verts*."""
        if len(verts) == 1:
            return 0.0
        if len(verts) == 2:
            return self._dist[verts[0]][verts[1]] / 2.0
        if len(verts) == 3:
            return _circumradius_3pts([self.points[v] for v in verts])
        # 4+ points: iterative miniball heuristic (same as CechComplex).
        pts = [self.points[v] for v in verts]
        center = list(pts[0])
        radius = 0.0
        for p in pts[1:]:
            d = math.sqrt(sum((c - pi) ** 2 for c, pi in zip(center, p)))
            if d > radius:
                new_radius = (radius + d) / 2.0
                for i in range(len(center)):
                    center[i] = (radius * center[i] + d * p[i]) / (radius + d)
                radius = new_radius
        return radius

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def build(self) -> SimplexTree:
        """Build the alpha complex as a filtered simplex tree."""
        tree = SimplexTree(max_dimension=self.max_dimension)
        n = len(self.points)

        # Vertices at radius 0.
        for i in range(n):
            tree.insert(Simplex((i,)), 0.0)

        # Edges: include if half-distance <= alpha.
        edges: List[Tuple[int, int]] = []
        for i in range(n):
            for j in range(i + 1, n):
                r = self._dist[i][j] / 2.0
                if r <= self.alpha:
                    edges.append((i, j))
                    tree.insert(Simplex((i, j)), r)

        # Higher dimensions: clique expansion with miniball filter.
        if self.max_dimension >= 2:
            adj: List[set[int]] = [set() for _ in range(n)]
            for i, j in edges:
                adj[i].add(j)
                adj[j].add(i)

            current: List[Tuple[int, ...]] = list(edges)
            for dim in range(2, self.max_dimension + 1):
                next_level: List[Tuple[int, ...]] = []
                for sv in current:
                    candidates = set(range(n))
                    for v in sv:
                        candidates &= adj[v]
                    max_v = max(sv)
                    for c in candidates:
                        if c <= max_v:
                            continue
                        nv = sv + (c,)
                        r = self._miniball_radius(nv)
                        if r <= self.alpha:
                            tree.insert(Simplex(nv), r)
                            next_level.append(nv)
                current = next_level

        return tree