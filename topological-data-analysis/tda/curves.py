"""
Persistence curves: Betti curves and persistence landscapes.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .diagram import PersistenceDiagram

Infinity = float("inf")


def betti_curve(
    diagrams: Dict[int, PersistenceDiagram],
    resolution: int = 100,
    t_min: float = 0.0,
    t_max: float = Infinity,
) -> Dict[int, List[Tuple[float, int]]]:
    """Compute the Betti curve for each dimension.

    The Betti curve β_k(t) = number of k-dimensional features alive at time t.

    Parameters
    ----------
    diagrams : dict of dimension -> PersistenceDiagram
    resolution : int
        Number of sample points along the t-axis.
    t_min, t_max : float
        Range of the parameter t. If t_max is inf, uses the maximum finite
        death value (or max birth if no finite deaths).

    Returns
    -------
    dict of dimension -> list of (t, betti_number) pairs.
    """
    result: Dict[int, List[Tuple[float, int]]] = {}

    for dim, diag in diagrams.items():
        if t_max == Infinity:
            finite_deaths = [p.death for p in diag if p.death != Infinity]
            births = [p.birth for p in diag]
            if finite_deaths:
                local_max = max(max(finite_deaths), max(births) if births else 0)
            elif births:
                local_max = max(births)
            else:
                local_max = 1.0
        else:
            local_max = t_max

        if local_max <= t_min:
            local_max = t_min + 1.0

        step = (local_max - t_min) / max(1, resolution - 1)
        curve: List[Tuple[float, int]] = []
        for i in range(resolution):
            t = t_min + i * step
            curve.append((t, diag.betti_number(t)))
        result[dim] = curve

    return result


def persistence_landscape(
    diagram: PersistenceDiagram,
    resolution: int = 100,
    max_functions: int = 5,
    t_min: float = 0.0,
    t_max: float = Infinity,
) -> List[List[Tuple[float, float]]]:
    """Compute the persistence landscape Λ_k(t) for k = 1, 2, ..., max_functions.

    The persistence landscape is a sequence of functions constructed from
    the persistence diagram. For each point (b, d) in the diagram, define a
    "tent" function:

        f_(b,d)(t) = max(0, min(t - b, d - t))

    Then Λ_k(t) is the k-th largest value of f_(b,d)(t) over all (b, d).

    Parameters
    ----------
    diagram : PersistenceDiagram
        A single-dimension persistence diagram.
    resolution : int
        Number of sample points.
    max_functions : int
        Number of landscape functions to compute (k = 1..max_functions).
    t_min, t_max : float
        Range of t. Default: [0, max death].

    Returns
    -------
    list of landscape functions, each a list of (t, value) pairs.
    """
    finite_pairs = [(p.birth, p.death) for p in diagram if p.death != Infinity]

    if not finite_pairs:
        # Return zero landscapes.
        t_vals = [t_min + i * (t_max - t_min) / max(1, resolution - 1)
                  for i in range(resolution)] if t_max != Infinity else [t_min] * resolution
        return [[(t, 0.0) for t in t_vals] for _ in range(max_functions)]

    if t_max == Infinity:
        t_max = max(d for _, d in finite_pairs)
    if t_max <= t_min:
        t_max = t_min + 1.0

    step = (t_max - t_min) / max(1, resolution - 1)
    t_vals = [t_min + i * step for i in range(resolution)]

    landscapes: List[List[Tuple[float, float]]] = [[] for _ in range(max_functions)]

    for t in t_vals:
        # Compute all tent function values at t.
        values: List[float] = []
        for b, d in finite_pairs:
            val = max(0.0, min(t - b, d - t))
            values.append(val)
        # Sort in descending order.
        values.sort(reverse=True)
        for k in range(max_functions):
            val = values[k] if k < len(values) else 0.0
            landscapes[k].append((t, val))

    return landscapes


def landscape_norm(landscape: List[Tuple[float, float]], p: int = 2) -> float:
    """Compute the L^p norm of a persistence landscape function.

    Uses trapezoidal numerical integration.

    Parameters
    ----------
    landscape : list of (t, value) pairs
    p : int
        Norm order (1, 2, ...). Use p=0 for the sup-norm (L∞).
    """
    if not landscape:
        return 0.0

    if p == 0:
        return max(v for _, v in landscape)

    total = 0.0
    for i in range(len(landscape) - 1):
        t0, v0 = landscape[i]
        t1, v1 = landscape[i + 1]
        dt = t1 - t0
        # Trapezoidal rule for |f|^p.
        total += dt * (abs(v0) ** p + abs(v1) ** p) / 2
    return total ** (1.0 / p)