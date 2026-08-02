"""Core matrix data structure and utility helpers.

A :class:`Matrix` is a plain ``list`` of ``list`` rows of floats wrapped in a
thin convenience class so that we get nice ``repr``/``str`` output and a few
helpers without dragging in NumPy.  All numerical code in the package operates
on these ``Matrix`` objects (or, equivalently, on raw ``list[list[float]]``
values, since the wrapping is transparent).

Design choices
---------------
* Rows are stored as plain Python lists of floats.  No NumPy.
* ``Matrix`` is deliberately *mutable* so that in-place factorisations (LU,
  Cholesky, QR, ...) can overwrite the working storage efficiently, matching
  the LAPACK convention of returning results in packed form.
* Every public function validates shape compatibility and raises a
  :class:`ValueError` with a descriptive message on mismatch.
"""

from __future__ import annotations

from typing import List, Sequence

# A small tolerance used across the package for floating-point comparisons.
EPS: float = 1e-12


class Matrix:
    """A simple row-major matrix of floats.

    Parameters
    ----------
    data : sequence of sequences of numbers
        Row-major initializer.  Rows must all have the same length.
    """

    __slots__ = ("data", "rows", "cols")

    def __init__(self, data: Sequence[Sequence[float]]):
        if not data:
            raise ValueError("Matrix must have at least one row")
        n_cols = None
        for row in data:
            if n_cols is None:
                n_cols = len(row)
            elif len(row) != n_cols:
                raise ValueError("All matrix rows must have the same length")
            if n_cols == 0:
                raise ValueError("Matrix must have at least one column")
        # Store as plain floats.
        self.data: List[List[float]] = [[float(x) for x in row] for row in data]
        self.rows: int = len(data)
        self.cols: int = n_cols  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_rows(cls, rows: Sequence[Sequence[float]]) -> "Matrix":
        """Construct a matrix from row-major data (alias of the constructor)."""
        return cls(rows)

    @classmethod
    def zeros(cls, rows: int, cols: int) -> "Matrix":
        return cls([[0.0] * cols for _ in range(rows)])

    @classmethod
    def identity(cls, n: int) -> "Matrix":
        return cls([[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)])

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------
    def row(self, i: int) -> List[float]:
        return list(self.data[i])

    def col(self, j: int) -> List[float]:
        return [self.data[i][j] for i in range(self.rows)]

    def copy(self) -> "Matrix":
        return Matrix([row[:] for row in self.data])

    def __getitem__(self, idx):
        return self.data[idx]

    def __setitem__(self, idx, value):
        self.data[idx] = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Matrix):
            return NotImplemented
        if self.rows != other.rows or self.cols != other.cols:
            return False
        for i in range(self.rows):
            for j in range(self.cols):
                if abs(self.data[i][j] - other.data[i][j]) > EPS:
                    return False
        return True

    def approx_equal(self, other: "Matrix", tol: float = 1e-9) -> bool:
        """Element-wise approximate equality with a configurable tolerance."""
        if not isinstance(other, Matrix):
            return False
        if self.rows != other.rows or self.cols != other.cols:
            return False
        for i in range(self.rows):
            for j in range(self.cols):
                if abs(self.data[i][j] - other.data[i][j]) > tol:
                    return False
        return True

    def shape(self) -> tuple[int, int]:
        return (self.rows, self.cols)

    def __repr__(self) -> str:
        return f"Matrix({self.data!r})"

    def __str__(self) -> str:
        # Pretty-print with aligned columns.
        s = [[f"{v:.6g}" for v in row] for row in self.data]
        widths = [max(len(s[i][j]) for i in range(self.rows)) for j in range(self.cols)]
        lines = []
        for i in range(self.rows):
            lines.append("  ".join(s[i][j].rjust(widths[j]) for j in range(self.cols)))
        return "[\n " + "\n ".join(lines) + "\n]"


# ----------------------------------------------------------------------
# Free-function helpers (operate on either Matrix or list[list[float]])
# ----------------------------------------------------------------------
def zeros(rows: int, cols: int) -> Matrix:
    """Return a rows x cols matrix of zeros."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Matrix dimensions must be positive")
    return Matrix.zeros(rows, cols)


def identity(n: int) -> Matrix:
    """Return the n x n identity matrix."""
    if n <= 0:
        raise ValueError("Identity dimension must be positive")
    return Matrix.identity(n)


def _to_data(m) -> List[List[float]]:
    """Accept a Matrix or a list[list[float]] and return the raw row data."""
    if isinstance(m, Matrix):
        return m.data
    return [[float(x) for x in row] for row in m]


def transpose(m) -> Matrix:
    """Return the transpose of ``m``."""
    d = _to_data(m)
    rows = len(d)
    cols = len(d[0]) if rows else 0
    return Matrix([[d[i][j] for i in range(rows)] for j in range(cols)])


def matmul(a, b) -> Matrix:
    """Matrix multiply ``a @ b``."""
    da = _to_data(a)
    db = _to_data(b)
    a_rows, a_cols = len(da), len(da[0])
    b_rows, b_cols = len(db), len(db[0])
    if a_cols != b_rows:
        raise ValueError(
            f"matmul shape mismatch: ({a_rows}x{a_cols}) @ ({b_rows}x{b_cols})"
        )
    # Transpose b once for cache-friendly column access.
    bt = list(zip(*db))
    out = [[0.0] * b_cols for _ in range(a_rows)]
    for i in range(a_rows):
        ai = da[i]
        oi = out[i]
        for j in range(b_cols):
            bj = bt[j]
            s = 0.0
            for k in range(a_cols):
                s += ai[k] * bj[k]
            oi[j] = s
    return Matrix(out)


def matvec(a, v: Sequence[float]) -> List[float]:
    """Matrix-vector product ``A @ x`` returning a plain list."""
    da = _to_data(a)
    a_rows, a_cols = len(da), len(da[0])
    if len(v) != a_cols:
        raise ValueError("matvec: vector length must match matrix columns")
    return [sum(da[i][k] * v[k] for k in range(a_cols)) for i in range(a_rows)]


def copy_matrix(m) -> Matrix:
    """Return a deep copy of ``m``."""
    if isinstance(m, Matrix):
        return m.copy()
    return Matrix([row[:] for row in m])


def is_square(m) -> bool:
    d = _to_data(m)
    return len(d) == len(d[0]) if d else False


def trace(m) -> float:
    """Trace (sum of the diagonal) of a square matrix."""
    d = _to_data(m)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("trace requires a square matrix")
    return sum(d[i][i] for i in range(n))


def frobenius_norm(m) -> float:
    """Frobenius norm ``sqrt(sum a_ij^2)``."""
    d = _to_data(m)
    s = 0.0
    for row in d:
        for v in row:
            s += v * v
    return s ** 0.5


def add(a, b) -> Matrix:
    """Element-wise matrix addition."""
    da = _to_data(a)
    db = _to_data(b)
    if len(da) != len(db) or len(da[0]) != len(db[0]):
        raise ValueError("add: shape mismatch")
    return Matrix([[da[i][j] + db[i][j] for j in range(len(da[0]))] for i in range(len(da))])


def scale(a, s: float) -> Matrix:
    """Scalar multiplication."""
    d = _to_data(a)
    return Matrix([[v * s for v in row] for row in d])