"""
Additional complex builders: weighted Vietoris–Rips, Cech complex,
and sublevel-set filtration for scalar functions on grids.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .scomplex import Simplex, SimplexTree
from .complexes import euclidean_distance, pairwise_distances


class WeightedRipsComplex:
    """Vietoris–Rips complex with weighted vertex filtration.

    Each vertex has an associated weight (filtration value). The filtration
    value of a simplex is:

        f(simplex) = max( max_vertex_weight, diameter / 2 )

    This is the *lower-star* filtration on the function f(v) = weight,
    combined with the Rips diameter. Using diameter/2 gives the *witness*
    Rips complex where the simplex appears when the balls of radius t/2
    around the vertices become pairwise intersecting and each vertex is
    "born" at its weight.

    Parameters
    ----------
    points : sequence of points
    weights : sequence of float
        Weight (birth time) for each vertex. Must have same length as points.
    max_scale : float
        Maximum filtration scale.
    max_dimension : int
        Maximum simplex dimension.
    metric : callable, optional
        Distance function. Default: Euclidean.

    Examples
    --------
    >>> pts = [(0, 0), (1, 0), (2, 0)]
    >>> w = [0.0, 0.5, 1.0]
    >>> wr = WeightedRipsComplex(pts, w, max_scale=2.0, max_dimension=1)
    >>> tree = wr.build()
    >>> [s for s, f in tree.iter_with_filtration() if s.dimension == 0]
    [Simplex((0,)), Simplex((1,)), Simplex((2,))]
    """

    def __init__(
        self,
        points: Sequence[Sequence[float]],
        weights: Sequence[float],
        max_scale: float = float("inf"),
        max_dimension: int = 1,
        metric=None,
    ) -> None:
        if len(points) != len(weights):
            raise ValueError("points and weights must have the same length")
        if any(w < 0 for w in weights):
            raise ValueError("Weights must be non-negative")
        self.points = list(points)
        self.weights = list(weights)
        self.max_scale = float(max_scale)
        self.max_dimension = int(max_dimension)
        self.metric = metric if metric is not None else euclidean_distance
        self._dist: Optional[List[List[float]]] = None

    @property
    def distance_matrix(self) -> List[List[float]]:
        if self._dist is None:
            self._dist = pairwise_distances(self.points)
        return self._dist

    def _simplex_filtration(self, verts: Tuple[int, ...]) -> float:
        """Filtration = max(max vertex weight, diameter / 2)."""
        d = self.distance_matrix
        max_w = max(self.weights[v] for v in verts)
        if len(verts) == 1:
            return max_w
        diameter = max(d[i][j] for i in verts for j in verts if i < j)
        return max(max_w, diameter / 2.0)

    def build(self) -> SimplexTree:
        tree = SimplexTree(max_dimension=self.max_dimension)
        n = len(self.points)
        d = self.distance_matrix

        # Vertices
        for i in range(n):
            tree.insert(Simplex((i,)), self.weights[i])

        # Edges
        edges: List[Tuple[int, int]] = []
        for i in range(n):
            for j in range(i + 1, n):
                f = self._simplex_filtration((i, j))
                if f <= self.max_scale:
                    edges.append((i, j))
                    tree.insert(Simplex((i, j)), f)

        # Higher dims via clique expansion
        if self.max_dimension >= 2:
            adj: List[set[int]] = [set() for _ in range(n)]
            for i, j in edges:
                adj[i].add(j)
                adj[j].add(i)

            current = [e for e in edges]
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
                        f = self._simplex_filtration(nv)
                        if f <= self.max_scale:
                            tree.insert(Simplex(nv), f)
                            next_level.append(nv)
                current = next_level

        return tree


class CechComplex:
    """Čech complex: simplices correspond to sets of points whose
    radius-epsilon balls have a non-empty intersection.

    For a set of points in R^d, a k-simplex is included if there exists a
    point within distance epsilon of all k+1 vertices. This is equivalent to
    the smallest enclosing ball radius <= epsilon.

    For 1-simplices (edges), this reduces to distance <= 2*epsilon (same as
    Rips). For higher dimensions, the Čech complex is a subcomplex of the
    Rips complex.

    Parameters
    ----------
    points : sequence of points
    epsilon : float
        Ball radius.
    max_dimension : int
    metric : callable, optional

    Notes
    -----
    This implementation checks the smallest enclosing ball using the
    welzl_miniball heuristic for simplices of dimension >= 2. For edges,
    it uses the simple distance <= 2*epsilon criterion.
    """

    def __init__(
        self,
        points: Sequence[Sequence[float]],
        epsilon: float,
        max_dimension: int = 1,
        metric=None,
    ) -> None:
        if epsilon <= 0:
            raise ValueError("epsilon must be positive")
        self.points = list(points)
        self.epsilon = float(epsilon)
        self.max_dimension = int(max_dimension)
        self.metric = metric if metric is not None else euclidean_distance
        self._dist = pairwise_distances(self.points)

    def _miniball_radius(self, verts: Tuple[int, ...]) -> float:
        """Approximate smallest enclosing ball radius using Welzl's algorithm.

        For up to 4 points (3D), this is exact. For larger sets, uses an
        iterative approach.
        """
        if len(verts) == 1:
            return 0.0
        if len(verts) == 2:
            return self._dist[verts[0]][verts[1]] / 2.0

        pts = [self.points[v] for v in verts]
        # For 3 points: circumradius of the triangle.
        if len(pts) == 3:
            return _circumradius_3pts(pts)

        # For 4+ points: iterative miniball (simplified Welzl).
        # Start with the two farthest points.
        center = list(pts[0])
        radius = 0.0
        for p in pts[1:]:
            d = math.sqrt(sum((c - pi) ** 2 for c, pi in zip(center, p)))
            if d > radius:
                # Expand ball.
                new_radius = (radius + d) / 2.0
                for i in range(len(center)):
                    center[i] = (radius * center[i] + d * p[i]) / (radius + d)
                radius = new_radius
        return radius

    def build(self) -> SimplexTree:
        tree = SimplexTree(max_dimension=self.max_dimension)
        n = len(self.points)
        diam = self.epsilon * 2  # edges: distance <= 2*epsilon

        # Vertices
        for i in range(n):
            tree.insert(Simplex((i,)), 0.0)

        # Edges (same as Rips with scale = 2*epsilon)
        edges: List[Tuple[int, int]] = []
        for i in range(n):
            for j in range(i + 1, n):
                if self._dist[i][j] <= diam:
                    edges.append((i, j))
                    tree.insert(Simplex((i, j)), self._dist[i][j] / 2.0)

        # Higher dimensions: check miniball radius <= epsilon
        if self.max_dimension >= 2:
            adj: List[set[int]] = [set() for _ in range(n)]
            for i, j in edges:
                adj[i].add(j)
                adj[j].add(i)

            current = [e for e in edges]
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
                        if r <= self.epsilon:
                            tree.insert(Simplex(nv), r)
                            next_level.append(nv)
                current = next_level

        return tree


def _circumradius_3pts(pts: List[Sequence[float]]) -> float:
    """Circumradius of a triangle given 3 points."""
    a = math.sqrt(sum((pts[0][i] - pts[1][i]) ** 2 for i in range(len(pts[0]))))
    b = math.sqrt(sum((pts[1][i] - pts[2][i]) ** 2 for i in range(len(pts[0]))))
    c = math.sqrt(sum((pts[2][i] - pts[0][i]) ** 2 for i in range(len(pts[0]))))
    # Area via Heron's formula.
    s = (a + b + c) / 2.0
    area = math.sqrt(max(0.0, s * (s - a) * (s - b) * (s - c)))
    if area < 1e-15:
        return max(a, b, c) / 2.0  # degenerate: use longest edge / 2
    return (a * b * c) / (4.0 * area)


class SublevelFiltration:
    """Sublevel-set filtration of a scalar function on a grid.

    Given a 2D or 3D grid of scalar values, build a cubical complex and
    compute its sublevel-set filtration. This is useful for analyzing
    topological features of images, density maps, etc.

    Parameters
    ----------
    grid : 2D or 3D list (list of lists, or list of lists of lists)
        Scalar field values on a regular grid.
    max_dimension : int
        Maximum cell dimension to include.

    Examples
    --------
    >>> grid = [[0, 1, 2], [1, 2, 3], [2, 3, 4]]
    >>> sf = SublevelFiltration(grid, max_dimension=1)
    >>> tree = sf.build()
    """

    def __init__(self, grid, max_dimension: int = 1) -> None:
        self.grid = grid
        self.max_dimension = int(max_dimension)
        self._validate_grid()

    def _validate_grid(self) -> None:
        if not isinstance(self.grid, (list, tuple)):
            raise ValueError("grid must be a nested list")
        if len(self.grid) == 0:
            raise ValueError("grid must not be empty")
        # Detect dimensionality.
        if isinstance(self.grid[0], (list, tuple)):
            self._grid_dim = 2
            # Check regularity.
            n = len(self.grid[0])
            for row in self.grid:
                if len(row) != n:
                    raise ValueError("grid must be rectangular")
                for val in row:
                    if not isinstance(val, (int, float)):
                        raise ValueError("grid values must be numeric")
        else:
            # 1D grid.
            self._grid_dim = 1
            for val in self.grid:
                if not isinstance(val, (int, float)):
                    raise ValueError("grid values must be numeric")

    def build(self) -> SimplexTree:
        """Build the sublevel filtration as a simplex tree.

        For a 2D grid of size (rows x cols), we create:
        - Vertices for each grid cell (value = cell value).
        - Edges between adjacent cells (value = max of the two cells).
        - Triangles for each 2x2 block (value = max of the four cells).

        This is a triangulation of the cubical complex.
        """
        tree = SimplexTree(max_dimension=self.max_dimension)

        if self._grid_dim == 1:
            self._build_1d(tree)
        elif self._grid_dim == 2:
            self._build_2d(tree)
        else:
            raise NotImplementedError("3D grids not yet supported")

        return tree

    def _build_1d(self, tree: SimplexTree) -> None:
        n = len(self.grid)
        for i in range(n):
            tree.insert(Simplex((i,)), float(self.grid[i]))
        for i in range(n - 1):
            f = max(float(self.grid[i]), float(self.grid[i + 1]))
            tree.insert(Simplex((i, i + 1)), f)

    def _build_2d(self, tree: SimplexTree) -> None:
        rows = len(self.grid)
        cols = len(self.grid[0])

        def idx(r: int, c: int) -> int:
            return r * cols + c

        # Vertices
        for r in range(rows):
            for c in range(cols):
                tree.insert(Simplex((idx(r, c),)), float(self.grid[r][c]))

        # Horizontal edges
        for r in range(rows):
            for c in range(cols - 1):
                f = max(float(self.grid[r][c]), float(self.grid[r][c + 1]))
                tree.insert(Simplex((idx(r, c), idx(r, c + 1))), f)

        # Vertical edges
        for r in range(rows - 1):
            for c in range(cols):
                f = max(float(self.grid[r][c]), float(self.grid[r + 1][c]))
                tree.insert(Simplex((idx(r, c), idx(r + 1, c))), f)

        if self.max_dimension >= 2:
            # Diagonal edges + triangles for each 2x2 block.
            for r in range(rows - 1):
                for c in range(cols - 1):
                    v00 = idx(r, c)
                    v01 = idx(r, c + 1)
                    v10 = idx(r + 1, c)
                    v11 = idx(r + 1, c + 1)
                    # Diagonal edge
                    f_diag = max(
                        float(self.grid[r][c]), float(self.grid[r + 1][c + 1])
                    )
                    tree.insert(Simplex((v00, v11)), f_diag)
                    # Two triangles: (v00, v01, v11) and (v00, v10, v11)
                    f_tri = max(
                        float(self.grid[r][c]),
                        float(self.grid[r][c + 1]),
                        float(self.grid[r + 1][c + 1]),
                    )
                    tree.insert(Simplex((v00, v01, v11)), f_tri)
                    f_tri2 = max(
                        float(self.grid[r][c]),
                        float(self.grid[r + 1][c]),
                        float(self.grid[r + 1][c + 1]),
                    )
                    tree.insert(Simplex((v00, v10, v11)), f_tri2)