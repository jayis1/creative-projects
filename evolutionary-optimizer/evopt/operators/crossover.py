"""Crossover/recombination operators."""

from __future__ import annotations

import random
import copy
from typing import List, Tuple, Sequence, Any


def uniform_crossover(parent1: Sequence, parent2: Sequence, prob: float = 0.5) -> Tuple[List, List]:
    """Uniform crossover: each gene independently inherited from either parent with probability prob.

    Args:
        parent1, parent2: Parent genomes (must have equal length).
        prob: Probability of inheriting from parent1 (default 0.5).
    """
    if len(parent1) != len(parent2):
        raise ValueError("Parents must have equal length for uniform crossover")
    if not (0.0 <= prob <= 1.0):
        raise ValueError("prob must be in [0, 1]")
    c1, c2 = [], []
    for g1, g2 in zip(parent1, parent2):
        if random.random() < prob:
            c1.append(copy.deepcopy(g1))
            c2.append(copy.deepcopy(g2))
        else:
            c1.append(copy.deepcopy(g2))
            c2.append(copy.deepcopy(g1))
    return c1, c2


def one_point_crossover(parent1: Sequence, parent2: Sequence) -> Tuple[List, List]:
    """One-point crossover: swap tails at a random point.

    Args:
        parent1, parent2: Parent genomes (must have equal length).
    """
    n = len(parent1)
    if n != len(parent2):
        raise ValueError("Parents must have equal length for one-point crossover")
    if n < 2:
        return list(parent1), list(parent2)
    point = random.randint(1, n - 1)
    c1 = list(parent1[:point]) + list(parent2[point:])
    c2 = list(parent2[:point]) + list(parent1[point:])
    return c1, c2


def two_point_crossover(parent1: Sequence, parent2: Sequence) -> Tuple[List, List]:
    """Two-point crossover: swap the middle segment between two random points."""
    n = len(parent1)
    if n != len(parent2):
        raise ValueError("Parents must have equal length for two-point crossover")
    if n < 3:
        return one_point_crossover(parent1, parent2)
    p1, p2 = sorted(random.sample(range(1, n), 2))
    c1 = list(parent1[:p1]) + list(parent2[p1:p2]) + list(parent1[p2:])
    c2 = list(parent2[:p1]) + list(parent1[p1:p2]) + list(parent2[p2:])
    return c1, c2


def blx_alpha_crossover(parent1: Sequence[float], parent2: Sequence[float], alpha: float = 0.5) -> Tuple[List[float], List[float]]:
    """BLX-α (Blend Crossover): sample children uniformly from an extended interval.

    For each dimension, the interval [min(p1,p2) - α*range, max(p1,p2) + α*range] is expanded by α.
    """
    if len(parent1) != len(parent2):
        raise ValueError("Parents must have equal length for BLX crossover")
    if alpha < 0:
        raise ValueError("alpha must be >= 0")
    c1, c2 = [], []
    for a, b in zip(parent1, parent2):
        lo, hi = min(a, b), max(a, b)
        ext = alpha * (hi - lo)
        lo -= ext
        hi += ext
        c1.append(random.uniform(lo, hi))
        c2.append(random.uniform(lo, hi))
    return c1, c2


def sbx_crossover(parent1: Sequence[float], parent2: Sequence[float], eta: float = 20.0, prob: float = 0.9) -> Tuple[List[float], List[float]]:
    """Simulated Binary Crossover (SBX) — produces real-valued children with parent-centric distribution.

    Args:
        parent1, parent2: Real-valued parent genomes.
        eta: Distribution index (higher = closer to parents). Typical: 5-20.
        prob: Crossover probability per pair.
    """
    if len(parent1) != len(parent2):
        raise ValueError("Parents must have equal length for SBX crossover")
    if eta < 0:
        raise ValueError("eta must be >= 0")
    c1, c2 = [], []
    for a, b in zip(parent1, parent2):
        if random.random() > prob:
            c1.append(a)
            c2.append(b)
            continue
        if abs(a - b) < 1e-14:
            c1.append(a)
            c2.append(b)
            continue
        # SBX beta calculation
        u = random.random()
        if u <= 0.5:
            beta = (2 * u) ** (1 / (eta + 1))
        else:
            beta = (1 / (2 * (1 - u))) ** (1 / (eta + 1))
        x1 = 0.5 * ((1 + beta) * a + (1 - beta) * b)
        x2 = 0.5 * ((1 - beta) * a + (1 + beta) * b)
        c1.append(x1)
        c2.append(x2)
    return c1, c2


