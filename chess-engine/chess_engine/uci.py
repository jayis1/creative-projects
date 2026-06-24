"""UCI (Universal Chess Interface) protocol support.

Implements a subset of the UCI protocol for engine communication.
This allows the engine to be used with GUI tools like Arena, Cute Chess,
or pychess.

Supported commands:
    uci          - identify engine and options
    isready      - ready check
    setoption    - set engine options
    ucinewgame   - start a new game
    position     - set up a position (startpos or fen + moves)
    go           - search for best move (with optional time/depth limits)
    stop         - stop searching immediately
    quit         - exit engine
"""

from __future__ import annotations

import sys
import time
from typing import Optional, TextIO

from .board import Board, Move, Color, Piece
from .search import Search
from .evaluate import Evaluator
from .transposition import TranspositionTable
from .notation import parse_square


class UCIEngine:
    """A UCI protocol handler for the chess engine."""

    def __init__(self, input_stream: TextIO = sys.stdin,
                 output_stream: TextIO = sys.stdout) -> None:
        self.board = Board()
        self.evaluator = Evaluator()
        self.tt = TranspositionTable()
        self.search = Search(evaluator=self.evaluator, tt=self.tt)
        self.running = False
        self.input = input_stream
        self.output = output_stream

        # Options
        self.options = {
            "depth": 4,
            "time_limit": None,
        }

    def send(self, msg: str) -> None:
        """Send a message to the output stream."""
        self.output.write(f"{msg}\n")
        self.output.flush()

    def run(self) -> None:
        """Main UCI loop."""
        self.running = True
        while self.running:
            line = self.input.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            self.handle_command(line)

    def handle_command(self, line: str) -> None:
        """Handle a single UCI command."""
        parts = line.split()
        if not parts:
            return
        cmd = parts[0].lower()

        if cmd == "uci":
            self._cmd_uci()
        elif cmd == "isready":
            self.send("readyok")
        elif cmd == "setoption":
            self._cmd_setoption(parts[1:])
        elif cmd == "ucinewgame":
            self.board = Board()
            self.tt.clear()
            self.search = Search(evaluator=self.evaluator, tt=self.tt)
        elif cmd == "position":
            self._cmd_position(parts[1:])
        elif cmd == "go":
            self._cmd_go(parts[1:])
        elif cmd == "stop":
            pass  # search is synchronous, can't interrupt easily
        elif cmd == "quit":
            self.running = False
        elif cmd == "d":
            # Non-standard but useful: display board
            self.send(self.board.to_string())
        elif cmd == "eval":
            score = self.evaluator.evaluate(self.board)
            self.send(f"info score cp {score}")

    def _cmd_uci(self) -> None:
        self.send("id name chess-engine v2.0")
        self.send("id author creative-projects")
        self.send("option name SearchDepth type spin default 4 min 1 max 10")
        self.send("option name TimeLimit type spin default 0 min 0 max 600000")
        self.send("uciok")

    def _cmd_setoption(self, args: list) -> None:
        """Handle: setoption name <name> value <value>"""
        try:
            # Parse "name X value Y"
            name_idx = args.index("name")
            value_idx = args.index("value")
            name = " ".join(args[name_idx + 1:value_idx])
            value = " ".join(args[value_idx + 1:])
            if name.lower() == "searchdepth":
                self.options["depth"] = int(value)
            elif name.lower() == "timelimit":
                v = int(value)
                self.options["time_limit"] = v / 1000.0 if v > 0 else None
        except (ValueError, IndexError):
            pass

    def _cmd_position(self, args: list) -> None:
        """Handle: position [fen <fenstring>] | startpos moves <move1> ..."""
        self.board = Board()
        self._position_history = {}
        idx = 0
        if idx < len(args) and args[idx] == "startpos":
            idx += 1
        elif idx < len(args) and args[idx] == "fen":
            idx += 1
            fen_parts = []
            while idx < len(args) and args[idx] != "moves":
                fen_parts.append(args[idx])
                idx += 1
            fen = " ".join(fen_parts)
            self.board = Board.from_fen(fen)

        # Apply moves
        if idx < len(args) and args[idx] == "moves":
            idx += 1
            for uci in args[idx:]:
                move = self._parse_uci(uci)
                if move:
                    self.board.push(move)

    def _cmd_go(self, args: list) -> None:
        """Handle: go [depth <n>] [movetime <ms>] [wtime <ms> btime <ms>]"""
        depth = self.options["depth"]
        time_limit = self.options["time_limit"]

        i = 0
        while i < len(args):
            if args[i] == "depth" and i + 1 < len(args):
                depth = int(args[i + 1])
                i += 2
            elif args[i] == "movetime" and i + 1 < len(args):
                time_limit = int(args[i + 1]) / 1000.0
                i += 2
            elif args[i] == "wtime" and i + 1 < len(args):
                # Simple time management: use a fraction of remaining time
                wtime = int(args[i + 1]) / 1000.0
                if self.board.turn == Color.WHITE:
                    time_limit = min(wtime / 30, 5.0)
                i += 2
            elif args[i] == "btime" and i + 1 < len(args):
                btime = int(args[i + 1]) / 1000.0
                if self.board.turn == Color.BLACK:
                    time_limit = min(btime / 30, 5.0)
                i += 2
            else:
                i += 1

        # Search
        move, score = self.search.search(self.board, depth=depth,
                                         time_limit=time_limit)

        if move:
            self.send(f"bestmove {move.uci()}")
        else:
            self.send("bestmove (none)")

    def _parse_uci(self, uci: str) -> Optional[Move]:
        """Parse a UCI move string."""
        uci = uci.strip().lower()
        if len(uci) < 4:
            return None
        from_sq = parse_square(uci[:2])
        to_sq = parse_square(uci[2:4])
        promotion = None
        if len(uci) == 5:
            promo_map = {"q": Piece.QUEEN, "r": Piece.ROOK,
                         "b": Piece.BISHOP, "n": Piece.KNIGHT}
            ptype = promo_map.get(uci[4])
            if ptype:
                promotion = Piece(ptype, self.board.turn)
        # Match against legal moves
        for m in self.board.legal_moves():
            if (m.from_square == from_sq and m.to_square == to_sq
                    and (m.promotion == promotion
                         or (m.promotion and promotion
                             and m.promotion.piece_type == promotion.piece_type))):
                return m
        return None