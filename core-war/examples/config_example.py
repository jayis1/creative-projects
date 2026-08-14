"""
Example: Use configuration files to run battles.

Demonstrates loading a YAML config file and running a tournament.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_war import BattleConfig, load_warrior, BattleScheduler

WARRIORS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warriors")


# Example config as YAML string
EXAMPLE_CONFIG = """
# Core War Battle Configuration
core_size: 8000
max_cycles: 20000
max_processes: 8000
min_separation: 100
rounds: 5
seed: 42
log_level: INFO
output_format: table

warriors:
  - warriors/imp.red
  - warriors/dwarf.red
  - warriors/stone.red
  - warriors/paper.red
"""


def main():
    import tempfile
    from pathlib import Path

    # Write example config to temp file
    config_path = Path(tempfile.mktemp(suffix=".yaml"))
    config_path.write_text(EXAMPLE_CONFIG)

    print(f"Config file: {config_path}")
    print(f"Config contents:\n{EXAMPLE_CONFIG}")

    # Load config
    config = BattleConfig.from_file(str(config_path))
    print(f"\nLoaded config:")
    print(f"  core_size:    {config.core_size}")
    print(f"  max_cycles:   {config.max_cycles}")
    print(f"  rounds:       {config.rounds}")
    print(f"  seed:         {config.seed}")
    print(f"  warriors:     {config.warriors}")

    # Load warriors from config
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    warriors = [load_warrior(os.path.join(base_dir, p)) for p in config.warriors]
    print(f"\nLoaded {len(warriors)} warriors: {[w.name for w in warriors]}")

    # Run tournament using config parameters
    scheduler = BattleScheduler(
        core_size=config.core_size,
        max_cycles=config.max_cycles,
        rounds=config.rounds,
        seed=config.seed,
    )

    result = scheduler.run_tournament(warriors)

    print(f"\nTournament Results ({result.total_battles} battles):")
    print(f"  {'Rank':<6} {'Warrior':<15} {'W':>4} {'L':>4} {'D':>4} {'Score':>8}")
    print("  " + "-" * 45)
    for rank, stat in enumerate(result.standings, 1):
        print(f"  {rank:<6} {stat.name:<15} {stat.wins:>4} {stat.losses:>4} "
              f"{stat.draws:>4} {stat.score:>8.0f}")

    champ = result.winner()
    if champ:
        print(f"\n  Champion: {champ.name} (score={champ.score:.0f})")

    # Cleanup
    config_path.unlink()


if __name__ == "__main__":
    main()