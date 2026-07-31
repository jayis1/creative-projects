"""
MCTS Engine — Monte Carlo Tree Search for game AI.

A from-scratch implementation of MCTS supporting multiple games
with UCT, RAVE/AMAF, transposition tables, and parallel search.
"""

from mcts.core import (
    GameState,
    GameMove,
    Player,
    MCTSNode,
    MCTSResult,
)
from mcts.engine import MCTSEngine
from mcts.games import (
    TicTacToe,
    Connect4,
    Hex,
    Gomoku,
    Reversi,
)
from mcts.uct import UCTPolicy
from mcts.rave import RAVEPolicy

__version__ = "1.0.0"

__all__ = [
    "GameState",
    "GameMove",
    "Player",
    "MCTSNode",
    "MCTSResult",
    "MCTSEngine",
    "TicTacToe",
    "Connect4",
    "Hex",
    "Gomoku",
    "Reversi",
    "UCTPolicy",
    "RAVEPolicy",
]