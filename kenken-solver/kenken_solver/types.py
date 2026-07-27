"""Common type definitions and coordinate helpers used across the KenKen package.

This module centralises the shared type aliases and low-level geometry
utilities so that every other module can import them from a single,
well-documented location.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

# A cell is identified by its (row, col) coordinate, 0-indexed.
Cell = Tuple[int, int]

# An assignment maps every filled cell to its value (1..n).
Assignment = Dict[Cell, int]


def neighbors(cell: Cell, n: int) -> List[Cell]:
    """Return the orthogonally-adjacent cells within an *n*×*n* grid.

    Parameters
    ----------
    cell:
        The ``(row, col)`` coordinate of the cell.
    n:
        The grid dimension.

    Returns
    -------
    list[Cell]
        Up to four neighbouring cells (up/down/left/right) that lie inside the
        *n*×*n* grid.
    """
    r, c = cell
    out: List[Cell] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n:
            out.append((nr, nc))
    return out


def is_contiguous(cells: List[Cell], n: int) -> bool:
    """Check whether *cells* form a single connected region (4-connectivity).

    Uses an iterative flood-fill / DFS from the first cell.  An empty list is
    considered trivially contiguous.

    Parameters
    ----------
    cells:
        The list of cell coordinates to test.
    n:
        The grid dimension (used to determine valid neighbours).
    """
    if not cells:
        return True
    cell_set: Set[Cell] = set(cells)
    visited: Set[Cell] = set()
    stack: List[Cell] = [cells[0]]
    while stack:
        c = stack.pop()
        if c in visited:
            continue
        visited.add(c)
        for nb in neighbors(c, n):
            if nb in cell_set and nb not in visited:
                stack.append(nb)
    return visited == cell_set


__all__ = ["Cell", "Assignment", "neighbors", "is_contiguous"]