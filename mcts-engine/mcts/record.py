"""
Game record and serialization for MCTS games.

Supports saving/loading games in a JSON format with full move history,
search statistics, and metadata. Also supports exporting to a
human-readable text format.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .core import GameMove, GameState, Player
from .engine import MCTSEngine


@dataclass
class GameRecord:
    """A record of a played game.

    Attributes:
        game_type: Name of the game (e.g., "tictactoe").
        moves: List of (player, move) tuples.
        winner: The winning player, or Player.NONE for draw.
        board_size: Size of the board (for size-configurable games).
        metadata: Optional metadata dict (timestamps, engine config, etc.).
        search_stats: Per-move search statistics (simulations, win_rate, time).
    """

    game_type: str
    moves: List[Dict[str, Any]] = field(default_factory=list)
    winner: str = "NONE"
    board_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    search_stats: List[Dict[str, Any]] = field(default_factory=list)

    def add_move(self, player: Player, move: GameMove, sims: int = 0, win_rate: float = 0.0, elapsed: float = 0.0) -> None:
        """Record a move in the game."""
        self.moves.append({
            "player": player.name,
            "row": move.row,
            "col": move.col,
        })
        self.search_stats.append({
            "simulations": sims,
            "win_rate": win_rate,
            "time": elapsed,
        })

    def set_winner(self, player: Player) -> None:
        self.winner = player.name

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "game_type": self.game_type,
            "winner": self.winner,
            "board_size": self.board_size,
            "moves": self.moves,
            "search_stats": self.search_stats,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameRecord":
        """Deserialize from a dictionary."""
        return cls(
            game_type=data["game_type"],
            moves=data.get("moves", []),
            winner=data.get("winner", "NONE"),
            board_size=data.get("board_size", 0),
            metadata=data.get("metadata", {}),
            search_stats=data.get("search_stats", []),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "GameRecord":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str) -> None:
        """Save to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "GameRecord":
        """Load from a JSON file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def to_text(self) -> str:
        """Convert to a human-readable text format."""
        lines = [
            f"Game: {self.game_type}",
            f"Winner: {self.winner}",
            f"Moves: {len(self.moves)}",
            "",
        ]
        for i, (move, stats) in enumerate(zip(self.moves, self.search_stats)):
            player = move["player"]
            row, col = move["row"], move["col"]
            sims = stats.get("simulations", 0)
            wr = stats.get("win_rate", 0.0)
            lines.append(f"  {i+1:3d}. {player:4s} ({row:2d},{col:2d})  sims={sims:6d}  wr={wr:.1%}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"GameRecord({self.game_type}, {len(self.moves)} moves, winner={self.winner})"


def play_recorded_game(
    game: GameState,
    engine: MCTSEngine,
    game_type: str = "",
    max_moves: int = 200,
) -> tuple:
    """Play a self-play game and return both the final state and a GameRecord.

    Args:
        game: Initial game state.
        engine: MCTS engine for all moves.
        game_type: Name of the game for the record.
        max_moves: Safety limit.

    Returns:
        (final_state, game_record)
    """
    from .games import Connect4, Gomoku, Hex, Reversi, TicTacToe

    if not game_type:
        game_type = type(game).__name__.lower()

    board_size = 0
    if isinstance(game, (Gomoku, Hex, Reversi)):
        board_size = game.rows
    elif isinstance(game, Connect4):
        board_size = game.cols

    record = GameRecord(game_type=game_type, board_size=board_size)
    record.metadata["timestamp"] = time.time()
    record.metadata["engine_policy"] = engine.policy.name
    record.metadata["simulation_limit"] = engine.simulation_limit

    current = game
    count = 0

    while not current.is_terminal() and count < max_moves:
        player = current.current_player()
        result = engine.search(current)
        if result.best_move is None:
            break
        record.add_move(
            player, result.best_move,
            sims=result.simulations,
            win_rate=result.win_rate,
            elapsed=result.time_elapsed,
        )
        current = current.apply(result.best_move)
        count += 1

    record.set_winner(current.winner())
    record.metadata["total_time"] = sum(s["time"] for s in record.search_stats)
    record.metadata["total_simulations"] = sum(s["simulations"] for s in record.search_stats)

    return current, record