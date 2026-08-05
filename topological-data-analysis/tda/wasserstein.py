"""
Wasserstein distance between persistence diagrams.

The p-th Wasserstein distance between two diagrams D1 and D2 is:

    W_p(D1, D2) = [ min_{matching M} sum_{(a,b) in M} d(a, b)^p ]^{1/p}

where the minimum is over all perfect matchings between the (diagonal-augmented)
diagrams, and d(a, b) is the L-infinity distance.

For p = infinity, this gives the bottleneck distance.

This module implements the Wasserstein distance via the Hungarian algorithm
(Kuhn-Munkres) applied to the augmented cost matrix.
"""

from __future__ import annotations

from typing import List, Tuple

from .diagram import PersistenceDiagram
from .distance import _l_inf

Infinity = float("inf")
Point = Tuple[float, float]


def wasserstein_distance(
    d1: PersistenceDiagram,
    d2: PersistenceDiagram,
    p: float = 2.0,
) -> float:
    """Compute the p-th Wasserstein distance between two persistence diagrams.

    Parameters
    ----------
    d1, d2 : PersistenceDiagram
        Diagrams to compare (must have the same dimension).
    p : float
        Wasserstein order (p >= 1). Use p=float('inf') for bottleneck.

    Returns
    -------
    float
        The p-Wasserstein distance.

    Raises
    ------
    ValueError
        If diagrams have different dimensions or p < 1.
    """
    if d1.dimension != d2.dimension:
        raise ValueError(
            f"Cannot compare diagrams of different dimensions "
            f"({d1.dimension} vs {d2.dimension})"
        )
    if p < 1 and p != Infinity:
        raise ValueError("Wasserstein order p must be >= 1")

    pts1 = d1.points()
    pts2 = d2.points()

    if not pts1 and not pts2:
        return 0.0

    # Augment with diagonal points.
    finite_deaths = [pt[1] for pt in pts1 + pts2 if pt[1] != Infinity]
    diag_val = (sum(finite_deaths) / len(finite_deaths)) if finite_deaths else 0.0

    n1, n2 = len(pts1), len(pts2)
    max_size = max(n1, n2)
    P1 = list(pts1) + [(diag_val, diag_val)] * (max_size - n1)
    P2 = list(pts2) + [(diag_val, diag_val)] * (max_size - n2)

    # Build cost matrix.
    if p == Infinity:
        cost = [[_l_inf(P1[i], P2[j]) for j in range(max_size)]
                for i in range(max_size)]
    else:
        cost = [[_l_inf(P1[i], P2[j]) ** p for j in range(max_size)]
                for i in range(max_size)]

    # Solve assignment problem via Hungarian algorithm.
    total_cost = _hungarian(cost)

    if p == Infinity:
        return total_cost
    return total_cost ** (1.0 / p)


def _hungarian(cost: List[List[float]]) -> float:
    """Solve the assignment problem using the Hungarian algorithm.

    Finds the minimum-cost perfect matching in a bipartite graph given by
    a square cost matrix.

    Implements the O(n^3) Kuhn-Munkres algorithm.

    Returns the minimum total cost.
    """
    n = len(cost)
    if n == 0:
        return 0.0
    m = len(cost[0])
    if n != m:
        raise ValueError("Cost matrix must be square")

    # Convert to a mutable copy.
    a = [row[:] for row in cost]

    # Potentials.
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)  # which row is matched to column j
    way = [0] * (m + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [Infinity] * (m + 1)
        used = [False] * (m + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = Infinity
            j1 = -1

            for j in range(1, m + 1):
                if not used[j]:
                    cur = a[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j

            for j in range(0, m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        while j0 != 0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1

    # Compute total cost.
    total = 0.0
    for j in range(1, m + 1):
        if p[j] != 0:
            total += a[p[j] - 1][j - 1]

    return total