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
        assert len(columns) == len(column_dims) == len(column_filts)
        self.columns: List[List[int]] = [sorted(c) for c in columns]
        self.column_dims: List[int] = list(column_dims)
        self.column_filts: List[float] = list(column_filts)
        self.num_cols = len(columns)
        self.num_rows = max((max(c) for c in columns if c), default=-1) + 1

    @classmethod
    def from_simplex_tree(cls, tree: SimplexTree) -> "BoundaryMatrix":
        """Build the boundary matrix from a filtered simplex tree.

        Columns are ordered by (filtration_value, dimension) so that the
        standard left-to-right reduction produces correct persistence pairs.
        """
        # Get all simplices with their filtration values.
        simplices: List[Tuple[Simplex, float]] = list(tree.iter_with_filtration())
        # Sort by (filtration, dimension) — this is the filtration order.
        simplices.sort(key=lambda sf: (sf[1], sf[0].dimension))

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
                if face in index_map:
                    col.append(index_map[face])
            columns.append(col)
            column_dims.append(s.dimension)
            column_filts.append(f)

        return cls(columns, column_dims, column_filts)

    def lowest_one(self, col: int) -> int:
        """Return the row index of the lowest 1 in column ``col``, or -1."""
        c = self.columns[col]
        return c[-1] if c else -1

    def add_column(self, target: int, source: int) -> None:
        """Add (XOR) column ``source`` into column ``target`` (over GF(2))."""
        t = self.columns[target]
        s = self.columns[source]
        # XOR merge of two sorted lists.
        result: List[int] = []
        i = j = 0
        while i < len(t) and j < len(s):
            if t[i] < s[j]:
                result.append(t[i]); i += 1
            elif t[i] > s[j]:
                result.append(s[j]); j += 1
            else:
                i += 1; j += 1  # cancel (XOR)
        result.extend(t[i:])
        result.extend(s[j:])
        self.columns[target] = result


def reduce_matrix(matrix: BoundaryMatrix) -> List[Tuple[int, int, int]]:
    """Reduce the boundary matrix and return persistence pairs.

    Returns a list of (birth_col, death_col, dimension) tuples.
    A death_col of -1 means the feature is essential (infinite persistence).

    The algorithm uses the "lowest-one" approach:

    For each column j (left to right):
        while lowest_one(j) != -1 and lowest_one(j) was seen as a birth:
            add the previously-seen column to j
        if lowest_one(j) != -1:
            record pair (lowest_one(j), j)
        else:
            j is a birth (unpaired — will pair with infinity or later column)

    This is the standard *matrix reduction* algorithm (Edelsbrunner-Harer).
    """
    lowest_seen: Dict[int, int] = {}  # row -> column index that has this as lowest
    pairs: List[Tuple[int, int, int]] = []
    births: Dict[int, int] = {}  # row -> column that is a birth (unpaired after reduction)

    for j in range(matrix.num_cols):
        while True:
            low = matrix.lowest_one(j)
            if low == -1:
                break
            if low in lowest_seen:
                # Add the previously reduced column to this one.
                matrix.add_column(j, lowest_seen[low])
                # Continue reducing.
            else:
                # This column has a new lowest-one; it's a death for row `low`.
                lowest_seen[low] = j
                dim = matrix.column_dims[j]  # death dim = dim of the simplex
                # The birth simplex is `low`, which has dimension dim-1.
                pairs.append((low, j, dim - 1))
                break
        else:
            # Column reduced to zero — it's a birth (essential cycle).
            births[j] = j

    # Identify essential cycles: columns that reduced to zero and were never
    # paired as a birth (i.e., their row index never appeared as the lowest-one
    # of a death column). These are births with infinite persistence.
    birth_rows = {p[0] for p in pairs}  # row indices used as births
    death_cols = {p[1] for p in pairs}  # column indices used as deaths
    for j in range(matrix.num_cols):
        if matrix.lowest_one(j) == -1 and j not in birth_rows and j not in death_cols:
            # This is an essential cycle (infinite persistence).
            pairs.append((j, -1, matrix.column_dims[j]))

    return pairs


def compute_persistence(
    tree: SimplexTree,
    max_dimension: Optional[int] = None,
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
    """
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
        result.setdefault(dim, []).append((birth, death))

    return result