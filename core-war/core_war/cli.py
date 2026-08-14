"""
Command-line interface for the Core War simulator.

Usage:
    python3 -m core_war.cli battle warrior1.red warrior2.red
    python3 -m core_war.cli tournament warrior1.red warrior2.red warrior3.red
    python3 -m core_war.cli trace warrior1.red
    python3 -m core_war.cli dump warrior1.red
"""

import argparse
import sys
from typing import List

from core_war.mars import MARS
from core_war.parser import RedcodeParser, ParseError
from core_war.scheduler import BattleScheduler


def load_warrior_file(path: str) -> "ParsedWarrior":
    """Load a warrior from a .red file."""
    import os
    from core_war.parser import ParsedWarrior

    with open(path, "r") as f:
        source = f.read()
    name = os.path.splitext(os.path.basename(path))[0]
    parser = RedcodeParser()
    return parser.parse(source, name=name)


def cmd_battle(args: argparse.Namespace) -> int:
    """Run a battle between two or more warriors."""
    warriors = [load_warrior_file(p) for p in args.warriors]

    scheduler = BattleScheduler(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        rounds=args.rounds,
        seed=args.seed,
    )
    stats = scheduler.run_battle(warriors)

    print(f"\n{'='*60}")
    print(f"  BATTLE RESULT ({args.rounds} rounds)")
    print(f"{'='*60}")
    print(f"{'Warrior':<20} {'W':>4} {'L':>4} {'D':>4} {'Rate':>8} {'Score':>8}")
    print(f"{'-'*60}")
    for stat in sorted(stats.values(), key=lambda s: -s.score):
        print(f"{stat.name:<20} {stat.wins:>4} {stat.losses:>4} {stat.draws:>4} "
              f"{stat.win_rate:>7.1%} {stat.score:>8.0f}")
    print(f"{'='*60}")
    winner = max(stats.values(), key=lambda s: s.score)
    if winner.score > 0:
        print(f"  Overall winner: {winner.name}")
    else:
        print("  No winner (all draws)")
    return 0


def cmd_tournament(args: argparse.Namespace) -> int:
    """Run a round-robin tournament."""
    warriors = [load_warrior_file(p) for p in args.warriors]

    scheduler = BattleScheduler(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        rounds=args.rounds,
        seed=args.seed,
    )
    result = scheduler.run_tournament(warriors)

    print(f"\n{'='*60}")
    print(f"  TOURNAMENT RESULT ({result.total_battles} battles, {result.total_rounds} rounds)")
    print(f"{'='*60}")
    print(f"{'Rank':<6} {'Warrior':<20} {'W':>4} {'L':>4} {'D':>4} {'Score':>8}")
    print(f"{'-'*60}")
    for rank, stat in enumerate(result.standings, 1):
        print(f"{rank:<6} {stat.name:<20} {stat.wins:>4} {stat.losses:>4} {stat.draws:>4} "
              f"{stat.score:>8.0f}")
    print(f"{'='*60}")
    w = result.winner()
    if w:
        print(f"  Tournament champion: {w.name}")
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    """Run a single warrior with execution trace."""
    warrior = load_warrior_file(args.warrior)

    mars = MARS(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        seed=args.seed,
    )
    mars.reset()
    mars.trace_enabled = True
    mars.load_warrior(warrior)

    result = mars.run()

    print(f"\nExecution trace for {warrior.name}:")
    print(f"  Cycles: {result.cycles}")
    print(f"  Status: {'alive' if warrior.name in result.survivors else 'dead'}")
    print(f"  Trace entries: {len(mars.trace)}")
    print()

    max_show = args.max_trace or 50
    for entry in mars.trace[:max_show]:
        print(f"  Cycle {entry['cycle']:>6} | PC {entry['pc']:>6} | {entry['instruction']}")

    if len(mars.trace) > max_show:
        print(f"  ... ({len(mars.trace) - max_show} more entries)")
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    """Dump the parsed instructions of a warrior."""
    warrior = load_warrior_file(args.warrior)
    print(f"\nWarrior: {warrior.name}")
    print(f"  Instructions: {len(warrior.instructions)}")
    print(f"  Start offset: {warrior.start_offset}")
    print(f"\nParsed instructions:")
    for i, instr in enumerate(warrior.instructions):
        marker = " <-- START" if i == warrior.start_offset else ""
        print(f"  {i:4d}: {instr}{marker}")
    return 0


def main(argv: List[str] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="core-war",
        description="Core War — MARS simulator for Redcode warriors",
    )
    parser.add_argument("--core-size", type=int, default=8000, help="Core memory size")
    parser.add_argument("--max-cycles", type=int, default=80000, help="Max cycles per round")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--rounds", type=int, default=10, help="Number of rounds")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Battle command
    p_battle = subparsers.add_parser("battle", help="Run a multi-round battle")
    p_battle.add_argument("warriors", nargs="+", help="Warrior .red files")
    p_battle.set_defaults(func=cmd_battle)

    # Tournament command
    p_tournament = subparsers.add_parser("tournament", help="Run a round-robin tournament")
    p_tournament.add_argument("warriors", nargs="+", help="Warrior .red files")
    p_tournament.set_defaults(func=cmd_tournament)

    # Trace command
    p_trace = subparsers.add_parser("trace", help="Trace a single warrior's execution")
    p_trace.add_argument("warrior", help="Warrior .red file")
    p_trace.add_argument("--max-trace", type=int, default=50, help="Max trace entries to show")
    p_trace.set_defaults(func=cmd_trace)

    # Dump command
    p_dump = subparsers.add_parser("dump", help="Dump parsed warrior instructions")
    p_dump.add_argument("warrior", help="Warrior .red file")
    p_dump.set_defaults(func=cmd_dump)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())