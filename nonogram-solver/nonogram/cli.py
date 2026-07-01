"""
Command-line interface for the nonogram solver.

Subcommands:
  solve    — solve a puzzle from a JSON file
  generate — create a new puzzle
  play     — interactive play (basic)
  hint     — print one hint for a puzzle state
  validate — check a JSON puzzle file for uniqueness
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.player import Player


def _load_board(path: str) -> Board:
    data = json.loads(Path(path).read_text())
    return Board.from_dict(data)


def _save_board(board: Board, path: str) -> None:
    Path(path).write_text(json.dumps(board.to_dict(), indent=2))


def cmd_solve(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    # Reset grid to unknown for solving.
    for r in range(board.height):
        for c in range(board.width):
            board.grid[r][c] = Cell.UNKNOWN
    solver = Solver(max_backtracks=args.max_backtracks)
    result = solver.solve(board)
    if result.solved:
        print(board.render())
        print(f"\nSolved in {result.iterations} iterations, "
              f"{result.backtracks} backtracks.")
        if args.output:
            _save_board(board, args.output)
        return 0
    else:
        print("No solution found.")
        print(f"(iterations={result.iterations}, backtracks={result.backtracks})")
        return 1


def cmd_generate(args: argparse.Namespace) -> int:
    gen = Generator(seed=args.seed)
    board = gen.generate(
        args.width, args.height,
        density=args.density,
        unique=not args.no_unique,
        max_attempts=args.max_attempts,
    )
    # Save with solution.
    if args.output:
        _save_board(board, args.output)
    # Print clues only.
    clue_board = Board(board.row_clues, board.col_clues)
    print("Row clues:", board.row_clues)
    print("Col clues:", board.col_clues)
    print()
    print("Solution:")
    print(board.render())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    solver = Solver()
    test = Board(board.row_clues, board.col_clues)
    result = solver.solve(test)
    if not result.solved:
        print("UNSOLVABLE: no solution exists for these clues.")
        return 1
    if solver.is_unique(Board(board.row_clues, board.col_clues)):
        print("VALID: puzzle has a unique solution.")
        return 0
    else:
        print("AMBIGUOUS: puzzle has multiple solutions.")
        return 2


def cmd_hint(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    player = Player(board)
    # The loaded board has the solution; reset for play.
    hint = player.hint()
    if hint:
        r, c, cell = hint
        print(f"Hint: cell ({r}, {c}) should be "
              f"{'FILLED' if cell is Cell.FILLED else 'EMPTY'}.")
        return 0
    else:
        print("No hint available — the solver is stuck.")
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nonogram",
        description="Nonogram solver, generator, and player.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # solve
    sp = sub.add_parser("solve", help="Solve a puzzle from a JSON file.")
    sp.add_argument("file", help="Path to puzzle JSON.")
    sp.add_argument("--output", "-o", help="Save solved board to file.")
    sp.add_argument("--max-backtracks", type=int, default=100000)
    sp.set_defaults(func=cmd_solve)

    # generate
    sp = sub.add_parser("generate", help="Generate a new puzzle.")
    sp.add_argument("--width", "-w", type=int, default=10)
    sp.add_argument("--height", "-H", type=int, default=10)
    sp.add_argument("--density", "-d", type=float, default=0.55)
    sp.add_argument("--seed", "-s", type=int, default=None)
    sp.add_argument("--no-unique", action="store_true",
                    help="Skip uniqueness check.")
    sp.add_argument("--max-attempts", type=int, default=200)
    sp.add_argument("--output", "-o", help="Save puzzle to JSON file.")
    sp.set_defaults(func=cmd_generate)

    # validate
    sp = sub.add_parser("validate", help="Check puzzle uniqueness.")
    sp.add_argument("file", help="Path to puzzle JSON.")
    sp.set_defaults(func=cmd_validate)

    # hint
    sp = sub.add_parser("hint", help="Get a hint for a puzzle.")
    sp.add_argument("file", help="Path to puzzle JSON.")
    sp.set_defaults(func=cmd_hint)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())