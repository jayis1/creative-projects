"""
Battle scheduler for running multi-round battles and tournaments.

Supports:
  - Round-robin tournaments between multiple warriors
  - Multi-round battles with randomized positions
  - Score tracking and statistics
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core_war.mars import MARS, BattleResult
from core_war.parser import ParsedWarrior


@dataclass
class BattleStats:
    """Statistics for a warrior across multiple rounds."""

    name: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_cycles: int = 0
    rounds_played: int = 0

    @property
    def score(self) -> float:
        """Score: 3 points per win, 1 per draw, 0 per loss."""
        return self.wins * 3 + self.draws

    @property
    def win_rate(self) -> float:
        """Fraction of rounds won."""
        if self.rounds_played == 0:
            return 0.0
        return self.wins / self.rounds_played

    def record(self, result: str, cycles: int = 0) -> None:
        """Record a single round result."""
        self.rounds_played += 1
        self.total_cycles += cycles
        if result == "win":
            self.wins += 1
        elif result == "loss":
            self.losses += 1
        else:
            self.draws += 1


@dataclass
class TournamentResult:
    """Results of a complete tournament."""

    standings: List[BattleStats] = field(default_factory=list)
    total_battles: int = 0
    total_rounds: int = 0

    def winner(self) -> Optional[BattleStats]:
        """Return the warrior with the highest score."""
        if not self.standings:
            return None
        return max(self.standings, key=lambda s: s.score)


class BattleScheduler:
    """
    Runs multi-round battles and tournaments between warriors.

    Args:
        core_size: Size of the MARS core memory.
        max_cycles: Max cycles per round.
        rounds: Number of rounds per battle pair.
        seed: Random seed for reproducibility.
    """

    def __init__(
        self,
        core_size: int = 8000,
        max_cycles: int = 80000,
        max_processes: int = 8000,
        min_separation: int = 100,
        rounds: int = 10,
        seed: Optional[int] = None,
    ):
        self.core_size = core_size
        self.max_cycles = max_cycles
        self.max_processes = max_processes
        self.min_separation = min_separation
        self.rounds = rounds
        self.rng = random.Random(seed)

    def run_battle(
        self,
        warriors: List[ParsedWarrior],
        rounds: Optional[int] = None,
    ) -> Dict[str, BattleStats]:
        """
        Run a multi-round battle between the given warriors.

        Returns a dict mapping warrior name → BattleStats.
        """
        rounds = rounds or self.rounds
        stats: Dict[str, BattleStats] = {
            w.name: BattleStats(name=w.name) for w in warriors
        }

        for round_num in range(rounds):
            mars = MARS(
                core_size=self.core_size,
                max_cycles=self.max_cycles,
                max_processes=self.max_processes,
                min_separation=self.min_separation,
                seed=self.rng.randint(0, 2**31 - 1),
            )
            mars.reset()

            shuffled = list(warriors)
            self.rng.shuffle(shuffled)
            for w in shuffled:
                mars.load_warrior(w)

            result = mars.run()

            for w in warriors:
                result_str = result.warrior_results.get(w.name, "draw")
                stats[w.name].record(result_str, result.cycles)

        return stats

    def run_tournament(
        self,
        warriors: List[ParsedWarrior],
        rounds_per_pair: Optional[int] = None,
    ) -> TournamentResult:
        """
        Run a round-robin tournament between all warriors.

        Each warrior fights every other warrior in 1v1 battles.
        Returns a TournamentResult with standings.
        """
        rounds_per_pair = rounds_per_pair or self.rounds
        all_stats: Dict[str, BattleStats] = {
            w.name: BattleStats(name=w.name) for w in warriors
        }

        total_battles = 0
        total_rounds = 0

        for i in range(len(warriors)):
            for j in range(i + 1, len(warriors)):
                pair = [warriors[i], warriors[j]]
                battle_stats = self.run_battle(pair, rounds=rounds_per_pair)
                for name, stat in battle_stats.items():
                    all_stats[name].wins += stat.wins
                    all_stats[name].losses += stat.losses
                    all_stats[name].draws += stat.draws
                    all_stats[name].rounds_played += stat.rounds_played
                    all_stats[name].total_cycles += stat.total_cycles
                total_battles += 1
                total_rounds += rounds_per_pair

        standings = sorted(all_stats.values(), key=lambda s: (-s.score, -s.wins, s.name))
        return TournamentResult(
            standings=standings,
            total_battles=total_battles,
            total_rounds=total_rounds,
        )