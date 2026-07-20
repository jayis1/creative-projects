"""TSP instance representation, generation, and I/O.

Provides :class:`TSPInstance` for representing TSP instances with either
explicit coordinates (Euclidean) or a precomputed distance matrix, plus
generation, TSPLIB loading/saving, and validation utilities.
"""

from __future__ import annotations

import math
import os
import random
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from .logging_util import get_logger

_log = get_logger(__name__)


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

    Raises
    ------
    ValueError
        If neither ``coords`` nor ``matrix`` is provided, or if the data is
        malformed (non-square matrix, negative distances, fewer than 2 cities).
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
        """Compute the pairwise Euclidean distance matrix from coordinates."""
        diff = coords[:, None, :] - coords[None, :, :]
        d = np.sqrt((diff ** 2).sum(axis=-1))
        if integer:
            d = np.round(d).astype(float)
        np.fill_diagonal(d, 0.0)
        return d

    def distance(self, i: int, j: int) -> float:
        """Return distance between cities *i* and *j*.

        Raises
        ------
        IndexError
            If *i* or *j* is out of range ``[0, n)``.
        """
        if not (0 <= i < self.n) or not (0 <= j < self.n):
            raise IndexError(f"City index out of range [0,{self.n}).")
        return float(self.matrix[i, j])

    def tour_length(self, tour: Sequence[int]) -> float:
        """Return the total length of *tour* (a permutation of 0..n-1).

        Raises
        ------
        ValueError
            If the tour has the wrong number of cities or is not a valid
            permutation.
        """
        if len(tour) != self.n:
            raise ValueError(f"Tour length {len(tour)} != n={self.n}.")
        tour_arr = np.asarray(tour, dtype=int)
        # Validate permutation
        if sorted(tour_arr.tolist()) != list(range(self.n)):
            raise ValueError("Tour is not a valid permutation of [0, n-1].")
        return float(self.matrix[tour_arr, np.roll(tour_arr, -1)].sum())

    def nearest(self, city: int, candidates: Optional[Sequence[int]] = None) -> int:
        """Return the nearest city to *city* among *candidates* (default: all others)."""
        if candidates is None:
            candidates = [j for j in range(self.n) if j != city]
        return min(candidates, key=lambda j: self.matrix[city, j])

    def to_matrix_list(self) -> List[List[float]]:
        """Return the distance matrix as a nested list."""
        return self.matrix.tolist()

    def __repr__(self) -> str:
        return f"TSPInstance(name={self.name!r}, n={self.n}, integer={self.integer})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TSPInstance):
            return NotImplemented
        return (
            self.n == other.n
            and np.array_equal(self.matrix, other.matrix)
        )

    def __hash__(self) -> int:
        return hash((self.n, self.matrix.tobytes()))


