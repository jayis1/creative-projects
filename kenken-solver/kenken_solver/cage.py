"""Cage definition and evaluation logic.

A *cage* is a contiguous group of cells sharing a single arithmetic
constraint — a target value and an operator.
"""

from __future__ import annotations

from itertools import permutations, product
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from kenken_solver.types import Cell


# The five valid KenKen cage operators.
VALID_OPS: FrozenSet[str] = frozenset({"+", "-", "*", "/", "="})


class Cage:
    """A cage: a set of cells, an operator, and a target value.

    Operators
    ---------
    ``+``
        Sum of all cell values equals target.
    ``*``
        Product of all cell values equals target.
    ``-``
        Some left-to-right ordering of the values subtracts to the target.
        For two-cell cages this is equivalent to the absolute difference.
    ``/``
        Some left-to-right ordering of the values divides to the target
        (evenly, with no remainder).
    ``=``
        Single-cell cage; the cell value equals the target.

    Parameters
    ----------
    cells:
        Non-empty list of ``(row, col)`` coordinates belonging to the cage.
    op:
        One of ``+``, ``-``, ``*``, ``/``, ``=``.
    target:
        The target value the operator must produce.
    label:
        Optional human-readable label (e.g. ``"A"``, ``"1"``).

    Raises
    ------
    ValueError
        If *cells* is empty, *op* is invalid, *target* is non-positive (for
        non-subtraction operators), or ``=`` is used with more than one cell.
    """

    __slots__ = ("cells", "op", "target", "label")

    def __init__(
        self,
        cells: List[Cell],
        op: str,
        target: int,
        label: str = "",
    ) -> None:
        if not cells:
            raise ValueError("Cage must contain at least one cell")
        if op not in VALID_OPS:
            raise ValueError(
                f"Invalid operator {op!r}; must be one of {sorted(VALID_OPS)}"
            )
        if target <= 0 and op != "-":
            raise ValueError(
                f"Target must be positive for operator {op!r}, got {target}"
            )
        if op == "=" and len(cells) != 1:
            raise ValueError("'=' operator requires exactly one cell")
        self.cells: List[Cell] = list(cells)
        self.op: str = op
        self.target: int = target
        self.label: str = label

    @property
    def size(self) -> int:
        """Number of cells in the cage."""
        return len(self.cells)

    # -- evaluation --------------------------------------------------------

    def _evaluate(self, values: List[int]) -> bool:
        """Evaluate the cage operator on the given list of cell values.

        For subtraction and division, all permutations are checked — the cage
        is satisfied if *any* ordering of the values yields the target when
        applied left-to-right.
        """
        op = self.op
        t = self.target
        if op == "+":
            return sum(values) == t
        if op == "*":
            p = 1
            for v in values:
                p *= v
            return p == t
        if op == "-":
            if len(values) == 1:
                return values[0] == t
            for perm in permutations(values):
                result = perm[0]
                for v in perm[1:]:
                    result = result - v
                if result == t:
                    return True
            return False
        if op == "/":
            if len(values) == 1:
                return values[0] == t
            for perm in permutations(values):
                result = perm[0]
                div_ok = True
                for v in perm[1:]:
                    if v == 0 or result % v != 0:
                        div_ok = False
                        break
                    result = result // v
                if div_ok and result == t:
                    return True
            return False
        if op == "=":
            return len(values) == 1 and values[0] == t
        raise ValueError(f"Unknown operator: {op}")

    def satisfied(self, assignment: Dict[Cell, int]) -> bool:
        """Check whether the cage is satisfied given a (partial) assignment.

        Returns ``True`` (vacuously) if not all cage cells are assigned yet.
        """
        vals = [assignment.get(c) for c in self.cells]
        if any(v is None for v in vals):
            return True
        return self._evaluate([v for v in vals if v is not None])  # type: ignore[list-item]

    # -- analysis ---------------------------------------------------------

    def possible_targets(self, n: int) -> Set[Tuple[str, int]]:
        """Return all ``(op, target)`` pairs achievable by this cage's cells.

        Enumerates all value combinations from 1..*n* (with repetition allowed
        since cage cells may be in different rows/columns) and computes the
        results for each operator.

        This is used for validation and analysis.  The cost is exponential in
        the cage size (``n^k``) but cages are typically ≤5 cells.
        """
        results: Set[Tuple[str, int]] = set()
        k = len(self.cells)
        for combo in product(range(1, n + 1), repeat=k):
            s = sum(combo)
            results.add(("+", s))
            p = 1
            for v in combo:
                p *= v
            results.add(("*", p))
            if k == 2:
                a, b = combo
                results.add(("-", abs(a - b)))
                if b != 0 and a % b == 0:
                    results.add(("/", a // b))
                if a != 0 and b % a == 0:
                    results.add(("/", b // a))
            elif k > 2:
                for perm in permutations(combo):
                    r = perm[0]
                    for v in perm[1:]:
                        r = r - v
                    if r > 0:
                        results.add(("-", r))
                    r2 = perm[0]
                    div_ok = True
                    for v in perm[1:]:
                        if v == 0 or r2 % v != 0:
                            div_ok = False
                            break
                        r2 = r2 // v
                    if div_ok and r2 > 0:
                        results.add(("/", r2))
        if k == 1:
            for v in range(1, n + 1):
                results.add(("=", v))
        return results

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the cage to a plain dict (for JSON)."""
        return {
            "cells": [list(c) for c in self.cells],
            "op": self.op,
            "target": self.target,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cage":
        """Reconstruct a cage from a dict produced by :meth:`to_dict`."""
        return cls(
            cells=[(int(r), int(c)) for r, c in d["cells"]],
            op=d["op"],
            target=int(d["target"]),
            label=d.get("label", ""),
        )

    # -- dunder methods ----------------------------------------------------

    def __repr__(self) -> str:
        return f"Cage(cells={self.cells}, op={self.op!r}, target={self.target})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cage):
            return NotImplemented
        return (
            set(self.cells) == set(other.cells)
            and self.op == other.op
            and self.target == other.target
        )

    def __hash__(self) -> int:
        return hash((frozenset(self.cells), self.op, self.target))


__all__ = ["Cage", "VALID_OPS"]