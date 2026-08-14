"""
Command-line interface for the Core War simulator.

Usage:
    python3 -m core_war.cli battle warrior1.red warrior2.red
    python3 -m core_war.cli tournament warrior1.red warrior2.red warrior3.red
    python3 -m core_war.cli trace warrior1.red
    python3 -m core_war.cli dump warrior1.red
    python3 -m core_war.cli core-dump warrior1.red warrior2.red
    python3 -m core_war.cli step warrior1.red warrior2.red
    python3 -m core_war.cli validate warrior1.red
"""

import argparse
import sys
from typing import List, Optional

from core_war.loader import load_warrior, load_warriors_from_dir
from core_war.mars import MARS
from core_war.parser import RedcodeParser, ParseError, ParsedWarrior
from core_war.scheduler import BattleScheduler
from core_war.disassembler import disassemble, disassemble_core, disassemble_around
from core_war.visualizer import core_heatmap, core_summary, format_core_summary, battle_log


def cmd_battle(args: argparse.Namespace) -> int:
    """Run a battle between two or more warriors."""
    warriors = [load_warrior(p) for p in args.warriors]

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
    warriors = [load_warrior(p) for p in args.warriors]

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
    warrior = load_warrior(args.warrior)

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
    warrior = load_warrior(args.warrior)
    print(f"\nWarrior: {warrior.name}")
    print(f"  Instructions: {len(warrior.instructions)}")
    print(f"  Start offset: {warrior.start_offset}")
    print(f"\nParsed instructions:")
    for i, instr in enumerate(warrior.instructions):
        marker = " <-- START" if i == warrior.start_offset else ""
        print(f"  {i:4d}: {disassemble(instr)}{marker}")
    return 0


def cmd_core_dump(args: argparse.Namespace) -> int:
    """Run a battle and show the final core memory state."""
    warriors = [load_warrior(p) for p in args.warriors]

    mars = MARS(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        seed=args.seed,
    )
    mars.reset()
    for w in warriors:
        mars.load_warrior(w)

    result = mars.run()

    print(f"\nBattle completed: {result.reason}")
    print(f"Cycles: {result.cycles}")
    print()
    print(battle_log(mars.core, mars.warriors))
    print()

    # Show core summary
    summary = core_summary(mars.core)
    print(format_core_summary(summary, len(mars.core)))
    print()

    # Show heatmap if requested
    if args.heatmap:
        print("Core memory heatmap (opcodes):")
        max_count = max(mars.access_counts.values()) if mars.access_counts else 1
        print(core_heatmap(mars.core, mars.access_counts, width=args.heatmap_width, max_count=max_count))
        print()

    # Show memory around each warrior's load address
    print("Memory around warrior load addresses:")
    for w in mars.warriors:
        print(f"\n  {w.name} (loaded at {w.load_address}):")
        print(disassemble_around(mars.core, w.load_address, radius=5))

    return 0


def cmd_step(args: argparse.Namespace) -> int:
    """Step through a battle interactively (or for N steps)."""
    warriors = [load_warrior(p) for p in args.warriors]

    mars = MARS(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        seed=args.seed,
    )
    mars.reset()
    for w in warriors:
        mars.load_warrior(w)

    print(f"\nStepping through battle: {' vs '.join(w.name for w in warriors)}")
    print(f"Core size: {mars.core_size}, Max cycles: {mars.max_cycles}")

    steps = args.steps or 20
    for i in range(steps):
        running = mars.step()
        if not running:
            break
        # Show current state
        alive_names = [w.name for w in mars.warriors if w.alive]
        print(f"\n  Step {i+1}: cycle {mars.cycle}, alive: {', '.join(alive_names)}")
        for w in mars.warriors:
            if w.alive:
                pc = w.processes[0] if w.processes else "?"
                print(f"    {w.name}: {len(w.processes)} proc(s), next PC={pc}")
        if not running:
            break

    result = mars._make_result()
    print(f"\n  Final: {result.reason}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a warrior file without running it."""
    try:
        warrior = load_warrior(args.warrior)
        print(f"✓ {warrior.name}: valid")
        print(f"  Instructions: {len(warrior.instructions)}")
        print(f"  Start offset: {warrior.start_offset}")
        print(f"  Max length: {200} (limit)")
        if len(warrior.instructions) > 200:
            print(f"  ⚠ WARNING: exceeds standard max length of 200")
        return 0
    except ParseError as e:
        print(f"✗ {args.warrior}: INVALID — {e}")
        return 1
    except FileNotFoundError as e:
        print(f"✗ {e}")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
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

    # Core dump command
    p_coredump = subparsers.add_parser("core-dump", help="Run battle and show final core state")
    p_coredump.add_argument("warriors", nargs="+", help="Warrior .red files")
    p_coredump.add_argument("--heatmap", action="store_true", help="Show core heatmap")
    p_coredump.add_argument("--heatmap-width", type=int, default=80, help="Heatmap row width")
    p_coredump.set_defaults(func=cmd_core_dump)

    # Step command
    p_step = subparsers.add_parser("step", help="Step through a battle")
    p_step.add_argument("warriors", nargs="+", help="Warrior .red files")
    p_step.add_argument("--steps", type=int, default=20, help="Number of steps")
    p_step.set_defaults(func=cmd_step)

    # Validate command
    p_validate = subparsers.add_parser("validate", help="Validate a warrior file")
    p_validate.add_argument("warrior", help="Warrior .red file")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())