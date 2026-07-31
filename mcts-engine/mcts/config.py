"""
Configuration support for the MCTS engine.

Provides YAML and JSON configuration file loading, a dataclass-based
configuration schema, and a factory that builds engines and games from
config files.

Example YAML configuration:

    # mcts-config.yaml
    game:
      name: connect4
      size: 0            # 0 = default

    engine:
      policy: uct        # uct | rave
      exploration: 1.4142
      rave_k: 300
      simulation_limit: 10000
      time_limit: 0.0
      max_depth: 0
      rollout_limit: 200
      seed: 42
      verbose: false
      tree_reuse: false
      use_transposition: false
      progressive_bias: 0.0
      heuristic: false
      epsilon_rollout: 0.0
      parallel: 0       # 0 = single-threaded

Example JSON configuration:

    {
      "game": {"name": "tictactoe", "size": 0},
      "engine": {
        "policy": "rave",
        "simulation_limit": 5000,
        "rave_k": 300,
        "seed": 42
      }
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .core import GameState
from .engine import MCTSEngine
from .games import Connect4, Gomoku, Hex, Reversi, TicTacToe
from .heuristics import get_heuristic, make_rollout_policy
from .uct import RAVEPolicy, UCTPolicy


@dataclass
class GameConfig:
    """Configuration for the game to play."""

    name: str = "tictactoe"
    size: int = 0  # 0 = use game default

    def create(self) -> GameState:
        """Create a game instance from this config."""
        name = self.name.lower()
        if name == "tictactoe":
            return TicTacToe()
        if name == "connect4":
            return Connect4()
        if name == "gomoku":
            return Gomoku(self.size if self.size > 0 else 15)
        if name == "reversi":
            return Reversi(self.size if self.size > 0 else 8)
        if name == "hex":
            return Hex(self.size if self.size > 0 else 11)
        raise ValueError(f"Unknown game: {name}")


@dataclass
class EngineConfig:
    """Configuration for the MCTS engine."""

    policy: str = "uct"  # "uct" or "rave"
    exploration: float = 1.4142
    rave_k: float = 300.0
    simulation_limit: int = 10000
    time_limit: float = 0.0
    max_depth: int = 0
    rollout_limit: int = 200
    seed: int = 42
    verbose: bool = False
    tree_reuse: bool = False
    use_transposition: bool = False
    progressive_bias: float = 0.0
    heuristic: bool = False
    epsilon_rollout: float = 0.0
    parallel: int = 0  # 0 = single-threaded

    def create(self, game_name: str = "") -> MCTSEngine:
        """Build an MCTSEngine from this config."""
        if self.policy.lower() == "rave":
            policy = RAVEPolicy(self.exploration, self.rave_k)
            rave = True
        else:
            policy = UCTPolicy(self.exploration)
            rave = False

        heuristic_fn = None
        rollout_policy = None
        progressive_bias = self.progressive_bias

        if self.heuristic and game_name:
            heuristic_fn = get_heuristic(game_name)
            if heuristic_fn is not None and progressive_bias == 0.0:
                progressive_bias = 1.0
            if heuristic_fn is not None and self.epsilon_rollout > 0:
                rollout_policy = make_rollout_policy(
                    heuristic_fn, self.epsilon_rollout
                )

        return MCTSEngine(
            selection_policy=policy,
            simulation_limit=self.simulation_limit,
            time_limit=self.time_limit,
            max_depth=self.max_depth,
            use_transposition=self.use_transposition,
            rave=rave,
            seed=self.seed,
            verbose=self.verbose,
            rollout_policy=rollout_policy,
            progressive_bias=progressive_bias,
            heuristic_fn=heuristic_fn,
            tree_reuse=self.tree_reuse,
            rollout_limit=self.rollout_limit,
        )


@dataclass
class MCTSConfig:
    """Top-level configuration: game + engine."""

    game: GameConfig = field(default_factory=GameConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCTSConfig":
        """Create config from a dictionary (e.g., parsed JSON)."""
        game_data = data.get("game", {})
        engine_data = data.get("engine", {})
        return cls(
            game=GameConfig(**game_data),
            engine=EngineConfig(**engine_data),
        )

    @classmethod
    def from_json(cls, path: str) -> "MCTSConfig":
        """Load config from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, path: str) -> "MCTSConfig":
        """Load config from a YAML file.

        Falls back to JSON parsing if PyYAML is not installed, so YAML
        files that are also valid JSON still work.
        """
        try:
            import yaml  # type: ignore
        except ImportError:
            # Fallback: try JSON (also handles simple YAML that is valid JSON)
            return cls.from_json(path)
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: str) -> "MCTSConfig":
        """Auto-detect format by extension (.yaml/.yml -> YAML, .json -> JSON)."""
        ext = os.path.splitext(path)[1].lower()
        if ext in (".yaml", ".yml"):
            return cls.from_yaml(path)
        return cls.from_json(path)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "game": {
                "name": self.game.name,
                "size": self.game.size,
            },
            "engine": {
                "policy": self.engine.policy,
                "exploration": self.engine.exploration,
                "rave_k": self.engine.rave_k,
                "simulation_limit": self.engine.simulation_limit,
                "time_limit": self.engine.time_limit,
                "max_depth": self.engine.max_depth,
                "rollout_limit": self.engine.rollout_limit,
                "seed": self.engine.seed,
                "verbose": self.engine.verbose,
                "tree_reuse": self.engine.tree_reuse,
                "use_transposition": self.engine.use_transposition,
                "progressive_bias": self.engine.progressive_bias,
                "heuristic": self.engine.heuristic,
                "epsilon_rollout": self.engine.epsilon_rollout,
                "parallel": self.engine.parallel,
            },
        }

    def to_json(self, path: str, indent: int = 2) -> None:
        """Save config to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=indent)