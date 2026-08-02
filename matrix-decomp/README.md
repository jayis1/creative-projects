# matrix-decomp

A from-scratch matrix decomposition & linear algebra library implemented in pure Python with **no third-party dependencies** (no NumPy, no SciPy). Every algorithm — LU, Cholesky, QR, SVD, eigenvalues, least-squares — is built on plain Python lists and floats.

## Features

### Matrix factorizations
- **LU decomposition** with partial pivoting (`PA = LU`), forward/back substitution, determinant, and matrix inverse
- **Cholesky decomposition** (`A = LLᵀ`) for symmetric positive-definite matrices, with SPD detection
- **QR decomposition** via Householder reflections (numerically stable), Givens rotations, plus classical and modified Gram-Schmidt orthogonalization
- **Singular Value Decomposition** (`A = UΣVᵀ`) via eigen-decomposition of `AᵀA`, with Moore-Penrose pseudo-inverse, numerical rank, condition number, and **truncated SVD** (low-rank approximation / PCA)

### Eigenvalue algorithms
- **QR algorithm** with **Wilkinson shift** and deflation — cubic convergence for symmetric matrices
- **Jacobi eigenvalue algorithm** for symmetric matrices — returns eigenvalues and eigenvectors
- **Power iteration** for the dominant eigenvalue/eigenvector pair
- **Tridiagonalization** of symmetric matrices via Householder reflections

### Solvers
- Linear system solve `Ax = b` (LU for square, QR for over-determined, pseudo-inverse for under-determined)
- **Least-squares** `min ‖Ax − b‖` via QR, with residual norm computation
- **Least-norm** `min ‖x‖ s.t. Ax = b` via pseudo-inverse
- Simple **linear regression** (slope, intercept, R²)
- **Polynomial regression** via Vandermonde least-squares

### Matrix utilities
- `Matrix` class with operator overloading (`@` for matmul/matvec, `+`, `-`, `*` scalar, unary `-`, `.T` transpose), pretty-printing, copy, equality (approximate and exact), `len()`
- Matrix norms: Frobenius, 1-norm (max column sum), ∞-norm (max row sum)
- Transpose, matmul, matvec, trace, Frobenius norm, element-wise add/sub/scalar-multiply
- **Matrix power** via binary exponentiation
- **Generators**: `diag`, `diagonal`, `hilbert`, `vandermonde`
- Input validation with descriptive error messages
- `SingularMatrixError` exception for numerical singularity detection

## How it works

The library is organized into focused modules:

| Module | Contents |
|--------|----------|
| `matrix.py` | `Matrix` data structure, construction, operators, utilities & generators |
| `lu.py` | LU decomposition, forward/back substitution, solve, inverse, determinant |
| `cholesky.py` | Cholesky factorization, SPD check, Cholesky solve |
| `qr.py` | Householder QR, Givens QR, Gram-Schmidt (classical & modified), QR solve |
| `svd.py` | SVD, reconstruction, pseudo-inverse, rank, condition number, truncated SVD |
| `eigen.py` | QR algorithm (Wilkinson shift), Jacobi eigenvalues, power iteration, tridiagonalization, eigen decomposition |
| `least_squares.py` | Least-squares, least-norm, linear regression, polynomial regression, residual norm |
| `cli.py` | Command-line interface (lu/cholesky/qr/svd/eigen/det/inv/rank/solve/power/polyfit/cond) |

All algorithms operate on `Matrix` objects (thin wrappers around `list[list[float]]`) with row-major storage. Partial pivoting is used in LU for numerical stability. Householder reflections (not Gram-Schmidt) are used for the production QR path. The QR eigenvalue algorithm uses Wilkinson shifts and deflation for fast convergence. SVD handles both tall and wide matrices by transposing as needed.

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
    matrix_power, hilbert, vandermonde, polynomial_fit, truncated_svd,
    tridiagonalize, qr_algorithm,
)

# Solve a 2x2 system
A = Matrix([[4.0, 3.0], [6.0, 3.0]])
x = lu_solve(A, [10.0, 12.0])
print(x)  # [1.0, 2.0]

