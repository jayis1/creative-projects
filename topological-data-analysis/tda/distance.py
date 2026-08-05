"""
Distance metrics for persistence diagrams: bottleneck and Hausdorff.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .diagram import PersistenceDiagram

Infinity = float("inf")
Point = Tuple[float, float]


def _l_inf(a: Point, b: Point) -> float:
    """L-infinity distance between two diagram points.

    Points at infinity are handled: if both have infinite death, the distance
    is the difference in births; if only one, distance is infinity.
    """
    a_b, a_d = a
    b_b, b_d = b
    if a_d == Infinity and b_d == Infinity:
        return abs(a_b - b_b)
    if a_d == Infinity or b_d == Infinity:
        return Infinity
    return max(abs(a_b - b_b), abs(a_d - b_d))


def _diagonal_point(p: Point, diag_val: float) -> Point:
    """Project a point onto the diagonal (birth == death)."""
    return (diag_val, diag_val)


def hausdorff_distance(d1: PersistenceDiagram,
                       d2: PersistenceDiagram) -> float:
    """Hausdorff distance between two persistence diagrams (same dimension).

    The Hausdorff distance is the max of the directed distances:
        sup_{p in D1} inf_{q in D2} d(p, q)
        sup_{q in D2} inf_{p in D1} d(p, q)

    Points are matched to the diagonal as a fallback.

    For diagrams with different dimensions, raises ValueError.
    """
    if d1.dimension != d2.dimension:
        raise ValueError(
            "Cannot compare diagrams of different dimensions "
            f"({d1.dimension} vs {d2.dimension})"
        )

    pts1 = d1.points()
    pts2 = d2.points()

    if not pts1 and not pts2:
        return 0.0
    if not pts1 or not pts2:
        # All points of the non-empty diagram must project to diagonal.
        nonempty = pts1 if pts1 else pts2
        if not nonempty:
            return 0.0
        # Distance from each point to the diagonal is (death - birth)/2 in
        # L-infinity, but we need a common diagonal reference. Use the
        # midpoint of each point's own birth-death as the projection.
        diag_dists = [abs(p[1] - p[0]) / 2 for p in nonempty if p[1] != Infinity]
        return max(diag_dists) if diag_dists else 0.0

    # Determine diagonal reference value (use overall mean of finite deaths).
    finite_deaths = [p[1] for p in pts1 + pts2 if p[1] != Infinity]
    diag_val = (sum(finite_deaths) / len(finite_deaths)) if finite_deaths else 0.0

    def dist_to_set(p: Point, qs: List[Point]) -> float:
        best = Infinity
        for q in qs:
            d = _l_inf(p, q)
            if d < best:
                best = d
        # Also consider the diagonal projection.
        d_diag = _l_inf(p, _diagonal_point(p, diag_val))
        if d_diag < best:
            best = d_diag
        return best

    d_12 = max(dist_to_set(p, pts2) for p in pts1) if pts1 else 0.0
    d_21 = max(dist_to_set(q, pts1) for q in pts2) if pts2 else 0.0
    return max(d_12, d_21)


def bottleneck_distance(d1: PersistenceDiagram,
                        d2: PersistenceDiagram,
                        tol: float = 1e-9) -> float:
    """Bottleneck distance between two persistence diagrams (same dimension).

    The bottleneck distance is the minimum over all perfect matchings (with
    diagonal augmentation) of the maximum L-infinity distance.

    This implementation uses a binary search + Hopcroft-Karp bipartite
    matching approach:

    1. Compute all pairwise L-infinity distances between points (including
       diagonal projections).
    2. Binary search over sorted unique distances.
    3. For each candidate distance, check if a perfect matching exists in the
       bipartite graph where edges have distance <= candidate.

    Parameters
    ----------
    d1, d2 : PersistenceDiagram
        Diagrams to compare (must have the same dimension).
    tol : float
        Tolerance for binary search convergence.

    Returns
    -------
    float
        The bottleneck distance.
    """
    if d1.dimension != d2.dimension:
        raise ValueError(
            "Cannot compare diagrams of different dimensions "
            f"({d1.dimension} vs {d2.dimension})"
        )

    pts1 = d1.points()
    pts2 = d2.points()

    if not pts1 and not pts2:
        return 0.0

    # Pad smaller diagram with diagonal points so both have the same size.
    # The diagonal value can be any value; we use the mean of finite deaths.
    finite_deaths = [p[1] for p in pts1 + pts2 if p[1] != Infinity]
    diag_val = (sum(finite_deaths) / len(finite_deaths)) if finite_deaths else 0.0

    n1, n2 = len(pts1), len(pts2)
    max_size = max(n1, n2)

    # Augment both point sets with diagonal points.
    P1 = list(pts1) + [diag_val] * (max_size - n1)  # placeholder
    P1 = list(pts1) + [(diag_val, diag_val)] * (max_size - n1)
    P2 = list(pts2) + [(diag_val, diag_val)] * (max_size - n2)

    # For infinite-death points, matching to another infinite-death point
    # uses |birth difference|. Matching to a diagonal point gives inf distance.
    # Compute the distance matrix.
    dist_matrix: List[List[float]] = []
    for p in P1:
        row: List[float] = []
        for q in P2:
            row.append(_l_inf(p, q))
        dist_matrix.append(row)

    # Collect all unique distances, sort them.
    all_dists: List[float] = []
    for row in dist_matrix:
        for d in row:
            if d != Infinity:
                all_dists.append(d)
    all_dists.sort()
    unique_dists = sorted(set(all_dists))

    if not unique_dists:
        # All distances are infinite — diagrams are incomparable (shouldn't
        # happen with diagonal augmentation unless both empty, handled above).
        return Infinity

    # Binary search for the minimum threshold allowing a perfect matching.
    lo, hi = 0, len(unique_dists) - 1
    result = unique_dists[-1]

    while lo <= hi:
        mid = (lo + hi) // 2
        threshold = unique_dists[mid]
        if _has_perfect_matching(dist_matrix, threshold):
            result = threshold
            hi = mid - 1
        else:
            lo = mid + 1

    return result


def _has_perfect_matching(dist_matrix: List[List[float]],
                          threshold: float) -> bool:
    """Check if a perfect matching exists in the bipartite graph where
    edge (i, j) exists iff dist_matrix[i][j] <= threshold.

    Uses the Hopcroft-Karp algorithm for maximum bipartite matching.
    """
    n = len(dist_matrix)
    if n == 0:
        return True
    m = len(dist_matrix[0])
    if n != m:
        return False

    # Build adjacency list.
    adj: List[List[int]] = []
    for i in range(n):
        row = [j for j in range(m) if dist_matrix[i][j] <= threshold]
        adj.append(row)

    # Hopcroft-Karp.
    pair_u: List[int] = [-1] * n
    pair_v: List[int] = [-1] * m
    dist: List[float] = [0] * n
    INF = float("inf")
    NIL = -1

    from collections import deque

    def bfs() -> bool:
        queue = deque()
        for u in range(n):
            if pair_u[u] == NIL:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = INF
        dist_nil = INF
        while queue:
            u = queue.popleft()
            if dist[u] < dist_nil:
                for v in adj[u]:
                    if pair_v[v] == NIL:
                        dist_nil = dist[u] + 1
                    elif dist[pair_v[v]] == INF:
                        dist[pair_v[v]] = dist[u] + 1
                        queue.append(pair_v[v])
        return dist_nil != INF

    def dfs(u: int) -> bool:
        for v in adj[u]:
            if pair_v[v] == NIL or (
                dist[pair_v[v]] == dist[u] + 1 and dfs(pair_v[v])
            ):
                pair_u[u] = v
                pair_v[v] = u
                return True
        dist[u] = INF
        return False

    matching = 0
    while bfs():
        for u in range(n):
            if pair_u[u] == NIL:
                if dfs(u):
                    matching += 1

    return matching == n