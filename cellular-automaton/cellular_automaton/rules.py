"""Rule definitions for 1D and 2D cellular automata.

This module provides:
  * ``Rule``           — abstract base class defining the rule interface.
  * ``ElementaryRule`` — Wolfram's 256 elementary 1D rules (radius 1).
  * ``GameOfLifeRule`` — Conway's Game of Life (2D, totalistic).
  * ``CustomRule``     — user-defined arbitrary neighbourhood rule.
  * ``RULES``          — registry of named builtin rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


class Rule(ABC):
    """Abstract base class — subclasses define how a cell updates from its neighbourhood."""

    radius: int = 1
    dimensions: int = 1

    @abstractmethod
    def apply(self, neighbourhood: np.ndarray) -> int:
        """Return the new state (0/1) given a neighbourhood slice.

        For 1D rules *neighbourhood* is a length ``2*radius+1`` array centred on the cell.
        For 2D rules it is a ``(2*radius+1, 2*radius+1)`` array centred on the cell.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Short human-readable name for the rule."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r})"


# ---------------------------------------------------------------------------
# 1D Elementary Cellular Automata (Wolfram)
# ---------------------------------------------------------------------------


class ElementaryRule(Rule):
    """Wolfram's elementary 1D CA rule (radius 1).

    There are 2^(2^3) = 256 possible rules.  Rule 30, 90, 110 and 184 are
    well-known examples.
    """

    dimensions = 1
    radius = 1

    def __init__(self, number: int) -> None:
        if not 0 <= number <= 255:
            raise ValueError(f"Elementary rule number must be in [0, 255], got {number}")
        self.number = number
        # Pre-compute the 8-bit lookup: index = neighbourhood pattern as a 3-bit int.
        self._table: List[int] = [
            (number >> i) & 1 for i in range(8)
        ]  # index 0 -> 000, index 7 -> 111

    @property
    def name(self) -> str:
        return f"Rule{self.number}"

    def apply(self, neighbourhood: np.ndarray) -> int:
        # neighbourhood is [left, centre, right] with values 0/1.
        left, centre, right = int(neighbourhood[0]), int(neighbourhood[1]), int(neighbourhood[2])
        index = (left << 2) | (centre << 1) | right
        return self._table[index]

    def wolfram_table(self) -> str:
        """Return a human-readable table of all 8 neighbourhood -> output mappings."""
        lines = []
        for i in range(8):
            pattern = format(i, "03b")
            output = self._table[i]
            lines.append(f"  {pattern} -> {output}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2D totalistic rules — Conway's Game of Life and friends
# ---------------------------------------------------------------------------


class GameOfLifeRule(Rule):
    """Conway's Game of Life — B3/S23.

    Also supports arbitrary outer-totalistic rules via ``birth`` and ``survive``
    sets, e.g. HighLife (B36/S23), Seeds (B2/S), Day & Night (B3678/S34678).
    """

    dimensions = 2
    radius = 1

    def __init__(
        self,
        birth: Iterable[int] = (3,),
        survive: Iterable[int] = (2, 3),
        name: str = "GameOfLife",
    ) -> None:
        self.birth = frozenset(birth)
        self.survive = frozenset(survive)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def apply(self, neighbourhood: np.ndarray) -> int:
        # neighbourhood is 3x3; centre is [1, 1]; count neighbours excluding centre.
        centre = int(neighbourhood[1, 1])
        count_neighbours = int(neighbourhood.sum()) - centre
        if centre == 1:
            return 1 if count_neighbours in self.survive else 0
        else:
            return 1 if count_neighbours in self.birth else 0

    def rule_string(self) -> str:
        """Return Bxx/Sxx notation."""
        b = "B" + "".join(str(n) for n in sorted(self.birth))
        s = "S" + "".join(str(n) for n in sorted(self.survive))
        return f"{b}/{s}"


# ---------------------------------------------------------------------------
# Custom arbitrary neighbourhood rule (works for any radius / dimensions)
# ---------------------------------------------------------------------------


class CustomRule(Rule):
    """User-defined rule given a Python callable.

    The callable receives the neighbourhood numpy array and returns 0 or 1.
    """

    def __init__(
        self,
        func,
        radius: int = 1,
        dimensions: int = 2,
        name: str = "Custom",
    ) -> None:
        self._func = func
        self.radius = radius
        self.dimensions = dimensions
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def apply(self, neighbourhood: np.ndarray) -> int:
        result = self._func(neighbourhood)
        return int(result)


# ---------------------------------------------------------------------------
# Builtin rule registry
# ---------------------------------------------------------------------------


def _make_gol_variants() -> Dict[str, Rule]:
    return {
        "GameOfLife": GameOfLifeRule((3,), (2, 3), "GameOfLife"),
        "HighLife": GameOfLifeRule((3, 6), (2, 3), "HighLife"),
        "Seeds": GameOfLifeRule((2,), (), "Seeds"),
        "DayNight": GameOfLifeRule((3, 6, 7, 8), (3, 4, 6, 7, 8), "DayNight"),
        "LifeWithoutDeath": GameOfLifeRule((3,), (0, 1, 2, 3, 4, 5, 6, 7, 8), "LifeWithoutDeath"),
        "Replicator": GameOfLifeRule((1, 3, 5, 7,), (1, 3, 5, 7), "Replicator"),
        "Maze": GameOfLifeRule((3,), (1, 2, 3, 4, 5), "Maze"),
        "Mazectric": GameOfLifeRule((3,), (1, 2, 3, 4), "Mazectric"),
        "TwoByTwo": GameOfLifeRule((3, 6), (1, 2, 5), "TwoByTwo"),
        "Anneal": GameOfLifeRule((4, 6, 7, 8), (3, 5, 6, 7, 8), "Anneal"),
        "Coral": GameOfLifeRule((3,), (4, 5, 6, 7, 8), "Coral"),
        "Diamoeba": GameOfLifeRule((3, 5, 6, 7, 8), (3, 5, 6, 7, 8), "Diamoeba"),
        "Majority": GameOfLifeRule((5, 6, 7, 8), (4, 5, 6, 7, 8), "Majority"),
        "WalledCities": GameOfLifeRule((4, 5, 6, 7, 8), (2, 3, 4, 5), "WalledCities"),
        "Gnarl": GameOfLifeRule((1,), (1, 2, 3, 4, 5), "Gnarl"),
    }


RULES: Dict[str, Rule] = {
    **{f"Rule{n}": ElementaryRule(n) for n in range(256)},
    **_make_gol_variants(),
}


def get_rule(name: str) -> Rule:
    """Look up a builtin rule by name (case-insensitive)."""
    if name in RULES:
        return RULES[name]
    # case-insensitive lookup
    lower_map = {k.lower(): v for k, v in RULES.items()}
    if name.lower() in lower_map:
        return lower_map[name.lower()]
    # Try Bxx/Sxx notation
    parsed = parse_bx_sx_notation(name)
    if parsed is not None:
        return parsed
    raise KeyError(f"Unknown rule: {name!r}")


def parse_bx_sx_notation(s: str) -> Optional[GameOfLifeRule]:
    """Parse Bxx/Sxx notation like 'B36/S23' into a GameOfLifeRule."""
    import re

    m = re.fullmatch(r"\s*B([0-8]*)\s*/\s*S([0-8]*)\s*", s, re.IGNORECASE)
    if not m:
        return None
    birth = tuple(int(c) for c in m.group(1))
    survive = tuple(int(c) for c in m.group(2))
    return GameOfLifeRule(birth, survive, name=s.strip())


# Alias
get = get_rule