"""Tests for the stats / PCA module."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import Matrix
from matrix_decomp.stats import (
    mean_center,
    standardize,
    covariance_matrix,
    correlation_matrix,
    pca,
    project,
)


def _approx(a, b, tol=1e-7):
    return abs(a - b) < tol


def _vec_approx(a, b, tol=1e-6):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def _mat_approx(A, B, tol=1e-6):
    return all(_approx(A[i][j], B[i][j], tol) for i in range(len(A)) for j in range(len(A[0])))


def test_mean_center():
    data = Matrix([[1.0, 3.0], [3.0, 1.0]])
    centered, means = mean_center(data)
    assert _vec_approx(means, [2.0, 2.0])
    assert _mat_approx(centered.data, [[-1.0, 1.0], [1.0, -1.0]])


def test_standardize():
    data = Matrix([[0.0], [2.0], [4.0]])
    std_data, means, stds = standardize(data)
    assert _approx(means[0], 2.0)
    # var = ((0-2)^2 + (2-2)^2 + (4-2)^2) / 2 = 4; std = 2
    assert _approx(stds[0], 2.0)
    # Standardized: [-1, 0, 1]
    assert _vec_approx(std_data.flatten(), [-1.0, 0.0, 1.0])


def test_covariance_matrix():
    data = Matrix([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    cov = covariance_matrix(data)
    # Column means = [3, 4]; centered = [[-2,-2],[0,0],[2,2]]
    # cov[0][0] = (4+0+4)/2 = 4; cov[1][1] = (4+0+4)/2 = 4; cov[0][1] = (4+0+4)/2 = 4
    assert _approx(cov[0][0], 4.0)
    assert _approx(cov[1][1], 4.0)
    assert _approx(cov[0][1], 4.0)
    assert _approx(cov[1][0], 4.0)


def test_correlation_matrix_diagonal_ones():
    data = Matrix([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]])
    corr = correlation_matrix(data)
    for i in range(3):
        assert _approx(corr[i][i], 1.0)


def test_correlation_matrix_symmetric():
    data = Matrix([[1.0, 2.0], [3.0, 5.0], [4.0, 1.0], [2.0, 3.0]])
    corr = correlation_matrix(data)
    assert _approx(corr[0][1], corr[1][0])


def test_pca_orthonormal_components():
    # Data along a line: should yield 1 significant component
    data = Matrix([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    comps, var, ratios = pca(data, k=2)
    # Components should be orthonormal (Q^T Q = I)
    QtQ = comps.T @ comps
    for i in range(2):
        for j in range(2):
            if i == j:
                assert _approx(QtQ[i][j], 1.0, tol=1e-5)
            else:
                assert _approx(QtQ[i][j], 0.0, tol=1e-5)


def test_pca_explained_variance_ratio():
    # Data with clear dominant direction
    data = Matrix([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    comps, var, ratios = pca(data, k=2, standardize_first=False)
    # All variance along axis 1; first PC captures everything
    assert ratios[0] > 0.99


def test_pca_k_default():
    data = Matrix([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    comps, var, ratios = pca(data)
    assert comps.shape()[1] == 2  # min(3, 2) = 2


def test_pca_invalid_k():
    try:
        pca(Matrix([[1.0, 2.0]]), k=0)
        assert False
    except ValueError:
        pass


def test_project_dimensions():
    data = Matrix([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    comps, var, ratios = pca(data, k=1)
    proj = project(data, comps)
    assert proj.rows == 3
    assert proj.cols == 1


def test_project_mismatch():
    data = Matrix([[1.0, 2.0], [3.0, 4.0]])
    comps = Matrix([[1.0], [0.0], [0.0]])  # 3 rows but data has 2 cols
    try:
        project(data, comps)
        assert False
    except ValueError:
        pass


def test_standardize_zero_variance_column():
    data = Matrix([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]])
    std_data, means, stds = standardize(data)
    # Second column has zero variance; std should be 1.0 (guard)
    assert _approx(stds[1], 1.0)
    # Second column standardized values should be 0 (mean-centered)
    for i in range(3):
        assert _approx(std_data[i][1], 0.0)