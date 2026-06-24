"""Search module: alpha-beta pruning with quiescence search and move ordering.

Implements:
- Negamax with alpha-beta pruning
- Quiescence search (captures only) to avoid the horizon effect
- MVV-LVA move ordering for captures
- Killer moves heuristic
- History heuristic
- Late move reductions (LMR)
- Null move pruning
- Iterative deepening
- Principal variation (PV) tracking
- Time management
- Mate score handling with ply adjustment
"""

from __future__ import annotations

import logging
import time
from typing import Optional, List, Tuple, Dict

from .board import Board, Move, Piece, Color
from .evaluate import Evaluator
from .transposition import TranspositionTable, TTEntry, FLAG_EXACT, FLAG_LOWER, FLAG_UPPER
from .zobrist import ZobristHash

logger = logging.getLogger(__name__)

MATE_SCORE = 100000
MATE_THRESHOLD = 99000

# Late-move-reduction parameters
LMR_FULL_DEPTH_MOVES = 3   # number of moves at full depth before reducing
LMR_REDUCTION = 1          # depth reduction for late moves
LMR_MIN_DEPTH = 3          # don't reduce below this depth

# Null-move pruning parameters
NULL_MOVE_R = 2            # depth reduction for null move search
NULL_MOVE_MIN_DEPTH = 3    # don't do null move below this depth


