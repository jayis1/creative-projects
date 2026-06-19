"""NumPy-accelerated O(N²) N-body force evaluator.

This module provides a vectorized implementation of the brute-force
pairwise acceleration calculation using NumPy arrays, which is typically
100–500× faster than the pure-Python :func:`nbody.brute_force.brute_force_accelerations`
for N > ~100.

The module also provides a ``numpy_energy`` function that computes the
total kinetic + softened potential energy using vectorized operations.
"""

from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np

from .body import Body


def numpy_accelerations(
    bodies: List[Body],
    G: float = 1.0,
    softening: float = 0.0,
) -> List[Tuple[float, float]]:
    """Vectorized O(N²) pairwise accelerations — returns a list of (ax, ay).

    Uses NumPy broadcasting for the pairwise computation. Results are
    identical (up to floating-point rounding) to the pure-Python
    :func:`nbody.brute_force.brute_force_accelerations`.
    """
    n = len(bodies)
    if n == 0:
        return []
    if n == 1:
        return [(0.0, 0.0)]

    pos = np.array([(b.x, b.y) for b in bodies], dtype=np.float64)  # (N, 2)
    mass = np.array([b.m for b in bodies], dtype=np.float64)  # (N,)
    soft_sq = softening * softening

    # Pairwise displacement: pos[j] - pos[i] → shape (N, N, 2)
    dpos = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]  # (N, N, 2)
    # Squared distances with softening: (N, N)
    r_sq = dpos[:, :, 0] ** 2 + dpos[:, :, 1] ** 2 + soft_sq  # (N, N)
    # Avoid division by zero and self-interaction.
    np.fill_diagonal(r_sq, 1.0)  # diagonal will be multiplied by zero mass later
    # inv_r3 = 1 / r^3
    inv_r3 = r_sq ** (-1.5)  # (N, N)
    # Zero out self-interactions.
    np.fill_diagonal(inv_r3, 0.0)
    # Acceleration: a_i = sum_j G * m_j * (r_j - r_i) / |r|^3
    # Shape: (N, N, 2) * (N, N) broadcast → sum over j (axis=1)
    m_j = mass[np.newaxis, :]  # (1, N)
    # Force coefficient: G * m_j / r^3 → (N, N)
    coeff = G * m_j * inv_r3  # (N, N)
    acc = (coeff[:, :, np.newaxis] * dpos).sum(axis=1)  # (N, 2)
    return [(float(acc[i, 0]), float(acc[i, 1])) for i in range(n)]


def numpy_energy(
    bodies: List[Body],
    G: float = 1.0,
    softening: float = 0.0,
) -> float:
    """Vectorized total energy (kinetic + softened potential)."""
    n = len(bodies)
    if n == 0:
        return 0.0
    pos = np.array([(b.x, b.y) for b in bodies], dtype=np.float64)  # (N, 2)
    vel = np.array([(b.vx, b.vy) for b in bodies], dtype=np.float64)  # (N, 2)
    mass = np.array([b.m for b in bodies], dtype=np.float64)  # (N,)
    soft_sq = softening * softening

    # Kinetic energy: 0.5 * sum(m_i * |v_i|^2)
    ke = 0.5 * np.sum(mass * (vel[:, 0] ** 2 + vel[:, 1] ** 2))

    # Potential energy: -G * sum_{i<j} m_i * m_j / sqrt(r_ij^2 + eps^2)
    # Use broadcasting: pairwise displacements (N, N, 2)
    dpos = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]
    r_sq = dpos[:, :, 0] ** 2 + dpos[:, :, 1] ** 2 + soft_sq  # (N, N)
    # Only upper triangle (i < j)
    triu_mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    inv_r = 1.0 / np.sqrt(r_sq)
    # m_i * m_j matrix
    m_ij = mass[:, np.newaxis] * mass[np.newaxis, :]
    pe = -G * np.sum(m_ij[triu_mask] * inv_r[triu_mask])
    return float(ke + pe)


def numpy_momentum(bodies: List[Body]) -> Tuple[float, float]:
    """Total linear momentum P = sum(m_i * v_i)."""
    if not bodies:
        return (0.0, 0.0)
    px = sum(b.m * b.vx for b in bodies)
    py = sum(b.m * b.vy for b in bodies)
    return (px, py)


__all__ = ["numpy_accelerations", "numpy_energy", "numpy_momentum"]