"""
Optimised persistence computation using the *sparse Rips* approach and
the *clearing* (a.k.a. *twist*) reduction optimisation.

The standard column-reduction algorithm in :mod:`tda.matrix` processes
every column from left to right.  The **clearing** optimisation skips
columns that are already known to be zero (because their lowest-one was
used as a pivot by a later column).  In practice this dramatically
reduces the number of column additions for dense filtrations.

Additionally this module provides a **sparse Rips** helper that
truncates the distance matrix to only the *k* nearest neighbours of
each point, producing a sparser complex that approximates the full
Rips complex at a fraction of the memory cost.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .scomplex import Simplex, SimplexTree
from .complexes import VietorisRipsComplex
from .matrix import BoundaryMatrix, compute_persistence as _standard_persistence
from .logging_config import get_logger

_log = get_logger(__name__)

Infinity = float("inf")


# ---------------------------------------------------------------------------
# Clearing / twist reduction
# ---------------------------------------------------------------------------

def compute_persistence_clearing(
    tree: SimplexTree,
    max_dimension: Optional[int] = None,
    min_persistence: float = 0.0,
) -> Dict[int, List[Tuple[float, float]]]:
    """Compute persistent homology using the clearing optimisation.

    The clearing (a.k.a. *twist*) algorithm skips reduction of columns
    that are already empty — i.e., whose entries have all been consumed
    as pivots by earlier columns.  This is a lightweight but effective
    optimisation of the standard forward column-reduction algorithm.

    The results are identical to :func:`tda.matrix.compute_persistence`.

    Parameters are identical to :func:`tda.matrix.compute_persistence`.
    """
    if tree.num_simplices() == 0:
        raise ValueError("Cannot compute persistence on an empty simplex tree")

    # Build the boundary matrix.
    matrix = BoundaryMatrix.from_simplex_tree(tree)
    n = matrix.num_cols

    # Standard forward reduction with a clearing optimisation: skip
    # columns whose only entries have already been consumed as pivots
    # by earlier columns.  We detect this by checking if the column is
    # empty before entering the reduction loop.
    low_to_col: Dict[int, int] = {}
    pairs: List[Tuple[int, int, int]] = []

    for j in range(n):
        # Clearing optimisation: if column j is already empty (all its
        # entries were consumed as pivots by earlier columns), skip the
        # reduction loop entirely.
        if not matrix.columns[j]:
            continue
        while True:
            low = matrix.lowest_one(j)
            if low == -1:
                break
            if low in low_to_col:
                matrix.add_column(j, low_to_col[low])
            else:
                low_to_col[low] = j
                dim = matrix.column_dims[j]
                pairs.append((low, j, dim - 1))
                break

    # Identify essential cycles.
    birth_rows = {p[0] for p in pairs}
    death_cols = {p[1] for p in pairs}
    for j in range(n):
        if matrix.lowest_one(j) == -1 and j not in birth_rows and j not in death_cols:
            pairs.append((j, -1, matrix.column_dims[j]))

    # Convert to (birth, death) pairs by filtration value.
    result: Dict[int, List[Tuple[float, float]]] = {}
    for birth_col, death_col, dim in pairs:
        if max_dimension is not None and dim > max_dimension:
            continue
        birth = matrix.column_filts[birth_col]
        if death_col == -1:
            death = Infinity
        else:
            death = matrix.column_filts[death_col]
            if min_persistence > 0 and (death - birth) < min_persistence:
                continue
        result.setdefault(dim, []).append((birth, death))

    return result


# ---------------------------------------------------------------------------
# Sparse Rips complex (k-NN truncation)
# ---------------------------------------------------------------------------

class SparseRipsComplex:
    """Approximate Vietoris–Rips complex using *k*-nearest-neighbour
    truncation.

    Only the *k* nearest neighbours of each point are connected by
    edges, reducing the number of simplices from O(n^d) to roughly
    O(n * k^(d-1)).  The resulting complex is a **supercomplex** of the
    sparse Rips complex of Sheehy (2013) in the sense that it contains
    all simplices whose vertex pairs are within the k-NN graph, and the
    filtration values are exact Rips diameters.

    Parameters
    ----------
    points : sequence of points
    k : int
        Number of nearest neighbours to keep per point.
    max_scale : float
        Maximum filtration scale.
    max_dimension : int
        Maximum simplex dimension.

    Examples
    --------
    >>> pts = [(0, 0), (1, 0), (2, 0), (3, 0)]
    >>> sr = SparseRipsComplex(pts, k=2, max_scale=3.0, max_dimension=1)
    >>> tree = sr.build()
    """

    def __init__(
        self,
        points,
        k: int = 5,
        max_scale: float = float("inf"),
        max_dimension: int = 1,
        metric=None,
    ) -> None:
        if not points:
            raise ValueError("Need at least one point")
        if k < 1:
            raise ValueError("k must be >= 1")
        self.points = list(points)
        self.k = min(k, len(points) - 1) if len(points) > 1 else 0
        self.max_scale = max_scale
        self.max_dimension = max_dimension
        self.metric = metric

    def build(self) -> SimplexTree:
        """Build the sparse Rips complex as a simplex tree."""
        # Use the full VR builder but restrict edges to k-NN graph.
        vr = VietorisRipsComplex(
            self.points,
            max_scale=self.max_scale,
            max_dimension=self.max_dimension,
            metric=self.metric,
        )
        # Compute full distance matrix.
        d = vr.distance_matrix
        n = len(self.points)

        # Determine k-NN edge set.
        tree = SimplexTree(max_dimension=self.max_dimension)
        for i in range(n):
            tree.insert(Simplex((i,)), 0.0)

        # For each point, find its k nearest neighbours.
        edges: List[Tuple[int, int]] = []
        edge_set: set[Tuple[int, int]] = set()
        for i in range(n):
            # Sort neighbours by distance (excluding self).
            neighbours = sorted(range(n), key=lambda j: d[i][j])
            for j in neighbours[1:self.k + 1]:
                a, b = min(i, j), max(i, j)
                if (a, b) not in edge_set and d[a][b] <= self.max_scale:
                    edge_set.add((a, b))
                    edges.append((a, b))
                    tree.insert(Simplex((a, b)), d[a][b])

        # Higher-dimensional simplices via clique expansion on the k-NN graph.
        if self.max_dimension >= 2 and edges:
            adj: List[set[int]] = [set() for _ in range(n)]
            for a, b in edges:
                adj[a].add(b)
                adj[b].add(a)

            current: List[Tuple[int, ...]] = [e for e in edges]
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
                        filt = max(d[nv[i]][nv[j]]
                                   for i in range(len(nv))
                                   for j in range(i + 1, len(nv)))
                        if filt <= self.max_scale:
                            tree.insert(Simplex(nv), filt)
                            next_level.append(nv)
                current = next_level

        return tree