class Search:
    """Alpha-beta search engine with quiescence, move ordering, and
    transposition table.

    Features:
    - Negamax with alpha-beta pruning
    - Quiescence search (captures only, or all moves when in check)
    - MVV-LVA move ordering for captures
    - Killer move heuristic for quiet moves
    - History heuristic for quiet move ordering
    - Late move reductions (LMR) for poorly-ordered moves
    - Null move pruning
    - Transposition table with Zobrist hashing
    - Iterative deepening with PV tracking
    - Time management
    - Mate score handling (prefers faster mates, ply-adjusted)
    """

    def __init__(self, evaluator: Optional[Evaluator] = None,
                 tt: Optional[TranspositionTable] = None) -> None:
        self.evaluator = evaluator or Evaluator()
        self.tt = tt or TranspositionTable()
        self.zobrist = ZobristHash()
        self.max_depth: int = 4
        self.time_limit: Optional[float] = None  # seconds
        self.nodes: int = 0
        self.start_time: float = 0.0
        self.stopped: bool = False

        # Killer moves: [depth][0] and [depth][1]
        self.killer_moves: Dict[int, List[Move]] = {}

        # History heuristic: [from_square][to_square] -> score
        self.history: List[List[int]] = [[0] * 64 for _ in range(64)]

        # Best move from the root
        self.best_move: Optional[Move] = None
        self.best_score: int = 0
        self.pv: List[Move] = []  # principal variation

        # Configuration
        self.use_quiescence: bool = True
        self.use_killers: bool = True
        self.use_history: bool = True
        self.use_lmr: bool = True
        self.use_null_move: bool = True
        self.use_iterative_deepening: bool = True
        self.use_tt: bool = True

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
        self.history = [[0] * 64 for _ in range(64)]
        self.best_move = None
        self.best_score = 0
        self.pv = []

        if depth is not None:
            self.max_depth = depth

        if self.use_iterative_deepening:
            best_move = None
            best_score = 0
            for d in range(1, self.max_depth + 1):
                move, score, pv = self._search_root(board, d)
                if self.stopped and best_move is not None:
                    # Don't use results from an incomplete search iteration
                    break
                if move is not None:
                    best_move = move
                    self.best_move = move
                    self.best_score = score
                    self.pv = pv
                logger.debug(
                    "iterative deepening depth=%d score=%d move=%s nodes=%d",
                    d, score, move.uci() if move else "none", self.nodes
                )
                # If we found a mate, stop searching
                if abs(score) > MATE_THRESHOLD:
                    break
            return best_move, self.best_score
        else:
            move, score, _ = self._search_root(board, self.max_depth)
            self.best_move = move
            self.best_score = score
            return move, score

    def _search_root(self, board: Board, depth: int
                     ) -> Tuple[Optional[Move], int, List[Move]]:
        """Root search: try all moves and return the best one.

        Returns (best_move, score, principal_variation).
        """
        moves = self._order_moves(board, board.legal_moves(), depth=0)
        best_move = None
        best_score = -MATE_SCORE - 1
        alpha = -MATE_SCORE - 1
        beta = MATE_SCORE + 1
        best_pv: List[Move] = []

        for i, move in enumerate(moves):
            board.push(move)
            # PV tracking: child returns its PV
            score, child_pv = self._negamax(board, depth - 1, -beta, -alpha, ply=1)
            score = -score
            board.pop()

            if self.stopped:
                break

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv

            if score > alpha:
                alpha = score

            # Update history for the move that raised alpha at root
            if self.use_history and not self._is_capture(board, move):
                self._update_history(move, depth)

        return best_move, best_score, best_pv

    def _negamax(self, board: Board, depth: int, alpha: int, beta: int,
                 ply: int, can_null: bool = True) -> Tuple[int, List[Move]]:
        """Negamax with alpha-beta pruning and transposition table lookup.

        Returns (score, principal_variation).
        """
        self.nodes += 1

        if self._time_up():
            self.stopped = True
            return 0, []

        if board.is_checkmate():
            return -MATE_SCORE + ply, []
        if board.is_stalemate() or board.is_insufficient_material():
            return 0, []
        if board.is_fifty_move():
            return 0, []
        if board.is_threefold_repetition():
            return 0, []

        # Transposition table probe
        tt_move: Optional[Move] = None
        key = 0
        if self.use_tt:
            key = self.zobrist.hash(board)
            entry = self.tt.probe(key)
            if entry is not None:
                tt_move = entry.best_move
                if entry.depth >= depth:
                    # Adjust mate scores for ply distance
                    score = entry.score
                    if abs(score) > MATE_THRESHOLD:
                        # Mate scores are stored relative to the ply at which
                        # they were found. Adjust for current ply.
                        if score > 0:
                            score = score + ply
                        else:
                            score = score - ply
                    if entry.flag == FLAG_EXACT:
                        return score, [tt_move] if tt_move else []
                    elif entry.flag == FLAG_LOWER and score >= beta:
                        return score, [tt_move] if tt_move else []
                    elif entry.flag == FLAG_UPPER and score <= alpha:
                        return score, [tt_move] if tt_move else []

        if depth <= 0:
            if self.use_quiescence:
                return self._quiescence(board, alpha, beta, ply), []
            else:
                return self.evaluator.evaluate(board), []

        # Null move pruning
        if (self.use_null_move and can_null and depth >= NULL_MOVE_MIN_DEPTH
                and not board.is_check()
                and self._has_non_pawn_material(board)):
            # Make a null move (pass turn)
            board.push_null()
            null_score, _ = self._negamax(
                board, depth - 1 - NULL_MOVE_R, -beta, -beta + 1, ply + 1,
                can_null=False)
            null_score = -null_score
            board.pop_null()

            if self.stopped:
                return 0, []

            if null_score >= beta:
                # Null move pruning: return beta (fail-high)
                return beta, []

        moves = self._order_moves(board, board.legal_moves(), depth=ply,
                                   tt_move=tt_move)
        if not moves:
            # No legal moves (shouldn't happen here since we checked
            # checkmate/stalemate above, but safety net)
            return 0, []

        best_score = -MATE_SCORE - 1
        best_move: Optional[Move] = None
        original_alpha = alpha
        best_pv: List[Move] = []

        for i, move in enumerate(moves):
            board.push(move)

            # Late move reductions
            score: int
            child_pv: List[Move]
            if (self.use_lmr and depth >= LMR_MIN_DEPTH
                    and i >= LMR_FULL_DEPTH_MOVES
                    and not self._is_capture(board, move)
                    and not move.promotion
                    and not board.is_check()):
                # Reduced search
                r_score, r_pv = self._negamax(
                    board, depth - 1 - LMR_REDUCTION, -alpha - 1, -alpha,
                    ply + 1)
                score = -r_score
                child_pv = r_pv
                # Re-search if the reduced search improves alpha
                if score > alpha:
                    score, child_pv = self._negamax(
                        board, depth - 1, -beta, -alpha, ply + 1)
                    score = -score
            else:
                raw_score, child_pv = self._negamax(
                    board, depth - 1, -beta, -alpha, ply + 1)
                score = -raw_score

            board.pop()

            if self.stopped:
                return 0, []

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv

            if score >= beta:
                # Killer move heuristic (non-capture cutoff)
                if self.use_killers and not self._is_capture(board, move):
                    self._store_killer(move, ply)
                if self.use_history and not self._is_capture(board, move):
                    self._update_history(move, depth)
                # Store in TT (adjust mate scores for ply)
                if self.use_tt:
                    store_score = score
                    if abs(store_score) > MATE_THRESHOLD:
                        store_score = store_score - ply if store_score > 0 else store_score + ply
                    self.tt.store(key, depth, store_score, FLAG_LOWER, best_move)
                return beta, best_pv  # fail-high

            if score > alpha:
                alpha = score

        # Store in TT (adjust mate scores for ply)
        if self.use_tt and not self.stopped:
            store_score = best_score
            if abs(store_score) > MATE_THRESHOLD:
                store_score = store_score - ply if store_score > 0 else store_score + ply
            if best_score > original_alpha:
                flag = FLAG_EXACT
            else:
                flag = FLAG_UPPER
            self.tt.store(key, depth, store_score, flag, best_move)

        return alpha, best_pv

    def _quiescence(self, board: Board, alpha: int, beta: int, ply: int) -> int:
        """Quiescence search: only search captures to avoid horizon effect.

        When in check, search ALL legal moves (not just captures) since
        the player must escape check. This prevents missing checkmates
        and check evasions at the horizon.

        Returns the quiescence score from the side-to-move perspective.
        """
        self.nodes += 1

        if self._time_up():
            self.stopped = True
            return 0

        if board.is_checkmate():
            return -MATE_SCORE + ply
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        in_check = board.is_check()

        if not in_check:
            # Stand-pat evaluation (not in check, can skip capturing)
            stand_pat = self.evaluator.evaluate(board)
            if stand_pat >= beta:
                return beta
            if stand_pat > alpha:
                alpha = stand_pat

        # When in check, search ALL legal moves (must escape check).
        # When not in check, search only captures.
        if in_check:
            moves = board.legal_moves()
        else:
            moves = [m for m in board.legal_moves()
                     if self._is_capture(board, m)]

        moves = self._order_moves(board, moves, depth=ply)

        for move in moves:
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

    def _has_non_pawn_material(self, board: Board) -> bool:
        """Check if the side to move has non-pawn material for null-move pruning.

        Null move pruning must not be used in zugzwang-like positions where
        the side to move has only pawns and king, because passing the move
        would be an advantage, not a disadvantage.
        """
        color = board.turn
        for sq in range(64):
            p = board.squares[sq]
            if (p is not None and p.color == color
                    and p.piece_type not in (Piece.PAWN, Piece.KING)):
                return True
        return False

    def _is_capture(self, board: Board, move: Move) -> bool:
        """Check if a move is a capture (including en passant)."""
        if move.is_en_passant:
            return True
        return board.piece_at(move.to_square) is not None

    def _order_moves(self, board: Board, moves: List[Move],
                     depth: int, tt_move: Optional[Move] = None) -> List[Move]:
        """Order moves for better alpha-beta pruning efficiency.

        Uses MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
        for captures, killer moves and history heuristic for quiet moves,
        and TT best move first.
        """
        def move_score(m: Move) -> int:
            score = 0

            # TT best move gets highest priority
            if tt_move is not None and m == tt_move:
                return 20000

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

            # History heuristic
            if self.use_history and score == 0:
                h = self.history[m.from_square][m.to_square]
                score = min(h, 4000)  # cap below killer range

            return score

        return sorted(moves, key=move_score, reverse=True)

    def _store_killer(self, move: Move, ply: int) -> None:
        """Store a killer move at the given ply."""
        killers = self.killer_moves.setdefault(ply, [])
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    def _update_history(self, move: Move, depth: int) -> None:
        """Update the history heuristic table for a quiet move that caused a cutoff."""
        self.history[move.from_square][move.to_square] += depth * depth

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
            "pv": [m.uci() for m in self.pv] if self.pv else [],
        }

    def reset(self) -> None:
        """Reset search state for a new game or position."""
        self.killer_moves = {}
        self.history = [[0] * 64 for _ in range(64)]
        self.nodes = 0
        self.best_move = None
        self.best_score = 0
        self.pv = []
        self.stopped = False