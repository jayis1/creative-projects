"""
Batch and streaming utilities for processing multiple point clouds.

The :class:`BatchProcessor` automates the common workflow of computing
persistent homology for many point clouds and aggregating results
(diagrams, statistics, kernel matrices, or vectorized features).

For very large collections, :func:`stream_persistence` processes point
clouds from an iterable one at a time, keeping memory usage constant.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .complexes import VietorisRipsComplex
from .matrix import compute_persistence
from .diagram import PersistenceDiagram, diagrams_from_persistence
from .statistics import diagram_statistics, vectorize
from .logging_config import get_logger

_log = get_logger(__name__)


class BatchProcessor:
    """Compute persistent homology for a collection of point clouds.

    Parameters
    ----------
    point_clouds : list of point-cloud sequences
    max_scale : float
        Maximum filtration scale.
    max_dimension : int
        Maximum homology dimension.
    min_persistence : float
        Minimum persistence to retain.
    complex_type : str
        Complex type (currently only ``"rips"`` is supported in batch
        mode).
    metric : callable, optional
        Custom metric.

    Examples
    --------
    >>> bp = BatchProcessor([[(0, 0), (1, 0)], [(0, 0), (2, 0)]],
    ...                      max_scale=1.5, max_dimension=1)
    >>> results = bp.run()
    >>> len(results)
    2
    """

    def __init__(
        self,
        point_clouds: Sequence[Sequence[Sequence[float]]],
        max_scale: float = float("inf"),
        max_dimension: int = 1,
        min_persistence: float = 0.0,
        complex_type: str = "rips",
        metric: Optional[Callable] = None,
    ) -> None:
        if complex_type != "rips":
            raise NotImplementedError(
                "BatchProcessor currently only supports 'rips' complex type"
            )
        self.point_clouds = list(point_clouds)
        self.max_scale = max_scale
        self.max_dimension = max_dimension
        self.min_persistence = min_persistence
        self.complex_type = complex_type
        self.metric = metric
        self._log = _log

    def run(self) -> List[Dict[int, PersistenceDiagram]]:
        """Compute persistence for all point clouds.

        Returns
        -------
        list of dict
            One diagram-dict per point cloud.
        """
        results: List[Dict[int, PersistenceDiagram]] = []
        for i, pts in enumerate(self.point_clouds):
            self._log.debug("Processing point cloud %d/%d", i + 1, len(self.point_clouds))
            vr = VietorisRipsComplex(
                pts,
                max_scale=self.max_scale,
                max_dimension=self.max_dimension,
                metric=self.metric,
            )
            tree = vr.build()
            pers = compute_persistence(
                tree,
                max_dimension=self.max_dimension,
                min_persistence=self.min_persistence,
            )
            results.append(diagrams_from_persistence(pers))
        return results

    def run_with_stats(self) -> List[Dict[int, Dict[str, float]]]:
        """Compute persistence and return per-dimension statistics."""
        diagrams = self.run()
        return [
            {dim: diagram_statistics(d) for dim, d in diag_dict.items()}
            for diag_dict in diagrams
        ]

    def run_with_vectors(
        self,
        max_features: int = 50,
    ) -> List[List[float]]:
        """Compute persistence and return vectorized features for the
        concatenated diagram of each point cloud."""
        diagrams = self.run()
        vectors: List[List[float]] = []
        for diag_dict in diagrams:
            # Concatenate all dimensions into one feature vector.
            vec: List[float] = []
            for dim in sorted(diag_dict):
                vec.extend(vectorize(diag_dict[dim], max_features=max_features))
            vectors.append(vec)
        return vectors


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

def stream_persistence(
    point_clouds: Iterable[Sequence[Sequence[float]]],
    max_scale: float = float("inf"),
    max_dimension: int = 1,
    min_persistence: float = 0.0,
    metric: Optional[Callable] = None,
    callback: Optional[Callable[[int, Dict[int, PersistenceDiagram]], None]] = None,
) -> Iterable[Dict[int, PersistenceDiagram]]:
    """Lazily compute persistence for each point cloud in an iterable.

    This generator is memory-efficient: it processes one cloud at a
    time and yields the diagram dict immediately.  Use *callback* to
    collect custom side information (e.g. writing to disk).

    Parameters
    ----------
    point_clouds : iterable of point-cloud sequences
    max_scale, max_dimension, min_persistence : see above
    metric : callable, optional
    callback : callable ``(index, diagrams) -> None``, optional

    Yields
    ------
    dict of dimension -> PersistenceDiagram
    """
    for i, pts in enumerate(point_clouds):
        _log.debug("Streaming point cloud %d", i)
        vr = VietorisRipsComplex(
            pts,
            max_scale=max_scale,
            max_dimension=max_dimension,
            metric=metric,
        )
        tree = vr.build()
        pers = compute_persistence(
            tree,
            max_dimension=max_dimension,
            min_persistence=min_persistence,
        )
        diag = diagrams_from_persistence(pers)
        if callback is not None:
            callback(i, diag)
        yield diag