"""
MCTS Engine — Monte Carlo Tree Search for game AI.

A from-scratch implementation of MCTS supporting multiple games
with UCT, RAVE/AMAF, transposition tables, progressive bias,
heuristic-guided rollouts, tree reuse, parallel search, minimax,
opening books, tournament mode, and configuration file support.
"""

from mcts.core import (
    GameState,
    GameMove,
    Player,
    MCTSNode,
    MCTSResult,
)
from mcts.engine import (
    MCTSEngine,
    TranspositionTable,
    SearchStats,
    RolloutPolicy,
)
from mcts.games import (
    TicTacToe,
    Connect4,
    Hex,
    Gomoku,
    Reversi,
)
from mcts.uct import UCTPolicy, SelectionPolicy
from mcts.rave import RAVEPolicy
from mcts.heuristics import (
    tictactoe_heuristic,
    connect4_heuristic,
    reversi_heuristic,
    hex_heuristic,
    gomoku_heuristic,
    get_heuristic,
    make_rollout_policy,
)
from mcts.record import GameRecord, play_recorded_game
from mcts.config import MCTSConfig, GameConfig, EngineConfig
from mcts.minimax import MinimaxEngine, MinimaxResult
from mcts.opening_book import OpeningBook
from mcts.tournament import Tournament, PlayerSpec, TournamentResult

__version__ = "3.0.0"

__all__ = [
    # Core
    "GameState",
    "GameMove",
    "Player",
    "MCTSNode",
    "MCTSResult",
    # Engine
    "MCTSEngine",
    "TranspositionTable",
    "SearchStats",
    "RolloutPolicy",
    # Games
    "TicTacToe",
    "Connect4",
    "Hex",
    "Gomoku",
    "Reversi",
    # Policies
    "UCTPolicy",
    "SelectionPolicy",
    "RAVEPolicy",
    # Heuristics
    "tictactoe_heuristic",
    "connect4_heuristic",
    "reversi_heuristic",
    "hex_heuristic",
    "gomoku_heuristic",
    "get_heuristic",
    "make_rollout_policy",
    # Records
    "GameRecord",
    "play_recorded_game",
    # Config
    "MCTSConfig",
    "GameConfig",
    "EngineConfig",
    # Minimax
    "MinimaxEngine",
    "MinimaxResult",
    # Opening Book
    "OpeningBook",
    # Tournament
    "Tournament",
    "PlayerSpec",
    "TournamentResult",
]