"""
Kernel functions for persistence diagrams.

Implements several **persistence kernels** — positive-definite kernel
functions on the space of persistence diagrams that enable kernel
methods (SVM, PCA, ridge regression) to operate directly on
topological features.

References
----------
- Reininghaus et al., "A Stable Multi-Scale Kernel for Topological
  Machine Learning" (CVPR 2015) — the persistence-scale-space kernel.
- Kusano, Hiraoka, "Persistence Weighted Gaussian Kernel for Topological
  Data Analysis" (ICML 2016) — the PWG kernel.
- Le, Yamada, "Persistence Fisher Kernel: A Riemannian Manifold Kernel
  for Persistence Diagrams" (NeurIPS 2018) — the Fisher kernel.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple

from .diagram import PersistenceDiagram, Infinity

Point = Tuple[float, float]


# ---------------------------------------------------------------------------
# Helper: convert diagram to finite points in (birth, persistence) space
# ---------------------------------------------------------------------------

def _to_persistence_coords(diag: PersistenceDiagram) -> List[Point]:
    """Convert (b, d) → (b, d−b) for finite features."""
    return [(p.birth, p.persistence) for p in diag.pairs
            if p.death != Infinity]


# ---------------------------------------------------------------------------
# Persistence Scale-Space Kernel (Reininghaus et al.)
# ---------------------------------------------------------------------------

def pss_kernel(
    d1: PersistenceDiagram,
    d2: PersistenceDiagram,
    sigma: float = 1.0,
) -> float:
    """Persistence Scale-Space (PSS) kernel between two diagrams.

    The PSS kernel places a Gaussian of bandwidth *sigma* at each
    finite point (b, d−b) of *d1* and at the reflection (b, b−d) below
    the diagonal, then integrates the product of the two resulting
    densities.

    Parameters
    ----------
    d1, d2 : PersistenceDiagram
        Diagrams (must have the same dimension).
    sigma : float
        Gaussian bandwidth (must be > 0).

    Returns
    -------
    float
        Kernel value ``K(d1, d2)``.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    pts1 = _to_persistence_coords(d1)
    pts2 = _to_persistence_coords(d2)

    if not pts1 or not pts2:
        return 0.0

    # Each point (b, p) has a mirror (b, −p) to enforce stability.
    # The kernel sums Gaussian-Gaussian interactions.
    two_sigma_sq = 2.0 * sigma * sigma
    total = 0.0
    for b1, p1 in pts1:
        for b2, p2 in pts2:
            # Same-point contribution (p1, p2).
            dist_sq = (b1 - b2) ** 2 + (p1 - p2) ** 2
            total += math.exp(-dist_sq / two_sigma_sq)
            # Cross contribution (p1, mirror of p2) = (b1, p1) vs (b2, -p2).
            dist_sq_mirror = (b1 - b2) ** 2 + (p1 + p2) ** 2
            total -= math.exp(-dist_sq_mirror / two_sigma_sq)
    # Normalise by (4 * pi * sigma).
    return total / (4.0 * math.pi * sigma)


# ---------------------------------------------------------------------------
# Persistence Weighted Gaussian Kernel (Kusano & Hiraoka)
# ---------------------------------------------------------------------------

def _default_weight(p: float, max_p: float) -> float:
    """Arctan weight function ``w(p) = atan(p / max_p * pi/2)``."""
    if max_p <= 0:
        return 1.0
    return math.atan(p / max_p * math.pi / 2.0)


