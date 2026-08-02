"""Statistical and dimensionality-reduction utilities.

Functions for computing covariance/correlation matrices, mean-centering,
standardization, and performing Principal Component Analysis (PCA) via
the truncated SVD implemented in :mod:`matrix_decomp.svd`.

Conventions
-----------

* Input **data** matrices are ``n_samples x n_features`` (rows are
  observations, columns are variables).  This matches the NumPy/SciPy
  convention.
* PCA returns ``principal_components`` as an ``n_features x k`` matrix
  whose columns are the top-``k`` directions, and ``explained_variance``
  as a length-``k`` list.

Example
-------

>>> from matrix_decomp import Matrix
>>> from matrix_decomp.stats import pca
>>> data = Matrix([[2.0, 0.0], [0.0, 2.0], [-2.0, 0.0], [0.0, -2.0]])
>>> comps, var, ratios = pca(data, k=2)
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .matrix import Matrix, _to_data
from .svd import svd, truncated_svd


def mean_center(data: Matrix) -> Tuple[Matrix, List[float]]:
    """Subtract the column means from each row.

    Returns ``(centered, means)``.
    """
    d = _to_data(data)
    n, m = len(d), len(d[0])
    means = [sum(d[i][j] for i in range(n)) / n for j in range(m)]
    centered = [[d[i][j] - means[j] for j in range(m)] for i in range(n)]
    return Matrix(centered), means


def standardize(data: Matrix) -> Tuple[Matrix, List[float], List[float]]:
    """Standardize columns to zero mean and unit variance.

    Returns ``(standardized, means, stds)``.
    """
    centered, means = mean_center(data)
    n = data.rows
    stds = [0.0] * data.cols
    for j in range(data.cols):
        var = sum(centered[i][j] ** 2 for i in range(n)) / max(n - 1, 1)
        stds[j] = math.sqrt(var) if var > 0 else 1.0  # guard zero-variance cols
    std_data = [[centered[i][j] / stds[j] for j in range(data.cols)] for i in range(n)]
    return Matrix(std_data), means, stds


def covariance_matrix(data: Matrix) -> Matrix:
    """Sample covariance matrix (``n_features x n_features``) using ``n-1``
    normalization.
    """
    centered, _ = mean_center(data)
    n = data.rows
    m = data.cols
    # cov = (1/(n-1)) * Xc^T Xc
    Xt = [[centered[i][j] for i in range(n)] for j in range(m)]  # m x n
    cov = [[0.0] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            s = sum(Xt[i][k] * Xt[j][k] for k in range(n))
            cov[i][j] = s / max(n - 1, 1)
    return Matrix(cov)


def correlation_matrix(data: Matrix) -> Matrix:
    """Pearson correlation matrix (symmetric, diagonal of ones)."""
    std_data, _, _ = standardize(data)
    n = data.rows
    m = data.cols
    # corr = (1/(n-1)) * Z^T Z
    Zt = [[std_data[i][j] for i in range(n)] for j in range(m)]
    corr = [[0.0] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            corr[i][j] = sum(Zt[i][k] * Zt[j][k] for k in range(n)) / max(n - 1, 1)
    return Matrix(corr)


def pca(data: Matrix, k: int | None = None, standardize_first: bool = True) -> Tuple[Matrix, List[float], List[float]]:
    """Principal Component Analysis via truncated SVD of the centered (and
    optionally standardized) data matrix.

    Parameters
    ----------
    data : Matrix
        ``n_samples x n_features``.
    k : int, optional
        Number of principal components to keep.  Defaults to all (``min(n, m)``).
    standardize_first : bool
        Whether to standardize columns before SVD (recommended when
        features have different scales).

    Returns
    -------
    (components, explained_variance, explained_variance_ratio)
        ``components`` is ``n_features x k`` (each column a direction),
        ``explained_variance`` is length ``k``, ``explained_variance_ratio``
        is length ``k`` and sums to ≤ 1.
    """
    work: Matrix
    if standardize_first:
        work, _, _ = standardize(data)
    else:
        work, _ = mean_center(data)
    n, m = work.rows, work.cols
    if k is None:
        k = min(n, m)
    if k <= 0:
        raise ValueError("k must be positive")
    # SVD of the centered data: X = U S Vt.
    # Principal components = rows of Vt (columns of V) = right singular vectors.
    Uk, Sk, Vtk = truncated_svd(work, k=k)
    # Explained variance: s_i^2 / (n - 1)
    explained_var = [Sk[i] ** 2 / max(n - 1, 1) for i in range(len(Sk))]
    total_var = sum(explained_var)
    # Total variance from ALL singular values (not just top-k) for ratio.
    _, Sall, _ = svd(work)
    total_var_all = sum(s * s for s in Sall) / max(n - 1, 1)
    ratios = [ev / total_var_all if total_var_all > 0 else 0.0 for ev in explained_var]
    # Components as columns: Vtk is k x m_features; transpose -> m_features x k
    comps = [[Vtk[i][j] for i in range(len(Sk))] for j in range(Vtk.cols)]
    return Matrix(comps), explained_var, ratios


def project(data: Matrix, components: Matrix) -> Matrix:
    """Project data onto the principal component subspace.

    ``data`` is ``n_samples x n_features``; ``components`` is
    ``n_features x k``; result is ``n_samples x k``.
    """
    if data.cols != components.rows:
        raise ValueError(
            f"project: data has {data.cols} features but components has {components.rows} rows"
        )
    # Center the data first using the stored means (assume data not pre-centered).
    centered, _ = mean_center(data)
    return centered @ components  # n_samples x k