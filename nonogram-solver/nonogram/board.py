"""
Core board representation for nonograms.

A ``Board`` holds the grid state (filled / blank / unknown), the row and column
clues, and provides query/mutation helpers used by the solver, generator, and
player.
"""

from __future__ import annotations

import enum
from typing import List, Optional, Tuple, Iterator


class Cell(enum.IntEnum):
    """Three possible states for a cell in a nonogram board."""

    UNKNOWN = -1
    EMPTY = 0      # confirmed blank (left blank in the solution)
    FILLED = 1     # confirmed filled

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        if self is Cell.UNKNOWN:
            return "?"
        if self is Cell.EMPTY:
            return "."
        return "#"

    @property
    def symbol(self) -> str:
        return str(self)


class Board:
    """
    A nonogram board.

    Parameters
    ----------
    row_clues : list of list of int
        For each row, the run-length clues (e.g. ``[3, 1]`` means a run of 3
        filled cells, at least one gap, then a run of 1).
    col_clues : list of list of int
        Same, for each column.
    """

    def __init__(
        self,
        row_clues: List[List[int]],
        col_clues: List[List[int]],
    ) -> None:
        self.row_clues: List[List[int]] = [list(r) for r in row_clues]
        self.col_clues: List[List[int]] = [list(c) for c in col_clues]
        self.height: int = len(row_clues)
        self.width: int = len(col_clues)
        self.grid: List[List[Cell]] = [
            [Cell.UNKNOWN] * self.width for _ in range(self.height)
        ]

    # ------------------------------------------------------------------ #
    # Clue helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def clue_sum(clue: List[int]) -> int:
        """Sum of run lengths plus mandatory gaps between runs."""
        if not clue:
            return 0
        return sum(clue) + len(clue) - 1

    @staticmethod
    def clues_from_line(line: List[Cell]) -> List[int]:
        """Derive clues from a fully-known line of cells."""
        runs: List[int] = []
        count = 0
        for c in line:
            if c is Cell.FILLED:
                count += 1
            else:
                if count > 0:
                    runs.append(count)
                    count = 0
        if count > 0:
            runs.append(count)
        return runs

    # ------------------------------------------------------------------ #
    # Grid access
    # ------------------------------------------------------------------ #
    def get_row(self, r: int) -> List[Cell]:
        return self.grid[r]

    def get_col(self, c: int) -> List[Cell]:
        return [self.grid[r][c] for r in range(self.height)]

    def set_row(self, r: int, line: List[Cell]) -> None:
        self.grid[r] = list(line)

    def set_col(self, c: int, line: List[Cell]) -> None:
        for r in range(self.height):
            self.grid[r][c] = line[r]

    def copy(self) -> "Board":
        """Deep-ish copy (grid is cloned; clues are shared reference-safe)."""
        b = Board(self.row_clues, self.col_clues)
        b.grid = [row[:] for row in self.grid]
        return b

    def clone(self) -> "Board":
        return self.copy()

    # ------------------------------------------------------------------ #
    # Query helpers
    # ------------------------------------------------------------------ #
    def is_complete(self) -> bool:
        """True when every cell is decided (FILLED or EMPTY)."""
        return all(c is not Cell.UNKNOWN for row in self.grid for c in row)

    def is_solved(self) -> bool:
        """True when complete *and* every row/col matches its clues."""
        if not self.is_complete():
            return False
        for r in range(self.height):
            if self.clues_from_line(self.get_row(r)) != self.row_clues[r]:
                return False
        for c in range(self.width):
            if self.clues_from_line(self.get_col(c)) != self.col_clues[c]:
                return False
        return True

    def contradicts(self) -> bool:
        """Quick check: any *decided* row/col that cannot match its clue."""
        for r in range(self.height):
            line = self.get_row(r)
            if not self._line_can_match(line, self.row_clues[r]):
                return True
        for c in range(self.width):
            line = self.get_col(c)
            if not self._line_can_match(line, self.col_clues[c]):
                return True
        return False

    @staticmethod
    def _line_can_match(line: List[Cell], clue: List[int]) -> bool:
        """Return False if a partially-known line *cannot* satisfy *clue*.

        This is a cheap necessary-but-not-sufficient check used by
        ``contradicts``. A full feasibility check is in ``LineSolver``.
        """
        known = [c for c in line if c is not Cell.UNKNOWN]
        if not known:
            return True
        # If fully known, compare derived clues directly.
        if len(known) == len(line):
            return Board.clues_from_line(line) == clue
        # Quick necessary checks:
        total_filled_needed = sum(clue)
        filled_present = sum(1 for c in line if c is Cell.FILLED)
        if filled_present > total_filled_needed:
            return False
        # If there are filled cells but the clue is empty, contradiction.
        if clue == [] and filled_present > 0:
            return False
        return True

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "row_clues": self.row_clues,
            "col_clues": self.col_clues,
            "grid": [[c.value for c in row] for row in self.grid],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Board":
        b = cls(d["row_clues"], d["col_clues"])
        if "grid" in d:
            for r, row in enumerate(d["grid"]):
                for c, v in enumerate(row):
                    b.grid[r][c] = Cell(v)
        return b

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #
    def render(self) -> str:
        """ASCII representation: ``#`` filled, ``.`` empty, ``?`` unknown."""
        lines: List[str] = []
        for row in self.grid:
            lines.append(" ".join(c.symbol for c in row))
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Board({self.height}x{self.width})"

    def __str__(self) -> str:
        return self.render()

    # ------------------------------------------------------------------ #
    # Grid export for the player / generator
    # ------------------------------------------------------------------ #
    def filled_cells(self) -> Iterator[Tuple[int, int]]:
        """Yield (row, col) of every FILLED cell."""
        for r in range(self.height):
            for c in range(self.width):
                if self.grid[r][c] is Cell.FILLED:
                    yield (r, c)

    def filled_bool_grid(self) -> List[List[bool]]:
        """Return a 2-D bool grid (True = filled), ignoring unknowns."""
        return [
            [self.grid[r][c] is Cell.FILLED for c in range(self.width)]
            for r in range(self.height)
        ]