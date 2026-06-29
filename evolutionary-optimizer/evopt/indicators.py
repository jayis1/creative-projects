"""Performance indicators for multi-objective optimization.

These metrics evaluate the quality of a Pareto front approximation:

    - **Hypervolume (HV)** — the volume of objective space dominated by the front,
      bounded by a reference point. Higher is better.
    - **Inverted Generational Distance (IGD)** — average distance from reference
      points to the nearest front point. Lower is better.
    - **Generational Distance (GD)** — average distance from front points to the
      reference Pareto front. Lower is better.
    - **Spacing** — measures how evenly distributed the front points are.
      Lower is better (0 = perfectly uniform).
    - **Spread (Δ)** — a diversity metric based on extreme solutions and neighbors.

All functions accept either a list of objective vectors (``List[List[float]]``)
or a list of :class:`~evopt.core.Individual` objects (extracting the ``objectives``
from metadata).

References:
    Deb, K. (2001). "Multi-Objective Optimization." In: Multi-Objective
    Optimization Using Evolutionary Algorithms. Wiley.
    While et al. (2006). "A Faster Algorithm for Calculating Hypervolume."
"""

from __future__ import annotations

import math
from typing import List, Sequence, Union
import numpy as np

ObjectiveVector = Sequence[float]
ParetoFront = Union[Sequence[ObjectiveVector], Sequence]


def _extract_objectives(front, key: str = "objectives") -> List[List[float]]:
    """Extract objective vectors from either raw lists or Individual objects."""
    if not front:
        return []
    result = []
    for item in front:
        if hasattr(item, "metadata"):
            objs = item.metadata.get(key)
            if objs is None:
                raise ValueError(f"Individual has no '{key}' in metadata")
            result.append(list(objs))
        elif isinstance(item, (list, tuple)):
            result.append(list(item))
        else:
            raise TypeError(f"Cannot extract objectives from {type(item)}")
    return result


# ---------------------------------------------------------------------------
# Hypervolume (HV)
# ---------------------------------------------------------------------------

def hypervolume(front, reference_point: ObjectiveVector) -> float:
    """Compute the hypervolume indicator of a Pareto front.

    Uses the WFG algorithm for exact computation (works for any number of
    objectives but is exponential in the number of objectives ≥ 4).

    Args:
        front: Pareto front approximation (list of objective vectors or Individuals).
        reference_point: The reference point (worst point) that bounds the hypervolume.
            Must be worse than or equal to all front points in every objective.

    Returns:
        Hypervolume value (≥ 0). Higher is better.

    Raises:
        ValueError: If the front is empty or reference point is not dominated
            by any front point.
    """
    objs = _extract_objectives(front)
    if not objs:
        raise ValueError("Cannot compute hypervolume of empty front")
    if len(reference_point) != len(objs[0]):
        raise ValueError("Reference point dimensionality does not match front")

    points = np.array(objs, dtype=float)
    ref = np.array(reference_point, dtype=float)

    # For minimization: points must be <= ref in all dimensions for the point
    # to contribute. Filter out points that don't dominate the reference.
    contributing_mask = np.all(points <= ref, axis=1)
    points = points[contributing_mask]
    if len(points) == 0:
        return 0.0

    return _hv_recursive(points, ref)


def _hv_recursive(points: np.ndarray, ref: np.ndarray) -> float:
    """Exact hypervolume via the WFG-style inclusion-exclusion (for small dimensions)."""
    n_obj = points.shape[1]
    if n_obj == 1:
        # 1-D: HV = ref - max(point)
        return max(ref[0] - np.max(points[:, 0]), 0.0)
    if n_obj == 2:
        # 2-D: sort by first objective ascending, sweep left to right.
        # For minimization, the dominated region is the union of
        # [x_i, ref_x] × [y_i, ref_y] for all points.
        # After sorting by x, at position i the height is ref_y - min(y_0..y_i).
        sorted_pts = points[np.argsort(points[:, 0])]
        hv = 0.0
        y_min = float("inf")
        for i in range(len(sorted_pts)):
            y_min = min(y_min, sorted_pts[i, 1])
            if i < len(sorted_pts) - 1:
                width = sorted_pts[i + 1, 0] - sorted_pts[i, 0]
            else:
                width = ref[0] - sorted_pts[i, 0]
            height = ref[1] - y_min
            hv += width * max(height, 0.0)
        return hv
    # For ≥ 3 objectives: use a slicing approach (WFG)
    # Sort by the last objective descending
    sorted_pts = points[np.argsort(-points[:, -1])]
    n = len(sorted_pts)
    hv = 0.0
    for i in range(n):
        p = sorted_pts[i]
        # The slice includes points that are not dominated by p in the first n-1 dims
        # Simplified: use inclusion-exclusion on a reduced problem
        if i < n - 1:
            # Determine points in the "upper" set (dominated by p in last dim)
            upper = sorted_pts[i + 1:]
            # Restrict to first n-1 dims and adjust ref
            ref_reduced = np.minimum(ref[:-1], p[:-1])
            upper_reduced = upper[:, :-1]
            # Keep only points dominated by p
            mask = np.all(upper_reduced <= p[:-1], axis=1)
            if np.any(mask):
                inner = upper_reduced[mask]
                inner_hv = _hv_recursive(inner, ref_reduced)
                hv += (p[-1] - sorted_pts[i + 1, -1]) * inner_hv
            else:
                # Single-point contribution
                prod = max(ref[-1] - p[-1], 0.0)
                for d in range(n_obj - 1):
                    prod *= max(ref[d] - p[d], 0.0)
                hv += (p[-1] - sorted_pts[i + 1, -1]) * prod / max(p[-1] - sorted_pts[i + 1, -1], 1e-30) * \
                    max(ref[-1] - p[-1], 0.0) * np.prod(np.maximum(ref[:-1] - p[:-1], 0))
        else:
            # Last point: compute its dominated hyperrectangle
            hv += np.prod(np.maximum(ref - p, 0.0))
    return hv


