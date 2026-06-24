"""Zobrist hashing for transposition tables.

Uses precomputed random numbers for each (square, piece) pair and
game state (castling rights, en passant file, side to move).
"""

from __future__ import annotations

import random

from .board import Board, Piece, Color


class ZobristHash:
    """Precomputed Zobrist keys for board positions."""

    def __init__(self, seed: int = 0xDEADBEEF) -> None:
        rng = random.Random(seed)
        # piece_type (1..6) x color (0..1) x square (0..63)
        self.pieces = [[[rng.getrandbits(64)
                         for _ in range(64)]
                        for _ in range(2)]   # colors
                       for _ in range(7)]    # piece types 0..6
        self.castling = {
            Color.WHITE: {"K": rng.getrandbits(64),
                          "Q": rng.getrandbits(64)},
            Color.BLACK: {"K": rng.getrandbits(64),
                          "Q": rng.getrandbits(64)},
        }
        self.ep_file = [rng.getrandbits(64) for _ in range(8)]
        self.side_to_move = rng.getrandbits(64)

    def hash(self, board: Board) -> int:
        """Compute the Zobrist hash for a board position."""
        h = 0
        for sq in range(64):
            p = board.squares[sq]
            if p is not None:
                h ^= self.pieces[p.piece_type][p.color][sq]

        # Castling rights
        if board.castling_rights[Color.WHITE]["K"]:
            h ^= self.castling[Color.WHITE]["K"]
        if board.castling_rights[Color.WHITE]["Q"]:
            h ^= self.castling[Color.WHITE]["Q"]
        if board.castling_rights[Color.BLACK]["K"]:
            h ^= self.castling[Color.BLACK]["K"]
        if board.castling_rights[Color.BLACK]["Q"]:
            h ^= self.castling[Color.BLACK]["Q"]

        # En passant file
        if board.ep_square >= 0:
            h ^= self.ep_file[board.ep_square % 8]

        # Side to move
        if board.turn == Color.BLACK:
            h ^= self.side_to_move

        return h