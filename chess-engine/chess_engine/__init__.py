"""chess-engine: A from-scratch chess engine in pure Python."""

from .board import Board, Move, Piece, Color, Square
from .search import Search
from .evaluate import Evaluator
from .notation import to_algebraic, parse_algebraic
from .zobrist import ZobristHash
from .transposition import TranspositionTable, TTEntry
from .opening_book import OpeningBook, create_default_book
from .pgn import PGNGame, board_to_pgn

__version__ = "2.0.0"

__all__ = [
    "Board", "Move", "Piece", "Color", "Square",
    "Search", "Evaluator",
    "to_algebraic", "parse_algebraic",
    "ZobristHash", "TranspositionTable", "TTEntry",
    "OpeningBook", "create_default_book",
    "PGNGame", "board_to_pgn",
]