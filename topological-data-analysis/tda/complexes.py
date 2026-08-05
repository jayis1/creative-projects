"""
Simplicial complex construction: Vietoris–Rips complex.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Iterable, List, Optional, Sequence, Tuple

from .scomplex import Simplex, SimplexTree


def euclidean_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Standard Euclidean (L2) distance between two points."""
    if len(a) != len(b):
        raise ValueError("Points must have the same dimension")
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def pairwise_distances(points: Sequence[Sequence[float]]) -> List[List[float]]:
    """Compute the full pairwise distance matrix for a set of points."""
    n = len(points)
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist = euclidean_distance(points[i], points[j])
            d[i][j] = dist
            d[j][i] = dist
    return d


class VietorisRipsComplex:
    """Vietoris–Rips filtered simplicial complex builder.

    Given a point cloud and a maximum scale (epsilon), the VR complex contains
    a simplex for every subset of points with pairwise diameter <= epsilon.

    The filtration value of a simplex is the maximum pairwise distance among
    its vertices (the *diameter* of the simplex).

    Parameters
    ----------
    points : sequence of points
        The input point cloud. Each point is a sequence of coordinates.
    max_scale : float, optional
        Maximum filtration scale. Simplices with diameter > max_scale are
        not included. Default: infinity (all simplices, beware exponential
        blow-up).
    max_dimension : int, optional
        Maximum dimension of simplices to construct. Default: 1 (graph).
    metric : callable, optional
        Distance function ``(a, b) -> float``. Default: Euclidean.

    Examples
    --------
    >>> pts = [(0, 0), (1, 0), (0.5, 0.866)]
    >>> vr = VietorisRipsComplex(pts, max_scale=1.5, max_dimension=2)
    >>> tree = vr.build()
    >>> tree.dimension()
    2
    """

    def __init__(
        self,
        points: Sequence[Sequence[float]],
        max_scale: float = float("inf"),
        max_dimension: int = 1,
        metric=None,
    ) -> None:
        if not points:
            raise ValueError("Need at least one point")
        self.points = list(points)
        self.max_scale = float(max_scale)
        self.max_dimension = int(max_dimension)
        self.metric = metric if metric is not None else euclidean_distance
        self._dist: Optional[List[List[float]]] = None

    @property
    def distance_matrix(self) -> List[List[float]]:
        if self._dist is None:
            self._dist = self._compute_distance_matrix()
        return self._dist

    def _compute_distance_matrix(self) -> List[List[float]]:
        """Compute the pairwise distance matrix using the configured metric."""
        n = len(self.points)
        d = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                dist = self.metric(self.points[i], self.points[j])
                d[i][j] = dist
                d[j][i] = dist
        return d

    def _simplex_filtration(self, vertices: Tuple[int, ...]) -> float:
        """Filtration value = max pairwise distance among vertices."""
        d = self.distance_matrix
        return max(d[i][j] for i in vertices for j in vertices if i < j)

    def build(self) -> SimplexTree:
        """Build the filtered simplex tree up to ``max_dimension``.

        Algorithm:
        1. Insert all vertices at filtration 0.
        2. Insert edges with distance <= max_scale.
        3. For dimension 2..max_dimension, enumerate all (dim+1)-cliques and
           insert those with diameter <= max_scale.
        """
        tree = SimplexTree(max_dimension=self.max_dimension)
        n = len(self.points)

        # 0-simplices (vertices) at filtration 0
        for i in range(n):
            tree.insert(Simplex((i,)), 0.0)

        # 1-simplices (edges)
        d = self.distance_matrix
        edges: List[Tuple[int, int]] = []
        for i in range(n):
            for j in range(i + 1, n):
                if d[i][j] <= self.max_scale:
                    edges.append((i, j))
                    tree.insert(Simplex((i, j)), d[i][j])

        # Higher-dimensional simplices via clique expansion.
        if self.max_dimension >= 2:
            self._build_higher(tree, edges)

        return tree

    def _build_higher(self, tree: SimplexTree,
                      edges: List[Tuple[int, int]]) -> None:
        """Build higher-dimensional simplices by clique enumeration.

        We use a BFS-like approach: for each k-simplex, try extending by every
        vertex that is connected to all existing vertices.
        """
        d = self.distance_matrix
        # adjacency list
        adj: List[set[int]] = [set() for _ in range(len(self.points))]
        for i, j in edges:
            adj[i].add(j)
            adj[j].add(i)

        # Start from edges, extend to triangles, then tetrahedra, etc.
        current: List[Tuple[int, ...]] = [(i, j) for i, j in edges]
        for dim in range(2, self.max_dimension + 1):
            next_level: List[Tuple[int, ...]] = []
            for simplex_verts in current:
                # Candidate vertices = intersection of neighbors of all verts.
                candidates = set(range(len(self.points)))
                for v in simplex_verts:
                    candidates &= adj[v]
                # Only consider vertices greater than max(simplex) to avoid
                # duplicates (canonical ordering).
                max_v = max(simplex_verts)
                for c in candidates:
                    if c <= max_v:
                        continue
                    new_verts = simplex_verts + (c,)
                    filt = self._simplex_filtration(new_verts)
                    if filt <= self.max_scale:
                        tree.insert(Simplex(new_verts), filt)
                        next_level.append(new_verts)
            current = next_level


def rips_filtration(
    points: Sequence[Sequence[float]],
    max_scale: float = float("inf"),
    max_dimension: int = 1,
    metric=None,
) -> SimplexTree:
    """Convenience function: build a Vietoris–Rips filtration."""
    vr = VietorisRipsComplex(points, max_scale, max_dimension, metric)
    return vr.build()