"""matrix_decomp: a from-scratch matrix decomposition & linear algebra library.

Pure-Python implementations of the core matrix factorizations and linear
algebra algorithms found in numerical libraries like LAPACK and NumPy's
``numpy.linalg``:

* LU decomposition (with partial pivoting) and linear system solve
* LU with complete pivoting (``PAQ = LU``)
* Gaussian elimination & matrix inverse via LU
* Cholesky decomposition (LL^T) for symmetric positive-definite matrices
* QR decomposition via Householder reflections
* Gram-Schmidt (classical & modified) orthogonalization
* Givens-rotation QR
* Eigenvalue / eigenvector computation via the unshifted & shifted QR algorithm
* Singular Value Decomposition (SVD) via eigen-decomposition of A^T A
* Schur, spectral, and polar decompositions
* Least-squares and least-norm solvers, Moore-Penrose pseudo-inverse
* Determinant, rank, condition number, trace, Frobenius norm
* Iterative solvers: Jacobi, Gauss-Seidel, SOR, Conjugate Gradient
* Sparse (CSR) matrix representation and operations
* Statistical utilities: covariance, correlation, PCA
* Matrix file I/O (CSV / JSON)
* Matrix utilities (transpose, multiply, identity, copy, power)

No third-party dependencies -- everything is built on plain Python lists.
The package is organised as a small number of focused modules so that each
algorithm is easy to read, test and reason about in isolation.
"""

from .matrix import (
    Matrix,
    zeros,
    identity,
    transpose,
    matmul,
    matvec,
    copy_matrix,
    is_square,
    trace,
    frobenius_norm,
    add,
    scale,
    diag,
    diagonal,
    matrix_power,
    hilbert,
    vandermonde,
)
from .lu import (
    lu_decompose,
    lu_solve,
    lu_inverse,
    determinant,
    forward_sub,
    back_sub,
    SingularMatrixError,
)
from .cholesky import (
    cholesky,
    cholesky_solve,
    is_symmetric,
    is_spd,
)
from .qr import (
    qr_householder,
    qr_solve,
    qr_givens,
    classical_gram_schmidt,
    modified_gram_schmidt,
)
from .svd import (
    svd,
    svd_reconstruct,
    pseudo_inverse,
    rank,
    condition_number,
    truncated_svd,
)
from .eigen import (
    qr_algorithm,
    eigen_decomposition,
    jacobi_eigen,
    power_iteration,
    tridiagonalize,
)
from .least_squares import (
    least_squares,
    least_norm,
    linear_fit,
    polynomial_fit,
    residual_norm,
)
from .iterative import (
    jacobi_solve,
    gauss_seidel_solve,
    sor_solve,
    conjugate_gradient,
    SolveResult,
)
from .sparse import CSRMatrix
from .stats import (
    mean_center,
    standardize,
    covariance_matrix,
    correlation_matrix,
    pca,
    project,
)
from .decompositions import (
    spectral_decomposition,
    schur_decomposition,
    polar_decomposition,
    lu_complete_pivot,
)
from .file_io import (
    save_csv,
    load_csv,
    save_json,
    load_json,
    parse_matrix_string,
)

__version__ = "3.0.0"

__all__ = [
    # matrix
    "Matrix",
    "zeros",
    "identity",
    "transpose",
    "matmul",
    "matvec",
    "copy_matrix",
    "is_square",
    "trace",
    "frobenius_norm",
    "add",
    "scale",
    "diag",
    "diagonal",
    "matrix_power",
    "hilbert",
    "vandermonde",
    # lu
    "lu_decompose",
    "lu_solve",
    "lu_inverse",
    "determinant",
    "forward_sub",
    "back_sub",
    "SingularMatrixError",
    # cholesky
    "cholesky",
    "cholesky_solve",
    "is_symmetric",
    "is_spd",
    # qr
    "qr_householder",
    "qr_solve",
    "qr_givens",
    "classical_gram_schmidt",
    "modified_gram_schmidt",
    # svd
    "svd",
    "svd_reconstruct",
    "pseudo_inverse",
    "rank",
    "condition_number",
    "truncated_svd",
    # eigen
    "qr_algorithm",
    "eigen_decomposition",
    "jacobi_eigen",
    "power_iteration",
    "tridiagonalize",
    # least squares
    "least_squares",
    "least_norm",
    "linear_fit",
    "polynomial_fit",
    "residual_norm",
    # iterative
    "jacobi_solve",
    "gauss_seidel_solve",
    "sor_solve",
    "conjugate_gradient",
    "SolveResult",
    # sparse
    "CSRMatrix",
    # stats
    "mean_center",
    "standardize",
    "covariance_matrix",
    "correlation_matrix",
    "pca",
    "project",
    # decompositions
    "spectral_decomposition",
    "schur_decomposition",
    "polar_decomposition",
    "lu_complete_pivot",
    # file_io
    "save_csv",
    "load_csv",
    "save_json",
    "load_json",
    "parse_matrix_string",
]