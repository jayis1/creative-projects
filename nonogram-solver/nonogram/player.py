"""
Interactive CLI player for nonograms.

Provides a turn-based interface where the user can fill/blank cells, ask for
hints, and check their progress against the clues.
"""

from __future__ import annotations

from typing import Optional, Tuple

from nonogram.board import Board, Cell
from nonogram.solver import Solver


class Player:
    """Interactive nonogram player (non-interactive mode for testing)."""

    def __init__(self, board: Board) -> None:
        self.solution = board.copy()
        # Reset the play board to all-unknown.
        self.board = Board(board.row_clues, board.col_clues)
        self.solver = Solver()
        self.moves: list = []

    # ------------------------------------------------------------------ #
    # Move API
    # ------------------------------------------------------------------ #
    def fill(self, r: int, c: int) -> bool:
        """Mark cell (r, c) as filled. Returns False if out of range."""
        if not self._in_range(r, c):
            return False
        self.board.grid[r][c] = Cell.FILLED
        self.moves.append(("fill", r, c))
        return True

    def blank(self, r: int, c: int) -> bool:
        """Mark cell (r, c) as empty. Returns False if out of range."""
        if not self._in_range(r, c):
            return False
        self.board.grid[r][c] = Cell.EMPTY
        self.moves.append(("blank", r, c))
        return True

    def erase(self, r: int, c: int) -> bool:
        """Reset cell (r, c) to unknown."""
        if not self._in_range(r, c):
            return False
        self.board.grid[r][c] = Cell.UNKNOWN
        self.moves.append(("erase", r, c))
        return True

    def hint(self) -> Optional[Tuple[int, int, Cell]]:
        """Return one cell the solver can deduce, or ``None`` if stuck."""
        test = self.board.copy()
        try:
            self.solver._propagate(test)
        except ValueError:
            return None
        for r in range(test.height):
            for c in range(test.width):
                if (test.grid[r][c] is not Cell.UNKNOWN
                        and self.board.grid[r][c] is Cell.UNKNOWN):
                    return (r, c, test.grid[r][c])
        return None

    def check(self) -> bool:
        """True if the current board matches the solution so far."""
        for r in range(self.board.height):
            for c in range(self.board.width):
                ps = self.board.grid[r][c]
                ss = self.solution.grid[r][c]
                if ps is not Cell.UNKNOWN and ps is not ss:
                    return False
        return True

    def is_won(self) -> bool:
        return self.board.is_solved()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _in_range(self, r: int, c: int) -> bool:
        return 0 <= r < self.board.height and 0 <= c < self.board.width

    def render(self) -> str:
        return self.board.render()

    def render_with_clues(self) -> str:
        """Render the board with row and column clues displayed."""
        max_row_clue = max(
            (len(" ".join(str(x) for x in clue)) for clue in self.board.row_clues),
            default=0,
        )
        max_col_clue = max(len(clue) for clue in self.board.col_clues) if self.board.col_clues else 1

        lines = []
        # Column clues (printed vertically above the grid).
        for ci in range(max_col_clue):
            prefix = " " * max_row_clue + " "
            parts = []
            for c in range(self.board.width):
                if ci < len(self.board.col_clues[c]):
                    parts.append(str(self.board.col_clues[c][ci]))
                else:
                    parts.append(" ")
            lines.append(prefix + " ".join(parts))

        # Rows with clues.
        for r in range(self.board.height):
            clue_str = " ".join(str(x) for x in self.board.row_clues[r])
            clue_str = clue_str.rjust(max_row_clue)
            row_str = " ".join(cell.symbol for cell in self.board.get_row(r))
            lines.append(f"{clue_str} {row_str}")
        return "\n".join(lines)