"""
Full-board nonogram solver.

Combines iterative constraint propagation (applying ``LineSolver`` to every
row and column until no more progress) with backtracking when propagation
alone cannot finish the puzzle.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from nonogram.board import Board, Cell
from nonogram.line_solver import LineSolver


class SolveResult:
    """Outcome of a solve attempt."""

    def __init__(self, solved: bool, board: Optional[Board], iterations: int,
                 backtracks: int) -> None:
        self.solved = solved
        self.board = board
        self.iterations = iterations
        self.backtracks = backtracks

    def __repr__(self) -> str:
        return (f"SolveResult(solved={self.solved}, "
                f"iterations={self.iterations}, backtracks={self.backtracks})")


class Solver:
    """Constraint-propagation + backtracking nonogram solver."""

    def __init__(self, max_iterations: int = 10000,
                 max_backtracks: int = 100000) -> None:
        self.line_solver = LineSolver()
        self.max_iterations = max_iterations
        self.max_backtracks = max_backtracks
        self.iterations = 0
        self.backtracks = 0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def solve(self, board: Board) -> SolveResult:
        """Attempt to solve *board* in place. Returns a ``SolveResult``."""
        self.iterations = 0
        self.backtracks = 0
        try:
            self._propagate(board)
            if board.is_complete():
                return SolveResult(True, board, self.iterations, self.backtracks)
            # Need backtracking.
            solved = self._backtrack(board)
            if solved:
                return SolveResult(True, board, self.iterations, self.backtracks)
            return SolveResult(False, None, self.iterations, self.backtracks)
        except ValueError:
            return SolveResult(False, None, self.iterations, self.backtracks)

    def is_unique(self, board: Board) -> bool:
        """Check whether *board* (clues only) has exactly one solution."""
        b1 = board.copy()
        r1 = Solver(max_backtracks=self.max_backtracks).solve(b1)
        if not r1.solved:
            return False
        # Find the first filled cell of the solution, then try to solve with
        # that cell forced empty — if a second solution exists, not unique.
        filled = list(b1.filled_cells())
        if not filled:
            return True  # empty board trivially unique
        r0, c0 = filled[0]
        b2 = board.copy()
        b2.grid[r0][c0] = Cell.EMPTY
        r2 = Solver(max_backtracks=self.max_backtracks).solve(b2)
        return not r2.solved

    # ------------------------------------------------------------------ #
    # Constraint propagation
    # ------------------------------------------------------------------ #
    def _propagate(self, board: Board) -> bool:
        """Iterate line-solving over all rows and columns until fixpoint.

        Returns ``True`` if no contradiction, ``False`` if contradiction found.
        Raises ``ValueError`` via ``LineSolver`` on infeasible lines.
        """
        changed = True
        while changed:
            changed = False
            self.iterations += 1
            if self.iterations > self.max_iterations:
                return True  # give up propagating, let backtracking try
            # Rows.
            for r in range(board.height):
                line = board.get_row(r)
                if all(c is not Cell.UNKNOWN for c in line):
                    continue
                new_line = self.line_solver.solve(line, board.row_clues[r])
                if new_line != line:
                    board.set_row(r, new_line)
                    changed = True
            # Columns.
            for c in range(board.width):
                line = board.get_col(c)
                if all(cell is not Cell.UNKNOWN for cell in line):
                    continue
                new_line = self.line_solver.solve(line, board.col_clues[c])
                if new_line != line:
                    board.set_col(c, new_line)
                    changed = True
        return True

    # ------------------------------------------------------------------ #
    # Backtracking
    # ------------------------------------------------------------------ #
    def _backtrack(self, board: Board) -> bool:
        """Depth-first backtracking with propagation at each node."""
        return self._backtrack_recursive(board, 0)

    def _backtrack_recursive(self, board: Board, depth: int) -> bool:
        if self.backtracks > self.max_backtracks:
            return False
        if board.is_complete():
            return board.is_solved()
        # Propagate first.
        try:
            self._propagate(board)
        except ValueError:
            self.backtracks += 1
            return False
        if board.is_complete():
            return board.is_solved()
        if board.contradicts():
            self.backtracks += 1
            return False
        # Pick the first unknown cell (could be improved with MRV heuristic).
        target = self._pick_cell(board)
        if target is None:
            return board.is_solved()
        r, c = target
        for value in (Cell.FILLED, Cell.EMPTY):
            snapshot = board.copy()
            board.grid[r][c] = value
            if self._backtrack_recursive(board, depth + 1):
                return True
            # Restore.
            board.grid = snapshot.grid
            self.backtracks += 1
        return False

    @staticmethod
    def _pick_cell(board: Board) -> Optional[Tuple[int, int]]:
        """Choose the next unknown cell — first found, row-major."""
        for r in range(board.height):
            for c in range(board.width):
                if board.grid[r][c] is Cell.UNKNOWN:
                    return (r, c)
        return None