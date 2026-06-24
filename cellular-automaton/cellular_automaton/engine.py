"""Core cellular automaton engine.

Provides ``CellularAutomaton`` — a flexible grid-based CA engine supporting
1D and 2D rules, boundary conditions, random / seeded initial states, step
history, and efficient vectorised stepping via NumPy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from .rules import Rule


class Boundary(str, Enum):
    """Boundary condition for cells outside the grid."""

    PERIODIC = "periodic"  # wrap-around (toroidal)
    FIXED = "fixed"         # out-of-bounds cells are a fixed value
    REFLECT = "reflect"     # mirror edge cells
    ZERO = "zero"           # out-of-bounds = 0


@dataclass
class StepResult:
    """Result of one CA step."""
    step: int
    grid: np.ndarray
    alive: int
    changed: int


class CellularAutomaton:
    """A cellular automaton simulator.

    Parameters
    ----------
    rule : Rule
        Update rule (ElementaryRule / GameOfLifeRule / CustomRule).
    width : int
        Grid width (x dimension).
    height : int, optional
        Grid height (y dimension). For 1D rules this should be omitted (or 1).
    boundary : Boundary
        Boundary condition for edge cells.
    fixed_value : int
        Value used when boundary == FIXED.
    """

    def __init__(
        self,
        rule: Rule,
        width: int,
        height: Optional[int] = None,
        boundary: Union[Boundary, str] = Boundary.PERIODIC,
        fixed_value: int = 0,
    ) -> None:
        if width <= 0:
            raise ValueError(f"width must be positive, got {width}")
        self.rule = rule
        self.width = width
        self.height = height if height is not None else 1
        if self.height <= 0:
            raise ValueError(f"height must be positive, got {self.height}")
        self.boundary = Boundary(boundary)
        self.fixed_value = fixed_value
        self.step_count = 0
        self._validate_dimensions()
        self.grid = np.zeros((self.height, self.width), dtype=np.uint8)
        self.history: List[np.ndarray] = []
        self._max_history = 1000

    # ------------------------------------------------------------------
    # Validation & helpers
    # ------------------------------------------------------------------

    def _validate_dimensions(self) -> None:
        if self.rule.dimensions == 1 and self.height != 1:
            raise ValueError(
                f"1D rule requires height=1, got height={self.height}"
            )

    # ------------------------------------------------------------------
    # Initial state setters
    # ------------------------------------------------------------------

    def set_grid(self, grid: Union[np.ndarray, List[List[int]]]) -> None:
        """Set the grid directly from a 2D array."""
        arr = np.array(grid, dtype=np.uint8)
        if self.rule.dimensions == 1:
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            if arr.shape[0] != 1:
                raise ValueError(f"1D rule requires a single row, got shape {arr.shape}")
        if arr.shape != (self.height, self.width):
            raise ValueError(
                f"grid shape {arr.shape} does not match ({self.height}, {self.width})"
            )
        self.grid = arr.copy()
        self.step_count = 0
        self.history.clear()

    def set_cell(self, x: int, y: int = 0, value: int = 1) -> None:
        """Set a single cell."""
        if not 0 <= x < self.width:
            raise IndexError(f"x={x} out of range [0, {self.width})")
        if not 0 <= y < self.height:
            raise IndexError(f"y={y} out of range [0, {self.height})")
        self.grid[y, x] = value

    def randomize(self, density: float = 0.5, seed: Optional[int] = None) -> None:
        """Fill grid with random 0/1 values at the given density."""
        if not 0.0 <= density <= 1.0:
            raise ValueError(f"density must be in [0,1], got {density}")
        rng = np.random.default_rng(seed)
        self.grid = (rng.random((self.height, self.width)) < density).astype(np.uint8)
        self.step_count = 0
        self.history.clear()

    def center_seed(self) -> None:
        """Place a single live cell in the centre (classic 1D seed)."""
        self.grid[:] = 0
        self.grid[0, self.width // 2] = 1
        self.step_count = 0
        self.history.clear()

    # ------------------------------------------------------------------
    # Boundary padding
    # ------------------------------------------------------------------

    def _pad(self) -> np.ndarray:
        """Return a padded copy of the grid according to boundary mode."""
        r = self.rule.radius
        if r == 0:
            return self.grid
        if self.boundary == Boundary.PERIODIC:
            return np.pad(self.grid, r, mode="wrap")
        if self.boundary == Boundary.REFLECT:
            return np.pad(self.grid, r, mode="reflect")
        if self.boundary == Boundary.FIXED:
            return np.pad(self.grid, r, mode="constant", constant_values=self.fixed_value)
        # zero
        return np.pad(self.grid, r, mode="constant", constant_values=0)

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def step(self, n: int = 1) -> StepResult:
        """Advance the CA by ``n`` steps. Returns the last StepResult."""
        if n < 0:
            raise ValueError("n must be non-negative")
        last: Optional[StepResult] = None
        for _ in range(n):
            last = self._single_step()
        if last is None:
            last = StepResult(self.step_count, self.grid.copy(), int(self.grid.sum()), 0)
        return last

    def _single_step(self) -> StepResult:
        prev = self.grid.copy()
        # store history
        if len(self.history) < self._max_history:
            self.history.append(prev)
        padded = self._pad()
        new_grid = np.zeros_like(self.grid)
        r = self.rule.radius
        # For 1D, height == 1 — iterate over columns.
        if self.rule.dimensions == 1:
            for x in range(self.width):
                neighbourhood = padded[0, x : x + 2 * r + 1]
                new_grid[0, x] = self.rule.apply(neighbourhood)
        else:
            for y in range(self.height):
                for x in range(self.width):
                    neighbourhood = padded[
                        y : y + 2 * r + 1, x : x + 2 * r + 1
                    ]
                    new_grid[y, x] = self.rule.apply(neighbourhood)
        changed = int(np.count_nonzero(new_grid != self.grid))
        self.grid = new_grid
        self.step_count += 1
        return StepResult(self.step_count, self.grid.copy(), int(self.grid.sum()), changed)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def alive_count(self) -> int:
        return int(self.grid.sum())

    def is_stable(self) -> bool:
        """True if the last step changed nothing."""
        if len(self.history) < 1:
            return False
        return bool(np.array_equal(self.history[-1], self.grid))

    def to_list(self) -> List[List[int]]:
        return self.grid.tolist()

    def to_string(self) -> str:
        """Return a compact string representation."""
        if self.rule.dimensions == 1:
            return "".join(str(int(c)) for c in self.grid[0])
        return "\n".join("".join(str(int(c)) for c in row) for row in self.grid)

    def get_state_hash(self) -> int:
        """Return a hash of the current grid for cycle detection."""
        return hash(self.grid.tobytes())

    def copy(self) -> "CellularAutomaton":
        """Return a deep copy."""
        ca = CellularAutomaton(
            self.rule, self.width, self.height, self.boundary, self.fixed_value
        )
        ca.grid = self.grid.copy()
        ca.step_count = self.step_count
        ca.history = [h.copy() for h in self.history]
        return ca

    def __repr__(self) -> str:
        return (
            f"CellularAutomaton(rule={self.rule.name!r}, "
            f"width={self.width}, height={self.height}, "
            f"boundary={self.boundary.value!r}, step={self.step_count})"
        )