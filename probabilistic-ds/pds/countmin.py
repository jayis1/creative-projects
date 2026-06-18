"""Count-Min Sketch: approximate frequency counting.

Provides point estimates, inner products, and heavy-hitters via a
space-efficient summary.  Overestimates frequencies (never underestimates).
"""
import math
from .hashing import fnv1a_64


class CountMinSketch:
    """Count-Min Sketch for approximate frequency estimation.

    Parameters
    ----------
    width : int
        Number of counters per row.  Controls error: error ≈ width / e^depth.
        If 0, auto-computed from ``error``.
    depth : int
        Number of rows (independent hash functions).  Controls confidence.
        If 0, auto-computed from ``confidence``.
    error : float
        Target additive error (used only if width=0).  Default 0.01.
    confidence : float
        Target probability that error bound holds (used only if depth=0).
    """

    def __init__(self, width: int = 0, depth: int = 0,
                 error: float = 0.01, confidence: float = 0.99):
        if width < 0 or depth < 0:
            raise ValueError("width and depth must be non-negative")
        if error <= 0 or confidence <= 0:
            raise ValueError("error and confidence must be positive")

        if depth == 0:
            depth = max(1, int(math.ceil(-math.log(1 - confidence))))
        if width == 0:
            width = max(1, int(math.ceil(math.e / error)))

        self.width = width
        self.depth = depth
        self.error = error
        self.confidence = confidence
        self._counts = [[0] * width for _ in range(depth)]
        self._seeds = [i * 0x9E3779B9 for i in range(depth)]
        self.total = 0

    def _hashes(self, data: bytes) -> list[int]:
        return [fnv1a_64(data + seed.to_bytes(8, "little")) % self.width
                for seed in self._seeds]

    def add(self, item, count: int = 1) -> None:
        """Increment the count for ``item`` by ``count``."""
        if count < 0:
            raise ValueError("CountMinSketch only supports non-negative counts")
        data = self._serialize(item)
        for row, col in enumerate(self._hashes(data)):
            self._counts[row][col] += count
        self.total += count

    def query(self, item) -> int:
        """Estimate the frequency of ``item`` (overestimate, never underestimate)."""
        data = self._serialize(item)
        return min(self._counts[row][col]
                   for row, col in enumerate(self._hashes(data)))

    def merge(self, other: "CountMinSketch") -> None:
        """Merge another CMS into this one (pointwise sum of counters).

        The merged sketch represents the union of both input streams.
        """
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Cannot merge sketches of different dimensions")
        for r in range(self.depth):
            for c in range(self.width):
                self._counts[r][c] += other._counts[r][c]
        self.total += other.total

    def inner_product(self, other: "CountMinSketch") -> int:
        """Estimate the inner product <self, other> of two frequency vectors."""
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Sketches must have same dimensions")
        return min(
            sum(self._counts[r][c] * other._counts[r][c] for c in range(self.width))
            for r in range(self.depth)
        )

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    def __getitem__(self, item) -> int:
        return self.query(item)