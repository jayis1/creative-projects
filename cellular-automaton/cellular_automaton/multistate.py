"""Multi-state cellular automata.

This module provides support for cellular automata with more than two states.
Unlike the binary (0/1) rules in :mod:`rules`, multi-state CAs can have cells
in several discrete states (e.g. 0, 1, 2, 3) with transition rules that depend
on the current state and the configuration of neighbours.

Included multi-state CA types:

* **Wireworld** — a simulated electronic circuit board.  States:
  empty (0), electron head (1), electron tail (2), conductor (3).
  Electron heads become tails, tails become conductors, and conductors
  become heads if exactly 1 or 2 of their neighbours are heads.

* **Brian's Brain** — a three-state CA producing beautiful wave patterns.
  States: dead (0), alive (1), dying (2).  Dead cells with exactly 2 alive
  neighbours become alive; alive cells become dying; dying cells become dead.

* **Forest Fire** — a simple ecological model.  States: empty (0), tree (1),
  burning (2).  Trees ignite if any neighbour is burning (or by spontaneous
  combustion with probability *p*).  Burning cells become empty; empty cells
  grow new trees with probability *g*.

* **Cyclic** — a generalised cyclic CA where each cell advances to the next
  state if enough of its neighbours are in the next state.

* **Immigration** — a two-species Game of Life variant where cells have a
  species label that influences birth.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Multi-state rule base class
# ---------------------------------------------------------------------------


class MultiStateRule:
    """Base class for multi-state CA rules.

    Subclasses implement :meth:`step` which takes the full grid and returns
    the next generation grid.  Unlike binary rules, multi-state rules receive
    the *entire* grid (not a per-cell neighbourhood) so they can use efficient
    NumPy vectorised operations.

    Attributes
    ----------
    n_states : int
        Number of distinct cell states (0 .. n_states-1).
    dimensions : int
        Grid dimensionality (1 or 2).
    """

    n_states: int = 2
    dimensions: int = 2
    radius: int = 1

    def step(self, grid: np.ndarray, mode: str = "periodic", fixed_value: int = 0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Compute the next grid state.

        Parameters
        ----------
        grid : np.ndarray
            Current grid (height × width for 2D, 1 × width for 1D).
        mode : str
            Boundary mode (``periodic``, ``fixed``, ``reflect``, ``zero``).
        fixed_value : int
            Value used when ``mode == "fixed"``.
        rng : np.random.Generator, optional
            Random number generator for stochastic rules.
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Short human-readable name."""
        return type(self).__name__

    def state_colors(self) -> Dict[int, Tuple[int, int, int]]:
        """Return a mapping of state value → RGB colour for rendering."""
        return {}

    # Provide compatibility with the binary Rule interface.
    def apply(self, neighbourhood: np.ndarray) -> int:
        """Per-cell apply — fallback for generic compatibility (not used by fast path)."""
        raise NotImplementedError(
            "Multi-state rules use grid-level step(), not per-cell apply()."
        )


# ---------------------------------------------------------------------------
# Wireworld
# ---------------------------------------------------------------------------


