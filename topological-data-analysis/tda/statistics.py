"""
Statistical summaries and descriptors for persistence diagrams.

These functions produce scalar or low-dimensional summaries of a
persistence diagram (or a :class:`~dict` of diagrams) that are useful
for exploratory analysis, comparison, and as features for downstream
machine-learning pipelines.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .diagram import PersistenceDiagram, Infinity

Point = Tuple[float, float]


# ---------------------------------------------------------------------------
# Per-dimension statistics
# ---------------------------------------------------------------------------

def diagram_statistics(diagram: PersistenceDiagram) -> Dict[str, float]:
    """Return a dictionary of summary statistics for a single diagram.

    Keys
    ----
    num_features : int  — total number of pairs
    num_essential : int  — pairs with infinite death
    num_finite    : int  — pairs with finite death
    max_persistence : float
    mean_persistence : float  (finite pairs only; ``nan`` if none)
    median_persistence : float
    std_persistence : float
    total_persistence : float  — sum of finite persistences
    entropy : float — Shannon entropy of the normalised persistence
                      distribution (``-sum p_i log p_i``); ``0.0`` if ≤ 1
                      finite feature.
    """
    finite = [p.persistence for p in diagram.pairs if p.death != Infinity]
    n_finite = len(finite)
    n_essential = diagram.num_essential
    n_total = diagram.num_features

    if n_finite > 0:
        total = sum(finite)
        mean = total / n_finite
        sorted_f = sorted(finite)
        median = (sorted_f[n_finite // 2]
                  if n_finite % 2 == 1
                  else (sorted_f[n_finite // 2 - 1] + sorted_f[n_finite // 2]) / 2.0)
        variance = sum((p - mean) ** 2 for p in finite) / n_finite
        std = math.sqrt(variance)
        max_pers = max(finite)
    else:
        total = 0.0
        mean = float("nan")
        median = float("nan")
        std = 0.0
        max_pers = 0.0

    # Entropy of the persistence distribution.
    if n_finite > 1 and total > 0:
        entropy = 0.0
        for p in finite:
            q = p / total
            if q > 0:
                entropy -= q * math.log(q)
    else:
        entropy = 0.0

    return {
        "num_features": n_total,
        "num_essential": n_essential,
        "num_finite": n_finite,
        "max_persistence": max_pers,
        "mean_persistence": mean,
        "median_persistence": median,
        "std_persistence": std,
        "total_persistence": total,
        "entropy": entropy,
    }


def all_statistics(
    diagrams: Dict[int, PersistenceDiagram],
) -> Dict[int, Dict[str, float]]:
    """Compute statistics for every dimension in *diagrams*."""
    return {dim: diagram_statistics(diag) for dim, diag in diagrams.items()}


def statistics_table(
    diagrams: Dict[int, PersistenceDiagram],
) -> str:
    """Return a human-readable table of per-dimension statistics."""
    headers = [
        "dim", "features", "essential", "finite",
        "max_pers", "mean_pers", "median_pers", "std_pers",
        "total_pers", "entropy",
    ]
    rows: List[List[str]] = []
    for dim in sorted(diagrams):
        s = diagram_statistics(diagrams[dim])
        rows.append([
            str(dim),
            str(int(s["num_features"])),
            str(int(s["num_essential"])),
            str(int(s["num_finite"])),
            f"{s['max_persistence']:.4f}",
            f"{s['mean_persistence']:.4f}",
            f"{s['median_persistence']:.4f}",
            f"{s['std_persistence']:.4f}",
            f"{s['total_persistence']:.4f}",
            f"{s['entropy']:.4f}",
        ])
    # Compute column widths.
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    # Format.
    def fmt_row(cells: List[str]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))
    lines = [fmt_row(headers), fmt_row(["-" * w for w in widths])]
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Complexity / shape descriptors
# ---------------------------------------------------------------------------

def persistent_entropy(
    diagram: PersistenceDiagram,
    base: float = math.e,
) -> float:
    """Persistent entropy of a diagram.

    Defined as ``H = -sum_i (p_i / S) log(p_i / S)`` where ``p_i`` is the
    persistence of the *i*-th finite feature and ``S = sum p_i``.  The
    result is normalised by ``log(n)`` so that it lies in ``[0, 1]``.

    Returns ``0.0`` if there are fewer than 2 finite features.
    """
    finite = [p.persistence for p in diagram.pairs if p.death != Infinity]
    n = len(finite)
    if n <= 1:
        return 0.0
    total = sum(finite)
    if total == 0:
        return 0.0
    h = 0.0
    for p in finite:
        q = p / total
        if q > 0:
            h -= q * math.log(q, base)
    return h / math.log(n, base)


def amplitudes(
    diagram: PersistenceDiagram,
    p: float = 2.0,
) -> float:
    """The *p*-th persistence amplitude (a.k.a. total persistence raised
    to the *p*-th power then to the *1/p*).

    ``amplitude(D, p) = ( sum |d_i - b_i|^p )^{1/p}``

    For ``p == inf`` returns the maximum persistence (bottleneck
    amplitude).  For ``p == 1`` this is the total persistence.
    """
    finite = [p.persistence for p in diagram.pairs if p.death != Infinity]
    if not finite:
        return 0.0
    if p == Infinity:
        return max(finite)
    if p == 1.0:
        return sum(finite)
    return sum(v ** p for v in finite) ** (1.0 / p)


# ---------------------------------------------------------------------------
# Stability-based comparison
# ---------------------------------------------------------------------------

def stability_bound(
    diagram: PersistenceDiagram,
    perturbation: float,
    p: float = 2.0,
) -> float:
    """Upper bound on how much the *p*-amplitude can change under a
    perturbation of the input point cloud of size *perturbation*.

    By the stability theorem, ``|amp(D) - amp(D')| ≤ C * perturbation``
    where ``C`` depends on *p*.  For ``p ≥ 1`` the bound is simply the
    perturbation magnitude (the 1-Lipschitz property of the amplitude
    w.r.t. the bottleneck/Wasserstein metric).
    """
    return abs(perturbation)


# ---------------------------------------------------------------------------
# Feature extraction for ML
# ---------------------------------------------------------------------------

def vectorize(
    diagram: PersistenceDiagram,
    max_features: int = 50,
) -> List[float]:
    """Convert a diagram into a fixed-length feature vector suitable
    for ML pipelines.

    The vector is a flattened concatenation of ``(birth, death,
    persistence)`` for the top *max_features* features sorted by
    decreasing persistence, zero-padded if fewer features exist.
    The resulting vector has length ``3 * max_features``.
    """
    pairs = sorted(diagram.pairs, key=lambda p: p.persistence, reverse=True)
    vec: List[float] = []
    for i in range(max_features):
        if i < len(pairs):
            p = pairs[i]
            death = p.death if p.death != Infinity else -1.0
            vec.extend([p.birth, death, p.persistence if p.death != Infinity else -1.0])
        else:
            vec.extend([0.0, 0.0, 0.0])
    return vec