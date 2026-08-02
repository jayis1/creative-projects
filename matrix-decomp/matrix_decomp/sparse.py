"""Compressed Sparse Row (CSR) matrix representation and operations.

CSR stores only non-zero entries, making it efficient for large sparse
matrices common in scientific computing.  This module provides a minimal
CSR implementation with:

* Construction from dense (list-of-lists) or COO (coordinate) data
* Matrix-vector multiplication ``y = A @ x``
* Matrix-matrix multiplication ``C = A @ B`` (CSR * CSR -> CSR)
* Transpose
* Conversion to dense :class:`~matrix_decomp.matrix.Matrix`
* Iteration over non-zero entries

Example
-------

>>> from matrix_decomp.sparse import CSRMatrix
>>> A = CSRMatrix.from_dense([[0, 0, 1], [2, 0, 0], [0, 3, 0]])
>>> y = A.matvec([1, 1, 1])
>>> y
[1, 2, 3]
"""

from __future__ import annotations

from typing import Iterable, Iterator, List, Sequence, Tuple

from .matrix import Matrix


class CSRMatrix:
    """A matrix in Compressed Sparse Row (CSR) format.

    Parameters
    ----------
    data : list[float]
        Non-zero values, left-to-right, top-to-bottom.
    indices : list[int]
        Column index for each value in ``data``.
    indptr : list[int]
        Row pointer; ``indptr[i]`` is the start index in ``data`` for row ``i``.
        Length must be ``rows + 1``; ``indptr[-1] == len(data)``.
    shape : tuple[int, int]
        ``(rows, cols)`` of the matrix.
    """

    __slots__ = ("data", "indices", "indptr", "rows", "cols")

    def __init__(
        self,
        data: List[float],
        indices: List[int],
        indptr: List[int],
        shape: Tuple[int, int],
    ) -> None:
        self.data = list(data)
        self.indices = list(indices)
        self.indptr = list(indptr)
        self.rows, self.cols = shape
        if len(self.indptr) != self.rows + 1:
            raise ValueError(
                f"indptr must have length rows+1 ({self.rows + 1}), got {len(self.indptr)}"
            )
        if len(self.data) != len(self.indices):
            raise ValueError("data and indices must have the same length")
        if self.indptr[-1] != len(self.data):
            raise ValueError(
                f"indptr[-1] ({self.indptr[-1]}) must equal len(data) ({len(self.data)})"
            )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_dense(cls, dense: Sequence[Sequence[float]], tol: float = 0.0) -> "CSRMatrix":
        """Build a CSR matrix from a dense list-of-lists, dropping entries
        with ``abs(v) <= tol`` (default: exact zeros only).
        """
        rows = len(dense)
        cols = len(dense[0]) if rows else 0
        data: List[float] = []
        indices: List[int] = []
        indptr: List[int] = [0]
        for i in range(rows):
            for j in range(cols):
                v = float(dense[i][j])
                if abs(v) > tol:
                    data.append(v)
                    indices.append(j)
            indptr.append(len(data))
        return cls(data, indices, indptr, (rows, cols))

    @classmethod
    def from_coo(
        cls,
        coords: Iterable[Tuple[int, int, float]],
        shape: Tuple[int, int],
    ) -> "CSRMatrix":
        """Build a CSR matrix from coordinate (COO) triples ``(row, col, value)``.

        Entries are sorted by row then column; duplicate coordinates are summed.
        """
        # Bucket into rows.
        row_buckets: List[List[Tuple[int, float]]] = [[] for _ in range(shape[0])]
        for r, c, v in coords:
            if not (0 <= r < shape[0] and 0 <= c < shape[1]):
                raise ValueError(f"Coordinate ({r}, {c}) out of bounds {shape}")
            row_buckets[r].append((c, float(v)))
        data: List[float] = []
        indices: List[int] = []
        indptr: List[int] = [0]
        for bucket in row_buckets:
            bucket.sort()  # sort by column index
            # Merge duplicates.
            merged: List[Tuple[int, float]] = []
            for c, v in bucket:
                if merged and merged[-1][0] == c:
                    merged[-1] = (c, merged[-1][1] + v)
                else:
                    merged.append((c, v))
            for c, v in merged:
                data.append(v)
                indices.append(c)
            indptr.append(len(data))
        return cls(data, indices, indptr, shape)

    # ------------------------------------------------------------------
    # Properties / info
    # ------------------------------------------------------------------
    @property
    def nnz(self) -> int:
        """Number of stored (non-zero) entries."""
        return len(self.data)

    @property
    def density(self) -> float:
        """Fraction of non-zero entries (nnz / total)."""
        total = self.rows * self.cols
        return self.nnz / total if total else 0.0

    def shape_tuple(self) -> Tuple[int, int]:
        return (self.rows, self.cols)

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------
    def matvec(self, x: Sequence[float]) -> List[float]:
        """Sparse matrix-vector product ``y = A @ x``."""
        if len(x) != self.cols:
            raise ValueError(f"matvec: vector length {len(x)} != cols {self.cols}")
        y = [0.0] * self.rows
        for i in range(self.rows):
            s = 0.0
            for idx in range(self.indptr[i], self.indptr[i + 1]):
                s += self.data[idx] * x[self.indices[idx]]
            y[i] = s
        return y

    def matmul(self, other: "CSRMatrix") -> "CSRMatrix":
        """Sparse matrix-matrix product ``C = A @ B`` (CSR * CSR -> CSR)."""
        if self.cols != other.rows:
            raise ValueError(
                f"matmul shape mismatch: ({self.rows}x{self.cols}) @ ({other.rows}x{other.cols})"
            )
        # Accumulate into row-wise dictionaries.
        data: List[float] = []
        indices: List[int] = []
        indptr: List[int] = [0]
        for i in range(self.rows):
            acc: dict[int, float] = {}
            for a_idx in range(self.indptr[i], self.indptr[i + 1]):
                a_val = self.data[a_idx]
                col_a = self.indices[a_idx]
                # Multiply row of A by row `col_a` of B.
                for b_idx in range(other.indptr[col_a], other.indptr[col_a + 1]):
                    col_b = other.indices[b_idx]
                    acc[col_b] = acc.get(col_b, 0.0) + a_val * other.data[b_idx]
            for col in sorted(acc):
                data.append(acc[col])
                indices.append(col)
            indptr.append(len(data))
        return CSRMatrix(data, indices, indptr, (self.rows, other.cols))

    def transpose(self) -> "CSRMatrix":
        """Return the transpose as a CSR matrix."""
        coords: List[Tuple[int, int, float]] = []
        for i in range(self.rows):
            for idx in range(self.indptr[i], self.indptr[i + 1]):
                coords.append((self.indices[idx], i, self.data[idx]))
        return CSRMatrix.from_coo(coords, (self.cols, self.rows))

    def to_dense(self) -> Matrix:
        """Convert to a dense :class:`Matrix`."""
        dense = [[0.0] * self.cols for _ in range(self.rows)]
        for i in range(self.rows):
            for idx in range(self.indptr[i], self.indptr[i + 1]):
                dense[i][self.indices[idx]] = self.data[idx]
        return Matrix(dense)

    def get(self, i: int, j: int) -> float:
        """Get element ``(i, j)`` (O(nnz_per_row) lookup)."""
        if not (0 <= i < self.rows and 0 <= j < self.cols):
            raise IndexError(f"({i}, {j}) out of bounds {(self.rows, self.cols)}")
        for idx in range(self.indptr[i], self.indptr[i + 1]):
            if self.indices[idx] == j:
                return self.data[idx]
        return 0.0

    def __iter__(self) -> Iterator[Tuple[int, int, float]]:
        """Iterate over non-zero entries as ``(row, col, value)``."""
        for i in range(self.rows):
            for idx in range(self.indptr[i], self.indptr[i + 1]):
                yield (i, self.indices[idx], self.data[idx])

    def __repr__(self) -> str:
        return f"CSRMatrix(shape=({self.rows}, {self.cols}), nnz={self.nnz})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CSRMatrix):
            return NotImplemented
        return (
            self.rows == other.rows
            and self.cols == other.cols
            and self.data == other.data
            and self.indices == other.indices
            and self.indptr == other.indptr
        )