def generate_instance(
    n: int,
    *,
    seed: Optional[int] = None,
    grid: int = 1000,
    integer: bool = True,
    name: str = "random",
    distribution: str = "uniform",
) -> TSPInstance:
    """Generate a random Euclidean TSP instance with *n* cities.

    Parameters
    ----------
    n : int
        Number of cities (must be >= 2).
    seed : int, optional
        RNG seed for reproducibility.
    grid : int
        Coordinate range is ``[0, grid)``.
    integer : bool
        Whether to round distances to integers (TSPLIB convention).
    name : str
        Instance name.
    distribution : str
        Coordinate distribution: ``"uniform"`` (default) or ``"cluster"``.
        The ``"cluster"`` distribution creates city clusters, producing
        harder instances for TSP heuristics.

    Raises
    ------
    ValueError
        If *n* < 2 or *distribution* is unknown.
    """
    if n < 2:
        raise ValueError("n must be >= 2.")
    rng = random.Random(seed)
    if distribution == "uniform":
        coords = [(rng.uniform(0, grid), rng.uniform(0, grid)) for _ in range(n)]
    elif distribution == "cluster":
        # Generate clusters: pick a few cluster centers, then distribute
        # cities around them.
        n_clusters = max(2, n // 10)
        centers = [(rng.uniform(0, grid), rng.uniform(0, grid)) for _ in range(n_clusters)]
        coords: List[Tuple[float, float]] = []  # type: ignore[no-redef]
        for _ in range(n):
            cx, cy = rng.choice(centers)
            spread = grid / (n_clusters * 5)
            coords.append((
                rng.gauss(cx, spread),
                rng.gauss(cy, spread),
            ))
    else:
        raise ValueError(f"Unknown distribution {distribution!r}. Use 'uniform' or 'cluster'.")
    return TSPInstance(coords=coords, integer=integer, name=name)


def load_tsplib(path: Union[str, os.PathLike]) -> TSPInstance:
    """Load a TSPLIB-style file.

    Supports the following:

    - ``NODE_COORD_SECTION`` with EUC_2D coordinates.
    - ``EDGE_WEIGHT_SECTION`` with an explicit full matrix.
    - Standard header fields: ``NAME``, ``DIMENSION``, ``EDGE_WEIGHT_TYPE``,
      ``EDGE_WEIGHT_FORMAT``.

    Coordinates are rounded to integers when ``EDGE_WEIGHT_TYPE`` is
    ``EUC_2D`` (the TSPLIB default).

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If no coordinates or edge weights are found.
    """
    coords: List[Tuple[float, float]] = []
    matrix: Optional[List[List[float]]] = None
    name = "loaded"
    integer = True
    edge_weight_type = "EUC_2D"
    edge_weight_format = None
    dimension = None
    section: Optional[str] = None
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"TSPLIB file not found: {path}")
    with open(path, "r") as fh:
        for line in fh:
            stripped = line.strip()
            upper = stripped.upper()
            # Detect section headers
            if upper.startswith("NODE_COORD_SECTION"):
                section = "coords"
                continue
            elif upper.startswith("EDGE_WEIGHT_SECTION"):
                section = "weights"
                matrix = []
                continue
            elif upper.startswith("EOF") or upper.startswith("DISPLAY_DATA_SECTION"):
                break
            elif upper.startswith("NAME"):
                parts = stripped.split(":")
                if len(parts) == 2:
                    name = parts[1].strip()
                continue
            elif upper.startswith("DIMENSION"):
                parts = stripped.split(":")
                if len(parts) == 2:
                    dimension = int(parts[1].strip())
                continue
            elif upper.startswith("EDGE_WEIGHT_TYPE"):
                parts = stripped.split(":")
                if len(parts) == 2:
                    edge_weight_type = parts[1].strip().upper()
                continue
            elif upper.startswith("EDGE_WEIGHT_FORMAT"):
                parts = stripped.split(":")
                if len(parts) == 2:
                    edge_weight_format = parts[1].strip().upper()
                continue
            # Parse section data
            if section == "coords" and stripped:
                parts = stripped.split()
                if len(parts) >= 3:
                    coords.append((float(parts[1]), float(parts[2])))
            elif section == "weights" and stripped:
                parts = stripped.split()
                if matrix is not None:
                    matrix.append([float(x) for x in parts])

    if coords:
        _log.debug("Loaded %d coordinates from %s", len(coords), path)
        return TSPInstance(coords=coords, integer=integer, name=name)
    if matrix is not None and len(matrix) > 0:
        _log.debug("Loaded %dx%d matrix from %s", len(matrix), len(matrix[0]), path)
        return TSPInstance(matrix=matrix, integer=False, name=name)
    raise ValueError(f"No coordinates or edge weights found in {path}.")


def save_tsplib(instance: TSPInstance, path: Union[str, os.PathLike]) -> None:
    """Save a :class:`TSPInstance` to a TSPLIB-style file.

    Only coordinate-based instances are fully supported; matrix-only instances
    are written using ``EDGE_WEIGHT_SECTION``.
    """
    path = Path(path)
    lines = [
        f"NAME : {instance.name}",
        f"TYPE : TSP",
        f"DIMENSION : {instance.n}",
    ]
    if instance.coords is not None:
        lines.append("EDGE_WEIGHT_TYPE : EUC_2D")
        lines.append("NODE_COORD_SECTION")
        for i, (x, y) in enumerate(instance.coords):
            lines.append(f"{i + 1} {x} {y}")
    else:
        lines.append("EDGE_WEIGHT_TYPE : EXPLICIT")
        lines.append("EDGE_WEIGHT_FORMAT : FULL_MATRIX")
        lines.append("EDGE_WEIGHT_SECTION")
        for row in instance.matrix:
            lines.append(" ".join(str(int(v)) if instance.integer else f"{v:.4f}" for v in row))
    lines.append("EOF")
    path.write_text("\n".join(lines) + "\n")
    _log.debug("Saved instance %s to %s", instance.name, path)