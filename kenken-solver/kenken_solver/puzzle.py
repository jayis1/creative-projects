"""Immutable KenKen puzzle representation with validation and serialization."""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Set, Tuple

from kenken_solver.cage import Cage
from kenken_solver.types import Cell, is_contiguous

logger = logging.getLogger(__name__)


class KenKenPuzzle:
    """Immutable representation of a KenKen puzzle.

    Parameters
    ----------
    size:
        Grid dimension (the puzzle is *size*×*size*).  Must be ≥ 2.
    cages:
        List of :class:`~kenken_solver.cage.Cage` objects that together cover
        every cell exactly once.
    validate:
        When ``True`` (default) the cages are checked for full coverage, no
        overlaps, contiguity, and operator consistency.  Set to ``False`` to
        skip validation (use with care).
    """

    def __init__(
        self,
        size: int,
        cages: List[Cage],
        validate: bool = True,
    ) -> None:
        if size < 2:
            raise ValueError("KenKen grid must be at least 2x2")
        self.size: int = size
        self.cages: List[Cage] = list(cages)
        self._cell_cage: Dict[Cell, Cage] = {}
        if validate:
            self._validate_partition()
            self._validate_cages()
        else:
            for cage in self.cages:
                for c in cage.cells:
                    self._cell_cage[c] = cage
        # Precompute cage cell-sets for fast membership tests.
        self._cage_sets: List[Set[Cell]] = [set(cg.cells) for cg in self.cages]

    # -- validation -------------------------------------------------------

    def _validate_partition(self) -> None:
        """Validate that the cages partition the grid (no gaps, no overlaps)."""
        seen: Set[Cell] = set()
        for cage in self.cages:
            for c in cage.cells:
                if c in seen:
                    raise ValueError(f"Cell {c} belongs to more than one cage")
                if not (0 <= c[0] < self.size and 0 <= c[1] < self.size):
                    raise ValueError(
                        f"Cell {c} out of bounds for size {self.size}"
                    )
                seen.add(c)
                self._cell_cage[c] = cage
        expected = {(r, c) for r in range(self.size) for c in range(self.size)}
        missing = expected - seen
        if missing:
            raise ValueError(f"Cells not covered by any cage: {sorted(missing)}")

    def _validate_cages(self) -> None:
        """Validate that each cage is contiguous and operator-consistent."""
        for i, cage in enumerate(self.cages):
            if not is_contiguous(cage.cells, self.size):
                raise ValueError(
                    f"Cage {i} (label={cage.label}) cells {cage.cells} "
                    f"are not contiguous"
                )
            if cage.op == "=" and cage.size != 1:
                raise ValueError(
                    f"Cage {i} has '=' operator but size {cage.size}"
                )

    # -- accessors --------------------------------------------------------

    def cage_for(self, cell: Cell) -> Cage:
        """Return the cage that owns *cell*.

        Raises
        ------
        KeyError
            If *cell* is not part of any cage.
        """
        return self._cell_cage[cell]

    # -- JSON serialization ------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the puzzle to a plain dict (for JSON)."""
        return {
            "size": self.size,
            "cages": [c.to_dict() for c in self.cages],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KenKenPuzzle":
        """Reconstruct a puzzle from a dict produced by :meth:`to_dict`."""
        return cls(
            size=int(d["size"]),
            cages=[Cage.from_dict(cd) for cd in d["cages"]],
        )

    def to_json(self) -> str:
        """Serialise to a pretty-printed JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, s: str) -> "KenKenPuzzle":
        """Reconstruct from a JSON string produced by :meth:`to_json`."""
        return cls.from_dict(json.loads(s))

    # -- text serialization -----------------------------------------------

    def to_text(self) -> str:
        """Export to a compact human-readable text format.

        Format::

            size: N
            R,C R,C ... op target
            ...

        Each line after the header is a cage: space-separated cell coordinates
        (row,col pairs), then the operator, then the target.
        """
        lines = [f"size: {self.size}"]
        for cage in self.cages:
            cells_str = " ".join(f"{r},{c}" for (r, c) in cage.cells)
            lines.append(f"{cells_str} {cage.op} {cage.target}")
        return "\n".join(lines) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "KenKenPuzzle":
        """Parse the compact text format produced by :meth:`to_text`.

        Lines starting with ``#`` are treated as comments and ignored.
        """
        lines = [
            l.strip()
            for l in text.strip().splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        if not lines:
            raise ValueError("Empty puzzle text")
        size: int | None = None
        cage_specs: List[Tuple[List[Cell], str, int]] = []
        for line in lines:
            if line.lower().startswith("size:"):
                size = int(line.split(":")[1].strip())
                continue
            parts = line.split()
            if len(parts) < 3:
                raise ValueError(f"Invalid cage line: {line!r}")
            op = parts[-2]
            target = int(parts[-1])
            cell_parts = parts[:-2]
            cells: List[Cell] = []
            for cp in cell_parts:
                r_str, c_str = cp.split(",")
                cells.append((int(r_str), int(c_str)))
            cage_specs.append((cells, op, target))
        if size is None:
            raise ValueError("Missing 'size:' header")
        cages = [
            Cage(cells=cs, op=op, target=target, label=str(i + 1))
            for i, (cs, op, target) in enumerate(cage_specs)
        ]
        return cls(size=size, cages=cages)

    # -- dunder -----------------------------------------------------------

    def __repr__(self) -> str:
        return f"KenKenPuzzle(size={self.size}, cages={len(self.cages)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KenKenPuzzle):
            return NotImplemented
        return self.size == other.size and self.cages == other.cages

    def __hash__(self) -> int:
        return hash((self.size, tuple(self.cages)))


__all__ = ["KenKenPuzzle"]