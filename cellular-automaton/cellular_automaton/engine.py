"""Core cellular automaton engine.

Provides ``CellularAutomaton`` — a flexible grid-based CA engine supporting
1D and 2D rules, boundary conditions, random / seeded initial states, step
history, cycle detection, statistics, serialization, and efficient vectorised
stepping via NumPy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from .rules import Rule, ElementaryRule, GameOfLifeRule, CustomRule
from .vectorized import (
    step_life_vectorized,
    step_elementary_vectorized,
    wolfram_rule_table,
)


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


@dataclass
class CAStats:
    """Aggregate statistics over a run."""
    steps: int = 0
    final_alive: int = 0
    total_births: int = 0
    total_deaths: int = 0
    max_alive: int = 0
    min_alive: int = 0
    stable: bool = False
    cycle_detected: bool = False
    cycle_length: int = 0

    def to_dict(self) -> Dict:
        return {
            "steps": self.steps,
            "final_alive": self.final_alive,
            "total_births": self.total_births,
            "total_deaths": self.total_deaths,
            "max_alive": self.max_alive,
            "min_alive": self.min_alive,
            "stable": self.stable,
            "cycle_detected": self.cycle_detected,
            "cycle_length": self.cycle_length,
        }


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
        # Spacetime history for 1D rules — each row is one timestep.
        self.spacetime: List[np.ndarray] = []
        self._max_spacetime = 10000

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
        self.spacetime.clear()

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
        self.spacetime.clear()

    def center_seed(self) -> None:
        """Place a single live cell in the centre (classic 1D seed)."""
        self.grid[:] = 0
        self.grid[0, self.width // 2] = 1
        self.step_count = 0
        self.history.clear()
        self.spacetime.clear()

    # ------------------------------------------------------------------
    # Boundary padding
    # ------------------------------------------------------------------

    def _pad(self) -> np.ndarray:
        """Return a padded copy of the grid according to boundary mode.

        For ``reflect`` we use ``edge`` (clamp/Neumann) for consistency with
        the vectorized paths — the out-of-bounds cell mirrors the nearest edge
        cell (zero-gradient).  NumPy's ``reflect`` mode mirrors the
        second-from-edge cell, which is a different boundary condition.
        """
        r = self.rule.radius
        if r == 0:
            return self.grid
        if self.boundary == Boundary.PERIODIC:
            return np.pad(self.grid, r, mode="wrap")
        if self.boundary == Boundary.REFLECT:
            # 'edge' = clamp = Neumann zero-gradient, consistent with vectorized paths.
            return np.pad(self.grid, r, mode="edge")
        if self.boundary == Boundary.FIXED:
            return np.pad(self.grid, r, mode="constant", constant_values=self.fixed_value)
        # zero
        return np.pad(self.grid, r, mode="constant", constant_values=0)

    # ------------------------------------------------------------------
    # Stepping — vectorised fast paths + generic fallback
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
        if len(self.history) < self._max_history:
            self.history.append(prev)
        # Record spacetime for 1D rules.
        if self.rule.dimensions == 1 and len(self.spacetime) < self._max_spacetime:
            self.spacetime.append(self.grid[0].copy())

        new_grid = self._compute_next()
        changed = int(np.count_nonzero(new_grid != self.grid))
        self.grid = new_grid
        self.step_count += 1
        return StepResult(self.step_count, self.grid.copy(), int(self.grid.sum()), changed)

    def _compute_next(self) -> np.ndarray:
        """Compute the next grid using a fast vectorised path when possible."""
        rule = self.rule
        mode = self.boundary.value

        # Fast path: ElementaryRule (1D)
        if isinstance(rule, ElementaryRule):
            table = wolfram_rule_table(rule.number)
            return step_elementary_vectorized(
                self.grid[0], table, mode=mode, fixed_value=self.fixed_value
            ).reshape(1, -1)

        # Fast path: GameOfLifeRule (2D outer totalistic, radius 1)
        if isinstance(rule, GameOfLifeRule) and rule.radius == 1:
            return step_life_vectorized(
                self.grid, rule.birth, rule.survive,
                mode=mode, fixed_value=self.fixed_value,
            )

        # Generic fallback: per-cell Python loop (CustomRule or radius > 1).
        return self._compute_next_generic()

    def _compute_next_generic(self) -> np.ndarray:
        padded = self._pad()
        new_grid = np.zeros_like(self.grid)
        r = self.rule.radius
        if self.rule.dimensions == 1:
            for x in range(self.width):
                neighbourhood = padded[0, x : x + 2 * r + 1]
                new_grid[0, x] = self.rule.apply(neighbourhood)
        else:
            for y in range(self.height):
                for x in range(self.width):
                    neighbourhood = padded[y : y + 2 * r + 1, x : x + 2 * r + 1]
                    new_grid[y, x] = self.rule.apply(neighbourhood)
        return new_grid

    # ------------------------------------------------------------------
    # Run with statistics & cycle detection
    # ------------------------------------------------------------------

    def run(self, steps: int, detect_cycles: bool = True) -> CAStats:
        """Run for ``steps`` steps, collecting statistics and detecting cycles.

        Stops early if a stable state or a cycle is found.
        """
        if steps < 0:
            raise ValueError("steps must be non-negative")
        stats = CAStats()
        seen: Dict[int, int] = {}  # state hash -> step number
        if detect_cycles:
            seen[self.get_state_hash()] = 0
        stats.max_alive = self.alive_count()
        stats.min_alive = self.alive_count()

        for _ in range(steps):
            prev_grid = self.grid.copy()
            result = self._single_step()
            stats.steps += 1
            stats.final_alive = result.alive
            # Births = dead cells that became alive; deaths = alive cells that died.
            # Compare prev_grid (before step) with current grid (after step).
            births = int(np.count_nonzero((prev_grid == 0) & (self.grid == 1)))
            deaths = int(np.count_nonzero((prev_grid == 1) & (self.grid == 0)))
            stats.total_births += births
            stats.total_deaths += deaths
            stats.max_alive = max(stats.max_alive, result.alive)
            stats.min_alive = min(stats.min_alive, result.alive)

            if result.changed == 0:
                stats.stable = True
                break
            if detect_cycles:
                h = self.get_state_hash()
                if h in seen:
                    stats.cycle_detected = True
                    stats.cycle_length = self.step_count - seen[h]
                    break
                seen[h] = self.step_count
        return stats

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

    def get_spacetime_array(self) -> np.ndarray:
        """Return the accumulated 1D spacetime history as a 2D array.

        Row 0 is the initial state; each subsequent row is one timestep.
        The current grid is appended as the last row.
        """
        rows = list(self.spacetime) + [self.grid[0]]
        return np.array(rows, dtype=np.uint8)

    def copy(self) -> "CellularAutomaton":
        """Return a deep copy."""
        ca = CellularAutomaton(
            self.rule, self.width, self.height, self.boundary, self.fixed_value
        )
        ca.grid = self.grid.copy()
        ca.step_count = self.step_count
        ca.history = [h.copy() for h in self.history]
        ca.spacetime = [s.copy() for s in self.spacetime]
        return ca

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        """Serialize the CA state to a JSON-compatible dict."""
        return {
            "rule": self.rule.name,
            "rule_type": type(self.rule).__name__,
            "width": self.width,
            "height": self.height,
            "boundary": self.boundary.value,
            "fixed_value": self.fixed_value,
            "step_count": self.step_count,
            "grid": self.grid.tolist(),
            "spacetime": [s.tolist() for s in self.spacetime],
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str) -> None:
        """Save state to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict) -> "CellularAutomaton":
        """Reconstruct a CA from a serialized dict."""
        from .rules import get_rule, parse_bx_sx_notation
        rule_name = data["rule"]
        # Try registry first; if not found, try Bxx/Sxx notation (for
        # custom-named GameOfLife rules like "B36/S23" that aren't in RULES).
        try:
            rule = get_rule(rule_name)
        except KeyError:
            parsed = parse_bx_sx_notation(rule_name)
            if parsed is not None:
                rule = parsed
            else:
                raise KeyError(
                    f"Cannot reconstruct rule {rule_name!r}: not in registry "
                    f"and not valid Bxx/Sxx notation"
                )
        ca = cls(
            rule,
            width=data["width"],
            height=data["height"],
            boundary=data["boundary"],
            fixed_value=data.get("fixed_value", 0),
        )
        ca.grid = np.array(data["grid"], dtype=np.uint8)
        ca.step_count = data.get("step_count", 0)
        ca.spacetime = [np.array(s, dtype=np.uint8) for s in data.get("spacetime", [])]
        return ca

    @classmethod
    def load(cls, path: str) -> "CellularAutomaton":
        """Load state from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return (
            f"CellularAutomaton(rule={self.rule.name!r}, "
            f"width={self.width}, height={self.height}, "
            f"boundary={self.boundary.value!r}, step={self.step_count})"
        )