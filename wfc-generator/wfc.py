"""
Wave Function Collapse (WFC) Procedural Generator

An implementation of the Wave Function Collapse algorithm for procedural
content generation. Supports both 2D tile-based and pixel-based generation
from example inputs or hand-defined constraint sets.

Core Algorithm:
  1. Start with a grid where every cell is in a superposition of all possible states
  2. Find the cell with the lowest entropy (fewest possible states)
  3. Collapse that cell to a single state (weighted random choice)
  4. Propagate constraints to neighboring cells (eliminate incompatible states)
  5. Repeat until all cells are collapsed or a contradiction is found

Supports:
  - Overlap model: learns adjacency constraints from a sample image
  - Tiled model: uses explicit tile definitions with adjacency rules
  - Custom constraint functions for domain-specific generation
  - Periodic boundary conditions
  - Backtracking on contradiction
  - SVG, HTML, PNG, ANSI, and plain text rendering
  - Tile rotation and reflection symmetry
  - JSON-based tile set definitions
  - Generation statistics and timing
"""

import random
import math
import json
import time
import logging
from collections import defaultdict
from typing import List, Tuple, Dict, Set, Optional, Callable, Any
from copy import deepcopy

logger = logging.getLogger(__name__)


class Tile:
    """Represents a single tile with adjacency constraints on each side.

    A tile has a name, optional display data, a weight for weighted random
    selection during collapse, and per-side adjacency constraints (sets of
    tile names allowed on each side).

    Sides are: 'top', 'right', 'bottom', 'left' (clockwise from top).
    """

    SIDES = ["top", "right", "bottom", "left"]

    def __init__(self, name: str, data: Any = None, weight: float = 1.0, color: str = ""):
        """
        Args:
            name: Unique identifier for this tile.
            data: Optional display/rendering data (e.g. symbol, color).
            weight: Relative probability weight for selection during collapse.
            color: Optional CSS color string for rendering.
        """
        self.name = name
        self.data = data
        self.weight = weight
        self.color = color
        # Maps side -> set of tile names that can be adjacent on that side
        self.constraints: Dict[str, Set[str]] = {
            side: set() for side in self.SIDES
        }

    def add_constraint(self, side: str, neighbor_name):
        """Add an adjacency constraint: this tile allows neighbor_name(s) on the given side.

        Args:
            side: One of 'top', 'right', 'bottom', 'left'.
            neighbor_name: A single tile name string, or a list/tuple/set of names.
        """
        if side not in self.constraints:
            raise ValueError(f"Invalid side '{side}'. Must be one of {self.SIDES}")
        if isinstance(neighbor_name, (list, tuple, set)):
            self.constraints[side].update(neighbor_name)
        else:
            self.constraints[side].add(neighbor_name)

    def remove_constraint(self, side: str, neighbor_name):
        """Remove a tile name from the allowed set on the given side."""
        if side not in self.constraints:
            raise ValueError(f"Invalid side '{side}'. Must be one of {self.SIDES}")
        if isinstance(neighbor_name, (list, tuple, set)):
            self.constraints[side] -= set(neighbor_name)
        else:
            self.constraints[side].discard(neighbor_name)

    def get_constraint(self, side: str) -> Set[str]:
        """Get all tile names allowed on the given side."""
        return self.constraints.get(side, set())

    def __repr__(self):
        return f"Tile({self.name!r}, weight={self.weight}, constraints={dict(self.constraints)})"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Tile):
            return self.name == other.name
        return NotImplemented


class TileSet:
    """A collection of tiles with their adjacency constraints.

    Provides methods for validation, symmetrization, loading from JSON,
    and generating rotated/reflected tile variants.
    """

    def __init__(self):
        self.tiles: Dict[str, Tile] = {}

    def add_tile(self, tile: Tile):
        """Add a tile to the tile set."""
        if tile.name in self.tiles:
            logger.warning(f"Overwriting existing tile '{tile.name}'")
        self.tiles[tile.name] = tile

    def get_tile(self, name: str) -> Optional[Tile]:
        """Get a tile by name, or None if not found."""
        return self.tiles.get(name)

    def remove_tile(self, name: str) -> Optional[Tile]:
        """Remove and return a tile by name, or None if not found."""
        return self.tiles.pop(name, None)

    @property
    def names(self) -> List[str]:
        """Sorted list of all tile names."""
        return sorted(self.tiles.keys())

    def make_symmetric(self, tile_name: str = None, direction: str = "both"):
        """
        Make adjacency constraints bidirectional.

        If tile A allows B on its 'right' side, then B allows A on its 'left' side.

        Args:
            tile_name: If given, only symmetrize from this tile. If None, symmetrize all.
            direction: 'horizontal' (left<->right), 'vertical' (top<->bottom), 'both'
        """
        opposite = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}

        tiles_to_process = [self.tiles[tile_name]] if tile_name else list(self.tiles.values())

        for tile in tiles_to_process:
            sides = []
            if direction in ("horizontal", "both"):
                sides.extend(["right", "left"])
            if direction in ("vertical", "both"):
                sides.extend(["top", "bottom"])

            for side in sides:
                opp = opposite[side]
                for neighbor_name in list(tile.constraints[side]):
                    neighbor = self.tiles.get(neighbor_name)
                    if neighbor:
                        neighbor.add_constraint(opp, tile.name)

    def make_all_symmetric(self):
        """Make all adjacency constraints bidirectional across all tiles."""
        self.make_symmetric(direction="both")

    def validate(self) -> List[str]:
        """Check for issues in the tile set. Returns list of warnings."""
        warnings = []
        for name, tile in self.tiles.items():
            for side in Tile.SIDES:
                for neighbor_name in tile.constraints[side]:
                    if neighbor_name not in self.tiles:
                        warnings.append(
                            f"Tile '{name}' references unknown tile '{neighbor_name}' on {side}"
                        )
            # Check for tiles with no constraints on any side (isolated tiles)
            total_constraints = sum(len(tile.constraints[s]) for s in Tile.SIDES)
            if total_constraints == 0:
                warnings.append(f"Tile '{name}' has no adjacency constraints (isolated)")

        # Check for tiles with zero total weight
        total_weight = sum(t.weight for t in self.tiles.values())
        if total_weight <= 0:
            warnings.append("Total weight of all tiles is zero or negative")
        return warnings

    def add_rotated_variants(self, base_name: str, suffixes: List[str] = None):
        """
        Add 90°, 180°, and 270° rotated variants of a tile.

        Rotating a tile 90° clockwise transforms:
          top -> right, right -> bottom, bottom -> left, left -> top

        The constraint sides are remapped, AND constraint tile name references
        that point to the base tile or its known variants are also remapped
        to the corresponding rotated variant names.

        Args:
            base_name: Name of the base tile to rotate.
            suffixes: Optional list of suffixes for the 4 rotations [0°, 90°, 180°, 270°].
                      Defaults to ['', '_r90', '_r180', '_r270'].
        """
        if suffixes is None:
            suffixes = ["", "_r90", "_r180", "_r270"]

        base = self.tiles.get(base_name)
        if not base:
            return

        # Build name mapping: original_name -> {suffix -> rotated_name}
        # We need to remap any constraint references that point to the base tile
        # to point to the corresponding rotated variant.
        name_map = {}  # original_name -> list of [0°, 90°, 180°, 270°] rotated names
        for suffix in suffixes:
            original = base_name + suffix
            name_map[original] = [base_name + s for s in suffixes]

        rotation_map = {
            # side mapping for 90° clockwise rotation
            # After 90°CW: what was above (top) is now to the right
            "top": "right",
            "right": "bottom",
            "bottom": "left",
            "left": "top",
        }

        def remap_constraints(constraints, rotation_idx):
            """Remap both sides and tile name references for a given rotation."""
            new_constraints = {side: set() for side in Tile.SIDES}
            for side, tile_names in constraints.items():
                new_side = side
                # Apply rotation (rotation_idx - 1) times since we're rotating
                # from the previous variant
                for _ in range(1):  # One 90° rotation per step
                    new_side = rotation_map[new_side]

                for tile_name in tile_names:
                    # If the referenced tile is one of our variants, remap it
                    if tile_name in name_map:
                        new_tile_name = name_map[tile_name][rotation_idx]
                        new_constraints[new_side].add(new_tile_name)
                    else:
                        # External tile reference stays the same
                        new_constraints[new_side].add(tile_name)
            return new_constraints

        # Create all 4 rotations
        variants = [base]  # 0° (already exists)
        for i in range(1, 4):
            name = f"{base_name}{suffixes[i]}"
            prev_constraints = variants[i - 1].constraints
            new_constraints = remap_constraints(prev_constraints, i)
            rotated = Tile(name, weight=base.weight, color=base.color)
            rotated.constraints = new_constraints
            variants.append(rotated)
            self.add_tile(rotated)

    @classmethod
    def from_json(cls, path: str) -> "TileSet":
        """
        Load a tile set from a JSON file.

        JSON format:
        {
            "tiles": [
                {
                    "name": "floor",
                    "weight": 10,
                    "color": "#88cc44",
                    "symbol": ".",
                    "constraints": {
                        "top": ["floor", "wall"],
                        "right": ["floor", "wall"],
                        "bottom": ["floor", "wall"],
                        "left": ["floor", "wall"]
                    }
                },
                ...
            ]
        }
        """
        with open(path, "r") as f:
            data = json.load(f)

        ts = cls()
        for i, tile_data in enumerate(data.get("tiles", [])):
            if "name" not in tile_data:
                raise ValueError(f"Tile at index {i} is missing required 'name' field")

            # Validate weight if provided
            weight = tile_data.get("weight", 1.0)
            if isinstance(weight, (int, float)) and weight < 0:
                raise ValueError(
                    f"Tile '{tile_data['name']}' has negative weight {weight}. "
                    f"All weights must be non-negative."
                )

            tile = Tile(
                name=tile_data["name"],
                weight=weight,
                color=tile_data.get("color", ""),
                data=tile_data.get("symbol", tile_data["name"]),
            )
            constraints = tile_data.get("constraints", {})
            for side in Tile.SIDES:
                if side in constraints:
                    tile.add_constraint(side, constraints[side])
            ts.add_tile(tile)
        return ts

    def to_json(self, path: str):
        """Save this tile set to a JSON file."""
        data = {"tiles": []}
        for name, tile in sorted(self.tiles.items()):
            tile_data = {
                "name": name,
                "weight": tile.weight,
                "color": tile.color,
                "symbol": tile.data,
                "constraints": {
                    side: sorted(list(constraints))
                    for side, constraints in tile.constraints.items()
                },
            }
            data["tiles"].append(tile_data)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)


