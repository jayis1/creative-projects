"""Interactive game manager for human-vs-engine and engine-vs-engine play.

Provides a :class:`Game` class that orchestrates a chess game with:

- Human input (SAN or UCI moves)
- Engine moves (with configurable depth / time)
- Opening book integration
- PGN export of the completed game
- Pretty board display with Unicode pieces
- Move history and game state tracking

Usage as a library::

    from chess_engine.game import Game

    game = Game()
    game.play_engine_vs_engine(depth=3, max_moves=80)

Usage from CLI::

    python -m chess_engine.cli play-human --depth 4
"""

from __future__ import annotations

import logging
import sys
from typing import List, Optional, Tuple, TextIO

from .board import Board, Move, Color, Piece
from .search import Search
from .evaluate import Evaluator
from .notation import to_algebraic, parse_algebraic, square_name, parse_square
from .opening_book import OpeningBook, create_default_book
from .pgn import PGNGame

logger = logging.getLogger(__name__)


class Game:
    """Orchestrates a chess game with human and/or engine players.

    Parameters
    ----------
    board: starting position (default: standard chess)
    search: optional pre-configured :class:`Search` instance
    book: optional :class:`OpeningBook` (default: built-in book)
    """

    def __init__(
        self,
        board: Optional[Board] = None,
        search: Optional[Search] = None,
        book: Optional[OpeningBook] = None,
    ) -> None:
        self.board = board or Board()
        self.search = search or Search()
        self.book: Optional[OpeningBook] = book  # may be None
        self.move_history: List[Move] = []
        self.san_history: List[str] = []

    # -- public API -------------------------------------------------

    def play_engine_move(
        self, depth: int = 4, time_limit: Optional[float] = None,
        use_book: bool = True,
    ) -> Optional[Tuple[Move, int]]:
        """Make the engine play one move.

        Returns ``(move, score)`` or ``None`` if the game is over.
        """
        if self.board.is_game_over():
            return None

        # Try opening book first
        if use_book and self.book is None:
            self.book = create_default_book()
        if use_book and self.book is not None:
            book_move = self.book.probe(self.board)
            if book_move is not None:
                self._apply_move(book_move, from_book=True)
                return (book_move, 0)

        move, score = self.search.search(
            self.board, depth=depth, time_limit=time_limit
        )
        if move is None:
            return None
        self._apply_move(move)
        return (move, score)

    def play_human_move(self, move_str: str) -> bool:
        """Apply a human-entered move (SAN or UCI).

        Returns ``True`` if the move was legal and applied.
        """
        move = self._parse_move(move_str)
        if move is None:
            return False
        self._apply_move(move)
        return True

    def play_engine_vs_engine(
        self, depth: int = 3, max_moves: int = 100,
        time_limit: Optional[float] = None,
        output: TextIO = sys.stdout,
    ) -> str:
        """Run a self-play game and return the result string."""
        while not self.board.is_game_over() and len(self.move_history) < max_moves:
            result = self.play_engine_move(
                depth=depth, time_limit=time_limit, use_book=True
            )
            if result is None:
                break
            move, score = result
            san = self.san_history[-1] if self.san_history else move.uci()
            output.write(
                f"{len(self.move_history):3d}. {self.board.turn.symbol()} "
                f"{san:8s} score={score:7d}\n"
            )
        result = self.board.result()
        output.write(f"\nGame over: {result}\n")
        return result

    def play_human_vs_engine(
        self,
        human_color: Color = Color.WHITE,
        depth: int = 4,
        time_limit: Optional[float] = None,
        input_stream: TextIO = sys.stdin,
        output: TextIO = sys.stdout,
    ) -> str:
        """Interactive human-vs-engine game loop.

        The human enters moves in SAN or UCI notation.  The engine
        responds automatically.  Type ``quit`` (or ``q``) to stop,
        ``moves`` to list legal moves, or ``fen`` to show the position.
        """
        output.write(self._banner())
        output.write(self.board.to_string(unicode=True) + "\n")

        while not self.board.is_game_over():
            if self.board.turn == human_color:
                output.write(f"\n{self.board.turn}'s turn. Enter move (SAN/UCI): ")
                output.flush()
                line = input_stream.readline()
                if not line:
                    break
                cmd = line.strip()
                if cmd.lower() in ("quit", "q", "exit"):
                    output.write("Game aborted.\n")
                    return "*"
                if cmd.lower() == "moves":
                    self._show_legal_moves(output)
                    continue
                if cmd.lower() == "fen":
                    output.write(self.board.fen() + "\n")
                    continue
                if not cmd:
                    continue
                if not self.play_human_move(cmd):
                    output.write(f"Illegal or unparseable move: {cmd}\n")
                    continue
            else:
                result = self.play_engine_move(
                    depth=depth, time_limit=time_limit, use_book=True
                )
                if result is None:
                    break
                move, score = result
                san = self.san_history[-1] if self.san_history else move.uci()
                output.write(f"Engine plays: {san} (score: {score})\n")

            output.write(self.board.to_string(unicode=True) + "\n")
            if self.board.is_check():
                output.write("** CHECK **\n")

        result = self.board.result()
        output.write(f"\nGame over: {result}\n")
        return result

    def to_pgn(self, headers: Optional[dict] = None) -> str:
        """Export the current game to PGN format."""
        game = PGNGame()
        if headers:
            for k, v in headers.items():
                game.add_header(k, v)
        else:
            game.add_header("Event", "chess-engine game")
            game.add_header("White", "chess-engine")
            game.add_header("Black", "chess-engine")
        for san in self.san_history:
            game.add_move(san)
        game.result = self.board.result() if self.board.is_game_over() else "*"
        return game.to_string()

    # -- internals --------------------------------------------------

    def _apply_move(self, move: Move, from_book: bool = False) -> None:
        san = to_algebraic(move, self.board)
        self.board.push(move)
        self.move_history.append(move)
        self.san_history.append(san)
        if from_book:
            logger.debug("Book move: %s", san)

    def _parse_move(self, text: str) -> Optional[Move]:
        """Parse a move in either SAN or UCI notation."""
        text = text.strip()
        # Try SAN first
        try:
            return parse_algebraic(text, self.board)
        except ValueError:
            pass
        # Try UCI
        try:
            return self._parse_uci(text)
        except (ValueError, IndexError):
            pass
        return None

    def _parse_uci(self, uci: str) -> Optional[Move]:
        """Parse a UCI move string like 'e2e4' or 'e7e8q'."""
        uci = uci.strip().lower()
        if len(uci) < 4 or len(uci) > 5:
            return None
        from_sq = parse_square(uci[:2])
        to_sq = parse_square(uci[2:4])
        promotion = None
        if len(uci) == 5:
            promo_map = {
                "q": Piece.QUEEN, "r": Piece.ROOK,
                "b": Piece.BISHOP, "n": Piece.KNIGHT,
            }
            ptype = promo_map.get(uci[4])
            if ptype is None:
                return None
            promotion = Piece(ptype, self.board.turn)
        for m in self.board.legal_moves():
            if (m.from_square == from_sq and m.to_square == to_sq
                    and (m.promotion == promotion
                         or (m.promotion and promotion
                             and m.promotion.piece_type == promotion.piece_type))):
                return m
        return None

    def _show_legal_moves(self, output: TextIO) -> None:
        moves = self.board.legal_moves()
        output.write(f"Legal moves ({len(moves)}):\n")
        for m in moves:
            san = to_algebraic(m, self.board)
            output.write(f"  {san:8s}  {m.uci()}\n")

    @staticmethod
    def _banner() -> str:
        return (
            "┌─────────────────────────────────────────┐\n"
            "│       chess-engine — Interactive        │\n"
            "│   Enter moves in SAN (e.g. e4, Nf3)     │\n"
            "│   or UCI (e.g. e2e4, g1f3).             │\n"
            "│   Commands: quit, moves, fen             │\n"
            "└─────────────────────────────────────────┘\n"
        )