"""chess-engine: A from-scratch chess engine in pure Python.

A complete chess engine with full legal move generation, alpha-beta search
with quiescence, null-move pruning, late move reductions, transposition table,
opening book, PGN support, UCI protocol, and interactive game play.

Basic usage::

    from chess_engine import Board, Search

    board = Board()
    search = Search()
    move, score = search.search(board, depth=4)
    print(f"Best move: {move.uci()}, score: {score}")

See the README for full documentation.
"""

from .board import Board, Move, Piece, Color, Square
from .search import Search
from .evaluate import Evaluator
from .notation import to_algebraic, parse_algebraic
from .zobrist import ZobristHash
from .transposition import TranspositionTable, TTEntry
from .opening_book import OpeningBook, create_default_book
from .pgn import PGNGame, board_to_pgn
from .game import Game
from .config import load_config, apply_search_config

__version__ = "3.0.0"

__all__ = [
    "Board", "Move", "Piece", "Color", "Square",
    "Search", "Evaluator",
    "to_algebraic", "parse_algebraic",
    "ZobristHash", "TranspositionTable", "TTEntry",
    "OpeningBook", "create_default_book",
    "PGNGame", "board_to_pgn",
    "Game",
    "load_config", "apply_search_config",
]