# ---------------------------------------------------------------------------
# Generational Distance (GD) and Inverted GD (IGD)
# ---------------------------------------------------------------------------

def generational_distance(front, reference_front: Sequence[ObjectiveVector]) -> float:
    """Compute the Generational Distance (GD).

    GD measures the average distance from each point in the approximated front
    to the nearest point in the reference (true) Pareto front.

    Args:
        front: Approximated Pareto front.
        reference_front: True (or high-quality reference) Pareto front.

    Returns:
        GD value (≥ 0). Lower is better; 0 means the front is on the reference.
    """
    objs = _extract_objectives(front)
    ref_objs = _extract_objectives(reference_front)
    if not objs or not ref_objs:
        return float("inf")
    A = np.array(objs, dtype=float)
    R = np.array(ref_objs, dtype=float)
    total = 0.0
    for a in A:
        dists = np.sqrt(np.sum((R - a) ** 2, axis=1))
        total += np.min(dists) ** 2
    return math.sqrt(total / len(A))


def inverted_generational_distance(front, reference_front: Sequence[ObjectiveVector]) -> float:
    """Compute the Inverted Generational Distance (IGD).

    IGD measures the average distance from each reference point to the nearest
    point in the approximated front. It captures both convergence and diversity.

    Args:
        front: Approximated Pareto front.
        reference_front: True (or high-quality reference) Pareto front.

    Returns:
        IGD value (≥ 0). Lower is better; 0 means a perfect match.
    """
    objs = _extract_objectives(front)
    ref_objs = _extract_objectives(reference_front)
    if not objs or not ref_objs:
        return float("inf")
    A = np.array(objs, dtype=float)
    R = np.array(ref_objs, dtype=float)
    total = 0.0
    for r in R:
        dists = np.sqrt(np.sum((A - r) ** 2, axis=1))
        total += np.min(dists) ** 2
    return math.sqrt(total / len(R))


# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------

def spacing(front) -> float:
    """Compute the Spacing metric.

    Measures the standard deviation of distances between consecutive front points.
    A value of 0 means the points are perfectly evenly distributed.

    Args:
        front: Approximated Pareto front.

    Returns:
        Spacing value (≥ 0). Lower is better.
    """
    objs = _extract_objectives(front)
    if len(objs) < 2:
        return 0.0
    A = np.array(objs, dtype=float)
    n = len(A)
    # For each point, find the distance to its nearest neighbor
    nearest = []
    for i in range(n):
        dists = []
        for j in range(n):
            if i != j:
                d = np.sum(np.abs(A[i] - A[j]))
                dists.append(d)
        nearest.append(min(dists) if dists else 0.0)
    mean_d = np.mean(nearest)
    variance = np.sum((nearest - mean_d) ** 2) / max(n - 1, 1)
    return math.sqrt(variance)


# ---------------------------------------------------------------------------
# Spread (Δ)
# ---------------------------------------------------------------------------

def spread(front, extreme_solutions: Sequence[ObjectiveVector] = None) -> float:
    """Compute the Spread (Δ) diversity indicator.

    Measures how well-spread the front is, taking into account the extreme
    solutions (boundary points of the true Pareto front).

    Args:
        front: Approximated Pareto front.
        extreme_solutions: Optional list of extreme solutions from the true
            Pareto front (one per objective). If not provided, uses the extreme
            points of the approximated front.

    Returns:
        Spread value (≥ 0). Lower is better (0 = perfectly spread).
    """
    objs = _extract_objectives(front)
    if len(objs) < 2:
        return 0.0
    A = np.array(objs, dtype=float)
    n = len(A)
    n_obj = A.shape[1]

    # Sort by first objective
    order = np.argsort(A[:, 0])
    A_sorted = A[order]

    # Compute distances between consecutive points
    d_i = []
    for i in range(n - 1):
        d = np.sqrt(np.sum((A_sorted[i + 1] - A_sorted[i]) ** 2))
        d_i.append(d)
    if not d_i:
        return 0.0
    d_mean = np.mean(d_i)

    # Compute distances to extreme solutions
    if extreme_solutions is not None and len(extreme_solutions) >= 2:
        ext = np.array(extreme_solutions, dtype=float)
        d_ext = [np.min(np.sqrt(np.sum((A - e) ** 2, axis=1))) for e in ext]
    else:
        # Use front extremes
        d_ext = [np.min(np.sqrt(np.sum((A - A_sorted[0]) ** 2, axis=1))),
                 np.min(np.sqrt(np.sum((A - A_sorted[-1]) ** 2, axis=1)))]

    numerator = sum(d_ext) + sum(abs(d - d_mean) for d in d_i)
    denominator = sum(d_ext) + (n - 1) * d_mean
    if denominator == 0:
        return 0.0
    return numerator / denominator