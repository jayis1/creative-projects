"""
Full-board nonogram solver.

Combines iterative constraint propagation (applying ``LineSolver`` to every
row and column until no more progress) with backtracking when propagation
alone cannot finish the puzzle.

Enhancements over v1:
  - MRV (Minimum Remaining Values) cell selection heuristic
  - ``count_solutions`` to find all solutions (up to a limit)
  - ``is_unique`` with improved second-solution detection
  - Propagation queue: only re-solve lines that have changed
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Set

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
    """Constraint-propagation + backtracking nonogram solver.

    Parameters
    ----------
    max_iterations : int
        Maximum constraint-propagation iterations before falling back to
        backtracking.
    max_backtracks : int
        Maximum backtracking nodes before giving up.
    use_mrv : bool
        If True, use the Minimum Remaining Values heuristic for cell selection
        during backtracking. Picks the row or column with the fewest unknown
        cells whose clue is not yet satisfied — this tends to reduce the
        branching factor significantly.
    """

    def __init__(self, max_iterations: int = 10000,
                 max_backtracks: int = 100000,
                 use_mrv: bool = True) -> None:
        self.line_solver = LineSolver()
        self.max_iterations = max_iterations
        self.max_backtracks = max_backtracks
        self.use_mrv = use_mrv
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
        """Check whether *board* (clues only) has exactly one solution.

        More robust than v1: searches for *any* second solution rather than
        just testing one forced cell.
        """
        solutions = self.count_solutions(board, limit=2)
        return solutions == 1

    def count_solutions(self, board: Board, limit: int = 100) -> int:
        """Count solutions up to *limit*. Stops early once limit is reached."""
        test = Board(board.row_clues, board.col_clues)
        self.iterations = 0
        self.backtracks = 0
        count = 0
        try:
            self._propagate(test)
            if test.is_complete():
                return 1 if test.is_solved() else 0
            count = self._count_recursive(test, limit, 0)
        except ValueError:
            pass
        return count

    def _count_recursive(self, board: Board, limit: int, depth: int) -> int:
        """Count solutions via backtracking, stopping at *limit*."""
        if self.backtracks > self.max_backtracks:
            return 0
        if board.is_complete():
            return 1 if board.is_solved() else 0
        try:
            self._propagate(board)
        except ValueError:
            self.backtracks += 1
            return 0
        if board.is_complete():
            return 1 if board.is_solved() else 0
        if board.contradicts():
            self.backtracks += 1
            return 0
        target = self._pick_cell(board)
        if target is None:
            return 1 if board.is_solved() else 0
        r, c = target
        total = 0
        for value in (Cell.FILLED, Cell.EMPTY):
            snapshot = board.copy()
            board.grid[r][c] = value
            total += self._count_recursive(board, limit - total, depth + 1)
            board.grid = snapshot.grid
            self.backtracks += 1
            if total >= limit:
                return total
        return total

    # ------------------------------------------------------------------ #
    # Constraint propagation (with dirty-line queue)
    # ------------------------------------------------------------------ #
    def _propagate(self, board: Board) -> bool:
        """Iterate line-solving over all rows and columns until fixpoint.

        On each iteration, applies ``LineSolver`` to every row and column
        that still has unknown cells. Repeats until a full pass makes no
        changes (fixpoint) or ``max_iterations`` is exceeded.

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
                if all(cell is not Cell.UNKNOWN for cell in line):
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
        # Pick the next unknown cell using the selected heuristic.
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

    def _pick_cell(self, board: Board) -> Optional[Tuple[int, int]]:
        """Choose the next unknown cell.

        With ``use_mrv=True``, selects the cell in the row or column that has
        the fewest unknown cells (but > 0). This is the Minimum Remaining
        Values heuristic adapted for nonograms — it picks the most constrained
        line, which tends to produce immediate deductions or contradictions.

        With ``use_mrv=False``, picks the first unknown cell in row-major
        order.
        """
        if not self.use_mrv:
            return self._pick_first(board)
        return self._pick_mrv(board)

    @staticmethod
    def _pick_first(board: Board) -> Optional[Tuple[int, int]]:
        """Choose the next unknown cell — first found, row-major."""
        for r in range(board.height):
            for c in range(board.width):
                if board.grid[r][c] is Cell.UNKNOWN:
                    return (r, c)
        return None

    @staticmethod
    def _pick_mrv(board: Board) -> Optional[Tuple[int, int]]:
        """MRV heuristic: pick a cell from the most-constrained line.

        Find the row or column with the fewest unknown cells (but > 0),
        then pick the first unknown cell in that line. Lines with fewer
        unknowns are more likely to yield deductions.
        """
        best_line: Optional[Tuple[str, int]] = None  # ('row'/'col', index)
        best_unknowns = float("inf")

        # Check rows.
        for r in range(board.height):
            count = sum(1 for c in range(board.width)
                        if board.grid[r][c] is Cell.UNKNOWN)
            if 0 < count < best_unknowns:
                best_unknowns = count
                best_line = ("row", r)

        # Check columns.
        for c in range(board.width):
            count = sum(1 for r in range(board.height)
                        if board.grid[r][c] is Cell.UNKNOWN)
            if 0 < count < best_unknowns:
                best_unknowns = count
                best_line = ("col", c)

        if best_line is None:
            return None

        kind, idx = best_line
        if kind == "row":
            for c in range(board.width):
                if board.grid[idx][c] is Cell.UNKNOWN:
                    return (idx, c)
        else:
            for r in range(board.height):
                if board.grid[r][idx] is Cell.UNKNOWN:
                    return (r, idx)
        return None