class GenerationStats:
    """Track statistics about a WFC generation run."""

    def __init__(self):
        self.start_time = 0.0
        self.end_time = 0.0
        self.collapse_steps = 0
        self.propagation_steps = 0
        self.backtrack_count = 0
        self.restart_count = 0
        self.contradiction = False
        self.grid_width = 0
        self.grid_height = 0

    @property
    def duration(self) -> float:
        """Time taken for generation in seconds."""
        return self.end_time - self.start_time if self.end_time else 0.0

    @property
    def cells_per_second(self) -> float:
        """Generation speed in cells/second."""
        total_cells = self.grid_width * self.grid_height
        if self.duration > 0:
            return total_cells / self.duration
        return 0.0

    def __repr__(self):
        return (
            f"GenerationStats("
            f"time={self.duration:.3f}s, "
            f"collapses={self.collapse_steps}, "
            f"propagations={self.propagation_steps}, "
            f"backtracks={self.backtrack_count}, "
            f"restarts={self.restart_count}, "
            f"speed={self.cells_per_second:.0f} cells/s, "
            f"contradiction={self.contradiction})"
        )


class WFCGrid:
    """
    The core Wave Function Collapse grid.

    Each cell maintains a set of possible states (superposition).
    The algorithm repeatedly collapses the lowest-entropy cell and propagates.

    Supports:
      - Periodic (toroidal) boundary conditions
      - Backtracking on contradiction
      - Automatic restart on irrecoverable contradiction
      - Progress callbacks for monitoring
      - Generation statistics tracking
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
    ):
        """
        Args:
            tile_set: The tile set with adjacency constraints.
            width: Grid width in cells.
            height: Grid height in cells.
            periodic: Whether to use toroidal (wrapping) boundary conditions.
            seed: Random seed for reproducibility.
            backtrack_limit: Max number of full restarts on contradiction.
            on_progress: Optional callback invoked with progress (0.0-1.0) after each step.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Grid dimensions must be positive, got {width}x{height}")
        if not tile_set.tiles:
            raise ValueError("Tile set must contain at least one tile")

        # Validate tile weights — negative weights cause issues with weighted selection
        for name, tile in tile_set.tiles.items():
            if tile.weight < 0:
                raise ValueError(
                    f"Tile '{name}' has negative weight {tile.weight}. "
                    f"All tile weights must be non-negative."
                )

        self.tile_set = tile_set
        self.width = width
        self.height = height
        self.periodic = periodic
        self.backtrack_limit = backtrack_limit
        self.on_progress = on_progress
        self.stats = GenerationStats()
        self.stats.grid_width = width
        self.stats.grid_height = height

        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()

        self.tile_names = sorted(self.tile_set.tiles.keys())
        self.tile_weights = {
            name: self.tile_set.tiles[name].weight for name in self.tile_names
        }

        # Pre-compute adjacency lookup: (tile_name, side) -> set of allowed neighbor tiles
        self._adjacency: Dict[Tuple[str, str], Set[str]] = {}
        for name in self.tile_names:
            tile = self.tile_set.tiles[name]
            for side in Tile.SIDES:
                self._adjacency[(name, side)] = tile.get_constraint(side).copy()

        # Initialize grid: every cell can be any tile
        self._init_grid()

    def _init_grid(self):
        """Initialize or reset the grid to full superposition."""
        all_tiles = set(self.tile_names)
        self.grid: List[List[Set[str]]] = [
            [all_tiles.copy() for _ in range(self.width)] for _ in range(self.height)
        ]
        self.history: List[Tuple[List[List[Set[str]]], Tuple[int, int]]] = []
        self.collapsed_count = 0
        self.contradiction = False
        self.done = False

    def _neighbors(self, x: int, y: int) -> List[Tuple[int, int, str]]:
        """Get valid neighbor coordinates and which side of OUR cell they face.

        Returns list of (nx, ny, our_side) where our_side is the side of (x,y)
        that faces (nx,ny). For example, if (nx,ny) is above (x,y), our_side
        is 'top'.
        """
        result = []
        # Top neighbor
        if y > 0:
            result.append((x, y - 1, "top"))
        elif self.periodic:
            result.append((x, self.height - 1, "top"))

        # Bottom neighbor
        if y < self.height - 1:
            result.append((x, y + 1, "bottom"))
        elif self.periodic:
            result.append((x, 0, "bottom"))

        # Left neighbor
        if x > 0:
            result.append((x - 1, y, "left"))
        elif self.periodic:
            result.append((self.width - 1, y, "left"))

        # Right neighbor
        if x < self.width - 1:
            result.append((x + 1, y, "right"))
        elif self.periodic:
            result.append((0, y, "right"))

        return result

    @staticmethod
    def _opposite_side(side: str) -> str:
        """Get the opposite side name."""
        return {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}[side]

    def entropy(self, x: int, y: int) -> float:
        """Calculate Shannon entropy of a cell based on remaining possible tiles.

        Lower entropy = fewer options = more constrained = should be collapsed next.
        Returns float('inf') for contradiction (empty set) and 0.0 for collapsed cells.
        Adds a small noise term for tie-breaking.
        """
        possible = self.grid[y][x]
        if len(possible) == 0:
            return float("inf")  # Contradiction
        if len(possible) == 1:
            return 0.0  # Already collapsed

        total_weight = sum(self.tile_weights[t] for t in possible)
        if total_weight <= 0:
            return float("inf")

        entropy = 0.0
        for tile_name in possible:
            p = self.tile_weights[tile_name] / total_weight
            if p > 0:
                entropy -= p * math.log2(p)

        # Add small noise for random tie-breaking (stable but varied)
        entropy += self.rng.random() * 0.001
        return entropy

    def find_lowest_entropy(self) -> Optional[Tuple[int, int]]:
        """Find the uncollapsed cell with the lowest entropy."""
        min_entropy = float("inf")
        best = None

        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                if len(cell) <= 1:
                    continue
                e = self.entropy(x, y)
                if e < min_entropy:
                    min_entropy = e
                    best = (x, y)

        return best

    def collapse(self, x: int, y: int) -> bool:
        """
        Collapse a cell to a single state by weighted random selection.
        Returns True if successful, False if contradiction (empty possibility set).
        """
        possible = self.grid[y][x]
        if len(possible) == 0:
            return False

        if len(possible) == 1:
            return True  # Already collapsed

        # Weighted random choice using cumulative distribution
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
        return True

    def propagate(self, start_x: int, start_y: int) -> bool:
        """
        Propagate constraints from a collapsed cell outward using arc consistency.

        Uses a stack-based approach for efficiency. Returns False if contradiction found.
        """
        stack = [(start_x, start_y)]

        while stack:
            cx, cy = stack.pop()
            current_possible = self.grid[cy][cx]

            if len(current_possible) == 0:
                self.contradiction = True
                return False

            # For each neighbor, enforce constraints
            for nx, ny, our_side in self._neighbors(cx, cy):
                their_side = self._opposite_side(our_side)

                # Aggregate: which tiles can the neighbor be, given our possibilities?
                # We use union: if any of our possible tiles allows a neighbor tile,
                # that neighbor tile remains possible. This is standard WFC propagation.
                # Note: tiles with empty constraints on a side are treated as wildcards
                # (they allow any neighbor). If you want a tile that cannot have neighbors
                # on a side, you must add explicit constraints or use a dedicated tile.
                allowed_neighbors = set()
                for our_tile in current_possible:
                    tile_neighbors = self._adjacency.get((our_tile, our_side), set())
                    if tile_neighbors:
                        allowed_neighbors |= tile_neighbors
                    else:
                        # Empty constraint set: treat as allowing all tiles (wildcard).
                        # This is the common WFC interpretation: no explicit constraints
                        # means unrestricted adjacency.
                        allowed_neighbors |= set(self.tile_names)

                neighbor_possible = self.grid[ny][nx]
                new_possible = neighbor_possible & allowed_neighbors

                if len(new_possible) == 0:
                    self.contradiction = True
                    return False

                if new_possible != neighbor_possible:
                    self.grid[ny][nx] = new_possible
                    stack.append((nx, ny))

            self.stats.propagation_steps += 1

        return True

    def step(self) -> bool:
        """
        Perform one step of the WFC algorithm.
        Returns True if successful, False if contradiction or done.
        """
        if self.done or self.contradiction:
            return False

        # Find lowest entropy cell
        cell = self.find_lowest_entropy()
        if cell is None:
            self.done = True
            return True  # All cells collapsed

        # Save state for backtracking
        self.history.append(
            (deepcopy(self.grid), cell)
        )

        x, y = cell

        # Collapse
        if not self.collapse(x, y):
            self.contradiction = True
            return False

        # Propagate
        if not self.propagate(x, y):
            # Contradiction during propagation - try backtracking
            return self._backtrack()

        # Report progress
        if self.on_progress:
            self.on_progress(self.get_progress())

        return True

    def _backtrack(self) -> bool:
        """Attempt to backtrack from a contradiction by restoring previous state."""
        while self.history:
            saved_grid, (bx, by) = self.history.pop()

            # Restore grid
            self.grid = saved_grid
            self.contradiction = False
            self.stats.backtrack_count += 1

            # Remove a random tile option from the cell that was collapsed
            possible = self.grid[by][bx]
            if len(possible) > 1:
                to_remove = self.rng.choice(list(possible))
                possible.discard(to_remove)
                self.grid[by][bx] = possible

                if len(possible) > 0:
                    if self.collapse(bx, by):
                        if self.propagate(bx, by):
                            return True

            # Try earlier state
            continue

        # Exhausted backtracking
        self.contradiction = True
        return False

    def run(self) -> bool:
        """Run the full WFC algorithm to completion. Returns True if successful."""
        self.stats.start_time = time.time()
        attempts = 0
        while not self.done and not self.contradiction:
            if not self.step():
                if self.contradiction and attempts < self.backtrack_limit:
                    # Full restart
                    attempts += 1
                    self.stats.restart_count += 1
                    self._init_grid()
                    continue
                self.stats.end_time = time.time()
                self.stats.contradiction = True
                return False

        self.stats.end_time = time.time()
        return not self.contradiction

    def _reset(self):
        """Reset the grid for a fresh attempt."""
        self._init_grid()

    def get_result(self) -> Optional[List[List[str]]]:
        """
        Get the final collapsed grid. Returns None if contradiction.
        Each cell contains the name of its collapsed tile.
        """
        if self.contradiction:
            return None
        result = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                cell = self.grid[y][x]
                if len(cell) == 1:
                    row.append(next(iter(cell)))
                else:
                    row.append(None)
            result.append(row)
        return result

    def get_progress(self) -> float:
        """Get the completion progress as a fraction [0, 1]."""
        total = self.width * self.height
        collapsed = sum(
            1 for y in range(self.height) for x in range(self.width)
            if len(self.grid[y][x]) == 1
        )
        return collapsed / total if total > 0 else 0.0


