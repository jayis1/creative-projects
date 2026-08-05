"""
Boundary matrix and persistence computation via column reduction.

The standard algorithm for persistent homology:

1. Build the boundary matrix D where D[j] = boundary of simplex j
   (as a column vector over GF(2), indexed by simplex ids).
2. Sort columns by filtration value (and dimension as tie-break).
3. Reduce columns from left to right: while the lowest nonzero entry of
   column j equals the lowest nonzero entry of some earlier column i,
   add column i to column j (XOR).
4. Read off persistence pairs: (i, j) where i is the lowest-1 row of j.

Unpaired columns represent essential cycles (infinite persistence).

This implementation uses the *lookup table* optimisation: a dictionary maps
each row index to the column that currently has it as its lowest-1, giving
O(1) lookup instead of scanning all prior columns.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from .scomplex import Simplex, SimplexTree


class BoundaryMatrix:
    """Sparse boundary matrix over GF(2).

    Columns are stored as sorted lists of row indices (positions of 1s).
    This representation is memory-efficient and supports fast lowest-bit
    lookup and XOR column addition.

    Parameters
    ----------
    columns : list of sorted-int lists
        Each column is a list of row indices where the entry is 1.
    column_dims : list of int
        Dimension of the simplex corresponding to each column.
    column_filts : list of float
        Filtration value of each column's simplex.

    Attributes
    ----------
    num_rows : int
    num_cols : int
    """

    def __init__(
        self,
        columns: List[List[int]],
        column_dims: List[int],
        column_filts: List[float],
    ) -> None:
        if not (len(columns) == len(column_dims) == len(column_filts)):
            raise ValueError(
                "columns, column_dims, and column_filts must have equal length"
            )
        self.columns: List[List[int]] = [sorted(c) for c in columns]
        self.column_dims: List[int] = list(column_dims)
        self.column_filts: List[float] = list(column_filts)
        self.num_cols = len(columns)
        self.num_rows = max((max(c) for c in columns if c), default=-1) + 1

    @classmethod
    def from_simplex_tree(cls, tree: SimplexTree) -> "BoundaryMatrix":
        """Build the boundary matrix from a filtered simplex tree.

        Columns are ordered by (filtration_value, dimension, simplex) so that
        the standard left-to-right reduction produces correct persistence pairs.
        The simplex ordering within a (filtration, dimension) group is
        lexicographic on vertices, which is a valid refinement of the partial
        order (a face always precedes its coface in lexicographic order when
        they share the same filtration value and dimension differs).
        """
        # Get all simplices with their filtration values.
        simplices: List[Tuple[Simplex, float]] = list(tree.iter_with_filtration())
        # Sort by (filtration, dimension, vertex tuple) — a total order that
        # respects the filtration and dimensional partial order.
        simplices.sort(key=lambda sf: (sf[1], sf[0].dimension, sf[0].vertices))

        # Assign column/row indices in sorted order.
        index_map: Dict[Simplex, int] = {}
        for i, (s, _) in enumerate(simplices):
            index_map[s] = i

        columns: List[List[int]] = []
        column_dims: List[int] = []
        column_filts: List[float] = []

        for s, f in simplices:
            col: List[int] = []
            for face in s.faces():
                idx = index_map.get(face)
                if idx is not None:
                    col.append(idx)
            columns.append(col)
            column_dims.append(s.dimension)
            column_filts.append(f)

        return cls(columns, column_dims, column_filts)

    def lowest_one(self, col: int) -> int:
        """Return the row index of the lowest 1 in column ``col``, or -1."""
        c = self.columns[col]
        return c[-1] if c else -1

    def add_column(self, target: int, source: int) -> None:
        """Add (XOR) column ``source`` into column ``target`` (over GF(2)).

        Both columns must be sorted lists of row indices. The result is also
        a sorted list (XOR of two sorted sets).
        """
        t = self.columns[target]
        s = self.columns[source]
        # XOR merge of two sorted lists.
        result: List[int] = []
        i = j = 0
        while i < len(t) and j < len(s):
            if t[i] < s[j]:
                result.append(t[i])
                i += 1
            elif t[i] > s[j]:
                result.append(s[j])
                j += 1
            else:
                i += 1
                j += 1  # cancel (XOR)
        result.extend(t[i:])
        result.extend(s[j:])
        self.columns[target] = result


def reduce_matrix(matrix: BoundaryMatrix) -> List[Tuple[int, int, int]]:
    """Reduce the boundary matrix and return persistence pairs.

    Returns a list of (birth_col, death_col, dimension) tuples.
    A death_col of -1 means the feature is essential (infinite persistence).

    Algorithm (standard column reduction with lookup table):

    For each column j (left to right):
        while lowest_one(j) != -1:
            low = lowest_one(j)
            if low in low_to_col:  # some earlier column has this as lowest
                add column low_to_col[low] to column j
            else:
                record pair (low, j) with dimension dim(j) - 1
                low_to_col[low] = j
                break
        # if column reduced to zero, it's a potential essential cycle

    After processing all columns, any column that reduced to zero and whose
    index never appeared as a birth row (lowest-one of a death column) is
    an essential cycle.
    """
    low_to_col: Dict[int, int] = {}  # row -> column that has this as lowest
    pairs: List[Tuple[int, int, int]] = []

    for j in range(matrix.num_cols):
        while True:
            low = matrix.lowest_one(j)
            if low == -1:
                break
            if low in low_to_col:
                # Add the previously reduced column to this one (XOR).
                matrix.add_column(j, low_to_col[low])
            else:
                # This column has a new lowest-one; it's a death for row `low`.
                low_to_col[low] = j
                dim = matrix.column_dims[j]
                # The birth simplex is row `low`, dimension dim - 1.
                pairs.append((low, j, dim - 1))
                break

    # Identify essential cycles.
    # A column j is an essential birth if:
    #   1. It was reduced to zero (lowest_one == -1 after reduction).
    #   2. j was never used as a death column (j not in death_cols).
    #   3. j was never used as a birth row (j not in birth_rows).
    # Condition 3 is key: if some death column has j as its lowest-one, then
    # j's homology class was killed, so j is not essential.
    birth_rows = {p[0] for p in pairs}
    death_cols = {p[1] for p in pairs}
    for j in range(matrix.num_cols):
        if matrix.lowest_one(j) == -1 and j not in birth_rows and j not in death_cols:
            pairs.append((j, -1, matrix.column_dims[j]))

    return pairs


def compute_persistence(
    tree: SimplexTree,
    max_dimension: Optional[int] = None,
    min_persistence: float = 0.0,
) -> Dict[int, List[Tuple[float, float]]]:
    """Compute persistent homology from a simplex tree.

    Returns a dictionary mapping dimension -> list of (birth, death) pairs.
    Death = inf for essential cycles.

    Parameters
    ----------
    tree : SimplexTree
        The filtered simplicial complex.
    max_dimension : int, optional
        Only return persistence pairs up to this dimension. Default: all.
    min_persistence : float, optional
        Filter out features with persistence < min_persistence (essential
        cycles are always kept). Default: 0.0 (keep all).

    Raises
    ------
    ValueError
        If the tree is empty.
    """
    if tree.num_simplices() == 0:
        raise ValueError("Cannot compute persistence on an empty simplex tree")

    matrix = BoundaryMatrix.from_simplex_tree(tree)
    raw_pairs = reduce_matrix(matrix)

    result: Dict[int, List[Tuple[float, float]]] = {}
    for birth_col, death_col, dim in raw_pairs:
        if max_dimension is not None and dim > max_dimension:
            continue
        birth = matrix.column_filts[birth_col]
        if death_col == -1:
            death = float("inf")
        else:
            death = matrix.column_filts[death_col]
            # Filter by minimum persistence (skip zero-persistence noise).
            if min_persistence > 0 and (death - birth) < min_persistence:
                continue
        result.setdefault(dim, []).append((birth, death))

    return result