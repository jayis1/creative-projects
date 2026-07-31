"""
Selection policies for MCTS.

Provides UCT (UCB1 applied to trees) and RAVE selection policies
that can be plugged into the MCTS engine.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import MCTSNode


class SelectionPolicy(ABC):
    """Abstract base class for tree-node selection policies."""

    @abstractmethod
    def select_child(self, node: "MCTSNode") -> "MCTSNode | None":
        """Select a child of the given node according to the policy."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this policy."""
        ...


class UCTPolicy(SelectionPolicy):
    """UCT (Upper Confidence bounds applied to Trees) selection policy.

    Uses the UCB1 formula: exploitation + exploration.
    The exploration constant controls the exploration/exploitation trade-off.
    A value of sqrt(2) ≈ 1.4142 is the classic default.
    """

    def __init__(self, exploration: float = 1.4142) -> None:
        if exploration < 0:
            raise ValueError("exploration constant must be non-negative")
        self.exploration = exploration

    def select_child(self, node: "MCTSNode") -> "MCTSNode | None":
        return node.best_child(self.exploration)

    @property
    def name(self) -> str:
        return f"UCT(c={self.exploration:.4f})"


class RAVEPolicy(SelectionPolicy):
    """RAVE (Rapid Action Value Estimation) selection policy.

    Blends MCTS value estimates with AMAF (All Moves As First) estimates
    for faster convergence, especially useful in games like Go and Hex.
    """

    def __init__(self, exploration: float = 1.4142, rave_k: float = 1000.0) -> None:
        if exploration < 0:
            raise ValueError("exploration constant must be non-negative")
        if rave_k <= 0:
            raise ValueError("rave_k must be positive")
        self.exploration = exploration
        self.rave_k = rave_k

    def select_child(self, node: "MCTSNode") -> "MCTSNode | None":
        return node.best_child_rave(self.exploration, self.rave_k)

    @property
    def name(self) -> str:
        return f"RAVE(c={self.exploration:.4f}, k={self.rave_k:.0f})"