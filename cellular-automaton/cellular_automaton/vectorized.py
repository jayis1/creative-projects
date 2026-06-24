"""Vectorized CA stepping using NumPy.

Provides fast ``step_vectorized`` functions that replace the slow Python
per-cell loops in :mod:`engine` with NumPy array operations.

For 2D outer-totalistic Life-like rules we use a 3×3 sum convolution (via
``np.add.reduceat`` on padded arrays) to compute neighbour counts in one
shot, then apply birth/survive masks vectorised across the whole grid.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def _pad2d(grid: np.ndarray, radius: int, mode: str, fixed_value: int = 0) -> np.ndarray:
    """Pad a 2D grid according to the boundary mode.

    For ``reflect`` we use ``edge`` (zero-gradient / Neumann boundary — the
    out-of-bounds cell mirrors the nearest edge cell).  This is consistent
    with the 1D vectorized path and the standard CA convention.  (NumPy's
    ``reflect`` mode mirrors the *second-from-edge* cell, which is a different
    boundary condition.)
    """
    if radius == 0:
        return grid
    if mode == "periodic":
        return np.pad(grid, radius, mode="wrap")
    if mode == "reflect":
        # Use 'edge' (clamp) for zero-gradient / Neumann boundary, consistent
        # with the 1D vectorized path.  NumPy's 'reflect' mirrors the
        # second-from-edge cell which is a different (Lagrange) condition.
        return np.pad(grid, radius, mode="edge")
    if mode == "fixed":
        return np.pad(grid, radius, mode="constant", constant_values=fixed_value)
    return np.pad(grid, radius, mode="constant", constant_values=0)


def neighbour_sum_2d(
    grid: np.ndarray,
    radius: int = 1,
    mode: str = "periodic",
    fixed_value: int = 0,
) -> np.ndarray:
    """Return the sum of the Moore neighbourhood (excluding centre) for each cell.

    Works for radius 1 (8 neighbours). For radius > 1 the sum includes all
    cells in the (2r+1)² block minus the centre.
    """
    if radius != 1:
        # Fall back to a sliding-window sum for arbitrary radius.
        padded = _pad2d(grid.astype(np.int32), radius, mode, fixed_value)
        h, w = grid.shape
        acc = np.zeros((h, w), dtype=np.int32)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dy == 0 and dx == 0:
                    continue
                acc += padded[radius + dy : radius + dy + h,
                              radius + dx : radius + dx + w]
        return acc

    padded = _pad2d(grid.astype(np.int32), 1, mode, fixed_value)
    # Sum of the 3×3 block around each cell.
    total = (
        padded[0:-2, 0:-2] + padded[0:-2, 1:-1] + padded[0:-2, 2:] +
        padded[1:-1, 0:-2] + padded[1:-1, 2:] +     # exclude centre (1:-1,1:-1)
        padded[2:, 0:-2] + padded[2:, 1:-1] + padded[2:, 2:]
    )
    return total


def step_life_vectorized(
    grid: np.ndarray,
    birth: Iterable[int],
    survive: Iterable[int],
    mode: str = "periodic",
    fixed_value: int = 0,
) -> np.ndarray:
    """Vectorised Game-of-Life-style step (outer totalistic, radius 1)."""
    birth = frozenset(birth)
    survive = frozenset(survive)
    # Clamp grid to binary — fixed_value > 1 in FIXED boundary mode could
    # introduce non-binary values that break the neighbour count logic.
    grid_bin = (grid > 0).astype(np.uint8)
    n = neighbour_sum_2d(grid_bin, radius=1, mode=mode, fixed_value=fixed_value)
    grid_int = grid_bin.astype(np.int32)
    new = np.zeros_like(grid_int)
    # Survive: currently alive AND neighbour count in survive set.
    for s in survive:
        new |= (grid_int & (n == s))
    # Birth: currently dead AND neighbour count in birth set.
    for b in birth:
        new |= ((1 - grid_int) & (n == b))
    return new.astype(np.uint8)


def step_elementary_vectorized(
    row: np.ndarray,
    table: np.ndarray,
    mode: str = "periodic",
    fixed_value: int = 0,
) -> np.ndarray:
    """Vectorised 1D elementary step.

    ``table`` is a length-8 array indexed by the 3-bit pattern
    (left<<2 | centre<<1 | right).
    """
    if mode == "periodic":
        left = np.roll(row, 1)
        right = np.roll(row, -1)
    elif mode == "reflect":
        left = np.empty_like(row)
        right = np.empty_like(row)
        left[0] = row[0]
        left[1:] = row[:-1]
        right[-1] = row[-1]
        right[:-1] = row[1:]
    else:  # fixed or zero
        fv = fixed_value if mode == "fixed" else 0
        # Clamp to binary — any non-zero value is treated as alive (1).
        # Without this, fixed_value > 1 would produce an index > 7, causing
        # an IndexError on the 8-element lookup table.
        fv = 1 if fv else 0
        left = np.empty_like(row)
        right = np.empty_like(row)
        left[0] = fv
        left[1:] = row[:-1]
        right[-1] = fv
        right[:-1] = row[1:]
    idx = (left.astype(np.int32) << 2) | (row.astype(np.int32) << 1) | right.astype(np.int32)
    return table[idx].astype(np.uint8)


def wolfram_rule_table(number: int) -> np.ndarray:
    """Return the 8-element lookup table for elementary rule ``number``."""
    if not 0 <= number <= 255:
        raise ValueError(f"rule number must be in [0,255], got {number}")
    return np.array([(number >> i) & 1 for i in range(8)], dtype=np.uint8)