class OverlapModel:
    """
    Learn adjacency constraints from a sample pattern using the overlap model.

    Given a 2D pattern (list of lists of symbols), extracts all NxN sub-patterns
    and their allowed overlaps to build a TileSet for WFC generation.
    """

    def __init__(self, sample: List[List[str]], n: int = 2, periodic: bool = True):
        """
        Args:
            sample: 2D grid of symbols (strings)
            n: Pattern size (overlap window). Default 2 for standard WFC.
            periodic: Whether the sample wraps around edges.
        """
        self.sample = sample
        self.n = n
        self.sample_periodic = periodic
        self.patterns: List[Tuple[str, ...]] = []
        self.pattern_weights: Dict[Tuple[str, ...], int] = {}
        self.tile_set = TileSet()

        # Validate sample
        if not sample or not sample[0]:
            raise ValueError("Sample must be a non-empty 2D array")

        if n < 1:
            raise ValueError(f"Pattern size n must be at least 1, got {n}")

        row_lengths = [len(row) for row in sample]
        if len(set(row_lengths)) > 1:
            raise ValueError(f"All sample rows must have the same length, got {set(row_lengths)}")

        # Validate pattern size fits in sample
        sample_h = len(sample)
        sample_w = len(sample[0])
        if not periodic and (n > sample_h or n > sample_w):
            raise ValueError(
                f"Pattern size n={n} exceeds sample dimensions {sample_w}x{sample_h}. "
                f"Use a smaller n or enable periodic mode."
            )

        self._extract_patterns()
        self._build_constraints()

    def _extract_patterns(self):
        """Extract all NxN patterns from the sample."""
        h = len(self.sample)
        w = len(self.sample[0])

        for y in range(h):
            for x in range(w):
                pattern = []
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
                    self.pattern_weights[pattern_tuple] = self.pattern_weights.get(pattern_tuple, 0) + 1

        self.patterns = list(self.pattern_weights.keys())
        if not self.patterns:
            raise ValueError(f"No valid {self.n}x{self.n} patterns found in sample")

    def _pattern_at(self, pattern: Tuple[str, ...], x: int, y: int) -> str:
        """Get the symbol at position (x, y) within an NxN pattern."""
        return pattern[y * self.n + x]

    def _build_constraints(self):
        """Build tile set with adjacency constraints from overlapping patterns."""
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
        """Check if 'right' pattern can be placed to the right of 'left' pattern."""
        for y in range(self.n):
            for dx in range(self.n - 1):
                left_val = left[y * self.n + (dx + 1)]
                right_val = right[y * self.n + dx]
                if left_val != right_val:
                    return False
        return True

    def _can_overlap_vertical(self, top: Tuple[str, ...], bottom: Tuple[str, ...]) -> bool:
        """Check if 'bottom' pattern can be placed below 'top' pattern."""
        for x in range(self.n):
            for dy in range(self.n - 1):
                top_val = top[(dy + 1) * self.n + x]
                bottom_val = bottom[dy * self.n + x]
                if top_val != bottom_val:
                    return False
        return True

    def generate(
        self, width: int, height: int, seed: Optional[int] = None, periodic: bool = True
    ) -> Optional[List[List[str]]]:
        """Generate a new pattern using the learned constraints."""
        grid = WFCGrid(
            self.tile_set,
            width,
            height,
            periodic=periodic,
            seed=seed,
        )
        if grid.run():
            result = grid.get_result()
            if result:
                # Convert pattern tiles back to symbol grid
                symbol_grid = []
                for y in range(height):
                    row = []
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


