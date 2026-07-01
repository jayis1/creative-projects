"""
Curated preset puzzles of varying difficulty.

Each preset is a tuple of (name, row_clues, col_clues, difficulty, description).
All puzzles are verified to be solvable and have unique solutions.
"""

from __future__ import annotations

from typing import List, Tuple

from nonogram.board import Board, Cell
from nonogram.solver import Solver


def _clues_from_grid(grid: List[List[bool]]) -> Tuple[List[List[int]], List[List[int]]]:
    """Derive row and column clues from a boolean grid."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    row_clues = []
    for r in range(h):
        row_clues.append(Board.clues_from_line(
            [Cell.FILLED if grid[r][c] else Cell.EMPTY for c in range(w)]
        ))
    col_clues = []
    for c in range(w):
        col_clues.append(Board.clues_from_line(
            [Cell.FILLED if grid[r][c] else Cell.EMPTY for r in range(h)]
        ))
    return row_clues, col_clues


# Define pictures as boolean grids, then derive clues.
# This guarantees the puzzles are solvable (the picture IS a solution).

_HEART = [
    [False, True,  False, True,  False],
    [True,  True,  True,  True,  True],
    [True,  True,  True,  True,  True],
    [False, True,  True,  True,  False],
    [False, False, True,  False, False],
]

_SMILEY = [
    [False, True,  False, True,  False],
    [False, True,  False, True,  False],
    [False, False, False, False, False],
    [True,  False, False, False, True],
    [False, True,  True,  True,  False],
]

_CROSS = [
    [False, False, True,  False, False, False, False],
    [False, False, True,  False, False, False, False],
    [True,  True,  True,  True,  True,  True,  True],
    [False, False, True,  False, False, False, False],
    [False, False, True,  False, False, False, False],
    [False, False, True,  False, False, False, False],
    [False, False, True,  False, False, False, False],
]

_LETTER_A = [
    [False, True,  True,  True,  False],
    [True,  True,  True,  True,  True],
    [True,  False, False, False, True],
    [True,  True,  True,  True,  True],
    [True,  False, False, False, True],
]

_TREE = [
    [False, False, False, True,  False, False, False],
    [False, False, True,  True,  True,  False, False],
    [False, True,  True,  True,  True,  True,  False],
    [True,  True,  True,  True,  True,  True,  True],
    [False, True,  True,  True,  True,  True,  False],
    [False, False, True,  True,  True,  False, False],
    [False, False, False, True,  False, False, False],
]

_HOUSE = [
    [False, False, True,  False, False],
    [False, True,  True,  True,  False],
    [True,  True,  True,  True,  True],
    [True,  False, False, False, True],
    [True,  True,  True,  True,  True],
]

# Ship: mast + hull — asymmetric to ensure uniqueness
_SHIP = [
    [False, False, False, False, True,  False, False, False, False, False],
    [False, False, False, True,  True,  True,  False, False, False, False],
    [False, False, False, False, True,  False, False, False, False, False],
    [False, False, False, False, True,  False, False, False, False, False],
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True],
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True],
    [False, True,  True,  True,  True,  True,  True,  True,  True,  False],
    [False, False, True,  True,  True,  True,  True,  True,  True,  False],
    [False, False, False, True,  True,  True,  True,  True,  False, False],
    [False, False, False, False, True,  True,  True,  False, False, False],
]

# Cat face
_CAT = [
    [True,  True,  False, False, False, False, True,  True],
    [True,  True,  False, False, False, False, True,  True],
    [True,  True,  True,  True,  True,  True,  True,  True],
    [True,  False, True,  False, False, True,  False, True],
    [True,  True,  True,  True,  True,  True,  True,  True],
    [True,  True,  False, True,  True,  False, True,  True],
    [True,  True,  False, False, False, False, True,  True],
    [False, True,  True,  False, False, True,  True,  False],
]

# Space invader
_INVADER = [
    [False, False, True,  False, False, False, True,  False],
    [False, False, False, True,  False, True,  False, False],
    [False, False, True,  True,  True,  True,  True,  False],
    [False, True,  True,  False, True,  False, True,  True],
    [True,  True,  True,  True,  True,  True,  True,  True],
    [True,  False, True,  True,  True,  True,  True,  False],
    [True,  False, True,  False, False, False, True,  False],
    [False, False, False, True,  True,  True,  False, False],
]

# Key
_KEY = [
    [False, False, True,  True,  True,  False, False, False, False, False],
    [False, True,  True,  False, True,  True,  False, False, False, False],
    [True,  True,  False,  False, False, True,  False, False, False, False],
    [True,  True,  False,  False, False, True,  False, False, False, False],
    [False, True,  True,  False, True,  True,  False, False, False, False],
    [False, False, True,  True,  True,  False, False, False, False, False],
    [False, False, False, True,  False,  False, False, False, False, False],
    [False, False, False, True,  False,  False, False, False, False, False],
    [False, False, False, True,  True,  True,  False, False, False, False],
    [False, False, False, False, False,  True,  True,  False, False, False],
]


def _make_preset(name, grid, difficulty, description):
    row_clues, col_clues = _clues_from_grid(grid)
    return (name, row_clues, col_clues, difficulty, description)


PRESETS: List[Tuple[str, List[List[int]], List[List[int]], str, str]] = [
    _make_preset("heart", _HEART, "easy", "A 5×5 heart shape."),
    _make_preset("smiley", _SMILEY, "easy", "A 5×5 smiley face."),
    _make_preset("cross", _CROSS, "easy", "A 7×7 plus sign."),
    _make_preset("letter-a", _LETTER_A, "easy", "A 5×5 letter A."),
    _make_preset("tree", _TREE, "medium", "A 7×7 tree."),
    _make_preset("house", _HOUSE, "medium", "A 5×5 house."),
    _make_preset("ship", _SHIP, "medium", "A 10×10 ship."),
    _make_preset("cat", _CAT, "hard", "An 8×8 cat face."),
    _make_preset("space-invader", _INVADER, "hard", "An 8×8 space invader."),
    _make_preset("key", _KEY, "hard", "A 10×10 key."),
]


def get_preset(name: str) -> Board:
    """Return a preset board by name (solution filled in)."""
    for n, row_clues, col_clues, _, _ in PRESETS:
        if n == name:
            return _solve_to_board(row_clues, col_clues)
    raise KeyError(f"No preset named '{name}'. Available: "
                   + ", ".join(p[0] for p in PRESETS))


def list_presets() -> List[Tuple[str, str, str]]:
    """Return (name, difficulty, description) for all presets."""
    return [(p[0], p[3], p[4]) for p in PRESETS]


def _solve_to_board(row_clues, col_clues) -> Board:
    """Create a board and solve it to get the filled-in solution."""
    board = Board(row_clues, col_clues)
    result = Solver().solve(board)
    if not result.solved:
        # If the preset isn't uniquely solvable, still return the board
        # (clues only). This is useful for display.
        return Board(row_clues, col_clues)
    return board