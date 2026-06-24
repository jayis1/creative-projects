"""Search module: alpha-beta pruning with quiescence search and move ordering.

Implements:
- Negamax with alpha-beta pruning
- Quiescence search (captures only) to avoid the horizon effect
- MVV-LVA move ordering for captures
- Killer moves heuristic
- Iterative deepening
- Time management
"""

from __future__ import annotations

import time
from typing import Optional, List, Tuple

from .board import Board, Move, Piece, Color
from .evaluate import Evaluator


MATE_SCORE = 100000
MATE_THRESHOLD = 99000


class Search:
    """Alpha-beta search engine with quiescence and move ordering."""

    def __init__(self, evaluator: Optional[Evaluator] = None) -> None:
        self.evaluator = evaluator or Evaluator()
        self.max_depth: int = 4
        self.time_limit: Optional[float] = None  # seconds
        self.nodes: int = 0
        self.start_time: float = 0.0
        self.stopped: bool = False

        # Killer moves: [depth][0] and [depth][1]
        self.killer_moves: dict[int, list[Move]] = {}

        # Best move from the root
        self.best_move: Optional[Move] = None
        self.best_score: int = 0
        self.pv: List[Move] = []  # principal variation

        # Configuration
        self.use_quiescence: bool = True
        self.use_killers: bool = True
        self.use_iterative_deepening: bool = True

    def _time_up(self) -> bool:
        if self.time_limit is None:
            return False
        return (time.time() - self.start_time) >= self.time_limit

    def search(self, board: Board, depth: Optional[int] = None,
               time_limit: Optional[float] = None) -> Tuple[Optional[Move], int]:
        """Search for the best move in the current position.

        Args:
            board: The current board position.
            depth: Maximum search depth (plies). If None, uses self.max_depth.
            time_limit: Maximum search time in seconds. If None, no time limit.

        Returns:
            (best_move, score) where score is from the side-to-move perspective.
        """
        self.nodes = 0
        self.stopped = False
        self.start_time = time.time()
        self.time_limit = time_limit
        self.killer_moves = {}
        self.best_move = None
        self.best_score = 0
        self.pv = []

        if depth is not None:
            self.max_depth = depth

        if self.use_iterative_deepening:
            best_move = None
            best_score = 0
            for d in range(1, self.max_depth + 1):
                move, score = self._search_root(board, d)
                if self.stopped:
                    break
                best_move = move
                self.best_move = move
                self.best_score = score
                # If we found a mate, stop searching
                if abs(score) > MATE_THRESHOLD:
                    break
            return best_move, self.best_score
        else:
            return self._search_root(board, self.max_depth)

    def _search_root(self, board: Board, depth: int) -> Tuple[Optional[Move], int]:
        """Root search: try all moves and return the best one."""
        moves = self._order_moves(board, board.legal_moves(), depth=0)
        best_move = None
        best_score = -MATE_SCORE - 1
        alpha = -MATE_SCORE - 1
        beta = MATE_SCORE + 1

        for move in moves:
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, ply=1)
            board.pop()

            if self.stopped:
                break

            if score > best_score:
                best_score = score
                best_move = move

            if score > alpha:
                alpha = score

        return best_move, best_score

    def _negamax(self, board: Board, depth: int, alpha: int, beta: int,
                 ply: int) -> int:
        """Negamax with alpha-beta pruning."""
        self.nodes += 1

        if self._time_up():
            self.stopped = True
            return 0

        if board.is_checkmate():
            return -MATE_SCORE + ply  # prefer faster mates
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        if board.is_fifty_move():
            return 0

        if depth <= 0:
            if self.use_quiescence:
                return self._quiescence(board, alpha, beta, ply)
            else:
                return self.evaluator.evaluate(board)

        moves = self._order_moves(board, board.legal_moves(), depth=ply)
        if not moves:
            # No legal moves (shouldn't happen here since we checked
            # checkmate/stalemate above, but safety net)
            return 0

        for move in moves:
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.pop()

            if self.stopped:
                return 0

            if score >= beta:
                # Killer move heuristic (non-capture cutoff)
                if self.use_killers and not self._is_capture(board, move):
                    self._store_killer(move, ply)
                return beta  # fail-high

            if score > alpha:
                alpha = score

        return alpha

    def _quiescence(self, board: Board, alpha: int, beta: int, ply: int) -> int:
        """Quiescence search: only search captures to avoid horizon effect."""
        self.nodes += 1

        if self._time_up():
            self.stopped = True
            return 0

        stand_pat = self.evaluator.evaluate(board)

        if board.is_checkmate():
            return -MATE_SCORE + ply
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Generate only capture moves
        captures = [m for m in board.legal_moves()
                    if self._is_capture(board, m)]
        captures = self._order_moves(board, captures, depth=ply)

        for move in captures:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, ply + 1)
            board.pop()

            if self.stopped:
                return 0

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def _is_capture(self, board: Board, move: Move) -> bool:
        """Check if a move is a capture (including en passant)."""
        if move.is_en_passant:
            return True
        return board.piece_at(move.to_square) is not None

    def _order_moves(self, board: Board, moves: List[Move],
                     depth: int) -> List[Move]:
        """Order moves for better alpha-beta pruning efficiency.

        Uses MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
        for captures, and killer moves for quiet moves.
        """
        def move_score(m: Move) -> int:
            score = 0
            # Captures: MVV-LVA
            if self._is_capture(board, m):
                victim = board.piece_at(m.to_square)
                attacker = board.piece_at(m.from_square)
                v_val = victim.value if victim else 100  # en passant = pawn
                a_val = attacker.value if attacker else 100
                score = 10000 + v_val - a_val

            # Promotions
            if m.promotion:
                score += 9000

            # Killer moves
            if self.use_killers and score == 0:
                killers = self.killer_moves.get(depth, [])
                if m in killers:
                    score = 5000 + (killers.index(m) == 0) * 100

            return score

        return sorted(moves, key=move_score, reverse=True)

    def _store_killer(self, move: Move, ply: int) -> None:
        """Store a killer move at the given ply."""
        killers = self.killer_moves.setdefault(ply, [])
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    def get_info(self) -> dict:
        """Return search statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        nps = int(self.nodes / elapsed) if elapsed > 0 else 0
        return {
            "nodes": self.nodes,
            "time": elapsed,
            "nps": nps,
            "best_move": self.best_move.uci() if self.best_move else None,
            "best_score": self.best_score,
            "depth": self.max_depth,
        }