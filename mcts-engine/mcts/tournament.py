"""
Tournament mode for comparing MCTS engine configurations.

Runs a round-robin tournament between multiple engine configurations,
records results, computes Elo ratings, and generates a summary report.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .core import GameMove, GameState, Player
from .engine import MCTSEngine
from .games import Connect4, Gomoku, Hex, Reversi, TicTacToe


@dataclass
class PlayerSpec:
    """Specification for a tournament player (engine configuration)."""
    name: str
    engine: MCTSEngine


@dataclass
class GameResult:
    """Result of a single tournament game."""
    player1: str
    player2: str
    winner: str  # player name or "Draw"
    moves: int
    duration: float


@dataclass
class TournamentResult:
    """Complete tournament results with standings."""
    games: List[GameResult] = field(default_factory=list)
    standings: Dict[str, Dict[str, float]] = field(default_factory=dict)
    elo_ratings: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate a text summary of the tournament."""
        lines = ["Tournament Results", "=" * 40, ""]

        # Standings table
        lines.append(f"{'Player':<20s} {'W':>4s} {'L':>4s} {'D':>4s} {'Elo':>6s}")
        lines.append("-" * 40)
        sorted_players = sorted(
            self.standings.items(),
            key=lambda x: x[1].get("elo", 1000),
            reverse=True,
        )
        for name, stats in sorted_players:
            w = stats.get("wins", 0)
            l = stats.get("losses", 0)
            d = stats.get("draws", 0)
            elo = stats.get("elo", 1000)
            lines.append(f"{name:<20s} {w:>4d} {l:>4d} {d:>4d} {elo:>6.0f}")

        lines.append("")
        lines.append(f"Total games: {len(self.games)}")
        return "\n".join(lines)


class Tournament:
    """Round-robin tournament between MCTS engine configurations.

    Each player plays every other player twice (once as first player,
    once as second). Elo ratings are updated after each game.

    Example::

        from mcts.tournament import Tournament, PlayerSpec
        from mcts import MCTSEngine, TicTacToe, UCTPolicy, RAVEPolicy

        players = [
            PlayerSpec("UCT", MCTSEngine(UCTPolicy(1.4142), simulation_limit=2000, seed=42)),
            PlayerSpec("RAVE", MCTSEngine(RAVEPolicy(1.4142, 300), simulation_limit=2000, rave=True, seed=99)),
        ]
        tourney = Tournament(players, game_factory=lambda: TicTacToe())
        result = tourney.run()
        print(result.summary())
    """

    def __init__(
        self,
        players: List[PlayerSpec],
        game_factory,
        rounds: int = 2,
        max_moves: int = 200,
        initial_elo: float = 1000.0,
        k_factor: float = 32.0,
    ) -> None:
        self.players = players
        self.game_factory = game_factory
        self.rounds = rounds
        self.max_moves = max_moves
        self.initial_elo = initial_elo
        self.k_factor = k_factor
        self._elo: Dict[str, float] = {
            p.name: initial_elo for p in players
        }
        self._standings: Dict[str, Dict[str, float]] = {
            p.name: {"wins": 0, "losses": 0, "draws": 0, "elo": initial_elo}
            for p in players
        }

    def _update_elo(self, p1: str, p2: str, result: float) -> None:
        """Update Elo ratings. result: 1.0 = p1 wins, 0.5 = draw, 0.0 = p2 wins."""
        e1 = 1.0 / (1.0 + 10 ** ((self._elo[p2] - self._elo[p1]) / 400.0))
        e2 = 1.0 - e1
        self._elo[p1] += self.k_factor * (result - e1)
        self._elo[p2] += self.k_factor * ((1.0 - result) - e2)
        self._standings[p1]["elo"] = self._elo[p1]
        self._standings[p2]["elo"] = self._elo[p2]

    def _play_game(self, p1: PlayerSpec, p2: PlayerSpec) -> GameResult:
        """Play a single game between two players."""
        game = self.game_factory()
        current = game
        count = 0
        start = time.time()

        while not current.is_terminal() and count < self.max_moves:
            player = current.current_player()
            eng = p1.engine if player == Player.ONE else p2.engine
            result = eng.search(current)
            if result.best_move is None:
                break
            current = current.apply(result.best_move)
            count += 1

        duration = time.time() - start
        w = current.winner()
        if w == Player.ONE:
            winner_name = p1.name
            self._standings[p1.name]["wins"] += 1
            self._standings[p2.name]["losses"] += 1
            self._update_elo(p1.name, p2.name, 1.0)
        elif w == Player.TWO:
            winner_name = p2.name
            self._standings[p2.name]["wins"] += 1
            self._standings[p1.name]["losses"] += 1
            self._update_elo(p1.name, p2.name, 0.0)
        else:
            winner_name = "Draw"
            self._standings[p1.name]["draws"] += 1
            self._standings[p2.name]["draws"] += 1
            self._update_elo(p1.name, p2.name, 0.5)

        return GameResult(
            player1=p1.name,
            player2=p2.name,
            winner=winner_name,
            moves=count,
            duration=duration,
        )

    def run(self) -> TournamentResult:
        """Run the full round-robin tournament.

        Each round, every pair plays two games (once as player 1,
        once as player 2). So with R rounds and N players, the total
        number of games is R * N * (N-1).
        """
        results = TournamentResult()
        results.elo_ratings = dict(self._elo)

        n = len(self.players)
        for r in range(self.rounds):
            for i in range(n):
                for j in range(i + 1, n):
                    # Play both sides each round
                    p1, p2 = self.players[i], self.players[j]
                    gr1 = self._play_game(p1, p2)
                    results.games.append(gr1)
                    print(f"  {gr1.player1} vs {gr1.player2}: {gr1.winner} "
                          f"({gr1.moves} moves, {gr1.duration:.1f}s)")
                    # Swap sides
                    gr2 = self._play_game(p2, p1)
                    results.games.append(gr2)
                    print(f"  {gr2.player1} vs {gr2.player2}: {gr2.winner} "
                          f"({gr2.moves} moves, {gr2.duration:.1f}s)")

        results.standings = dict(self._standings)
        results.elo_ratings = dict(self._elo)
        return results