class Renderer:
    """Render WFC output grids in various formats: ANSI, plain text, HTML, SVG, and PNG."""

    # ANSI color codes for common tile types
    COLOR_MAP = {
        "deep_water": "\033[44m",   "shallow_water": "\033[46m",
        "water": "\033[44m",        "land": "\033[42m",
        "forest": "\033[32m",       "mountain": "\033[37m",
        "snow": "\033[47m",         "sand": "\033[43m",
        "grass": "\033[42m",        "hill": "\033[33m",
        "road": "\033[40m",         "road_h": "\033[40m",
        "road_v": "\033[40m",       "building": "\033[41m",
        "park": "\033[42m",         "sidewalk": "\033[47m",
        "parking": "\033[43m",      "intersection": "\033[40m",
        "floor": "\033[40m",        "wall": "\033[37m",
        "corridor": "\033[44m",     "door": "\033[43m",
        "pillar": "\033[33m",       "stairs": "\033[46m",
        "treasure": "\033[41m",     "empty": "\033[48m\033[38m",
        "wire_h": "\033[32m",       "wire_v": "\033[32m",
        "wire_ne": "\033[32m",      "wire_nw": "\033[32m",
        "wire_se": "\033[32m",      "wire_sw": "\033[32m",
        "junction": "\033[31m",     "component": "\033[33m",
        "via": "\033[36m",
        # Single char aliases
        "~": "\033[44m",   ".": "\033[43m",   "#": "\033[42m",
        "T": "\033[32m",   "^": "\033[37m",   " ": "\033[47m",
        "R": "\033[40m",   "B": "\033[41m",   "g": "\033[42m",
        "h": "\033[33m",
    }

    RESET = "\033[0m"

    SYMBOL_MAP = {
        "deep_water": "~",     "shallow_water": "~",
        "water": "~",          "land": "#",
        "forest": "T",         "mountain": "^",
        "snow": " ",           "sand": ".",
        "grass": "g",          "hill": "h",
        "road": "R",           "road_h": "-",
        "road_v": "|",         "building": "B",
        "park": "P",           "sidewalk": "s",
        "parking": "p",        "intersection": "+",
        "floor": ".",          "wall": "#",
        "corridor": "=",        "door": "D",
        "pillar": "o",         "stairs": ">",
        "treasure": "$",       "empty": " ",
        "wire_h": "-",         "wire_v": "|",
        "wire_ne": "└",        "wire_nw": "┘",
        "wire_se": "┌",        "wire_sw": "┐",
        "junction": "+",       "component": "■",
        "via": "⊙",
        # Single char aliases
        "~": "~",   ".": ".",   "#": "#",
        "T": "T",   "^": "^",   " ": " ",
        "R": "R",   "B": "B",   "g": "g",
        "h": "h",
    }

    # HTML colors for all tile types
    HTML_COLOR_MAP = {
        "deep_water": "#1a5276",   "shallow_water": "#5dade2",
        "water": "#4488cc",        "land": "#88cc44",
        "forest": "#336622",       "mountain": "#888888",
        "snow": "#ffffff",         "sand": "#ccaa44",
        "grass": "#7dce6e",        "hill": "#c4a63d",
        "road": "#444444",         "road_h": "#555555",
        "road_v": "#555555",       "building": "#cc4444",
        "park": "#66aa44",         "sidewalk": "#bbbbbb",
        "parking": "#999966",      "intersection": "#666666",
        "floor": "#443322",        "wall": "#888877",
        "corridor": "#665544",     "door": "#ccaa44",
        "pillar": "#888888",       "stairs": "#55aacc",
        "treasure": "#ffcc00",     "empty": "#1a1a1a",
        "wire_h": "#33cc33",       "wire_v": "#33cc33",
        "wire_ne": "#33cc33",      "wire_nw": "#33cc33",
        "wire_se": "#33cc33",      "wire_sw": "#33cc33",
        "junction": "#cc3333",     "component": "#ccaa33",
        "via": "#33cccc",
        "~": "#4488cc",   ".": "#ccaa44",   "#": "#88cc44",
        "T": "#336622",   "^": "#888888",   " ": "#ffffff",
        "R": "#444444",   "B": "#cc4444",   "g": "#7dce6e",
        "h": "#c4a63d",
    }

    @classmethod
    def _get_symbol(cls, cell: str) -> str:
        """Get display symbol for a cell value."""
        return cls.SYMBOL_MAP.get(cell, str(cell)[0] if cell else "?")

    @classmethod
    def _get_color(cls, cell: str) -> str:
        """Get ANSI color code for a cell value."""
        return cls.COLOR_MAP.get(cell, "")

    @classmethod
    def _get_html_color(cls, cell: str) -> str:
        """Get HTML color for a cell value."""
        return cls.HTML_COLOR_MAP.get(cell, "#cccccc")

    @classmethod
    def render_colored(cls, grid: List[List[str]]) -> str:
        """Render a grid with ANSI colors."""
        lines = []
        for row in grid:
            line = ""
            for cell in row:
                color = cls._get_color(cell)
                symbol = cls._get_symbol(cell)
                line += f"{color}{symbol}{cls.RESET}"
            lines.append(line)
        return "\n".join(lines)

    @classmethod
    def render_plain(cls, grid: List[List[str]]) -> str:
        """Render a grid as plain text."""
        lines = []
        for row in grid:
            line = ""
            for cell in row:
                symbol = cls._get_symbol(cell)
                line += symbol
            lines.append(line)
        return "\n".join(lines)

    @classmethod
    def render_html(cls, grid: List[List[str]], cell_size: int = 16, title: str = "WFC Output") -> str:
        """Render a grid as an HTML page with colored cells."""
        html = '<!DOCTYPE html>\n<html><head>\n'
        html += f'<title>{title}</title>\n'
        html += '<style>\n'
        html += '  body { background: #1a1a2e; color: #eee; font-family: monospace; padding: 20px; }\n'
        html += f'  td {{ width: {cell_size}px; height: {cell_size}px; text-align: center; font-size: {max(8, cell_size//2)}px; }}\n'
        html += '  table { border-collapse: collapse; }\n'
        html += '  h1 { color: #e0e0e0; }\n'
        html += '</style>\n</head>\n<body>\n'
        html += f'<h1>{title}</h1>\n'
        html += f'<p>Grid: {len(grid[0]) if grid else 0}x{len(grid)}</p>\n'
        html += '<table>\n'
        for row in grid:
            html += '<tr>'
            for cell in row:
                color = cls._get_html_color(cell)
                symbol = cls._get_symbol(cell)
                html += f'<td style="background-color: {color};" title="{cell}">{symbol}</td>'
            html += '</tr>\n'
        html += '</table>\n</body>\n</html>'
        return html

    @classmethod
    def render_svg(cls, grid: List[List[str]], cell_size: int = 20, title: str = "WFC Output") -> str:
        """Render a grid as an SVG image with colored cells."""
        if not grid:
            return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

        height = len(grid)
        width = len(grid[0]) if grid else 0
        svg_width = width * cell_size
        svg_height = height * cell_size

        lines = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
            f'<title>{title}</title>',
            f'<rect width="100%" height="100%" fill="#1a1a2e"/>',
        ]

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                color = cls._get_html_color(cell)
                symbol = cls._get_symbol(cell)
                cx = x * cell_size
                cy = y * cell_size
                lines.append(f'  <rect x="{cx}" y="{cy}" width="{cell_size}" height="{cell_size}" fill="{color}"/>')
                if cell_size >= 12:
                    font_size = max(8, cell_size * 0.55)
                    lines.append(
                        f'  <text x="{cx + cell_size//2}" y="{cy + cell_size//2 + int(font_size*0.35)}" '
                        f'text-anchor="middle" font-size="{font_size:.0f}" fill="#fff" '
                        f'font-family="monospace">{symbol}</text>'
                    )

        lines.append('</svg>')
        return '\n'.join(lines)

    @classmethod
    def render_png(cls, grid: List[List[str]], cell_size: int = 16, title: str = "WFC Output") -> Optional[bytes]:
        """Render a grid as a PNG image. Requires Pillow (PIL).

        Returns PNG bytes, or None if Pillow is not available.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("Pillow not installed. Install with: pip install Pillow")
            return None

        if not grid:
            return None

        height = len(grid)
        width = len(grid[0])
        img_width = width * cell_size
        img_height = height * cell_size

        img = Image.new("RGB", (img_width, img_height), (26, 26, 46))
        draw = ImageDraw.Draw(img)

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                color_hex = cls._get_html_color(cell)
                # Convert hex to RGB
                r = int(color_hex[1:3], 16)
                g = int(color_hex[3:5], 16)
                b = int(color_hex[5:7], 16)
                x0, y0 = x * cell_size, y * cell_size
                draw.rectangle([x0, y0, x0 + cell_size - 1, y0 + cell_size - 1], fill=(r, g, b))

                if cell_size >= 14:
                    symbol = cls._get_symbol(cell)
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", max(8, cell_size // 2))
                    except (OSError, IOError):
                        font = ImageFont.load_default()
                    draw.text((x0 + cell_size // 2, y0 + cell_size // 2), symbol,
                              fill=(255, 255, 255), font=font, anchor="mm")

        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# =============================================
# Preset Tile Sets for common generation tasks
# =============================================

def create_dungeon_tileset() -> TileSet:
    """Create a tile set for dungeon/cave generation.

    Includes: floor, wall, corridor, door, pillar, stairs, treasure.
    Walls are heavy (high weight) to create room-like structures.
    """
    ts = TileSet()

    floor = Tile("floor", weight=10, color="#443322", data=".")
    wall = Tile("wall", weight=8, color="#888877", data="#")
    corridor = Tile("corridor", weight=5, color="#665544", data="=")
    door = Tile("door", weight=2, color="#ccaa44", data="D")
    pillar = Tile("pillar", weight=1, color="#888888", data="o")
    stairs = Tile("stairs", weight=1, color="#55aacc", data=">")
    treasure = Tile("treasure", weight=0.5, color="#ffcc00", data="$")

    # Floor: can be next to most interior tiles
    for n in ["floor", "corridor", "door", "stairs", "treasure", "pillar"]:
        floor.add_constraint("top", n)
        floor.add_constraint("bottom", n)
        floor.add_constraint("left", n)
        floor.add_constraint("right", n)

    # Walls form boundaries
    wall.add_constraint("top", ["wall", "floor", "corridor", "door", "pillar"])
    wall.add_constraint("bottom", ["wall", "floor", "corridor", "door", "pillar"])
    wall.add_constraint("left", ["wall", "floor", "corridor", "door", "pillar"])
    wall.add_constraint("right", ["wall", "floor", "corridor", "door", "pillar"])

    # Corridors connect spaces
    for n in ["floor", "corridor", "door", "stairs"]:
        corridor.add_constraint("top", n)
        corridor.add_constraint("bottom", n)
        corridor.add_constraint("left", n)
        corridor.add_constraint("right", n)

    # Doors: passages between rooms
    for n in ["floor", "corridor", "wall"]:
        door.add_constraint("top", n)
        door.add_constraint("bottom", n)
        door.add_constraint("left", n)
        door.add_constraint("right", n)

    # Pillars: structural support in rooms
    for n in ["floor", "wall", "corridor"]:
        pillar.add_constraint("top", n)
        pillar.add_constraint("bottom", n)
        pillar.add_constraint("left", n)
        pillar.add_constraint("right", n)

    # Stairs connect levels
    for n in ["floor", "corridor", "door"]:
        stairs.add_constraint("top", n)
        stairs.add_constraint("bottom", n)
        stairs.add_constraint("left", n)
        stairs.add_constraint("right", n)

    # Treasure: rare loot rooms
    for n in ["floor", "wall"]:
        treasure.add_constraint("top", n)
        treasure.add_constraint("bottom", n)
        treasure.add_constraint("left", n)
        treasure.add_constraint("right", n)

    for tile in [floor, wall, corridor, door, pillar, stairs, treasure]:
        ts.add_tile(tile)

    # Make all constraints bidirectional
    ts.make_all_symmetric()
    return ts


def create_terrain_tileset() -> TileSet:
    """Create a tile set for terrain/map generation.

    Includes: deep_water, shallow_water, sand, grass, forest, hill, mountain, snow.
    Enforces natural terrain transitions (e.g. water→sand→grass→forest→hill→mountain→snow).
    """
    ts = TileSet()

    deep_water = Tile("deep_water", weight=5, color="#1a5276", data="~")
    shallow_water = Tile("shallow_water", weight=4, color="#5dade2", data="~")
    sand = Tile("sand", weight=3, color="#ccaa44", data=".")
    grass = Tile("grass", weight=12, color="#7dce6e", data="g")
    forest = Tile("forest", weight=8, color="#336622", data="T")
    hill = Tile("hill", weight=4, color="#c4a63d", data="h")
    mountain = Tile("mountain", weight=2, color="#888888", data="^")
    snow = Tile("snow", weight=1, color="#ffffff", data=" ")

    # Each terrain type can transition to adjacent elevation types
    for n in ["deep_water", "shallow_water"]:
        deep_water.add_constraint("top", n)
        deep_water.add_constraint("right", n)
        deep_water.add_constraint("bottom", n)
        deep_water.add_constraint("left", n)

    for n in ["deep_water", "shallow_water", "sand"]:
        shallow_water.add_constraint("top", n)
        shallow_water.add_constraint("right", n)
        shallow_water.add_constraint("bottom", n)
        shallow_water.add_constraint("left", n)

    for n in ["shallow_water", "sand", "grass"]:
        sand.add_constraint("top", n)
        sand.add_constraint("right", n)
        sand.add_constraint("bottom", n)
        sand.add_constraint("left", n)

    for n in ["sand", "grass", "forest", "hill"]:
        grass.add_constraint("top", n)
        grass.add_constraint("right", n)
        grass.add_constraint("bottom", n)
        grass.add_constraint("left", n)

    for n in ["grass", "forest", "hill"]:
        forest.add_constraint("top", n)
        forest.add_constraint("right", n)
        forest.add_constraint("bottom", n)
        forest.add_constraint("left", n)

    for n in ["grass", "forest", "hill", "mountain"]:
        hill.add_constraint("top", n)
        hill.add_constraint("right", n)
        hill.add_constraint("bottom", n)
        hill.add_constraint("left", n)

    for n in ["hill", "mountain", "snow"]:
        mountain.add_constraint("top", n)
        mountain.add_constraint("right", n)
        mountain.add_constraint("bottom", n)
        mountain.add_constraint("left", n)

    for n in ["mountain", "snow"]:
        snow.add_constraint("top", n)
        snow.add_constraint("right", n)
        snow.add_constraint("bottom", n)
        snow.add_constraint("left", n)

    for tile in [deep_water, shallow_water, sand, grass, forest, hill, mountain, snow]:
        ts.add_tile(tile)

    # Make all constraints bidirectional for consistency
    ts.make_all_symmetric()
    return ts


def create_city_tileset() -> TileSet:
    """Create a tile set for city/street generation.

    Includes: road_h, road_v, intersection, building, park, sidewalk, parking.
    Enforces that roads connect properly and buildings cluster together.
    """
    ts = TileSet()

    road_h = Tile("road_h", weight=8, color="#555555", data="-")
    road_v = Tile("road_v", weight=8, color="#555555", data="|")
    intersection = Tile("intersection", weight=5, color="#666666", data="+")
    building = Tile("building", weight=10, color="#cc4444", data="B")
    park = Tile("park", weight=3, color="#66aa44", data="P")
    sidewalk = Tile("sidewalk", weight=4, color="#bbbbbb", data="s")
    parking = Tile("parking", weight=2, color="#999966", data="p")

    # Horizontal road connects left-right
    for n in ["road_h", "intersection", "sidewalk"]:
        road_h.add_constraint("left", n)
        road_h.add_constraint("right", n)
    for n in ["sidewalk", "building", "park", "parking"]:
        road_h.add_constraint("top", n)
        road_h.add_constraint("bottom", n)

    # Vertical road connects top-bottom
    for n in ["road_v", "intersection", "sidewalk"]:
        road_v.add_constraint("top", n)
        road_v.add_constraint("bottom", n)
    for n in ["sidewalk", "building", "park", "parking"]:
        road_v.add_constraint("left", n)
        road_v.add_constraint("right", n)

    # Intersection connects all road types
    for n in ["road_h", "road_v", "intersection"]:
        intersection.add_constraint("top", n)
        intersection.add_constraint("bottom", n)
        intersection.add_constraint("left", n)
        intersection.add_constraint("right", n)

    # Buildings surrounded by sidewalk
    for n in ["sidewalk", "building"]:
        building.add_constraint("top", n)
        building.add_constraint("bottom", n)
        building.add_constraint("left", n)
        building.add_constraint("right", n)

    # Parks surrounded by sidewalk
    for n in ["sidewalk", "park", "building"]:
        park.add_constraint("top", n)
        park.add_constraint("bottom", n)
        park.add_constraint("left", n)
        park.add_constraint("right", n)

    # Sidewalk connects most things
    for n in ["sidewalk", "building", "park", "road_h", "road_v", "parking"]:
        sidewalk.add_constraint("top", n)
        sidewalk.add_constraint("bottom", n)
        sidewalk.add_constraint("left", n)
        sidewalk.add_constraint("right", n)

    # Parking lots
    for n in ["sidewalk", "parking", "road_h", "road_v"]:
        parking.add_constraint("top", n)
        parking.add_constraint("bottom", n)
        parking.add_constraint("left", n)
        parking.add_constraint("right", n)

    for tile in [road_h, road_v, intersection, building, park, sidewalk, parking]:
        ts.add_tile(tile)

    ts.make_all_symmetric()
    return ts


def create_circuit_tileset() -> TileSet:
    """Create a tile set for circuit board pattern generation.

    Includes: empty, wire_h, wire_v, wire corners (NE/NW/SE/SW), junction, component, via.
    Enforces that wires connect properly at endpoints and corners.
    """
    ts = TileSet()

    empty = Tile("empty", weight=15, color="#1a1a1a", data=" ")
    wire_h = Tile("wire_h", weight=6, color="#33cc33", data="-")
    wire_v = Tile("wire_v", weight=6, color="#33cc33", data="|")
    wire_ne = Tile("wire_ne", weight=3, color="#33cc33", data="└")
    wire_nw = Tile("wire_nw", weight=3, color="#33cc33", data="┘")
    wire_se = Tile("wire_se", weight=3, color="#33cc33", data="┌")
    wire_sw = Tile("wire_sw", weight=3, color="#33cc33", data="┐")
    junction = Tile("junction", weight=2, color="#cc3333", data="+")
    component = Tile("component", weight=4, color="#ccaa33", data="■")
    via = Tile("via", weight=1, color="#33cccc", data="⊙")

    # Empty: connects to anything
    all_tiles = ["empty", "wire_h", "wire_v", "wire_ne", "wire_nw",
                 "wire_se", "wire_sw", "junction", "component", "via"]
    for n in all_tiles:
        empty.add_constraint("top", n)
        empty.add_constraint("right", n)
        empty.add_constraint("bottom", n)
        empty.add_constraint("left", n)

    # Wire horizontal: connects left-right
    for n in ["empty", "wire_h", "wire_ne", "wire_se", "junction", "component"]:
        wire_h.add_constraint("left", n)
        wire_h.add_constraint("right", n)
    for n in ["empty", "wire_v", "wire_ne", "wire_nw", "via"]:
        wire_h.add_constraint("top", n)
        wire_h.add_constraint("bottom", n)

    # Wire vertical: connects top-bottom
    for n in ["empty", "wire_v", "wire_se", "wire_sw", "junction", "component"]:
        wire_v.add_constraint("top", n)
        wire_v.add_constraint("bottom", n)
    for n in ["empty", "wire_h", "wire_ne", "wire_se", "via"]:
        wire_v.add_constraint("left", n)
        wire_v.add_constraint("right", n)

    # Corner NE: wire from left, goes up
    for n in ["empty", "wire_h", "wire_ne", "wire_se", "junction"]:
        wire_ne.add_constraint("left", n)
    for n in ["empty", "wire_v", "wire_ne", "wire_nw", "junction"]:
        wire_ne.add_constraint("top", n)
    wire_ne.add_constraint("right", ["empty"])
    wire_ne.add_constraint("bottom", ["empty"])

    # Corner NW: wire from right, goes up
    for n in ["empty", "wire_h", "wire_nw", "wire_sw", "junction"]:
        wire_nw.add_constraint("right", n)
    for n in ["empty", "wire_v", "wire_ne", "wire_nw", "junction"]:
        wire_nw.add_constraint("top", n)
    wire_nw.add_constraint("left", ["empty"])
    wire_nw.add_constraint("bottom", ["empty"])

    # Corner SE: wire from left, goes down
    for n in ["empty", "wire_h", "wire_ne", "wire_se", "junction"]:
        wire_se.add_constraint("left", n)
    for n in ["empty", "wire_v", "wire_se", "wire_sw", "junction"]:
        wire_se.add_constraint("bottom", n)
    wire_se.add_constraint("right", ["empty"])
    wire_se.add_constraint("top", ["empty"])

    # Corner SW: wire from right, goes down
    for n in ["empty", "wire_h", "wire_nw", "wire_sw", "junction"]:
        wire_sw.add_constraint("right", n)
    for n in ["empty", "wire_v", "wire_se", "wire_sw", "junction"]:
        wire_sw.add_constraint("bottom", n)
    wire_sw.add_constraint("left", ["empty"])
    wire_sw.add_constraint("top", ["empty"])

    # Junction: connects in all directions
    for n in ["empty", "wire_h", "wire_v", "wire_ne", "wire_nw", "wire_se", "wire_sw", "junction", "component", "via"]:
        junction.add_constraint("top", n)
        junction.add_constraint("right", n)
        junction.add_constraint("bottom", n)
        junction.add_constraint("left", n)

    # Component: connects to wires
    for n in ["empty", "wire_h", "wire_v", "component"]:
        component.add_constraint("top", n)
        component.add_constraint("right", n)
        component.add_constraint("bottom", n)
        component.add_constraint("left", n)

    # Via: connects layers
    for n in ["empty", "wire_h", "wire_v", "via", "junction"]:
        via.add_constraint("top", n)
        via.add_constraint("right", n)
        via.add_constraint("bottom", n)
        via.add_constraint("left", n)

    for tile in [empty, wire_h, wire_v, wire_ne, wire_nw,
                 wire_se, wire_sw, junction, component, via]:
        ts.add_tile(tile)

    ts.make_all_symmetric()
    return ts


def create_maze_tileset() -> TileSet:
    """Create a tile set for maze generation.

    Uses wall and path tiles with constraints that ensure paths connect.
    Produces maze-like patterns with corridors and dead ends.
    """
    ts = TileSet()

    path = Tile("path", weight=6, color="#443322", data=".")
    wall = Tile("wall", weight=10, color="#888877", data="#")
    dead_end = Tile("dead_end", weight=1, color="#665544", data="D")

    # Path: connects to paths and dead ends
    for n in ["path", "dead_end"]:
        path.add_constraint("top", n)
        path.add_constraint("right", n)
        path.add_constraint("bottom", n)
        path.add_constraint("left", n)

    # Path also connects to walls (transitions)
    for side in ["top", "right", "bottom", "left"]:
        path.add_constraint(side, "wall")

    # Walls: can be adjacent to paths or walls
    for side in ["top", "right", "bottom", "left"]:
        wall.add_constraint(side, ["wall", "path", "dead_end"])

    # Dead ends: path that ends, has one path neighbor and walls for the rest
    dead_end.add_constraint("top", ["path", "wall", "dead_end"])
    dead_end.add_constraint("right", ["path", "wall", "dead_end"])
    dead_end.add_constraint("bottom", ["path", "wall", "dead_end"])
    dead_end.add_constraint("left", ["path", "wall", "dead_end"])

    for tile in [path, wall, dead_end]:
        ts.add_tile(tile)

    ts.make_all_symmetric()
    return ts


# =============================================
# CLI Interface
# =============================================

def main():
    """Main CLI entry point for WFC generator."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Wave Function Collapse Procedural Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate terrain map (30x20)
  python3 wfc.py terrain --width 30 --height 20 --seed 42

  # Generate dungeon (40x25)
  python3 wfc.py dungeon --width 40 --height 25

  # Generate from sample pattern using overlap model
  python3 wfc.py overlap --width 20 --height 20 --sample sample.json

  # Generate city layout with HTML output
  python3 wfc.py city --width 25 --height 25 --output city.html

  # Generate maze with SVG output
  python3 wfc.py maze --width 40 --height 30 --output maze.svg

  # Generate circuit pattern with PNG output (requires Pillow)
  python3 wfc.py circuit --width 25 --height 25 --output circuit.png

  # Load custom tile set from JSON
  python3 wfc.py custom --tileset tiles.json --width 20 --height 20

  # Show generation statistics
  python3 wfc.py terrain --width 50 --height 40 --stats
        """,
    )

    subparsers = parser.add_subparsers(dest="mode", help="Generation mode")

    # Common arguments for all modes
    def add_common_args(p):
        p.add_argument("--width", type=int, default=30, help="Grid width")
        p.add_argument("--height", type=int, default=20, help="Grid height")
        p.add_argument("--seed", type=int, default=None, help="Random seed")
        p.add_argument("--periodic", action="store_true", help="Use periodic boundaries")
        p.add_argument("--output", type=str, default=None, help="Output file (html, svg, png, txt)")
        p.add_argument("--stats", action="store_true", help="Print generation statistics")
        p.add_argument("--cell-size", type=int, default=16, help="Cell size in pixels (for html/svg/png)")

    # Terrain mode
    terrain_p = subparsers.add_parser("terrain", help="Generate terrain maps")
    add_common_args(terrain_p)

    # Dungeon mode
    dungeon_p = subparsers.add_parser("dungeon", help="Generate dungeon maps")
    add_common_args(dungeon_p)

    # City mode
    city_p = subparsers.add_parser("city", help="Generate city layouts")
    add_common_args(city_p)

    # Circuit mode
    circuit_p = subparsers.add_parser("circuit", help="Generate circuit board patterns")
    add_common_args(circuit_p)

    # Maze mode
    maze_p = subparsers.add_parser("maze", help="Generate maze patterns")
    add_common_args(maze_p)

    # Overlap mode
    overlap_p = subparsers.add_parser("overlap", help="Generate from sample pattern (overlap model)")
    add_common_args(overlap_p)
    overlap_p.add_argument("--sample", type=str, required=True, help="Sample file (JSON)")
    overlap_p.add_argument("--n", type=int, default=2, help="Pattern size")

    # Custom tile set mode
    custom_p = subparsers.add_parser("custom", help="Generate from custom tile set (JSON)")
    add_common_args(custom_p)
    custom_p.add_argument("--tileset", type=str, required=True, help="Tile set JSON file")
    custom_p.add_argument("--symmetrize", action="store_true", help="Auto-symmetrize constraints")

    args = parser.parse_args()

    if args.mode is None:
        parser.print_help()
        sys.exit(1)

    tileset_creators = {
        "terrain": create_terrain_tileset,
        "dungeon": create_dungeon_tileset,
        "city": create_city_tileset,
        "circuit": create_circuit_tileset,
        "maze": create_maze_tileset,
    }

    if args.mode == "overlap":
        # Load sample
        try:
            with open(args.sample, "r") as f:
                sample = json.load(f)
        except Exception as e:
            print(f"Error loading sample file: {e}", file=sys.stderr)
            sys.exit(1)

        model = OverlapModel(sample, n=args.n)
        grid_obj = WFCGrid(
            model.tile_set,
            args.width,
            args.height,
            periodic=args.periodic,
            seed=args.seed,
        )
        start = time.time()
        success = grid_obj.run()
        elapsed = time.time() - start

        if not success:
            print("Generation failed: contradiction encountered!", file=sys.stderr)
            if args.stats:
                print(f"Stats: {grid_obj.stats}", file=sys.stderr)
            sys.exit(1)

        result_grid = grid_obj.get_result()
        if result_grid is None:
            print("Generation failed!", file=sys.stderr)
            sys.exit(1)

        # Convert pattern tiles back to symbol grid
        result = []
        for y in range(args.height):
            row = []
            for x in range(args.width):
                tile_name = result_grid[y][x]
                if tile_name is None:
                    row.append("?")
                    continue
                tile = model.tile_set.get_tile(tile_name)
                row.append(model._pattern_at(tile.data, 0, 0))
            result.append(row)

    elif args.mode == "custom":
        try:
            tileset = TileSet.from_json(args.tileset)
        except Exception as e:
            print(f"Error loading tile set: {e}", file=sys.stderr)
            sys.exit(1)

        if args.symmetrize:
            tileset.make_all_symmetric()

        warnings = tileset.validate()
        for w in warnings:
            print(f"Warning: {w}", file=sys.stderr)

        grid_obj = WFCGrid(tileset, args.width, args.height, periodic=args.periodic, seed=args.seed)
        success = grid_obj.run()

        if not success:
            print("Generation failed: contradiction encountered!", file=sys.stderr)
            if args.stats:
                print(f"Stats: {grid_obj.stats}", file=sys.stderr)
            sys.exit(1)

        result = grid_obj.get_result()

    elif args.mode in tileset_creators:
        tileset = tileset_creators[args.mode]()
        warnings = tileset.validate()
        for w in warnings:
            print(f"Warning: {w}", file=sys.stderr)

        grid_obj = WFCGrid(tileset, args.width, args.height, periodic=args.periodic, seed=args.seed)
        success = grid_obj.run()

        if not success:
            print("Generation failed: contradiction encountered!", file=sys.stderr)
            if args.stats:
                print(f"Stats: {grid_obj.stats}", file=sys.stderr)
            sys.exit(1)

        result = grid_obj.get_result()
    else:
        parser.print_help()
        sys.exit(1)

    if result is None:
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)

    # Print stats if requested
    if args.stats:
        print(f"Stats: {grid_obj.stats}", file=sys.stderr)

    # Render output
    if args.output:
        ext = args.output.rsplit(".", 1)[-1].lower()
        if ext == "html":
            content = Renderer.render_html(result, cell_size=args.cell_size, title=f"WFC {args.mode}")
        elif ext == "svg":
            content = Renderer.render_svg(result, cell_size=args.cell_size, title=f"WFC {args.mode}")
        elif ext == "png":
            png_bytes = Renderer.render_png(result, cell_size=args.cell_size, title=f"WFC {args.mode}")
            if png_bytes is None:
                print("PNG rendering requires Pillow. Install with: pip install Pillow", file=sys.stderr)
                sys.exit(1)
            with open(args.output, "wb") as f:
                f.write(png_bytes)
            print(f"Output written to {args.output}")
            if args.stats:
                print(f"Stats: {grid_obj.stats}")
            return
        else:
            content = Renderer.render_plain(result)

        with open(args.output, "w") as f:
            f.write(content)
        print(f"Output written to {args.output}")
    else:
        print(Renderer.render_colored(result))
        print()
        print(Renderer.render_plain(result))

    if args.stats:
        print(f"Stats: {grid_obj.stats}")


if __name__ == "__main__":
    main()