<div align="center">

# matrix-decomp

**A from-scratch matrix decomposition & linear algebra library in pure Python — no NumPy, no SciPy.**

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Tests: 177](https://img.shields.io/badge/Tests-177-green)](#running-the-tests)
[![No Dependencies](https://img.shields.io/badge/Dependencies-0-success)](#)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Iterative Solvers](#iterative-solvers)
  - [Sparse Matrices](#sparse-matrices)
  - [PCA & Statistics](#pca--statistics)
  - [File I/O](#file-io)
- [Architecture](#architecture)
- [Examples](#examples)
- [Running the Tests](#running-the-tests)
- [Configuration](#configuration)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## Overview

**matrix-decomp** is a comprehensive linear algebra library written entirely
in pure Python with **zero third-party dependencies**. Every algorithm — LU,
Cholesky, QR, SVD, eigenvalues, iterative solvers, PCA — is built from scratch
on plain Python lists and floats. The library is designed to be readable and
educational (algorithms match textbook notation) while remaining genuinely
useful for small-to-medium-scale numerical work.

## Features

### Matrix Factorizations
- **LU decomposition** with partial pivoting (`PA = LU`) and **complete pivoting** (`PAQ = LU`)
- **Cholesky decomposition** (`A = LLᵀ`) for symmetric positive-definite matrices, with SPD detection
- **QR decomposition** via Householder reflections, Givens rotations, and Gram-Schmidt (classical & modified)
- **Singular Value Decomposition** (`A = UΣVᵀ`) with Moore-Penrose pseudo-inverse, numerical rank, condition number, and **truncated SVD** (low-rank approximation)
- **Schur decomposition** (`A = QTQᵀ`) for symmetric matrices
- **Polar decomposition** (`A = QP`) via SVD
- **Spectral decomposition** for symmetric matrices

### Eigenvalue Algorithms
- **QR algorithm** with **Wilkinson shift** and deflation — cubic convergence for symmetric matrices
- **Jacobi eigenvalue algorithm** for symmetric matrices — returns eigenvalues and eigenvectors
- **Power iteration** for the dominant eigenvalue/eigenvector pair
- **Tridiagonalization** of symmetric matrices via Householder reflections

### Iterative Solvers
- **Jacobi** iteration
- **Gauss-Seidel** iteration
- **SOR** (Successive Over-Relaxation)
- **Conjugate Gradient** for SPD systems
- All return a `SolveResult` with convergence diagnostics (iterations, residual, history)

### Solvers
- Linear system solve `Ax = b` (LU for square, QR for over-determined, pseudo-inverse for under-determined)
- **Least-squares** `min ‖Ax − b‖` via QR
- **Least-norm** `min ‖x‖ s.t. Ax = b` via pseudo-inverse
- **Linear regression** (slope, intercept, R²)
- **Polynomial regression** via Vandermonde least-squares

### Sparse Matrices (CSR)
- `CSRMatrix` class with Compressed Sparse Row format
- Construction from dense or COO (coordinate) data
- Matrix-vector and matrix-matrix multiplication
- Transpose, element access, iteration over non-zeros
- Density and nnz tracking

### Statistics & PCA
- Mean-centering and standardization
- Sample covariance and Pearson correlation matrices
- **PCA** via truncated SVD with explained variance ratios
- Data projection onto principal components

### Matrix Utilities
- `Matrix` class with operator overloading (`@`, `+`, `-`, `*`, `/`, `**`, `.T`, unary `-`)
- `__iter__`, `__contains__`, `to_list`, `flatten`, `map`, `is_symmetric`
- Matrix norms: Frobenius, 1-norm, ∞-norm
- Matrix power via binary exponentiation
- Generators: `diag`, `hilbert`, `vandermonde`
- Input validation with descriptive error messages
- `SingularMatrixError` exception for numerical singularity

### File I/O
- CSV read/write (auto-detects comma, semicolon, or whitespace delimiters)
- JSON read/write (bare array or wrapped `{"matrix": [...]}` format)
- Matrix string parsing (JSON, semicolon/newline rows)

### CLI
- 22 subcommands: `lu`, `lu-cp`, `cholesky`, `qr`, `svd`, `eigen`, `det`, `inv`, `rank`, `solve`, `power`, `polyfit`, `cond`, `jacobi`, `gs`, `sor`, `cg`, `pca`, `cov`, `corr`, `schur`, `polar`, `convert`, `bench`
- File input via `--file` (CSV/JSON)
- Configurable solver methods, tolerances, and output formats
- `--verbose`/`--debug` logging flags

## Installation

```bash
cd matrix-decomp
pip install -e .
```

Or add the project root to your `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/matrix-decomp
```

**Requirements:** Python 3.10+. No third-party dependencies.

## Quick Start

```python
from matrix_decomp import Matrix, lu_solve, svd, jacobi_eigen

# Solve a 2×2 system
A = Matrix([[4.0, 3.0], [6.0, 3.0]])
x = lu_solve(A, [10.0, 12.0])
print(x)  # [1.0, 2.0]

# SVD
U, S, Vt = svd(Matrix([[3.0, 0.0], [0.0, 2.0]]))
print(S)  # [3.0, 2.0]

# Eigenvalues
vals, vecs = jacobi_eigen(Matrix([[2.0, 1.0], [1.0, 2.0]]))
print(vals)  # [3.0, 1.0]
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

# --- Solve a 2×2 system ---
A = Matrix([[4.0, 3.0], [6.0, 3.0]])
x = lu_solve(A, [10.0, 12.0])
print(x)  # [1.0, 2.0]

# --- Operator overloads ---
B = Matrix([[1.0, 2.0], [3.0, 4.0]])
C = B @ B        # matrix multiply
v = B @ [1, 0]   # matrix-vector
At = B.T         # transpose
P = B * 3        # scalar multiply
D = B ** 3       # matrix power (binary exponentiation)
E = B / 2        # scalar division

# --- Cholesky of an SPD matrix ---
L = cholesky(Matrix([[4.0, 2.0], [2.0, 3.0]]))
print(L.data)  # [[2.0, 0.0], [1.0, 1.414...]]

# --- QR decomposition (Householder, Givens, or Gram-Schmidt) ---
Q, R = qr_householder(Matrix([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]]))

# --- SVD and truncated SVD (low-rank approximation) ---
U, S, Vt = svd(Matrix([[3.0, 0.0], [0.0, 2.0]]))
print(S)  # [3.0, 2.0]
Uk, Sk, Vtk = truncated_svd(Matrix([[1,0,0],[0,2,0],[0,0,0.001]]), k=2)

# --- Eigenvalues ---
vals = qr_algorithm(Matrix([[4.0, 1.0], [1.0, 4.0]]))  # [5.0, 3.0]
vals, V = jacobi_eigen(Matrix([[2.0, 1.0], [1.0, 2.0]]))

# --- Linear & polynomial regression ---
slope, intercept, r2 = linear_fit([0, 1, 2, 3], [1, 3, 5, 7])
print(slope, intercept, r2)  # 2.0 1.0 1.0

coeffs = polynomial_fit([-2,-1,0,1,2], [-2,4,2,4,0], degree=2)
print(coeffs)  # [2.0, 3.0, -1.0]

# --- Pseudo-inverse and rank ---
Aplus = pseudo_inverse(Matrix([[1, 2, 3], [4, 5, 6]]))
r = rank(Matrix([[1, 2], [2, 4]]))  # 1

# --- Hilbert matrix (ill-conditioned test case) ---
H = hilbert(4)
```

### CLI

```bash
# LU decomposition and solve
matrix-decomp lu "[[4,3],[6,3]]" --solve "[10,12]"

# LU with complete pivoting
matrix-decomp lu-cp "[[0,1],[1,0]]"

# Determinant
matrix-decomp det "[[6,1,1],[4,-2,5],[2,8,7]]"   # -306.0

# QR decomposition (householder, givens, or mgs)
matrix-decomp qr "[[12,-51,4],[6,167,-68],[-4,24,-41]]"
matrix-decomp qr "[[1,2],[3,4]]" --method givens

# SVD (with optional truncation)
matrix-decomp svd "[[1,2],[3,4],[5,6]]"
matrix-decomp svd "[[1,0,0],[0,2,0],[0,0,3]]" --truncate 2

# Eigenvalues (with eigenvectors for symmetric matrices)
matrix-decomp eigen "[[2,1],[1,2]]" --vectors
matrix-decomp eigen "[[3,0],[0,1]]" --method power

# Matrix inverse, rank, condition number
matrix-decomp inv "[[4,7],[2,6]]"
matrix-decomp rank "[[1,2],[2,4]]"     # 1
matrix-decomp cond "[[1,0],[0,1e6]]"   # 1000000.0

# Solve A x = b (lu, qr, or cg method)
matrix-decomp solve "[[2,1],[1,3]]" "[5,10]" --method lu
matrix-decomp solve "[[4,1],[1,3]]" "[1,2]" --method cg

# Matrix power and polynomial fit
matrix-decomp power "[[1,1],[0,1]]" 3    # [[1,3],[0,1]]
matrix-decomp polyfit "[0,1,2,3]" "[1,3,5,7]" 1   # [1.0, 2.0]

# Iterative solvers
matrix-decomp jacobi "[[10,1],[1,10]]" "[11,11]"
matrix-decomp gs "[[10,1],[1,10]]" "[11,11]"
matrix-decomp sor "[[10,1],[1,10]]" "[11,11]" --omega 1.5
matrix-decomp cg "[[4,1],[1,3]]" "[1,2]"

# Statistics & PCA
matrix-decomp cov "[[1,2],[3,4],[5,6]]"
matrix-decomp corr "[[1,2],[3,5],[4,1],[2,3]]"
matrix-decomp pca "[[0,0],[1,0],[2,0],[3,0]]" --k 2

# Advanced decompositions
matrix-decomp schur "[[4,1],[1,4]]"
matrix-decomp polar "[[3,1],[1,2]]"

# File I/O: load from file, convert formats
matrix-decomp lu --file data.csv
matrix-decomp convert data.csv data.json

# Benchmark all decompositions
matrix-decomp bench 50 --seed 42
```

Matrices can be passed as JSON arrays (`"[[1,2],[3,4]]"`), semicolon/newline-separated rows with comma- or space-separated values, or loaded from CSV/JSON files via `--file PATH`.

### Iterative Solvers

```python
from matrix_decomp import Matrix
from matrix_decomp.iterative import jacobi_solve, gauss_seidel_solve, sor_solve, conjugate_gradient

A = Matrix([[10.0, -1.0, 2.0], [-1.0, 11.0, -1.0], [2.0, -1.0, 10.0]])
b = [12.0, -3.0, 7.0]

# Each returns a SolveResult with .x, .iterations, .residual, .converged, .history
result = conjugate_gradient(A, b, tol=1e-14)
print(result)  # SolveResult(method='cg', converged, iters=3, residual=2.86e-17)

# SOR with over-relaxation
result = sor_solve(A, b, omega=1.5, tol=1e-12)
print(f"SOR converged in {result.iterations} iterations")
```

### Sparse Matrices

```python
from matrix_decomp.sparse import CSRMatrix

# Build from dense (drops exact zeros)
A = CSRMatrix.from_dense([[0, 0, 1], [2, 0, 0], [0, 3, 0]])
print(f"nnz={A.nnz}, density={A.density:.2%}")

# Matrix-vector product
y = A.matvec([1, 1, 1])  # [1, 2, 3]

# Build from COO triples (duplicates are summed)
B = CSRMatrix.from_coo([(0, 1, 5.0), (1, 0, 3.0)], shape=(2, 2))

# Transpose, matmul, iterate
At = A.transpose()
C = A.matmul(A.transpose())
for i, j, v in A:
    print(f"A[{i},{j}] = {v}")
```

### PCA & Statistics

```python
from matrix_decomp import Matrix
from matrix_decomp.stats import pca, project, covariance_matrix

# Data: n_samples × n_features
data = Matrix([[2.5, 2.4], [0.5, 0.7], [2.2, 2.9], [1.9, 2.2], [3.1, 3.0]])

# PCA
components, explained_var, ratios = pca(data, k=2)
print("Explained variance ratio:", ratios)  # e.g., [0.96, 0.04]

# Project data onto principal components
proj = project(data, components)
```

### File I/O

```python
from matrix_decomp import Matrix
from matrix_decomp.file_io import save_csv, load_csv, save_json, load_json

M = Matrix([[1.0, 2.0], [3.0, 4.0]])

save_csv(M, "data.csv")       # write CSV
M2 = load_csv("data.csv")     # read CSV back

save_json(M, "data.json", wrapper=True)  # {"matrix": [[1,2],[3,4]], "shape": [2,2]}
M3 = load_json("data.json")   # read JSON back
```

## Architecture

```
matrix_decomp/
├── __init__.py          # Public API, re-exports all symbols
├── matrix.py            # Matrix class, operators, utilities, generators
├── lu.py                # LU decomposition (partial pivoting), solve, inverse, determinant
├── cholesky.py          # Cholesky factorization, SPD check, Cholesky solve
├── qr.py                # QR via Householder, Givens, Gram-Schmidt
├── svd.py               # SVD, reconstruction, pseudo-inverse, rank, condition number
├── eigen.py             # QR algorithm (Wilkinson shift), Jacobi, power iteration
├── least_squares.py     # Least-squares, least-norm, linear/polynomial regression
├── iterative.py         # Jacobi, Gauss-Seidel, SOR, Conjugate Gradient
├── sparse.py            # CSRMatrix (Compressed Sparse Row)
├── stats.py             # Covariance, correlation, PCA, projection
├── decompositions.py    # Schur, spectral, polar, LU with complete pivoting
├── file_io.py           # CSV/JSON matrix I/O, string parsing
├── cli.py               # 22-subcommand CLI interface
└── logging_config.py    # Structured logging configuration
```

All algorithms operate on `Matrix` objects (thin wrappers around `list[list[float]]`)
or `CSRMatrix` objects. Partial pivoting is used in LU for numerical stability.
Householder reflections (not Gram-Schmidt) are used for the production QR path.
The QR eigenvalue algorithm uses Wilkinson shifts and deflation for fast
convergence. SVD handles both tall and wide matrices by transposing as needed.

## Examples

The `examples/` directory contains runnable demonstrations:

| File | Description |
|------|-------------|
| `demo.py` | Basic LU, Cholesky, QR, SVD, eigenvalues, least-squares |
| `demo_iterative.py` | Jacobi, Gauss-Seidel, SOR, CG with convergence history |
| `demo_pca.py` | PCA on a 2-D dataset with ASCII visualization |
| `demo_sparse.py` | CSR matrix construction, matvec, matmul, transpose |
| `demo_decompositions.py` | Schur and polar decompositions with verification |

```bash
PYTHONPATH=. python3 examples/demo.py
PYTHONPATH=. python3 examples/demo_iterative.py
PYTHONPATH=. python3 examples/demo_pca.py
PYTHONPATH=. python3 examples/demo_sparse.py
PYTHONPATH=. python3 examples/demo_decompositions.py
```

### Demo Output (Iterative Solvers)

```
Direct (LU) solution: [1.0, -0.2, 0.6, 1.0]

Jacobi                     iters=  43  residual=6.71e-15  converged=yes  correct=True
Gauss-Seidel               iters=  16  residual=3.55e-15  converged=yes  correct=True
SOR (omega=1.5)            iters=  54  residual=8.88e-15  converged=yes  correct=True
Conjugate Gradient         iters=   4  residual=2.19e-16  converged=yes  correct=True

Convergence history (Jacobi vs CG, first 20 iterations):
  iter  0  Jacobi ######################################## 3.17e+01
           CG     ######                                   5.15e+00
  iter  1  Jacobi ##############                           1.14e+01
           CG     #                                        1.04e+00
  iter  2  Jacobi ######                                   4.99e+00
           CG                                              1.93e-01
  iter  3  Jacobi ##                                       2.03e+00
           CG                                              2.19e-16
```

## Running the Tests

```bash
cd matrix-decomp
python -m pytest tests/ -v          # all 177 tests
python -m pytest tests/test_iterative.py -v   # iterative solvers only
python -m pytest tests/test_sparse.py -v      # sparse matrices only
python -m pytest tests/test_stats.py -v      # PCA & statistics only
python -m pytest tests/test_cli.py -v         # CLI interface
```

## Configuration

A example configuration file is provided at `config.example.toml`. Copy it
to `config.toml` to customize default parameters for solvers, eigenvalue
algorithms, and output formatting. The logging level can also be set via
the `MATRIX_DECOMP_LOG` environment variable:

```bash
MATRIX_DECOMP_LOG=DEBUG python3 my_script.py
```

## Known Issues (Resolved)

### Bug 1: `rank()` used absolute tolerance (fixed)
The `rank()` function used a fixed absolute tolerance (`tol=1e-9`) to decide which
singular values are non-zero. For rank-deficient matrices with O(1) entries,
numerical roundoff in the Jacobi eigenvalue algorithm produces tiny singular
values (~1e-8) that exceed this absolute threshold, resulting in an incorrectly
inflated rank. **Fix:** The tolerance is now *relative* (`tol * max(singular_value)`),
making the rank test scale-invariant. The default tolerance was increased to `1e-6`.

### Bug 2: `condition_number()` used absolute zero-threshold (fixed)
The `condition_number()` function used a fixed `1e-15` threshold to identify
zero singular values. For rank-deficient matrices with only one non-zero
singular value, the function returned 1.0 instead of `inf`. **Fix:** The
threshold is now relative (`1e-12 * s_max`), with an explicit check for zero
singular values before computing the ratio.

### Bug 3: QR algorithm crashed on complex eigenvalues (fixed)
The Wilkinson shift formula computed `sqrt(tr²/4 - det)` which produces a
complex number when the trailing 2×2 block has complex eigenvalues (e.g.,
a rotation matrix `[[0,-1],[1,0]]`). **Fix:** The discriminant is checked for
negativity; when negative, the shift falls back to the real part (`tr/2`).

### Bug 4: Polar decomposition sign error (fixed)
`polar_decomposition` computed `Q = U @ V` instead of `Q = U @ V^T`, producing
an incorrect orthogonal factor. **Fix:** Corrected to `Q = matmul(U, Vt)`
since `Vt = V^T` is what the SVD returns.

## Roadmap

- [ ] **GMRES** — Generalized Minimum RESidual for non-symmetric systems
- [ ] **BiCGStab** — Biconjugate Gradient Stabilized
- [ ] **Lanczos iteration** — for large symmetric eigenvalue problems
- [ ] **Blocked matrix operations** — cache-blocked matmul for large matrices
- [ ] **Matrix market I/O** — read/write Matrix Market exchange format
- [ ] **Eigenvalue eigenvectors for non-symmetric matrices** — via inverse iteration
- [ ] **Sparse Cholesky** — for large SPD sparse systems
- [ ] **GPU acceleration** — optional backend via `__array_interface__`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding new algorithms,
running tests, and code style. The main principles:

- **No third-party dependencies** — pure Python only
- **Readable, educational code** — match textbook notation
- **Comprehensive tests** — every feature needs tests
- **Type hints** — all public functions should be annotated

## Changelog

### v3.0.0 — Comprehensive Improvement
- **New module: `iterative.py`** — Jacobi, Gauss-Seidel, SOR, Conjugate Gradient
  solvers with `SolveResult` diagnostics
- **New module: `sparse.py`** — `CSRMatrix` (Compressed Sparse Row) with
  matvec, matmul, transpose, COO construction
- **New module: `stats.py`** — covariance, correlation, PCA, data projection
- **New module: `decompositions.py`** — Schur, spectral, polar decompositions,
  LU with complete pivoting
- **New module: `file_io.py`** — CSV/JSON matrix I/O, string parsing
- **New module: `logging_config.py`** — structured logging with env var control
- **Enhanced `Matrix` class** — `**` (power), `/` (scalar division), `__iter__`,
  `__contains__`, `to_list`, `flatten`, `map`, `is_symmetric`
- **Expanded CLI** — 22 subcommands (was 11), `--file` input, `--verbose`/`--debug`
  logging, solver method selection
- **104 new tests** (177 total, was 73)
- **GitHub Actions CI** — tests on Python 3.10–3.13
- **4 new example scripts** — iterative, PCA, sparse, decompositions
- **CONTRIBUTING.md**, **LICENSE**, **config.example.toml**
- **Bug fix:** polar decomposition sign error (Q = U@V → Q = U@Vt)

### v2.0.0 — Enhanced
- Operator overloading (`@`, `+`, `-`, `*`, `.T`, norms)
- Wilkinson-shift QR algorithm with deflation
- Givens-rotation QR, symmetric tridiagonalization
- Truncated SVD, matrix power, polynomial regression
- Hilbert/Vandermonde generators
- 18 new tests (54 → 73 total)

### v1.0.0 — Initial Release
- LU, Cholesky, QR, SVD, eigenvalues, least-squares
- 36 tests

## License

[MIT](LICENSE)