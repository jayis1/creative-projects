# matrix-decomp

A from-scratch matrix decomposition & linear algebra library implemented in pure Python with **no third-party dependencies** (no NumPy, no SciPy). Every algorithm — LU, Cholesky, QR, SVD, eigenvalues, least-squares — is built on plain Python lists and floats.

## Features

### Matrix factorizations
- **LU decomposition** with partial pivoting (`PA = LU`), forward/back substitution, determinant, and matrix inverse
- **Cholesky decomposition** (`A = LLᵀ`) for symmetric positive-definite matrices, with SPD detection
- **QR decomposition** via Householder reflections (numerically stable), plus classical and modified Gram-Schmidt orthogonalization
- **Singular Value Decomposition** (`A = UΣVᵀ`) via eigen-decomposition of `AᵀA`, with Moore-Penrose pseudo-inverse, numerical rank, and condition number

### Eigenvalue algorithms
- **QR algorithm** (unshifted) for general square matrices — converges to Schur form
- **Jacobi eigenvalue algorithm** for symmetric matrices — returns eigenvalues and eigenvectors
- **Power iteration** for the dominant eigenvalue/eigenvector pair

### Solvers
- Linear system solve `Ax = b` (LU for square, QR for over-determined, pseudo-inverse for under-determined)
- **Least-squares** `min ‖Ax − b‖` via QR
- **Least-norm** `min ‖x‖ s.t. Ax = b` via pseudo-inverse
- Simple **linear regression** (slope, intercept, R²)

### Utilities
- `Matrix` class with pretty-printing, copy, equality (approximate and exact)
- Transpose, matmul, matvec, trace, Frobenius norm, element-wise add/scalar-multiply
- Input validation with descriptive error messages

## How it works

The library is organized into focused modules:

| Module | Contents |
|--------|----------|
| `matrix.py` | `Matrix` data structure, construction & utility helpers |
| `lu.py` | LU decomposition, forward/back substitution, solve, inverse, determinant |
| `cholesky.py` | Cholesky factorization, SPD check, Cholesky solve |
| `qr.py` | Householder QR, Gram-Schmidt (classical & modified), QR solve |
| `svd.py` | SVD, reconstruction, pseudo-inverse, rank, condition number |
| `eigen.py` | QR algorithm, Jacobi eigenvalues, power iteration, eigen decomposition |
| `least_squares.py` | Least-squares, least-norm, linear regression |
| `cli.py` | Command-line interface (lu/cholesky/qr/svd/eigen/det/inv/rank/solve) |

All algorithms operate on `Matrix` objects (thin wrappers around `list[list[float]]`) with row-major storage. Partial pivoting is used in LU for numerical stability. Householder reflections (not Gram-Schmidt) are used for the production QR path. SVD handles both tall and wide matrices by transposing as needed.

## Installation

```bash
cd matrix-decomp
pip install -e .
```

Or simply add the project root to `PYTHONPATH`:
```bash
PYTHONPATH=. python3 examples/demo.py
```

## Usage

### Python API

```python
from matrix_decomp import (
    Matrix, lu_solve, cholesky, qr_householder, svd,
    jacobi_eigen, least_squares, linear_fit, pseudo_inverse, rank,
)

# Solve a 2x2 system
A = Matrix([[4.0, 3.0], [6.0, 3.0]])
x = lu_solve(A, [10.0, 12.0])
print(x)  # [1.0, 2.0]

# Cholesky of an SPD matrix
L = cholesky(Matrix([[4.0, 2.0], [2.0, 3.0]]))
print(L.data)  # [[2.0, 0.0], [1.0, 1.414...]]

# QR decomposition
Q, R = qr_householder(Matrix([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]]))

# SVD
U, S, Vt = svd(Matrix([[3.0, 0.0], [0.0, 2.0]]))
print(S)  # [3.0, 2.0]

# Eigenvalues of a symmetric matrix
vals, V = jacobi_eigen(Matrix([[2.0, 1.0], [1.0, 2.0]]))
print(vals)  # [3.0, 1.0]

# Linear regression
slope, intercept, r2 = linear_fit([0, 1, 2, 3], [1, 3, 5, 7])
print(slope, intercept, r2)  # 2.0 1.0 1.0

# Pseudo-inverse and rank
Aplus = pseudo_inverse(Matrix([[1, 2, 3], [4, 5, 6]]))
r = rank(Matrix([[1, 2], [2, 4]]))  # 1
```

### CLI

```bash
# LU decomposition and solve
matrix-decomp lu "[[4,3],[6,3]]" --solve "[10,12]"

# Determinant
matrix-decomp det "[[6,1,1],[4,-2,5],[2,8,7]]"   # -306.0

# QR decomposition
matrix-decomp qr "[[12,-51,4],[6,167,-68],[-4,24,-41]]"

# SVD
matrix-decomp svd "[[1,2],[3,4],[5,6]]"

# Eigenvalues (with eigenvectors for symmetric matrices)
matrix-decomp eigen "[[2,1],[1,2]]" --vectors

# Matrix inverse
matrix-decomp inv "[[4,7],[2,6]]"

# Numerical rank
matrix-decomp rank "[[1,2],[2,4]]"   # 1
```

Matrices can be passed as JSON arrays (`"[[1,2],[3,4]]"`) or as semicolon/newline-separated rows with comma- or space-separated values.

## Running the tests

```bash
cd matrix-decomp
PYTHONPATH=. python3 -m pytest tests/ -v
```

## Examples

```bash
PYTHONPATH=. python3 examples/demo.py
```

## License

MIT