"""TSP instance representation and distance utilities."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

import numpy as np


class TSPInstance:
    """A TSP instance with N cities.

    The instance stores either explicit coordinates (Euclidean or geo) or an
    explicit distance matrix. Distances are cached in a numpy array for O(1)
    lookup. Symmetric TSP only — the matrix is made symmetric by copying the
    lower triangle to the upper (and vice versa) when coordinates are given.

    Parameters
    ----------
    coords : array-like of shape (N, 2)
        City coordinates. If ``matrix`` is None, these are used to compute
        Euclidean distances (rounded to integers by default, matching TSPLIB
        convention when ``integer=True``).
    matrix : array-like of shape (N, N), optional
        Explicit distance matrix. When provided, it overrides coordinate-based
        computation.
    integer : bool
        Whether to round distances to integers (TSPLIB EUC_2D convention).
    name : str
        Optional instance name for display / logging.
    """

    def __init__(
        self,
        coords: Optional[Sequence[Sequence[float]]] = None,
        matrix: Optional[Sequence[Sequence[float]]] = None,
        *,
        integer: bool = True,
        name: str = "instance",
    ) -> None:
        if coords is None and matrix is None:
            raise ValueError("Either coords or matrix must be provided.")

        self.name = name
        self.integer = integer

        if coords is not None:
            self.coords = np.asarray(coords, dtype=float)
            if self.coords.ndim != 2 or self.coords.shape[1] != 2:
                raise ValueError("coords must be of shape (N, 2).")
            self.n = self.coords.shape[0]
        else:
            self.coords = None

        if matrix is not None:
            self.matrix = np.asarray(matrix, dtype=float)
            if self.matrix.ndim != 2 or self.matrix.shape[0] != self.matrix.shape[1]:
                raise ValueError("matrix must be square (N, N).")
            self.n = self.matrix.shape[0]
            # Ensure symmetric and zero diagonal
            self.matrix = (self.matrix + self.matrix.T) / 2.0
            np.fill_diagonal(self.matrix, 0.0)
        elif coords is not None:
            self.matrix = self._euclidean_matrix(self.coords, integer)
        else:  # pragma: no cover - guarded above
            raise ValueError("Either coords or matrix must be provided.")

        # Validate
        if self.n < 2:
            raise ValueError("A TSP instance needs at least 2 cities.")
        if np.any(self.matrix < 0):
            raise ValueError("Distances must be non-negative.")

    @staticmethod
    def _euclidean_matrix(coords: np.ndarray, integer: bool) -> np.ndarray:
        diff = coords[:, None, :] - coords[None, :, :]
        d = np.sqrt((diff ** 2).sum(axis=-1))
        if integer:
            d = np.round(d).astype(float)
        np.fill_diagonal(d, 0.0)
        return d

    def distance(self, i: int, j: int) -> float:
        """Return distance between cities *i* and *j*."""
        if not (0 <= i < self.n) or not (0 <= j < self.n):
            raise IndexError(f"City index out of range [0,{self.n}).")
        return float(self.matrix[i, j])

    def tour_length(self, tour: Sequence[int]) -> float:
        """Return the total length of *tour* (a permutation of 0..n-1)."""
        if len(tour) != self.n:
            raise ValueError(f"Tour length {len(tour)} != n={self.n}.")
        tour_arr = np.asarray(tour, dtype=int)
        return float(self.matrix[tour_arr, np.roll(tour_arr, -1)].sum())

    def __repr__(self) -> str:
        return f"TSPInstance(name={self.name!r}, n={self.n}, integer={self.integer})"


def generate_instance(
    n: int,
    *,
    seed: Optional[int] = None,
    grid: int = 1000,
    integer: bool = True,
    name: str = "random",
) -> TSPInstance:
    """Generate a random Euclidean TSP instance with *n* cities."""
    if n < 2:
        raise ValueError("n must be >= 2.")
    rng = random.Random(seed)
    coords = [(rng.uniform(0, grid), rng.uniform(0, grid)) for _ in range(n)]
    return TSPInstance(coords=coords, integer=integer, name=name)


def load_tsplib(path: str) -> TSPInstance:
    """Load a minimal TSPLIB-style file (NODE_COORD_SECTION only).

    Supports ``EDGE_WEIGHT_TYPE : EUC_2D``. Distances are rounded to integers
    when the file specifies ``EDGE_WEIGHT_FORMAT`` integer rounding.
    """
    coords: List[Tuple[float, float]] = []
    name = "loaded"
    integer = True
    in_coords = False
    with open(path, "r") as fh:
        for line in fh:
            stripped = line.strip()
            upper = stripped.upper()
            if upper.startswith("NAME"):
                parts = stripped.split(":")
                if len(parts) == 2:
                    name = parts[1].strip()
            elif upper.startswith("EDGE_WEIGHT_TYPE"):
                # EUC_2D is the default; we accept it.
                pass
            elif upper.startswith("NODE_COORD_SECTION"):
                in_coords = True
                continue
            elif upper.startswith("EOF") or upper.startswith("DISPLAY_DATA_SECTION"):
                break
            elif in_coords and stripped:
                parts = stripped.split()
                if len(parts) >= 3:
                    coords.append((float(parts[1]), float(parts[2])))
    if not coords:
        raise ValueError("No coordinates found in file.")
    return TSPInstance(coords=coords, integer=integer, name=name)