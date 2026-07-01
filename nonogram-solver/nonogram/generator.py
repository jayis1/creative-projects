"""
Nonogram puzzle generator.

Creates random nonograms and (optionally) verifies that they have a unique
solution by using the solver.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from nonogram.board import Board, Cell
from nonogram.solver import Solver


class Generator:
    """Random nonogram generator with unique-solution checking."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.solver = Solver()

    def generate(
        self,
        width: int,
        height: int,
        density: float = 0.55,
        unique: bool = True,
        max_attempts: int = 200,
    ) -> Board:
        """Generate a nonogram board.

        Parameters
        ----------
        width, height : int
            Grid dimensions.
        density : float
            Approximate fraction of filled cells (0–1).
        unique : bool
            If True, retry until the clues produce a unique solution.
        max_attempts : int
            Maximum number of random grids to try.

        Returns
        -------
        Board
            A board with clues set and the solution filled in.
        """
        if not (0 < density < 1):
            raise ValueError("density must be in (0, 1)")
        if width < 1 or height < 1:
            raise ValueError("width and height must be >= 1")

        for _ in range(max_attempts):
            grid = self._random_grid(width, height, density)
            row_clues = [
                Board.clues_from_line(
                    [Cell.FILLED if v else Cell.EMPTY for v in row]
                )
                for row in grid
            ]
            col_clues = [
                Board.clues_from_line(
                    [Cell.FILLED if grid[r][c] else Cell.EMPTY
                     for r in range(height)]
                )
                for c in range(width)
            ]
            board = Board(row_clues, col_clues)
            # Fill in the solution.
            for r in range(height):
                for c in range(width):
                    board.grid[r][c] = Cell.FILLED if grid[r][c] else Cell.EMPTY
            if not unique:
                return board
            # Check uniqueness: the clues must have exactly one solution.
            test = Board(row_clues, col_clues)
            count = self.solver.count_solutions(test, limit=2)
            if count == 1:
                return board
        raise RuntimeError(
            f"Could not generate a unique {width}x{height} nonogram "
            f"in {max_attempts} attempts."
        )

    def _random_grid(
        self, width: int, height: int, density: float
    ) -> List[List[bool]]:
        return [
            [self.rng.random() < density for _ in range(width)]
            for _ in range(height)
        ]

    def generate_easy(self, size: int = 5) -> Board:
        """Small, dense puzzle — typically solvable by propagation alone."""
        return self.generate(size, size, density=0.6, unique=True)

    def generate_medium(self, size: int = 10) -> Board:
        return self.generate(size, size, density=0.55, unique=True)

    def generate_hard(self, size: int = 15) -> Board:
        return self.generate(size, size, density=0.5, unique=True,
                             max_attempts=500)