def pwg_kernel(
    d1: PersistenceDiagram,
    d2: PersistenceDiagram,
    sigma: float = 1.0,
    weight_fn: Optional[Callable[[float], float]] = None,
) -> float:
    """Persistence Weighted Gaussian (PWG) kernel.

    ``K(D1, D2) = sum_{p in D1} sum_{q in D2} w(pers(p)) * w(pers(q))
                   * N(p, q; sigma)``

    where ``N`` is a Gaussian evaluated in persistence coordinates.

    Parameters
    ----------
    d1, d2 : PersistenceDiagram
    sigma : float
        Gaussian bandwidth.
    weight_fn : callable, optional
        Weight function ``w(persistence) -> float``.  Default: arctan
        weight scaled by the maximum persistence across both diagrams.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    pts1 = _to_persistence_coords(d1)
    pts2 = _to_persistence_coords(d2)

    if not pts1 or not pts2:
        return 0.0

    all_pers = [p for _, p in pts1 + pts2]
    max_p = max(all_pers) if all_pers else 1.0

    if weight_fn is None:
        wfn: Callable[[float], float] = lambda p: _default_weight(p, max_p)
    else:
        wfn = weight_fn

    two_sigma_sq = 2.0 * sigma * sigma
    total = 0.0
    for b1, p1 in pts1:
        w1 = wfn(p1)
        for b2, p2 in pts2:
            w2 = wfn(p2)
            dist_sq = (b1 - b2) ** 2 + (p1 - p2) ** 2
            total += w1 * w2 * math.exp(-dist_sq / two_sigma_sq)
    return total


# ---------------------------------------------------------------------------
# Persistence Fisher Kernel (Le & Yamada)
# ---------------------------------------------------------------------------

def fisher_kernel(
    d1: PersistenceDiagram,
    d2: PersistenceDiagram,
    sigma: float = 1.0,
    beta: float = 1.0,
) -> float:
    """Persistence Fisher kernel.

    Approximates the Fisher information metric by computing a Gaussian
    smoothed probability density for each diagram (in persistence
    coordinates) and then taking ``exp(-beta * Fisher distance)``.

    Parameters
    ----------
    d1, d2 : PersistenceDiagram
    sigma : float
        Gaussian bandwidth for density estimation.
    beta : float
        Scaling parameter for the Fisher distance.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    if beta <= 0:
        raise ValueError("beta must be positive")

    pts1 = _to_persistence_coords(d1)
    pts2 = _to_persistence_coords(d2)

    if not pts1 and not pts2:
        return 1.0  # identical empty diagrams
    if not pts1 or not pts2:
        return 0.0

    # Gaussian-smoothed density: p(x) = sum_i N(x; p_i, sigma^2)
    # Fisher distance: d_F^2 = sum_i (sqrt(p_i) - sqrt(q_i))^2 / (2*sigma^2)
    # Simplified: use Hellinger-like distance on the Gaussian mixtures
    # evaluated at the union of support points.
    all_pts = pts1 + pts2
    two_sigma_sq = 2.0 * sigma * sigma

    def density(pts: List[Point], x: Point) -> float:
        return sum(math.exp(-((x[0] - b) ** 2 + (x[1] - p) ** 2) / two_sigma_sq)
                   for b, p in pts) / max(1, len(pts))

    hellinger_sq = 0.0
    for x in all_pts:
        p_val = density(pts1, x)
        q_val = density(pts2, x)
        if p_val > 0 and q_val > 0:
            hellinger_sq += (math.sqrt(p_val) - math.sqrt(q_val)) ** 2
    hellinger_sq /= 2.0 * sigma * sigma
    return math.exp(-beta * hellinger_sq)


# ---------------------------------------------------------------------------
# Kernel matrix
# ---------------------------------------------------------------------------

def kernel_matrix(
    diagrams: List[PersistenceDiagram],
    kernel_fn: Callable[..., float],
    **kwargs,
) -> List[List[float]]:
    """Compute the *n × n* kernel matrix for a list of diagrams.

    Parameters
    ----------
    diagrams : list of PersistenceDiagram
    kernel_fn : callable
        Kernel function ``(d1, d2, **kwargs) -> float``.
    **kwargs
        Extra keyword arguments passed to *kernel_fn*.

    Returns
    -------
    list of list of float
        Symmetric ``n × n`` matrix.
    """
    n = len(diagrams)
    K = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            val = kernel_fn(diagrams[i], diagrams[j], **kwargs)
            K[i][j] = val
            K[j][i] = val
    return K