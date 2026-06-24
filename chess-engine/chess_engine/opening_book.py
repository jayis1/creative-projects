"""Opening book support for the chess engine.

Stores opening positions and their known moves in a simple dictionary
keyed by Zobrist hash. Provides a small built-in book of common
openings.
"""

from __future__ import annotations

from typing import Optional, List, Tuple
import json

from .board import Board, Move, Color, Piece
from .notation import parse_algebraic, to_algebraic
from .zobrist import ZobristHash


class OpeningBook:
    """A simple opening book mapping position hashes to candidate moves."""

    def __init__(self) -> None:
        self.entries: dict[int, List[Tuple[str, int]]] = {}  # hash -> [(SAN, weight)]
        self.zobrist = ZobristHash()

    def add(self, board: Board, san: str, weight: int = 1) -> None:
        """Add an opening move for the current board position."""
        h = self.zobrist.hash(board)
        if h not in self.entries:
            self.entries[h] = []
        self.entries[h].append((san, weight))

    def probe(self, board: Board) -> Optional[Move]:
        """Look up the board position in the book.

        Returns a random weighted move, or None if not in book.
        """
        import random
        h = self.zobrist.hash(board)
        if h not in self.entries:
            return None
        candidates = self.entries[h]
        if not candidates:
            return None
        # Weighted random selection
        weights = [w for _, w in candidates]
        total = sum(weights)
        r = random.randint(1, total)
        cumulative = 0
        for san, w in candidates:
            cumulative += w
            if r <= cumulative:
                try:
                    return parse_algebraic(san, board)
                except ValueError:
                    return None
        return None

    def to_json(self) -> str:
        """Serialize the book to JSON."""
        return json.dumps({
            str(k): v for k, v in self.entries.items()
        })

    @classmethod
    def from_json(cls, text: str) -> "OpeningBook":
        """Load a book from JSON."""
        book = cls()
        data = json.loads(text)
        for k, v in data.items():
            book.entries[int(k)] = [tuple(x) for x in v]
        return book


def create_default_book() -> OpeningBook:
    """Create a small opening book with common chess openings."""
    book = OpeningBook()

    # Helper to add a sequence of moves
    def add_line(moves: List[str], weight: int = 1) -> None:
        b = Board()
        for san in moves:
            book.add(b, san, weight)
            move = parse_algebraic(san, b)
            b.push(move)

    # 1. e4
    add_line(["e4", "e5", "Nf3", "Nc6", "Bb5"], weight=3)  # Ruy Lopez
    add_line(["e4", "e5", "Nf3", "Nc6", "Bc4"], weight=2)  # Italian Game
    add_line(["e4", "e5", "Nf3", "Nc6", "d4"], weight=1)  # Scotch Game
    add_line(["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3"], weight=3)  # Sicilian
    add_line(["e4", "e6"], weight=2)  # French Defense
    add_line(["e4", "c6"], weight=2)  # Caro-Kann
    add_line(["e4", "d6", "d4", "g6"], weight=1)  # Pirc

    # 1. d4
    add_line(["d4", "d5", "c4"], weight=3)  # Queen's Gambit
    add_line(["d4", "Nf6", "c4", "e6"], weight=2)  # Indian Defense
    add_line(["d4", "Nf6", "c4", "g6"], weight=2)  # King's Indian
    add_line(["d4", "f5"], weight=1)  # Dutch Defense
    add_line(["d4", "d5", "Nf3", "Nf6", "c4"], weight=1)  # QGD

    # Other first moves
    add_line(["Nf3"], weight=1)  # Reti
    add_line(["c4"], weight=1)  # English Opening

    return book