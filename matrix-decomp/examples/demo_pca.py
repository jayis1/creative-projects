#!/usr/bin/env python3
"""Example: Principal Component Analysis (PCA) on a 2-D dataset.

Shows mean-centering, standardization, PCA decomposition, and projection
onto the principal components.
"""

from matrix_decomp import Matrix
from matrix_decomp.stats import pca, project, mean_center, covariance_matrix


def main() -> None:
    # A simple 2-D dataset with correlation between features.
    data = Matrix([
        [2.5, 2.4],
        [0.5, 0.7],
        [2.2, 2.9],
        [1.9, 2.2],
        [3.1, 3.0],
        [2.3, 2.7],
        [2.0, 1.6],
        [1.0, 1.1],
        [1.5, 1.6],
        [1.1, 0.9],
    ])

    print(f"Data shape: {data.shape()}  (n_samples x n_features)")

    # Center the data.
    centered, means = mean_center(data)
    print(f"Column means: {[round(m, 4) for m in means]}")

    # Covariance matrix.
    cov = covariance_matrix(data)
    print("\nCovariance matrix:")
    print(cov)

    # PCA with k=2 components.
    comps, var, ratios = pca(data, k=2)
    print("\nPrincipal components (columns):")
    print(comps)
    print(f"\nExplained variance:     {[round(v, 6) for v in var]}")
    print(f"Explained variance ratio: {[round(r, 6) for r in ratios]}")

    # Project data onto top-1 component.
    proj = project(data, Matrix([[comps[i][0]] for i in range(comps.rows)]))
    print(f"\nProjection onto PC1 (shape {proj.shape()}):")
    for i in range(proj.rows):
        print(f"  sample {i}: {proj[i][0]:.6f}")

    # ASCII scatter of the projection.
    print("\n  PC1 projection (ASCII):")
    vals = [proj[i][0] for i in range(proj.rows)]
    vmin, vmax = min(vals), max(vals)
    span = vmax - vmin if vmax != vmin else 1.0
    for i in range(proj.rows):
        pos = int(50 * (vals[i] - vmin) / span)
        print(f"  {' ' * pos}#")


if __name__ == "__main__":
    main()