class WireworldRule(MultiStateRule):
    """Wireworld cellular automaton.

    States:
        0 = empty, 1 = electron head, 2 = electron tail, 3 = conductor.

    Rules:
        * Head → Tail
        * Tail → Conductor
        * Conductor → Head if exactly 1 or 2 Moore neighbours are heads
        * Empty → Empty
    """

    n_states = 4
    dimensions = 2
    radius = 1

    EMPTY = 0
    HEAD = 1
    TAIL = 2
    CONDUCTOR = 3

    def __init__(self, name: str = "Wireworld") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def step(self, grid: np.ndarray, mode: str = "periodic", fixed_value: int = 0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        new = grid.copy()
        # Head → Tail
        new[grid == self.HEAD] = self.TAIL
        # Tail → Conductor
        new[grid == self.TAIL] = self.CONDUCTOR

        # Count head neighbours for conductor cells.
        head_mask = (grid == self.HEAD).astype(np.int32)
        n_heads = _moore_neighbour_count(head_mask, mode)

        # Conductor → Head if 1 or 2 head neighbours.
        conductor_mask = grid == self.CONDUCTOR
        new[conductor_mask & (n_heads >= 1) & (n_heads <= 2)] = self.HEAD
        # Conductors with 0 or 3+ head neighbours stay conductors.
        return new.astype(np.uint8)

    def state_colors(self) -> Dict[int, Tuple[int, int, int]]:
        return {
            0: (0, 0, 0),         # empty — black
            1: (255, 0, 0),       # head — red
            2: (200, 100, 0),     # tail — orange
            3: (80, 140, 255),    # conductor — blue
        }


# ---------------------------------------------------------------------------
# Brian's Brain
# ---------------------------------------------------------------------------


class BriansBrainRule(MultiStateRule):
    """Brian's Brain — a three-state CA.

    States:
        0 = dead, 1 = alive, 2 = dying.

    Rules:
        * Dead → Alive if exactly 2 alive neighbours
        * Alive → Dying
        * Dying → Dead
    """

    n_states = 3
    dimensions = 2
    radius = 1

    DEAD = 0
    ALIVE = 1
    DYING = 2

    def __init__(self, name: str = "BriansBrain") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def step(self, grid: np.ndarray, mode: str = "periodic", fixed_value: int = 0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        new = np.zeros_like(grid)
        # Alive → Dying
        new[grid == self.ALIVE] = self.DYING
        # Dying → Dead (already 0)

        # Count alive neighbours.
        alive_mask = (grid == self.ALIVE).astype(np.int32)
        n_alive = _moore_neighbour_count(alive_mask, mode)

        # Dead → Alive if exactly 2 alive neighbours.
        dead_mask = grid == self.DEAD
        new[dead_mask & (n_alive == 2)] = self.ALIVE
        return new.astype(np.uint8)

    def state_colors(self) -> Dict[int, Tuple[int, int, int]]:
        return {
            0: (10, 10, 30),      # dead — dark blue
            1: (100, 255, 200),   # alive — cyan-green
            2: (50, 100, 180),    # dying — blue
        }


# ---------------------------------------------------------------------------
# Forest Fire
# ---------------------------------------------------------------------------


class ForestFireRule(MultiStateRule):
    """Forest fire CA — a simple ecological model.

    States:
        0 = empty, 1 = tree, 2 = burning.

    Rules:
        * Burning → Empty
        * Tree → Burning if any neighbour is burning, or spontaneously with probability *p*
        * Empty → Tree with probability *g*

    Parameters
    ----------
    p : float
        Spontaneous ignition probability per tree per step.
    g : float
        Tree growth probability per empty cell per step.
    """

    n_states = 3
    dimensions = 2
    radius = 1

    EMPTY = 0
    TREE = 1
    BURNING = 2

    def __init__(self, p: float = 0.001, g: float = 0.05, name: str = "ForestFire") -> None:
        self.p = p
        self.g = g
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def step(self, grid: np.ndarray, mode: str = "periodic", fixed_value: int = 0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        if rng is None:
            rng = np.random.default_rng()
        new = np.zeros_like(grid)

        # Burning → Empty
        # (already 0 in new)

        # Tree → Burning if any burning neighbour, or spontaneously.
        burning_mask = (grid == self.BURNING).astype(np.int32)
        n_burning = _moore_neighbour_count(burning_mask, mode)

        tree_mask = grid == self.TREE
        ignite = tree_mask & ((n_burning >= 1) | (rng.random(grid.shape) < self.p))
        new[ignite] = self.BURNING

        # Trees that don't ignite stay trees.
        new[tree_mask & (new != self.BURNING)] = self.TREE

        # Empty → Tree with probability g.
        empty_mask = grid == self.EMPTY
        grow = empty_mask & (rng.random(grid.shape) < self.g)
        new[grow] = self.TREE
        return new.astype(np.uint8)

    def state_colors(self) -> Dict[int, Tuple[int, int, int]]:
        return {
            0: (60, 40, 20),       # empty — brown
            1: (20, 120, 30),      # tree — green
            2: (255, 80, 0),       # burning — red-orange
        }


# ---------------------------------------------------------------------------
# Cyclic CA
# ---------------------------------------------------------------------------


class CyclicRule(MultiStateRule):
    """Cyclic cellular automaton.

    Each cell in state *k* advances to state *k+1 (mod n)* if at least
    *threshold* of its neighbours are in state *k+1 (mod n)*.

    Parameters
    ----------
    n_states : int
        Total number of states (cycle length).
    threshold : int
        Minimum number of neighbours in the next state required to advance.
    """

    dimensions = 2
    radius = 1

    def __init__(self, n_states: int = 14, threshold: int = 3, name: str = "Cyclic") -> None:
        if n_states < 2:
            raise ValueError("n_states must be >= 2")
        self.n_states = n_states
        self.threshold = threshold
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def step(self, grid: np.ndarray, mode: str = "periodic", fixed_value: int = 0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        new = grid.copy()
        for s in range(self.n_states):
            next_s = (s + 1) % self.n_states
            # Count neighbours in the next state.
            next_mask = (grid == next_s).astype(np.int32)
            n_next = _moore_neighbour_count(next_mask, mode)
            # Cells in state s advance to next_s if enough neighbours.
            advance = (grid == s) & (n_next >= self.threshold)
            new[advance] = next_s
        return new

    def state_colors(self) -> Dict[int, Tuple[int, int, int]]:
        """Generate a rainbow colour map for the cyclic states."""
        colors = {}
        for i in range(self.n_states):
            hue = i / self.n_states
            # Simple HSV → RGB (s=1, v=1).
            h6 = hue * 6
            c = 255
            x = int(c * (1 - abs((h6 % 2) - 1)))
            if h6 < 1: r, g, b = c, x, 0
            elif h6 < 2: r, g, b = x, c, 0
            elif h6 < 3: r, g, b = 0, c, x
            elif h6 < 4: r, g, b = 0, x, c
            elif h6 < 5: r, g, b = x, 0, c
            else: r, g, b = c, 0, x
            colors[i] = (r, g, b)
        return colors


# ---------------------------------------------------------------------------
# Immigration (two-species Game of Life)
# ---------------------------------------------------------------------------


class ImmigrationRule(MultiStateRule):
    """Immigration CA — two-species Game of Life.

    States: 0 = dead, 1 = species A, 2 = species B.

    Rules follow standard B3/S23 with the modification that a dead cell
    is born with the colour of the *majority* among its 3 alive neighbours.
    """

    n_states = 3
    dimensions = 2
    radius = 1

    DEAD = 0
    A = 1
    B = 2

    def __init__(self, name: str = "Immigration") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def step(self, grid: np.ndarray, mode: str = "periodic", fixed_value: int = 0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        a_mask = (grid == self.A).astype(np.int32)
        b_mask = (grid == self.B).astype(np.int32)
        alive = a_mask + b_mask
        n_alive = _moore_neighbour_count(alive, mode)
        n_a = _moore_neighbour_count(a_mask, mode)
        n_b = _moore_neighbour_count(b_mask, mode)

        new = np.zeros_like(grid)

        # Survive: alive cells with 2 or 3 neighbours stay alive (keep colour).
        survive = (alive == 1) & ((n_alive == 2) | (n_alive == 3))
        new[survive & (grid == self.A)] = self.A
        new[survive & (grid == self.B)] = self.B

        # Birth: dead cells with exactly 3 neighbours — adopt majority colour.
        birth = (grid == self.DEAD) & (n_alive == 3)
        new[birth & (n_a >= n_b)] = self.A
        new[birth & (n_b > n_a)] = self.B
        return new.astype(np.uint8)

    def state_colors(self) -> Dict[int, Tuple[int, int, int]]:
        return {
            0: (0, 0, 0),         # dead — black
            1: (255, 100, 100),    # species A — red
            2: (100, 100, 255),    # species B — blue
        }


# ---------------------------------------------------------------------------
# Helper: Moore neighbour count for multi-state grids
# ---------------------------------------------------------------------------


def _moore_neighbour_count(mask: np.ndarray, mode: str = "periodic") -> np.ndarray:
    """Count Moore neighbours (8-connected) for each cell of a binary mask.

    Parameters
    ----------
    mask : np.ndarray
        2D array of 0/1 values.
    mode : str
        Boundary mode: ``periodic``, ``fixed``, ``reflect``, ``zero``.
    """
    if mask.ndim == 1:
        # 1D fallback
        if mode == "periodic":
            left = np.roll(mask, 1)
            right = np.roll(mask, -1)
        elif mode == "reflect":
            left = np.empty_like(mask)
            right = np.empty_like(mask)
            left[0] = mask[0]
            left[1:] = mask[:-1]
            right[-1] = mask[-1]
            right[:-1] = mask[1:]
        else:
            fv = 0
            left = np.empty_like(mask)
            right = np.empty_like(mask)
            left[0] = fv
            left[1:] = mask[:-1]
            right[-1] = fv
            right[:-1] = mask[1:]
        return (left + right).astype(np.int32)

    if mode == "periodic":
        padded = np.pad(mask, 1, mode="wrap")
    elif mode == "reflect":
        padded = np.pad(mask, 1, mode="edge")
    elif mode == "fixed":
        padded = np.pad(mask, 1, mode="constant", constant_values=0)
    else:
        padded = np.pad(mask, 1, mode="constant", constant_values=0)

    return (
        padded[0:-2, 0:-2] + padded[0:-2, 1:-1] + padded[0:-2, 2:] +
        padded[1:-1, 0:-2] + padded[1:-1, 2:] +
        padded[2:, 0:-2] + padded[2:, 1:-1] + padded[2:, 2:]
    ).astype(np.int32)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


MULTISTATE_RULES: Dict[str, MultiStateRule] = {
    "Wireworld": WireworldRule(),
    "BriansBrain": BriansBrainRule(),
    "ForestFire": ForestFireRule(),
    "Cyclic": CyclicRule(n_states=14, threshold=3),
    "Immigration": ImmigrationRule(),
}


def get_multistate_rule(name: str, **kwargs) -> MultiStateRule:
    """Look up a multi-state rule by name (case-insensitive).

    Extra keyword arguments are passed to the rule constructor for
    parameterised rules (e.g. ``ForestFire(p=0.01, g=0.1)``).
    """
    lower_map = {k.lower(): k for k in MULTISTATE_RULES}
    if name.lower() in lower_map:
        key = lower_map[name.lower()]
        if kwargs:
            # Recreate with custom parameters.
            cls = type(MULTISTATE_RULES[key])
            return cls(**kwargs)
        return MULTISTATE_RULES[key]
    raise KeyError(f"Unknown multi-state rule: {name!r}")


def is_multistate_rule(name: str) -> bool:
    """Check whether *name* refers to a multi-state rule."""
    lower = {k.lower() for k in MULTISTATE_RULES}
    return name.lower() in lower