# Operator overloads
B = Matrix([[1.0, 2.0], [3.0, 4.0]])
C = B @ B        # matrix multiply
v = B @ [1, 0]   # matrix-vector
At = B.T         # transpose
P = B * 3        # scalar multiply

# Matrix power
print(matrix_power(Matrix([[1,1],[0,1]]), 5))  # [[1,5],[0,1]]

# Cholesky of an SPD matrix
L = cholesky(Matrix([[4.0, 2.0], [2.0, 3.0]]))
print(L.data)  # [[2.0, 0.0], [1.0, 1.414...]]

# QR decomposition (Householder or Givens)
Q, R = qr_householder(Matrix([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]]))

# SVD and truncated SVD (low-rank approximation)
U, S, Vt = svd(Matrix([[3.0, 0.0], [0.0, 2.0]]))
print(S)  # [3.0, 2.0]
Uk, Sk, Vtk = truncated_svd(Matrix([[1,0,0],[0,2,0],[0,0,0.001]]), k=2)

# Eigenvalues — QR algorithm (shifted) or Jacobi (symmetric, with vectors)
vals = qr_algorithm(Matrix([[4.0, 1.0], [1.0, 4.0]]))  # [5.0, 3.0]
vals, V = jacobi_eigen(Matrix([[2.0, 1.0], [1.0, 2.0]]))

# Tridiagonalize a symmetric matrix
T = tridiagonalize(Matrix([[4,1,2],[1,5,3],[2,3,6]]))

# Linear regression
slope, intercept, r2 = linear_fit([0, 1, 2, 3], [1, 3, 5, 7])
print(slope, intercept, r2)  # 2.0 1.0 1.0

# Polynomial regression: y = 2 + 3x - x^2
coeffs = polynomial_fit([-2,-1,0,1,2], [-2,4,2,4,0], degree=2)
print(coeffs)  # [2.0, 3.0, -1.0]

# Pseudo-inverse and rank
Aplus = pseudo_inverse(Matrix([[1, 2, 3], [4, 5, 6]]))
r = rank(Matrix([[1, 2], [2, 4]]))  # 1

# Hilbert matrix (ill-conditioned test case)
H = hilbert(4)
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

# Matrix power
matrix-decomp power "[[1,1],[0,1]]" 3   # [[1,3],[0,1]]

# Polynomial fit
matrix-decomp polyfit "[0,1,2,3]" "[1,3,5,7]" 1   # [1.0, 2.0]

# Condition number
matrix-decomp cond "[[1,0],[0,1e6]]"   # 1000000.0
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

## Known Issues (Resolved)

### Bug 1: `rank()` used absolute tolerance (fixed)
The `rank()` function used a fixed absolute tolerance (`tol=1e-9`) to decide which singular values are non-zero. For rank-deficient matrices with O(1) entries, numerical roundoff in the Jacobi eigenvalue algorithm produces tiny singular values (~1e-8) that exceed this absolute threshold, resulting in an incorrectly inflated rank. **Fix:** The tolerance is now *relative* (`tol * max(singular_value)`), making the rank test scale-invariant. The default tolerance was also increased to `1e-6` to account for the Jacobi algorithm's accuracy limits for small eigenvalues.

### Bug 2: `condition_number()` used absolute zero-threshold (fixed)
The `condition_number()` function used a fixed `1e-15` threshold to identify zero singular values. This caused two problems: (a) for scaled matrices the threshold was too tight, and (b) for rank-deficient matrices with only one non-zero singular value, the function returned 1.0 instead of `inf` because `min()` picked up the sole non-zero value. **Fix:** The threshold is now relative (`1e-12 * s_max`), and the function explicitly checks whether *any* singular value is effectively zero before computing the ratio.

### Bug 3: QR algorithm crashed on complex eigenvalues (fixed)
The Wilkinson shift formula computed `sqrt(tr²/4 - det)` which produces a complex number in Python 3 when the trailing 2×2 block has complex eigenvalues (e.g., a rotation matrix `[[0,-1],[1,0]]`). The complex value then propagated through the computation, causing a `TypeError` when `float()` was called. **Fix:** The discriminant is now checked for negativity; when it's negative (indicating complex eigenvalues), the shift falls back to the real part (`tr/2`) instead of attempting the square root.

## License

MIT