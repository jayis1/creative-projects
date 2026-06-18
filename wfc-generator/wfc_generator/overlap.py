"""Overlap model: learn adjacency constraints from a sample pattern.

Given a 2D pattern (a list of lists of symbols), the :class:`OverlapModel`
extracts every ``n x n`` sub-pattern, counts their frequencies, and builds a
:class:`~wfc_generator.tileset.TileSet` whose tiles are the unique
sub-patterns and whose adjacency constraints come from allowed overlaps.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from .grid import WFCGrid
from .tile import Tile
from .tileset import TileSet

logger = logging.getLogger(__name__)


class OverlapModel:
    """Learn adjacency constraints from a sample pattern using the overlap model.

    Parameters
    ----------
    sample:
        2D grid of symbols (list of equal-length lists of strings).
    n:
        Pattern size (overlap window). Default 2.
    periodic:
        Whether the sample wraps around edges when extracting patterns.
    """

    def __init__(
        self, sample: List[List[str]], n: int = 2, periodic: bool = True
    ) -> None:
        self.sample = sample
        self.n = n
        self.sample_periodic = periodic
        self.patterns: List[Tuple[str, ...]] = []
        self.pattern_weights: Dict[Tuple[str, ...], int] = {}
        self.tile_set = TileSet()

        if not sample or not sample[0]:
            raise ValueError("Sample must be a non-empty 2D array")
        if n < 1:
            raise ValueError(f"Pattern size n must be at least 1, got {n}")
        row_lengths = [len(row) for row in sample]
        if len(set(row_lengths)) > 1:
            raise ValueError(
                f"All sample rows must have the same length, got {set(row_lengths)}"
            )

        sample_h = len(sample)
        sample_w = len(sample[0])
        if not periodic and (n > sample_h or n > sample_w):
            raise ValueError(
                f"Pattern size n={n} exceeds sample dimensions "
                f"{sample_w}x{sample_h}. Use a smaller n or enable periodic mode."
            )

        self._extract_patterns()
        self._build_constraints()

    def _extract_patterns(self) -> None:
        """Extract all ``n x n`` patterns from the sample."""
        h = len(self.sample)
        w = len(self.sample[0])
        for y in range(h):
            for x in range(w):
                pattern: List[str] = []
                valid = True
                for dy in range(self.n):
                    for dx in range(self.n):
                        ny = (y + dy) % h if self.sample_periodic else y + dy
                        nx = (x + dx) % w if self.sample_periodic else x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            pattern.append(self.sample[ny][nx])
                        else:
                            valid = False
                            break
                    if not valid:
                        break
                if valid:
                    pattern_tuple = tuple(pattern)
                    self.pattern_weights[pattern_tuple] = (
                        self.pattern_weights.get(pattern_tuple, 0) + 1
                    )
        self.patterns = list(self.pattern_weights.keys())
        if not self.patterns:
            raise ValueError(f"No valid {self.n}x{self.n} patterns found in sample")

    def _pattern_at(self, pattern: Tuple[str, ...], x: int, y: int) -> str:
        """Get the symbol at position ``(x, y)`` within an ``n x n`` pattern."""
        return pattern[y * self.n + x]

    def _build_constraints(self) -> None:
        """Build a tile set with adjacency constraints from overlapping patterns."""
        for i, pattern in enumerate(self.patterns):
            tile = Tile(
                name=f"p{i}",
                data=pattern,
                weight=self.pattern_weights[pattern],
            )
            self.tile_set.add_tile(tile)

        for i, pat_a in enumerate(self.patterns):
            for j, pat_b in enumerate(self.patterns):
                if self._can_overlap_horizontal(pat_a, pat_b):
                    self.tile_set.tiles[f"p{i}"].add_constraint("right", f"p{j}")
                    self.tile_set.tiles[f"p{j}"].add_constraint("left", f"p{i}")
                if self._can_overlap_vertical(pat_a, pat_b):
                    self.tile_set.tiles[f"p{i}"].add_constraint("bottom", f"p{j}")
                    self.tile_set.tiles[f"p{j}"].add_constraint("top", f"p{i}")

    def _can_overlap_horizontal(self, left: Tuple[str, ...], right: Tuple[str, ...]) -> bool:
        """Check if ``right`` can be placed to the right of ``left``."""
        for y in range(self.n):
            for dx in range(self.n - 1):
                left_val = left[y * self.n + (dx + 1)]
                right_val = right[y * self.n + dx]
                if left_val != right_val:
                    return False
        return True

    def _can_overlap_vertical(self, top: Tuple[str, ...], bottom: Tuple[str, ...]) -> bool:
        """Check if ``bottom`` can be placed below ``top``."""
        for x in range(self.n):
            for dy in range(self.n - 1):
                top_val = top[(dy + 1) * self.n + x]
                bottom_val = bottom[dy * self.n + x]
                if top_val != bottom_val:
                    return False
        return True

    def generate(
        self,
        width: int,
        height: int,
        seed: Optional[int] = None,
        periodic: bool = True,
    ) -> Optional[List[List[str]]]:
        """Generate a new pattern using the learned constraints."""
        grid = WFCGrid(self.tile_set, width, height, periodic=periodic, seed=seed)
        if grid.run():
            result = grid.get_result()
            if result:
                symbol_grid: List[List[str]] = []
                for y in range(height):
                    row: List[str] = []
                    for x in range(width):
                        tile_name = result[y][x]
                        if tile_name is None:
                            row.append("?")
                            continue
                        tile = self.tile_set.get_tile(tile_name)
                        row.append(self._pattern_at(tile.data, 0, 0))
                    symbol_grid.append(row)
                return symbol_grid
        return None