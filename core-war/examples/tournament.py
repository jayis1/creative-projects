"""
Example: Run a tournament between classic warriors.

This script loads the built-in warriors and runs a round-robin tournament.
"""

import sys
import os

# Add the parent directory to path so we can import core_war
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_war.parser import RedcodeParser
from core_war.scheduler import BattleScheduler

WARRIORS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warriors")


def load_warrior(name: str):
    """Load a warrior from the warriors directory."""
    path = os.path.join(WARRIORS_DIR, f"{name}.red")
    with open(path) as f:
        source = f.read()
    parser = RedcodeParser()
    return parser.parse(source, name=name.capitalize())


def main():
    # Load all warriors
    warrior_names = ["imp", "dwarf", "stone", "paper", "scanner"]
    warriors = [load_warrior(n) for n in warrior_names]

    print(f"Loaded {len(warriors)} warriors: {[w.name for w in warriors]}")
    print()

    # Run tournament
    scheduler = BattleScheduler(
        core_size=8000,
        max_cycles=20000,
        rounds=5,
        seed=42,
    )
    result = scheduler.run_tournament(warriors)

    # Print standings
    print(f"Tournament complete! {result.total_battles} battles, {result.total_rounds} rounds")
    print()
    print(f"{'Rank':<6} {'Warrior':<15} {'W':>4} {'L':>4} {'D':>4} {'Score':>8} {'Win%':>8}")
    print("-" * 50)
    for rank, stat in enumerate(result.standings, 1):
        print(f"{rank:<6} {stat.name:<15} {stat.wins:>4} {stat.losses:>4} {stat.draws:>4} "
              f"{stat.score:>8.0f} {stat.win_rate:>7.1%}")

    champ = result.winner()
    if champ:
        print(f"\nTournament champion: {champ.name} (score={champ.score:.0f})")


if __name__ == "__main__":
    main()