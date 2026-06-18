"""Core Wave Function Collapse grid algorithm.

The :class:`WFCGrid` is the heart of the engine.  Each cell holds a *set* of
possible tile names (the "wave function" superposition).  The algorithm
repeatedly:

1. finds the uncollapsed cell with the lowest entropy,
2. collapses it to a single tile via weighted random choice,
3. propagates the resulting constraints to neighbours (arc consistency),

until every cell is collapsed or an unrecoverable contradiction is reached.
Backtracking and full restarts are supported to recover from contradictions.

This module also adds:

* pluggable **selection strategies** (minimum-entropy, MRV/scanning,
  random, lexical);
* optional **entropy caching** for large grids to avoid recomputing
  Shannon entropy on every iteration;
* JSON serialization of the collapsed grid.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from collections import deque
from copy import deepcopy
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .stats import GenerationStats
from .tile import SIDES, OPPOSITE_SIDE
from .tileset import TileSet

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Strategy for choosing which cell to collapse next."""

    MIN_ENTROPY = "min_entropy"  # Shannon entropy + noise (default, original)
    MRV = "mrv"  # Minimum Remaining Values: fewest options, ties broken randomly
    RANDOM = "random"  # Pick a random uncollapsed cell
    LEXICAL = "lexical"  # First uncollapsed cell in row-major order


