"""
Difficulty analyzer for nonogram puzzles.

Estimates puzzle difficulty based on:
  - Grid size
  - Clue complexity (number of blocks, total filled ratio)
  - How much constraint propagation alone can solve (no backtracking needed?)
  - Backtracking effort required by the solver
"""

from __future__ import annotations

from typing import Tuple

from nonogram.board import Board, Cell
from nonogram.solver import Solver


class DifficultyAnalyzer:
    """Estimate the difficulty of a nonogram puzzle."""

    def __init__(self) -> None:
        self.solver = Solver()

    def analyze(self, board: Board) -> dict:
        """Return a difficulty analysis dict."""
        # Solve from scratch (all unknown).
        test = Board(board.row_clues, board.col_clues)
        result = self.solver.solve(test)

        total_cells = board.width * board.height
        filled_ratio = sum(sum(c) for c in board.col_clues) / max(total_cells, 1)
        num_blocks = sum(len(c) for c in board.row_clues) + sum(len(c) for c in board.col_clues)
        avg_block_size = (
            sum(sum(c) for c in board.row_clues) / max(num_blocks, 1)
        )
        grid_size = max(board.width, board.height)

        # How much was solved by propagation vs backtracking?
        prop_solved = result.iterations > 0 and result.backtracks == 0
        backtrack_ratio = result.backtracks / max(total_cells, 1)

        # Compute a difficulty score.
        score = 0.0
        score += grid_size * 1.5
        score += num_blocks * 0.5
        score += backtrack_ratio * 50
        if not prop_solved:
            score += 20
        if filled_ratio < 0.4:
            score += 10  # sparse puzzles are harder
        if filled_ratio > 0.8:
            score += 5   # very dense puzzles can also be tricky

        # Classify.
        if score < 20:
            level = "trivial"
        elif score < 40:
            level = "easy"
        elif score < 70:
            level = "medium"
        elif score < 120:
            level = "hard"
        else:
            level = "expert"

        return {
            "difficulty": level,
            "score": round(score, 1),
            "grid_size": f"{board.width}x{board.height}",
            "total_cells": total_cells,
            "filled_ratio": round(filled_ratio, 3),
            "num_blocks": num_blocks,
            "avg_block_size": round(avg_block_size, 2),
            "solved": result.solved,
            "iterations": result.iterations,
            "backtracks": result.backtracks,
            "propagation_only": prop_solved,
            "backtrack_ratio": round(backtrack_ratio, 4),
        }

    def grade(self, board: Board) -> str:
        """Return just the difficulty level string."""
        return self.analyze(board)["difficulty"]