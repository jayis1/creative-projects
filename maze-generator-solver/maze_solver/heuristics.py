"""Heuristic functions for A* and greedy best-first search."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .core import Cell

HeuristicFn = Callable[["Cell", "Cell"], float]


def manhattan_distance(a: "Cell", b: "Cell") -> float:
    """Manhattan (L1) distance — admissible for 4-connected grids."""
    return abs(a.x - b.x) + abs(a.y - b.y)


def euclidean_distance(a: "Cell", b: "Cell") -> float:
    """Euclidean (L2) distance — admissible but less tight for grids."""
    return math.hypot(a.x - b.x, a.y - b.y)


def chebyshev_distance(a: "Cell", b: "Cell") -> float:
    """Chebyshev (L∞) distance — admissible for 8-connected grids."""
    return max(abs(a.x - b.x), abs(a.y - b.y))


HEURISTICS: dict[str, HeuristicFn] = {
    "manhattan": manhattan_distance,
    "euclidean": euclidean_distance,
    "chebyshev": chebyshev_distance,
}