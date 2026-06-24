"""chess-engine: A from-scratch chess engine in pure Python."""

from .board import Board, Move, Piece, Color, Square
from .search import Search
from .evaluate import Evaluator
from .notation import to_algebraic, parse_algebraic

__version__ = "1.0.0"

__all__ = [
    "Board", "Move", "Piece", "Color", "Square",
    "Search", "Evaluator",
    "to_algebraic", "parse_algebraic",
]