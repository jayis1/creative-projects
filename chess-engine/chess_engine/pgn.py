"""PGN (Portable Game Notation) read/write support.

PGN is the standard format for recording chess games. This module
provides simple parsing and generation of PGN files.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from .board import Board, Move
from .notation import to_algebraic, parse_algebraic


class PGNGame:
    """A chess game in PGN format."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.moves: List[str] = []  # SAN move strings
        self.result: str = "*"

    def add_header(self, key: str, value: str) -> None:
        self.headers[key] = value

    def add_move(self, san: str) -> None:
        self.moves.append(san)

    def to_string(self) -> str:
        """Generate PGN text."""
        lines = []
        for key, value in self.headers.items():
            lines.append(f'[{key} "{value}"]')
        if lines:
            lines.append("")

        # Move text: 1. e4 e5 2. Nf3 ...
        move_text_parts = []
        for i, san in enumerate(self.moves):
            if i % 2 == 0:
                move_text_parts.append(f"{i // 2 + 1}.")
            move_text_parts.append(san)
        move_text_parts.append(self.result)
        move_text = " ".join(move_text_parts)

        # Wrap at 80 chars
        lines.append(move_text)
        return "\n".join(lines)

    @classmethod
    def from_string(cls, text: str) -> "PGNGame":
        """Parse PGN text into a PGNGame object."""
        game = cls()
        lines = text.strip().split("\n")
        i = 0
        # Parse headers
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if line.startswith("[") and line.endswith("]"):
                # [Key "Value"]
                inner = line[1:-1]
                space_idx = inner.index(" ")
                key = inner[:space_idx]
                value = inner[space_idx + 2:-1]  # strip quotes
                game.headers[key] = value
                i += 1
            else:
                break

        # Parse moves
        remaining = " ".join(lines[i:])
        # Remove comments
        import re
        remaining = re.sub(r"\{[^}]*\}", "", remaining)
        # Remove move numbers like "1." or "1..."
        remaining = re.sub(r"\d+\.+", "", remaining)
        # Remove NAGs like $1
        remaining = re.sub(r"\$\d+", "", remaining)
        # Remove variations (...)
        # Simple approach: strip parentheticals
        while "(" in remaining:
            remaining = re.sub(r"\([^)]*\)", "", remaining)

        tokens = remaining.split()
        results = {"1-0", "0-1", "1/2-1/2", "*"}
        for token in tokens:
            if token in results:
                game.result = token
            elif token:
                game.moves.append(token)

        return game

    def play_on_board(self, board: Optional[Board] = None) -> Board:
        """Replay the moves on a board and return the final position."""
        b = board or Board()
        for san in self.moves:
            move = parse_algebraic(san, b)
            b.push(move)
        return b


def board_to_pgn(board: Board, headers: Optional[dict] = None) -> str:
    """Convert a board's move history to PGN format.

    Note: this requires replaying from the start since we don't store
    SAN during play. This replays all moves from the starting position.
    """
    if not board.history:
        return "*"

    # Replay from start
    start = Board()
    # Count moves to replay
    n_moves = len(board.history)
    moves_uci = []
    for _ in range(n_moves):
        state = board.history[-1]
        move = state["move"]
        moves_uci.append(move)
        board.pop()

    # Now replay forward, collecting SAN
    game = PGNGame()
    if headers:
        for k, v in headers.items():
            game.add_header(k, v)

    temp = Board()
    for move in reversed(moves_uci):
        san = to_algebraic(move, temp)
        game.add_move(san)
        temp.push(move)

    game.result = temp.result() if temp.is_game_over() else "*"

    # Restore the board
    for move in reversed(moves_uci):
        board.push(move)

    return game.to_string()