class WFCGrid:
    """The core Wave Function Collapse grid.

    Parameters
    ----------
    tile_set:
        Tile set with adjacency constraints.
    width, height:
        Grid dimensions in cells (must be positive).
    periodic:
        Use toroidal (wrapping) boundary conditions.
    seed:
        Random seed for reproducibility.
    backtrack_limit:
        Maximum number of full restarts on irrecoverable contradiction.
    on_progress:
        Optional callback ``f(fraction: float)`` invoked after each step.
    selection:
        :class:`SelectionStrategy` controlling which cell collapses next.
    cache_entropy:
        If True, maintain an entropy cache updated incrementally.  Speeds up
        large grids at the cost of extra memory and code complexity.
    """

    def __init__(
        self,
        tile_set: TileSet,
        width: int,
        height: int,
        periodic: bool = False,
        seed: Optional[int] = None,
        backtrack_limit: int = 10,
        on_progress: Optional[Callable[[float], None]] = None,
        selection: SelectionStrategy = SelectionStrategy.MIN_ENTROPY,
        cache_entropy: bool = False,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"Grid dimensions must be positive, got {width}x{height}")
        if not tile_set.tiles:
            raise ValueError("Tile set must contain at least one tile")
        if isinstance(selection, str):
            selection = SelectionStrategy(selection)
        for name, tile in tile_set.tiles.items():
            if tile.weight < 0:
                raise ValueError(
                    f"Tile {name!r} has negative weight {tile.weight}. "
                    f"All tile weights must be non-negative."
                )

        self.tile_set = tile_set
        self.width = width
        self.height = height
        self.periodic = periodic
        self.backtrack_limit = backtrack_limit
        self.on_progress = on_progress
        self.selection = selection
        self.cache_entropy = cache_entropy
        self.stats = GenerationStats()
        self.stats.grid_width = width
        self.stats.grid_height = height

        self.rng = random.Random(seed) if seed is not None else random.Random()

        self.tile_names = sorted(self.tile_set.tiles.keys())
        self.tile_weights = {
            name: self.tile_set.tiles[name].weight for name in self.tile_names
        }

        # Pre-compute adjacency: (tile_name, side) -> frozenset of allowed neighbors
        self._adjacency: Dict[Tuple[str, str], frozenset] = {}
        for name in self.tile_names:
            tile = self.tile_set.tiles[name]
            for side in SIDES:
                self._adjacency[(name, side)] = frozenset(tile.get_constraint(side))

        self._init_grid()

    # ------------------------------------------------------------------ #
    # Grid state
    # ------------------------------------------------------------------ #
    def _init_grid(self) -> None:
        """Initialize or reset the grid to full superposition."""
        all_tiles = set(self.tile_names)
        self.grid: List[List[Set[str]]] = [
            [all_tiles.copy() for _ in range(self.width)] for _ in range(self.height)
        ]
        self.history: List[Tuple[List[List[Set[str]]], Tuple[int, int]]] = []
        self.collapsed_count = 0
        self.contradiction = False
        self.done = False
        self._entropy_cache: Optional[List[List[float]]] = None
        if self.cache_entropy:
            self._rebuild_entropy_cache()

    def _neighbors(self, x: int, y: int) -> List[Tuple[int, int, str]]:
        """Return ``(nx, ny, our_side)`` for each valid neighbor of ``(x, y)``."""
        result: List[Tuple[int, int, str]] = []
        if y > 0:
            result.append((x, y - 1, "top"))
        elif self.periodic and self.height > 1:
            result.append((x, self.height - 1, "top"))

        if y < self.height - 1:
            result.append((x, y + 1, "bottom"))
        elif self.periodic and self.height > 1:
            result.append((x, 0, "bottom"))

        if x > 0:
            result.append((x - 1, y, "left"))
        elif self.periodic and self.width > 1:
            result.append((self.width - 1, y, "left"))

        if x < self.width - 1:
            result.append((x + 1, y, "right"))
        elif self.periodic and self.width > 1:
            result.append((0, y, "right"))

        return result

    @staticmethod
    def _opposite_side(side: str) -> str:
        return OPPOSITE_SIDE[side]

    # ------------------------------------------------------------------ #
    # Entropy
    # ------------------------------------------------------------------ #
    def entropy(self, x: int, y: int) -> float:
        """Shannon entropy of a cell with noise for tie-breaking.

        Returns ``inf`` for a contradiction (empty set) and ``0.0`` for a
        collapsed cell.  A small noise term is added for randomized
        tie-breaking.
        """
        possible = self.grid[y][x]
        if len(possible) == 0:
            return float("inf")
        if len(possible) == 1:
            return 0.0
        total_weight = sum(self.tile_weights[t] for t in possible)
        if total_weight <= 0:
            return float("inf")
        entropy = 0.0
        for tile_name in possible:
            p = self.tile_weights[tile_name] / total_weight
            if p > 0:
                entropy -= p * math.log2(p)
        entropy += self.rng.random() * 0.001
        return entropy

    def _rebuild_entropy_cache(self) -> None:
        """Recompute the entire entropy cache from scratch."""
        self._entropy_cache = [
            [self.entropy(x, y) for x in range(self.width)]
            for y in range(self.height)
        ]

    def _cache_get(self, x: int, y: int) -> float:
        if self._entropy_cache is None:
            return self.entropy(x, y)
        return self._entropy_cache[y][x]

    def _cache_invalidate(self, x: int, y: int) -> None:
        if self._entropy_cache is not None:
            self._entropy_cache[y][x] = self.entropy(x, y)

    # ------------------------------------------------------------------ #
    # Cell selection
    # ------------------------------------------------------------------ #
    def find_lowest_entropy(self) -> Optional[Tuple[int, int]]:
        """Find the uncollapsed cell with the lowest entropy."""
        min_entropy = float("inf")
        best: Optional[Tuple[int, int]] = None
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                if len(cell) <= 1:
                    continue
                e = self._cache_get(x, y)
                if e < min_entropy:
                    min_entropy = e
                    best = (x, y)
        return best

    def _find_mrv(self) -> Optional[Tuple[int, int]]:
        """Minimum-Remaining-Values: pick the cell with the fewest options."""
        best: Optional[Tuple[int, int]] = None
        best_size: Optional[int] = None
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                size = len(cell)
                if size <= 1:
                    continue
                if best_size is None or size < best_size:
                    best_size = size
                    best = (x, y)
                elif size == best_size and self.rng.random() < 0.5:
                    # random tie-break among equally-constrained cells
                    best = (x, y)
        return best

    def _find_random_cell(self) -> Optional[Tuple[int, int]]:
        """Pick a uniformly random uncollapsed cell."""
        candidates = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if len(self.grid[y][x]) > 1
        ]
        if not candidates:
            return None
        return self.rng.choice(candidates)

    def _find_lexical(self) -> Optional[Tuple[int, int]]:
        """Return the first uncollapsed cell in row-major order."""
        for y in range(self.height):
            for x in range(self.width):
                if len(self.grid[y][x]) > 1:
                    return (x, y)
        return None

    def _select_cell(self) -> Optional[Tuple[int, int]]:
        if self.selection is SelectionStrategy.MRV:
            return self._find_mrv()
        if self.selection is SelectionStrategy.RANDOM:
            return self._find_random_cell()
        if self.selection is SelectionStrategy.LEXICAL:
            return self._find_lexical()
        return self.find_lowest_entropy()

    # ------------------------------------------------------------------ #
    # Collapse
    # ------------------------------------------------------------------ #
    def collapse(self, x: int, y: int) -> bool:
        """Collapse a cell to a single state via weighted random selection."""
        possible = self.grid[y][x]
        if len(possible) == 0:
            return False
        if len(possible) == 1:
            return True

        names = list(possible)
        weights = [self.tile_weights[n] for n in names]
        total = sum(weights)
        if total <= 0:
            return False
        r = self.rng.random() * total
        cumulative = 0.0
        chosen = names[0]
        for name, w in zip(names, weights):
            cumulative += w
            if r <= cumulative:
                chosen = name
                break
        self.grid[y][x] = {chosen}
        self.collapsed_count += 1
        self.stats.collapse_steps += 1
        if self._entropy_cache is not None:
            self._entropy_cache[y][x] = 0.0
        return True

    # ------------------------------------------------------------------ #
    # Propagation
    # ------------------------------------------------------------------ #
    def propagate(self, start_x: int, start_y: int) -> bool:
        """Propagate constraints from a collapsed cell using arc consistency.

        Returns ``False`` if a contradiction (empty possibility set) is found.
        """
        stack: deque = deque([(start_x, start_y)])
        all_tiles = set(self.tile_names)

        while stack:
            cx, cy = stack.popleft()
            current_possible = self.grid[cy][cx]
            if len(current_possible) == 0:
                self.contradiction = True
                return False

            for nx, ny, our_side in self._neighbors(cx, cy):
                their_side = self._opposite_side(our_side)

                allowed_neighbors: Set[str] = set()
                for our_tile in current_possible:
                    tile_neighbors = self._adjacency.get((our_tile, our_side), frozenset())
                    if tile_neighbors:
                        allowed_neighbors |= tile_neighbors
                    else:
                        # Empty constraint set: treat as wildcard (allow all).
                        allowed_neighbors |= all_tiles

                neighbor_possible = self.grid[ny][nx]
                new_possible = neighbor_possible & allowed_neighbors

                if len(new_possible) == 0:
                    self.contradiction = True
                    return False

                if new_possible != neighbor_possible:
                    self.grid[ny][nx] = new_possible
                    if self._entropy_cache is not None:
                        self._cache_invalidate(nx, ny)
                    stack.append((nx, ny))

            self.stats.propagation_steps += 1

        return True

    # ------------------------------------------------------------------ #
    # Stepping / backtracking / run
    # ------------------------------------------------------------------ #
    def step(self) -> bool:
        """Perform one step of the WFC algorithm.

        Returns ``True`` if successful, ``False`` on contradiction or done.
        """
        if self.done or self.contradiction:
            return False

        cell = self._select_cell()
        if cell is None:
            self.done = True
            return True

        self.history.append((deepcopy(self.grid), cell))
        x, y = cell

        if not self.collapse(x, y):
            self.contradiction = True
            return False

        if not self.propagate(x, y):
            return self._backtrack()

        if self.on_progress:
            self.on_progress(self.get_progress())
        return True

    def _backtrack(self) -> bool:
        """Attempt to backtrack from a contradiction."""
        while self.history:
            saved_grid, (bx, by) = self.history.pop()
            self.grid = saved_grid
            if self._entropy_cache is not None:
                self._rebuild_entropy_cache()
            self.contradiction = False
            self.stats.backtrack_count += 1

            possible = self.grid[by][bx]
            if len(possible) > 1:
                to_remove = self.rng.choice(list(possible))
                possible.discard(to_remove)
                self.grid[by][bx] = possible
                if self._entropy_cache is not None:
                    self._cache_invalidate(bx, by)
                if len(possible) > 0:
                    if self.collapse(bx, by):
                        if self.propagate(bx, by):
                            return True
            continue

        self.contradiction = True
        return False

    def run(self) -> bool:
        """Run the full WFC algorithm to completion. Returns ``True`` on success."""
        self.stats.start_time = time.time()
        attempts = 0
        while not self.done and not self.contradiction:
            if not self.step():
                if self.contradiction and attempts < self.backtrack_limit:
                    attempts += 1
                    self.stats.restart_count += 1
                    self._init_grid()
                    continue
                self.stats.end_time = time.time()
                self.stats.contradiction = True
                return False
        self.stats.end_time = time.time()
        return not self.contradiction

    # ------------------------------------------------------------------ #
    # Results / progress / serialization
    # ------------------------------------------------------------------ #
    def get_result(self) -> Optional[List[List[Optional[str]]]]:
        """Return the collapsed grid as a 2D list of tile names (or ``None``)."""
        if self.contradiction:
            return None
        result: List[List[Optional[str]]] = []
        for y in range(self.height):
            row: List[Optional[str]] = []
            for x in range(self.width):
                cell = self.grid[y][x]
                row.append(next(iter(cell)) if len(cell) == 1 else None)
            result.append(row)
        return result

    def get_progress(self) -> float:
        """Completion progress as a fraction in ``[0, 1]``."""
        total = self.width * self.height
        if total == 0:
            return 0.0
        collapsed = sum(
            1
            for y in range(self.height)
            for x in range(self.width)
            if len(self.grid[y][x]) == 1
        )
        return collapsed / total

    def to_json(self, path: Optional[str] = None) -> str:
        """Serialize the collapsed grid to JSON.

        If ``path`` is given the JSON is also written to that file.
        """
        result = self.get_result()
        payload = {
            "width": self.width,
            "height": self.height,
            "periodic": self.periodic,
            "selection": self.selection.value,
            "stats": self.stats.to_dict(),
            "grid": result,
        }
        text = json.dumps(payload, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return text