def order_crossover(parent1: Sequence[int], parent2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Order Crossover (OX) for permutation-based genomes (e.g., TSP).

    Preserves a contiguous segment from parent1, fills remaining positions from parent2 in order.
    """
    n = len(parent1)
    if n != len(parent2):
        raise ValueError("Parents must have equal length for order crossover")
    if n < 2:
        return list(parent1), list(parent2)
    # Pick two cut points
    a, b = sorted(random.sample(range(n), 2))
    # Child 1: segment from parent1, rest from parent2
    seg1 = list(parent1[a:b + 1])
    remaining2 = [x for x in parent2 if x not in seg1]
    c1 = remaining2[:a] + seg1 + remaining2[a:]
    # Child 2: segment from parent2, rest from parent1
    seg2 = list(parent2[a:b + 1])
    remaining1 = [x for x in parent1 if x not in seg2]
    c2 = remaining1[:a] + seg2 + remaining1[a:]
    return c1, c2


def cycle_crossover(parent1: Sequence[int], parent2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Cycle Crossover (CX) for permutation-based genomes.

    Identifies cycles of corresponding positions and alternates parents per cycle.
    """
    n = len(parent1)
    if n != len(parent2):
        raise ValueError("Parents must have equal length for cycle crossover")
    c1 = [None] * n
    c2 = [None] * n
    # Map values to positions in parent2 for fast lookup
    pos2 = {v: i for i, v in enumerate(parent2)}
    visited = [False] * n
    turn = 0  # 0: p1->c1, p2->c2; 1: swap
    for start in range(n):
        if visited[start]:
            continue
        # Follow the cycle
        cycle = []
        idx = start
        while not visited[idx]:
            visited[idx] = True
            cycle.append(idx)
            idx = pos2[parent1[idx]]
        for i in cycle:
            if turn == 0:
                c1[i] = parent1[i]
                c2[i] = parent2[i]
            else:
                c1[i] = parent2[i]
                c2[i] = parent1[i]
        turn = 1 - turn
    return c1, c2  # type: ignore


def pmx_crossover(parent1: Sequence[int], parent2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Partially Mapped Crossover (PMX) for permutation-based genomes.

    Preserves a segment from each parent and resolves conflicts via mapping.
    """
    n = len(parent1)
    if n != len(parent2):
        raise ValueError("Parents must have equal length for PMX crossover")
    if n < 2:
        return list(parent1), list(parent2)
    a, b = sorted(random.sample(range(n), 2))
    c1 = list(parent2)  # start as copy of opposite parent
    c2 = list(parent1)
    # Copy segment
    c1[a:b + 1] = parent1[a:b + 1]
    c2[a:b + 1] = parent2[a:b + 1]
    # Build mappings
    map1 = {parent2[i]: parent1[i] for i in range(a, b + 1)}
    map2 = {parent1[i]: parent2[i] for i in range(a, b + 1)}
    # Fix conflicts outside the segment
    for i in range(n):
        if a <= i <= b:
            continue
        # Fix c1
        val = c1[i]
        while val in map1 and map1[val] != val:
            val = map1[val]
        c1[i] = val
        # Fix c2
        val2 = c2[i]
        while val2 in map2 and map2[val2] != val2:
            val2 = map2[val2]
        c2[i] = val2
    return c1, c2