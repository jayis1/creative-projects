"""
Minimax with alpha-beta pruning — an alternative to MCTS for small games.

Provides exact search for games with small state spaces (like Tic-Tac-Toe
and small Hex boards). Supports depth limiting, transposition tables,
and move ordering for efficient pruning.

Example::

    from mcts.games import TicTacToe
    from mcts.minimax import MinimaxEngine

    game = TicTacToe()
    engine = MinimaxEngine(max_depth=9)
    result = engine.search(game)
    print(f"Best move: {result.best_move}, score: {result.score}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .core import GameMove, GameState, Player


@dataclass
class MinimaxResult:
    """Result of a minimax search.

    Attributes:
        best_move: The best move found.
        score: The minimax score from the searching player's perspective
            (+1 win, -1 loss, 0 draw).
        depth: Search depth reached.
        nodes_searched: Number of nodes evaluated.
        time_elapsed: Wall-clock time in seconds.
        principal_variation: Best move sequence.
    """
    best_move: Optional[GameMove] = None
    score: float = 0.0
    depth: int = 0
    nodes_searched: int = 0
    time_elapsed: float = 0.0
    principal_variation: List[GameMove] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"MinimaxResult(best_move={self.best_move}, score={self.score:+.1f}, "
            f"depth={self.depth}, nodes={self.nodes_searched}, "
            f"time={self.time_elapsed:.3f}s)"
        )


class MinimaxEngine:
    """Minimax with alpha-beta pruning.

    For small games (Tic-Tac-Toe, small Hex), this provides exact
    play — it will never lose if a draw or win is possible.

    Args:
        max_depth: Maximum search depth (0 = unlimited).
        use_transposition: Whether to use a transposition table.
        verbose: If True, print search statistics.
    """

    def __init__(
        self,
        max_depth: int = 0,
        use_transposition: bool = True,
        verbose: bool = False,
    ) -> None:
        self.max_depth = max_depth
        self.use_transposition = use_transposition
        self.verbose = verbose
        self._transposition: Dict[str, Tuple[float, int]] = {}
        self._nodes = 0

    def search(self, state: GameState) -> MinimaxResult:
        """Run minimax search from the given state.

        Returns the best move and score from the current player's perspective.
        """
        start = time.time()
        self._nodes = 0
        if self.use_transposition:
            self._transposition.clear()

        player = state.current_player()
        depth = self.max_depth if self.max_depth > 0 else 1000
        score, move, pv = self._minimax(
            state, depth, -2.0, 2.0, True, player
        )

        elapsed = time.time() - start
        if self.verbose:
            print(f"Minimax: score={score:+.1f}, nodes={self._nodes}, "
                  f"time={elapsed:.3f}s")

        return MinimaxResult(
            best_move=move,
            score=score,
            depth=depth,
            nodes_searched=self._nodes,
            time_elapsed=elapsed,
            principal_variation=pv,
        )

    def _minimax(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
        root_player: Player,
    ) -> Tuple[float, Optional[GameMove], List[GameMove]]:
        """Recursive minimax with alpha-beta pruning.

        Returns (score, best_move, principal_variation).
        """
        self._nodes += 1

        # Terminal node
        if state.is_terminal():
            w = state.winner()
            if w == root_player:
                return 1.0, None, []
            if w == Player.NONE:
                return 0.0, None, []
            return -1.0, None, []

        # Depth limit
        if depth <= 0:
            return 0.0, None, []

        # Transposition table lookup
        key = state.hash_key()
        if self.use_transposition and key in self._transposition:
            cached_score, cached_depth = self._transposition[key]
            if cached_depth >= depth:
                return cached_score, None, []

        legal = state.legal_moves()
        if not legal:
            return 0.0, None, []

        # Move ordering: try center moves first for better pruning
        ordered = self._order_moves(legal, state)

        best_move = ordered[0]
        best_pv: List[GameMove] = []

        # Standard minimax (not negamax): terminal scores are always from
        # root_player's perspective. At maximizing nodes (root_player's turn)
        # we pick the highest score; at minimizing nodes (opponent's turn)
        # we pick the lowest. No score negation needed.
        if maximizing:
            best_score = -2.0
            for move in ordered:
                child = state.apply(move)
                score, _, child_pv = self._minimax(
                    child, depth - 1, alpha, beta, False, root_player
                )
                if score > best_score:
                    best_score = score
                    best_move = move
                    best_pv = [move] + child_pv
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break  # alpha-beta cutoff
        else:
            best_score = 2.0
            for move in ordered:
                child = state.apply(move)
                score, _, child_pv = self._minimax(
                    child, depth - 1, alpha, beta, True, root_player
                )
                if score < best_score:
                    best_score = score
                    best_move = move
                    best_pv = [move] + child_pv
                beta = min(beta, best_score)
                if beta <= alpha:
                    break  # alpha-beta cutoff

        if self.use_transposition:
            self._transposition[key] = (best_score, depth)

        return best_score, best_move, best_pv

    def _order_moves(self, moves: List[GameMove], state: GameState) -> List[GameMove]:
        """Order moves for better alpha-beta pruning.

        Center moves are tried first, as they tend to be stronger
        in most grid games.
        """
        if not hasattr(state, "rows"):
            return moves
        center_r = state.rows / 2  # type: ignore
        center_c = state.cols / 2  # type: ignore
        return sorted(
            moves,
            key=lambda m: abs(m.row - center_r) + abs(m.col - center_c),
        )

    def reset(self) -> None:
        """Reset the engine state."""
        self._transposition.clear()
        self._nodes = 0