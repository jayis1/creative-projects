"""
Core data structures for MCTS.

Defines the abstract GameState interface that all games must implement,
the MCTSNode tree structure, and supporting types.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple


class Player(Enum):
    """Represents a player in a two-player zero-sum game."""

    NONE = 0
    ONE = 1
    TWO = 2

    @property
    def opponent(self) -> "Player":
        if self == Player.ONE:
            return Player.TWO
        if self == Player.TWO:
            return Player.ONE
        return Player.NONE

    def __str__(self) -> str:
        if self == Player.ONE:
            return "X"
        if self == Player.TWO:
            return "O"
        return "."


@dataclass(frozen=True)
class GameMove:
    """An immutable move representation.

    Args:
        row: Row index (0-based) for grid-based games, or -1 for non-grid.
        col: Column index (0-based) for grid-based games, or -1 for non-grid.
        extra: Optional extra data for moves that need more than (row, col).
    """

    row: int = -1
    col: int = -1
    extra: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        if self.extra:
            return f"Move({self.row},{self.col},{self.extra})"
        return f"Move({self.row},{self.col})"


class GameState(ABC):
    """Abstract base class for game states.

    All games must implement this interface to work with the MCTS engine.
    States should be immutable (or treated as such) — apply() returns a new
    state rather than mutating in place.
    """

    @abstractmethod
    def current_player(self) -> Player:
        """Return the player whose turn it is, or Player.NONE if terminal."""
        ...

    @abstractmethod
    def legal_moves(self) -> List[GameMove]:
        """Return all legal moves from this state. Empty if terminal."""
        ...

    @abstractmethod
    def apply(self, move: GameMove) -> "GameState":
        """Return a new state after applying the given move."""
        ...

    @abstractmethod
    def winner(self) -> Player:
        """Return the winning player, or Player.NONE if no winner / not terminal."""
        ...

    @abstractmethod
    def is_terminal(self) -> bool:
        """Return True if the game is over (win or draw)."""
        ...

    @abstractmethod
    def hash_key(self) -> str:
        """Return a unique string key for this state (for transposition tables)."""
        ...

    @abstractmethod
    def display(self) -> str:
        """Return a human-readable string representation of the board."""
        ...

    def reward(self, player: Player) -> float:
        """Return the reward for the given player from this terminal state.

        Default: 1.0 for win, 0.0 for loss, 0.5 for draw.
        Override for custom reward schemes.
        """
        if not self.is_terminal():
            return 0.0
        w = self.winner()
        if w == player:
            return 1.0
        if w == Player.NONE:
            return 0.5
        return 0.0


class MCTSNode:
    """A node in the MCTS search tree.

    Each node tracks visit counts, total reward, children, and parent
    information. Uses lazy expansion — children are created on first
    expansion, not at construction time.
    """

    __slots__ = (
        "state",
        "parent",
        "move",
        "children",
        "untried_moves",
        "visits",
        "total_reward",
        "player_to_move",
        "_is_terminal",
        "_winner",
        "_amaf_visits",
        "_amaf_reward",
        "_transposition_key",
    )

    def __init__(
        self,
        state: GameState,
        parent: Optional["MCTSNode"] = None,
        move: Optional[GameMove] = None,
    ) -> None:
        self.state: GameState = state
        self.parent: Optional[MCTSNode] = parent
        self.move: Optional[GameMove] = move  # move that led to this node
        self.children: List[MCTSNode] = []
        self.untried_moves: List[GameMove] = list(state.legal_moves()) if not state.is_terminal() else []
        self.visits: int = 0
        self.total_reward: float = 0.0
        self.player_to_move: Player = state.current_player()
        self._is_terminal: bool = state.is_terminal()
        self._winner: Player = state.winner()
        # RAVE/AMAF statistics
        self._amaf_visits: int = 0
        self._amaf_reward: float = 0.0
        self._transposition_key: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        return self._is_terminal

    @property
    def is_fully_expanded(self) -> bool:
        """True when all legal moves have been tried at least once."""
        return len(self.untried_moves) == 0 and not self._is_terminal

    @property
    def is_leaf(self) -> bool:
        """True when this node has no children (may still have untried moves)."""
        return len(self.children) == 0

    def average_reward(self) -> float:
        """Mean reward per visit (0 if unvisited)."""
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def ucb_value(self, exploration: float = 1.4142, parent_visits: int = 0) -> float:
        """UCB1 value for this node (from the parent's perspective).

        Args:
            exploration: Exploration constant (sqrt(2) by default).
            parent_visits: Number of visits to the parent node.

        Returns:
            UCB1 score. Returns infinity for unvisited nodes.
        """
        if self.visits == 0:
            return float("inf")
        exploit = self.average_reward()
        # BUG FIX: Guard against parent_visits=0 which causes math.log(0) -> ValueError.
        # When the parent has 0 visits, there's no exploration data, so we
        # return just the exploitation term. This can happen for the root node's
        # children when the root hasn't been visited yet via backprop.
        if parent_visits <= 0:
            return exploit
        explore = exploration * math.sqrt(math.log(parent_visits) / self.visits)
        return exploit + explore

    def best_child(self, exploration: float = 1.4142) -> Optional["MCTSNode"]:
        """Select the child with the highest UCB1 value.

        Returns:
            Best child node, or None if no children exist.
        """
        if not self.children:
            return None
        pv = self.visits
        return max(self.children, key=lambda c: c.ucb_value(exploration, pv))

    def expand(self) -> Optional["MCTSNode"]:
        """Expand one untried move, creating a new child node.

        Returns:
            The newly created child node, or None if no untried moves remain.
        """
        if not self.untried_moves:
            return None
        move = self.untried_moves.pop()
        new_state = self.state.apply(move)
        child = MCTSNode(new_state, parent=self, move=move)
        self.children.append(child)
        return child

    def update(self, reward: float) -> None:
        """Backpropagate a reward through this node and all ancestors."""
        node: Optional[MCTSNode] = self
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            # Flip reward perspective for parent (zero-sum)
            reward = 1.0 - reward
            node = node.parent

    def update_amaf(self, move: GameMove, reward: float) -> None:
        """Update AMAF (All Moves As First) statistics for RAVE.

        Called during backpropagation: for each ancestor, if the simulated
        move matches a child's move, update that child's AMAF stats.
        """
        for child in self.children:
            if child.move == move:
                child._amaf_visits += 1
                child._amaf_reward += reward

    def rave_value(self, exploration: float, parent_visits: int, rave_k: float = 1000.0) -> float:
        """RAVE-modified UCB value.

        Blends the node's own average reward with the AMAF estimate,
        weighted by a confidence parameter that decreases as visits grow.

        Args:
            exploration: UCB exploration constant.
            parent_visits: Parent node visit count.
            rave_k: RAVE equivalence parameter (higher = trust AMAF longer).

        Returns:
            RAVE score.
        """
        if self.visits == 0:
            return float("inf")
        beta = self._amaf_visits / (self.visits + self._amaf_visits + 4.0 * rave_k * self.visits * self._amaf_visits / max(1, (self.visits + self._amaf_visits + 4.0 * rave_k)))
        amaf_avg = self._amaf_reward / self._amaf_visits if self._amaf_visits > 0 else 0.0
        mc_avg = self.average_reward()
        blended = (1.0 - beta) * mc_avg + beta * amaf_avg
        # BUG FIX: Guard against parent_visits<=0 to avoid math.log(0) ValueError.
        if parent_visits <= 0:
            return blended
        explore = exploration * math.sqrt(math.log(parent_visits) / self.visits)
        return blended + explore

    def best_child_rave(self, exploration: float = 1.4142, rave_k: float = 1000.0) -> Optional["MCTSNode"]:
        """Select best child using RAVE values."""
        if not self.children:
            return None
        pv = self.visits
        return max(self.children, key=lambda c: c.rave_value(exploration, pv, rave_k))

    def depth(self) -> int:
        """Return the depth of this node from the root."""
        d = 0
        node = self.parent
        while node is not None:
            d += 1
            node = node.parent
        return d

    def tree_size(self) -> int:
        """Return total number of nodes in the subtree rooted here."""
        return 1 + sum(c.tree_size() for c in self.children)

    def principal_variation(self, exploration: float = 0.0) -> List[GameMove]:
        """Return the principal variation (best move sequence) from this node.

        With exploration=0, follows the most-visited child at each step.
        """
        pv: List[GameMove] = []
        node: Optional[MCTSNode] = self
        while node is not None and node.children:
            if exploration == 0.0:
                best = max(node.children, key=lambda c: c.visits)
            else:
                best = node.best_child(exploration)
            if best is None:
                break
            pv.append(best.move)  # type: ignore[arg-type]
            node = best
        return pv

    def __repr__(self) -> str:
        return (
            f"MCTSNode(visits={self.visits}, reward={self.total_reward:.2f}, "
            f"children={len(self.children)}, untried={len(self.untried_moves)}, "
            f"terminal={self._is_terminal})"
        )


@dataclass
class MCTSResult:
    """Result of an MCTS search.

    Attributes:
        best_move: The recommended move.
        root: The root MCTSNode (for tree analysis).
        simulations: Number of simulations performed.
        time_elapsed: Wall-clock time in seconds.
        win_rate: Estimated win rate for the best move.
    """

    best_move: Optional[GameMove]
    root: MCTSNode
    simulations: int
    time_elapsed: float
    win_rate: float
    principal_variation: List[GameMove] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"MCTSResult(best_move={self.best_move}, sims={self.simulations}, "
            f"time={self.time_elapsed:.3f}s, win_rate={self.win_rate:.1%}, "
            f"pv={self.principal_variation})"
        )