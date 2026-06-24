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
    """Create a medium-sized opening book with common chess openings.

    Includes 20+ named opening lines covering the major opening systems:
    Ruy Lopez, Italian, Sicilian, French, Caro-Kann, Pirc, Queen's Gambit,
    King's/Queen's Indian, Dutch, English, Réti, Slav, London, etc.
    """
    book = OpeningBook()

    # Helper to add a sequence of moves
    def add_line(moves: List[str], weight: int = 1) -> None:
        b = Board()
        for san in moves:
            book.add(b, san, weight)
            move = parse_algebraic(san, b)
            b.push(move)

    # ── 1. e4 openings ──────────────────────────────────────────
    add_line(["e4", "e5", "Nf3", "Nc6", "Bb5"], weight=3)  # Ruy Lopez
    add_line(["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O"], weight=2)  # Ruy Lopez Morphy
    add_line(["e4", "e5", "Nf3", "Nc6", "Bc4"], weight=2)  # Italian Game
    add_line(["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"], weight=1)  # Italian Giuoco Piano
    add_line(["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6"], weight=1)  # Italian Two Knights
    add_line(["e4", "e5", "Nf3", "Nc6", "d4"], weight=1)  # Scotch Game
    add_line(["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Bxc6", "dxc6"], weight=1)  # Ruy Exchange
    add_line(["e4", "e5", "Nf3", "Nc6", "Nc3", "Nf6"], weight=1)  # Four Knights
    add_line(["e4", "e5", "Bc4", "Nf6", "d3"], weight=1)  # Bishop's Opening

    # ── Sicilian Defence ────────────────────────────────────────
    add_line(["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3"], weight=3)  # Sicilian Najdorf
    add_line(["e4", "c5", "Nf3", "Nc6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "g6"], weight=1)  # Sicilian Dragon
    add_line(["e4", "c5", "Nf3", "e6"], weight=2)  # Sicilian Taimanov/Paulsen
    add_line(["e4", "c5", "c3"], weight=1)  # Sicilian Alapin
    add_line(["e4", "c5", "Nf3", "Nc6", "Bb5"], weight=1)  # Sicilian Rossolimo

    # ── 1. e4 … semi-open ───────────────────────────────────────
    add_line(["e4", "e6"], weight=2)  # French Defence
    add_line(["e4", "e6", "d4", "d5", "Nc3"], weight=1)  # French Classical
    add_line(["e4", "c6"], weight=2)  # Caro-Kann
    add_line(["e4", "c6", "d4", "d5", "Nc3", "dxe4", "Nxe4"], weight=1)  # Caro-Kann Classical
    add_line(["e4", "d6", "d4", "g6"], weight=1)  # Pirc Defence
    add_line(["e4", "g6", "d4", "Bg7", "Nc3"], weight=1)  # Modern Defence
    add_line(["e4", "Nf6"], weight=1)  # Alekhine's Defence

    # ── 1. d4 openings ──────────────────────────────────────────
    add_line(["d4", "d5", "c4"], weight=3)  # Queen's Gambit
    add_line(["d4", "d5", "c4", "e6"], weight=2)  # QGD
    add_line(["d4", "d5", "c4", "c6"], weight=2)  # Slav Defence
    add_line(["d4", "d5", "c4", "dxc4"], weight=1)  # QGA
    add_line(["d4", "d5", "c4", "e6", "Nc3", "Nf6", "Bg5"], weight=1)  # QGD Orthodox
    add_line(["d4", "Nf6", "c4", "e6"], weight=2)  # Indian Defence
    add_line(["d4", "Nf6", "c4", "g6"], weight=2)  # King's Indian
    add_line(["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6"], weight=1)  # KID Classical
    add_line(["d4", "Nf6", "c4", "e6", "Nc3", "Bb4"], weight=2)  # Nimzo-Indian
    add_line(["d4", "Nf6", "c4", "e6", "Nf3", "b6"], weight=1)  # Queen's Indian
    add_line(["d4", "f5"], weight=1)  # Dutch Defence
    add_line(["d4", "d5", "Nf3", "Nf6", "c4"], weight=1)  # QGD via Nf3

    # ── Other first moves ────────────────────────────────────────
    add_line(["Nf3"], weight=1)  # Réti Opening
    add_line(["c4"], weight=2)  # English Opening
    add_line(["c4", "e5"], weight=1)  # English Reversed Sicilian
    add_line(["c4", "Nf6"], weight=1)  # English Indian
    add_line(["g3"], weight=1)  # Hungarian / King's Fianchetto
    add_line(["b3"], weight=1)  # Larsen's Opening
    add_line(["d4", "Nf6", "Nf3", "g6", "Bf4"], weight=1)  # London System
    add_line(["e4", "e5", "f4"], weight=1)  # King's Gambit

    return book