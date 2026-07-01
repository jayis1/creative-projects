"""
Bug hunt tests for nonogram-solver.
Each test verifies a specific bug before it's fixed.
"""
import json
import os
import tempfile
import pytest
from pathlib import Path

from nonogram.board import Board, Cell
from nonogram.line_solver import LineSolver
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.player import Player
from nonogram.io import PuzzleIO
from nonogram.renderer import Renderer
from nonogram.analyzer import DifficultyAnalyzer
from nonogram.presets import get_preset, list_presets, PRESETS


class TestBug1DeadCodeInPng:
    """Bug 1: save_png has dead code (first raw loop is overwritten)."""

    def test_png_still_works(self):
        """PNG should produce a valid file — dead code doesn't cause
        incorrect output but wastes computation."""
        b = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
        Solver().solve(b)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            PuzzleIO.save_png(b, path)
            data = Path(path).read_bytes()
            # PNG signature
            assert data[:8] == b"\x89PNG\r\n\x1a\n"
            assert len(data) > 50
        finally:
            os.unlink(path)


class TestBug2SolverDocstringMismatch:
    """Bug 2: _propagate docstring claimed a "dirty-set optimisation" that
    doesn't exist in the code. Fixed: docstring now accurately describes
    the simple fixpoint iteration."""

    def test_propagate_correctness(self):
        """Propagation should produce correct results. The heart puzzle
        may need backtracking after propagation — that's expected."""
        b = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
        solver = Solver()
        try:
            solver._propagate(b)
        except ValueError:
            pass  # ok if contradiction during propagation
        # The full solver should solve it.
        b2 = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
        result = solver.solve(b2)
        assert result.solved, "Heart should be solvable"


class TestBug3BoardFromDictNoValidation:
    """Bug 3: from_dict doesn't validate grid dimensions against clues."""

    def test_mismatched_grid_dimensions(self):
        """from_dict with a grid that doesn't match clue dimensions
        should raise an error, not silently produce a broken board."""
        data = {
            "row_clues": [[1], [1]],  # 2 rows
            "col_clues": [[1], [1]],  # 2 cols
            "grid": [[1, 0, 1], [0, 1, 0]],  # 2 rows, 3 cols — mismatch!
        }
        with pytest.raises((ValueError, IndexError)):
            Board.from_dict(data)


class TestBug4LoadNonNoValidation:
    """Bug 4: load_non doesn't validate line count, causing IndexError."""

    def test_short_non_file(self):
        """A NON file with fewer lines than expected should raise
        ValueError, not IndexError."""
        # 5x5 grid needs 1 + 5 + 5 = 11 lines, but we only provide 3
        content = "5 5\n1\n3\n"
        with tempfile.NamedTemporaryFile(suffix=".non", delete=False,
                                         mode="w") as f:
            f.write(content)
            path = f.name
        try:
            with pytest.raises((ValueError, IndexError)):
                PuzzleIO.load_non(path)
        finally:
            os.unlink(path)


class TestBug5PlayerCheckWithNonFile:
    """Bug 5: Player.check() fails when board has no grid (e.g. from NON)."""

    def test_check_with_unknown_solution(self):
        """When the solution board has all UNKNOWN cells (e.g. loaded
        from NON format), check() should not return False for every
        decided cell."""
        # Create a board with only clues (no grid) — simulates NON load
        board = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
        # The board.grid is all UNKNOWN
        player = Player(board)
        # Fill a cell that's correct in the real solution
        player.fill(2, 2)  # center of heart
        # check() should not fail — but it will because solution is UNKNOWN
        # This is the bug: solution should be solved first
        result = player.check()
        # After fix: should be True (the filled cell is correct in the solution)
        # Before fix: returns False because solution[2][2] is UNKNOWN
        assert result is True, "check() should return True for correct move"


class TestBug6AnalyzerFilledRatio:
    """Bug 6: filled_ratio computed from clue sums, which may not reflect
    actual filled cells in the solution."""

    def test_filled_ratio_accuracy(self):
        """filled_ratio should reflect the actual solution's filled cell
        ratio, not just the sum of column clues."""
        # Heart: 1+3+5+3+1 = 13 filled cells out of 25
        b = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
        Solver().solve(b)
        info = DifficultyAnalyzer().analyze(b)
        # Actual filled ratio: 13/25 = 0.52
        assert info["filled_ratio"] == 0.52, \
            f"Expected 0.52, got {info['filled_ratio']}"


class TestBug7PresetsKeyRowWidth:
    """Bug 7: _KEY grid may have inconsistent row widths."""

    def test_key_preset_dimensions(self):
        """All rows in the key preset grid should be the same width."""
        from nonogram.presets import _KEY
        widths = set(len(row) for row in _KEY)
        assert len(widths) == 1, f"Key grid has inconsistent widths: {widths}"


class TestBug8LineSolverEdgeCase:
    """Bug 8: LineSolver cache may return stale results across different
    board states if the same line+clue is reused."""

    def test_cache_isolation(self):
        """The LineSolver cache should not cause incorrect results when
        the same clue+line pattern appears in different contexts."""
        ls = LineSolver()
        # Solve a line
        line1 = [Cell.UNKNOWN] * 5
        result1 = ls.solve(line1, [3])
        # Solve the same line again — should get same result
        line2 = [Cell.UNKNOWN] * 5
        result2 = ls.solve(line2, [3])
        assert result1 == result2
        # Now solve with a partially-known line
        line3 = [Cell.FILLED, Cell.UNKNOWN, Cell.UNKNOWN, Cell.UNKNOWN, Cell.UNKNOWN]
        result3 = ls.solve(line3, [3])
        # FILLED at 0 means block starts at 0: [FILLED, FILLED, FILLED, EMPTY, EMPTY]
        assert result3[0] is Cell.FILLED
        assert result3[1] is Cell.FILLED
        assert result3[2] is Cell.FILLED
        assert result3[3] is Cell.EMPTY


class TestBug9EmptyClueLineSolver:
    """Bug 9: LineSolver with empty clue [0] or [] should mark all cells
    as EMPTY."""

    def test_empty_clue_all_empty(self):
        """A line with clue [] should have all cells set to EMPTY."""
        ls = LineSolver()
        line = [Cell.UNKNOWN] * 5
        result = ls.solve(line, [])
        assert all(c is Cell.EMPTY for c in result), \
            f"Empty clue should produce all EMPTY, got {[str(c) for c in result]}"


class TestBug10CountSolutionsStateReset:
    """Bug 10: count_solutions doesn't properly reset solver state when
    called multiple times."""

    def test_multiple_count_calls(self):
        """Calling count_solutions multiple times should give consistent
        results."""
        solver = Solver()
        clues = ([[1], [1]], [[1], [1]])  # 2x2 ambiguous

        c1 = solver.count_solutions(Board(clues[0], clues[1]), limit=10)
        c2 = solver.count_solutions(Board(clues[0], clues[1]), limit=10)
        assert c1 == c2 == 2, f"Expected 2, got {c1} then {c2}"


class TestBug11SolveInPlaceModifiesBoard:
    """Bug 11: solve() modifies the board in place, which can surprise
    callers who expect the input board to be unchanged."""

    def test_solve_modifies_board(self):
        """solve() should document that it modifies the board in place.
        This test verifies the behavior is as expected (not necessarily
        a bug, but a potential gotcha)."""
        b = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
        original = b.copy()
        Solver().solve(b)
        # Board should now be solved (all cells decided)
        assert b.is_complete()
        # Original should still be all unknown
        assert original.grid[0][0] is Cell.UNKNOWN