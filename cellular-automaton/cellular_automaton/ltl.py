"""Larger than Life (LtL) cellular automata.

Larger than Life is a family of Life-like cellular automata that use
*larger neighbourhoods* than the standard 3×3 Moore neighbourhood.  A LtL
rule is specified as ``B<birth>/S<survive>/R<radius>`` where birth and
survive are neighbour-count ranges and radius can be 1, 2, 3, or more.

For example, the rule **B5678/S45678/R5** (Boon) uses a 5×5 neighbourhood
and produces beautiful "blob" patterns.

This module provides:

* :class:`LargerThanLifeRule` — a configurable LtL rule with arbitrary radius.
* :func:`parse_ltl_notation` — parse ``B/S/R`` notation strings.
* Preset registry of well-known LtL rules.
"""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

import numpy as np

from .rules import Rule
from .vectorized import neighbour_sum_2d


class LargerThanLifeRule(Rule):
    """Larger than Life rule with configurable neighbourhood radius.

    Parameters
    ----------
    birth : iterable of int
        Neighbour counts that cause a dead cell to be born.
    survive : iterable of int
        Neighbour counts that cause an alive cell to survive.
    radius : int
        Neighbourhood radius (1 = standard Life, 2 = 5×5, etc.).
    name : str
        Rule name.

    Examples
    --------
    >>> rule = LargerThanLifeRule((5678,), (45678,), radius=5, name="Boon")
    """

    dimensions = 2

    def __init__(
        self,
        birth: Iterable[int] = (5678,),
        survive: Iterable[int] = (45678,),
        radius: int = 2,
        name: str = "LtL",
    ) -> None:
        if radius < 1:
            raise ValueError(f"radius must be >= 1, got {radius}")
        self.birth = frozenset(birth)
        self.survive = frozenset(survive)
        self.radius = radius
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def apply(self, neighbourhood: np.ndarray) -> int:
        centre = int(neighbourhood[neighbourhood.shape[0] // 2, neighbourhood.shape[1] // 2])
        count = int(neighbourhood.sum()) - centre
        if centre == 1:
            return 1 if count in self.survive else 0
        return 1 if count in self.birth else 0

    def step_vectorized(
        self,
        grid: np.ndarray,
        mode: str = "periodic",
        fixed_value: int = 0,
    ) -> np.ndarray:
        """Vectorised stepping for larger-radius Life-like rules."""
        grid_int = (grid > 0).astype(np.int32)
        n = neighbour_sum_2d(grid_int, radius=self.radius, mode=mode, fixed_value=fixed_value)
        alive = grid_int
        new = np.zeros_like(grid_int)
        for s in self.survive:
            new |= alive & (n == s)
        for b in self.birth:
            new |= (1 - alive) & (n == b)
        return new.astype(np.uint8)

    def rule_string(self) -> str:
        """Return B/S/R notation."""
        b = "B" + "".join(str(n) for n in sorted(self.birth))
        s = "S" + "".join(str(n) for n in sorted(self.survive))
        return f"{b}/{s}/R{self.radius}"


def parse_ltl_notation(s: str) -> Optional[LargerThanLifeRule]:
    """Parse Larger-than-Life notation: ``Bxx/Sxx/Rn``.

    Examples
    --------
    >>> rule = parse_ltl_notation("B5678/S45678/R5")
    >>> rule.radius
    5
    >>> rule.birth
    frozenset({5, 6, 7, 8})
    """
    import re

    m = re.fullmatch(r"\s*B([0-9]*)\s*/\s*S([0-9]*)\s*/\s*R([0-9]+)\s*", s, re.IGNORECASE)
    if not m:
        return None
    birth = tuple(int(c) for c in m.group(1))
    survive = tuple(int(c) for c in m.group(2))
    radius = int(m.group(3))
    return LargerThanLifeRule(birth, survive, radius=radius, name=s.strip())


# Well-known LtL presets.
LTL_PRESETS: dict = {
    "Boon":         LargerThanLifeRule((5678,), (45678,), radius=5, name="Boon"),
    "Grenville":    LargerThanLifeRule((34,), (234,), radius=3, name="Grenville"),
    "Bugs":         LargerThanLifeRule((567,), (456,), radius=4, name="Bugs"),
    "B3678/S45678/R5": parse_ltl_notation("B3678/S45678/R5"),
    "B3/S23/R2":    parse_ltl_notation("B3/S23/R2"),
}

# Clean up None entries from failed parses
LTL_PRESETS = {k: v for k, v in LTL_PRESETS.items() if v is not None}