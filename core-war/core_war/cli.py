"""
Command-line interface for the Core War simulator.

Subcommands:
    battle      Run a multi-round battle between warriors
    tournament  Run a round-robin tournament
    trace       Trace a single warrior's execution
    dump        Dump parsed warrior instructions
    core-dump   Run battle and show final core state
    step        Step through a battle one cycle at a time
    validate    Validate a warrior file
    analyze     Analyze warrior strategy and vulnerabilities
    replay      Record a battle and replay it
    evolve      Evolve warriors using a genetic algorithm
    config      Create a template config file
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List, Optional

from core_war.loader import load_warrior, load_warriors_from_dir
from core_war.mars import MARS
from core_war.parser import RedcodeParser, ParseError, ParsedWarrior
from core_war.scheduler import BattleScheduler
from core_war.disassembler import disassemble, disassemble_core, disassemble_around
from core_war.visualizer import core_heatmap, core_summary, format_core_summary, battle_log
from core_war.config import BattleConfig
from core_war.logging_config import setup_logging, get_logger
from core_war.strategy_analyzer import StrategyAnalyzer, StrategyType
from core_war.replay import BattleRecorder, BattleReplay
from core_war.mutator import GeneticEvolver

logger = get_logger("cli")


# ============================================================================
# Helper functions
# ============================================================================

def _format_table(headers: list[str], rows: list[list[str]], title: str = "") -> str:
    """Format data as a text table."""
    lines = []
    if title:
        lines.append(f"\n{'=' * 60}")
        lines.append(f"  {title}")
        lines.append(f"{'=' * 60}")

    col_widths = [max(len(h), *(len(str(r[i])) for r in rows if i < len(r)))
                  for i, h in enumerate(headers)]
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    lines.append(header_line)
    lines.append("-" * len(header_line))
    for row in rows:
        lines.append("  ".join(str(c).ljust(w) for c, w in zip(row, col_widths)))
    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def _load_warriors_safe(paths: List[str]) -> List[ParsedWarrior]:
    """Load warriors from file paths, raising on any error."""
    warriors = []
    for p in paths:
        try:
            warriors.append(load_warrior(p))
        except ParseError as e:
            print(f"Error loading {p}: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    return warriors


# ============================================================================
# Command implementations
# ============================================================================

def cmd_battle(args: argparse.Namespace) -> int:
    """Run a battle between two or more warriors."""
    warriors = _load_warriors_safe(args.warriors)

    scheduler = BattleScheduler(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        rounds=args.rounds,
        seed=args.seed,
    )
    stats = scheduler.run_battle(warriors)

    if args.output_format == "json":
        result = {name: {"wins": s.wins, "losses": s.losses, "draws": s.draws,
                         "score": s.score, "win_rate": s.win_rate}
                  for name, s in stats.items()}
        print(json.dumps(result, indent=2))
        return 0

    rows = []
    for stat in sorted(stats.values(), key=lambda s: -s.score):
        rows.append([stat.name, str(stat.wins), str(stat.losses), str(stat.draws),
                     f"{stat.win_rate:.1%}", f"{stat.score:.0f}"])

    print(_format_table(
        ["Warrior", "W", "L", "D", "Rate", "Score"],
        rows,
        f"BATTLE RESULT ({args.rounds} rounds)"
    ))
    winner = max(stats.values(), key=lambda s: s.score)
    if winner.score > 0:
        print(f"  Overall winner: {winner.name}")
    else:
        print("  No winner (all draws)")
    return 0


def cmd_tournament(args: argparse.Namespace) -> int:
    """Run a round-robin tournament."""
    warriors = _load_warriors_safe(args.warriors)

    scheduler = BattleScheduler(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        rounds=args.rounds,
        seed=args.seed,
    )
    result = scheduler.run_tournament(warriors)

    rows = []
    for rank, stat in enumerate(result.standings, 1):
        rows.append([str(rank), stat.name, str(stat.wins), str(stat.losses),
                     str(stat.draws), f"{stat.score:.0f}"])

    print(_format_table(
        ["Rank", "Warrior", "W", "L", "D", "Score"],
        rows,
        f"TOURNAMENT RESULT ({result.total_battles} battles, {result.total_rounds} rounds)"
    ))
    w = result.winner()
    if w:
        print(f"  Tournament champion: {w.name}")
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    """Run a single warrior with execution trace."""
    warrior = _load_warriors_safe([args.warrior])[0]

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
    warrior = _load_warriors_safe([args.warrior])[0]
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
    warriors = _load_warriors_safe(args.warriors)

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

    summary = core_summary(mars.core)
    print(format_core_summary(summary, len(mars.core)))
    print()

    if args.heatmap:
        print("Core memory heatmap (opcodes):")
        max_count = max(mars.access_counts.values()) if mars.access_counts else 1
        print(core_heatmap(mars.core, mars.access_counts, width=args.heatmap_width, max_count=max_count))
        print()

    print("Memory around warrior load addresses:")
    for w in mars.warriors:
        print(f"\n  {w.name} (loaded at {w.load_address}):")
        print(disassemble_around(mars.core, w.load_address, radius=5))

    return 0


def cmd_step(args: argparse.Namespace) -> int:
    """Step through a battle interactively (or for N steps)."""
    warriors = _load_warriors_safe(args.warriors)

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
        print(f"  Max length: 200 (standard limit)")
        if len(warrior.instructions) > 200:
            print(f"  ⚠ WARNING: exceeds standard max length of 200")
        return 0
    except ParseError as e:
        print(f"✗ {args.warrior}: INVALID — {e}")
        return 1
    except FileNotFoundError as e:
        print(f"✗ {e}")
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze warrior strategy and find vulnerabilities."""
    warrior = _load_warriors_safe([args.warrior])[0]
    analyzer = StrategyAnalyzer()
    result = analyzer.analyze(warrior)

    print(f"\n{'=' * 60}")
    print(f"  WARRIOR ANALYSIS: {warrior.name}")
    print(f"{'=' * 60}")
    print(f"\n  Strategy:          {result.strategy.value}")
    if result.secondary_strategy:
        print(f"  Secondary:         {result.secondary_strategy.value}")
    print(f"  Instructions:      {result.instruction_count}")
    print(f"  Start offset:      {result.start_offset}")
    print(f"  Has SPL:           {result.has_spl}")
    print(f"  Has JMP:           {result.has_jmp}")
    print(f"  Scanning:          {result.has_scanning}")
    print(f"  Bombing:           {result.has_bombing}")
    print(f"  Replication:       {result.has_replication}")
    print(f"  Self-modifying:    {result.self_modifying}")
    print(f"  Uses indirect:     {result.uses_indirect}")
    print(f"  Uses predec:       {result.uses_predec}")
    print(f"  Uses postinc:      {result.uses_postinc}")
    print(f"  Process estimate: {result.process_estimate}")
    print(f"\n  Aggressiveness:    {result.estimated_aggressiveness}/10")
    print(f"  Resilience:        {result.estimated_resilience}/10")
    print(f"\n  Opcode frequency:")
    for name, count in result.opcode_freq.most_common():
        pct = result.opcode_freq.percentage(name)
        bar = "█" * int(pct / 5)
        print(f"    {name:<6} {count:>3} ({pct:>5.1f}%) {bar}")

    if result.vulnerabilities:
        print(f"\n  Vulnerabilities ({len(result.vulnerabilities)}):")
        for v in result.vulnerabilities:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡",
                    "low": "🔵", "info": "ℹ️"}.get(v.severity, "❓")
            print(f"    {icon} [{v.severity.upper()}] {v.description}")
            if v.recommendation:
                print(f"        → {v.recommendation}")
    else:
        print(f"\n  No vulnerabilities detected.")

    print(f"\n  Summary: {result.summary}")
    print(f"{'=' * 60}")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Record a battle and optionally replay it from a file."""
    if args.replay_file and args.record:
        # Record mode
        warriors = _load_warriors_safe(args.warriors)
        mars = MARS(
            core_size=args.core_size,
            max_cycles=args.max_cycles,
            seed=args.seed,
        )
        recorder = BattleRecorder(max_snapshots=args.max_snapshots)
        recording = recorder.record(mars, warriors, metadata={"warriors": args.warriors})
        recording.save(args.replay_file)
        print(f"\nBattle recorded to {args.replay_file}")
        print(f"  Snapshots: {len(recording.snapshots)}")
        print(BattleReplay(recording).summary())
        return 0

    if args.replay_file and not args.record:
        # Replay mode
        from core_war.replay import BattleRecording
        recording = BattleRecording.from_file(args.replay_file)
        replay = BattleReplay(recording)
        print(replay.summary())
        print()

        limit = args.max_snapshots or 50
        count = 0
        for snapshot in replay.play():
            if count >= limit:
                print(f"  ... ({replay.total_cycles() - limit} more cycles)")
                break
            alive = ", ".join(snapshot.alive_warriors) or "(none)"
            print(f"  Cycle {snapshot.cycle:>6}: alive=[{alive}]")
            for name, state in snapshot.warrior_states.items():
                if state["alive"]:
                    pc = state.get("next_pc", "?")
                    print(f"    {name}: {state['process_count']} proc(s), PC={pc}, exec={state['instructions_executed']}")
            count += 1
        return 0

    # Default: record then replay inline
    warriors = _load_warriors_safe(args.warriors)
    mars = MARS(
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        seed=args.seed,
    )
    recorder = BattleRecorder(max_snapshots=args.max_snapshots)
    recording = recorder.record(mars, warriors)
    replay = BattleReplay(recording)
    print(replay.summary())
    print()
    for snapshot in replay.play():
        alive = ", ".join(snapshot.alive_warriors) or "(none)"
        print(f"  Cycle {snapshot.cycle:>6}: alive=[{alive}]")
    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    """Evolve warriors using a genetic algorithm."""
    # Load opponents
    opponents = []
    if args.opponents:
        opponents = _load_warriors_safe(args.opponents)
    elif args.warriors_dir:
        opponents = load_warriors_from_dir(args.warriors_dir)

    if not opponents:
        print("Warning: No opponents specified. Fitness will be based on instruction count.", file=sys.stderr)

    # Load seed warriors
    seeds = []
    if args.seeds:
        seeds = _load_warriors_safe(args.seeds)

    evolver = GeneticEvolver(
        population_size=args.population,
        generations=args.generations,
        opponents=opponents,
        core_size=args.core_size,
        max_cycles=args.max_cycles,
        rounds_per_battle=args.rounds,
        mutation_rate=args.mutation_rate,
        seed=args.seed,
    )

    print(f"\nEvolving warriors: {args.generations} generations, "
          f"population={args.population}, opponents={len(opponents)}")
    print(f"Mutation rate: {args.mutation_rate}")
    print()

    def on_gen(gen: int, stats) -> None:
        print(f"  Gen {gen:3d}: best={stats.best_fitness:.1f}, "
              f"avg={stats.avg_fitness:.1f}, diversity={stats.diversiveness:.0%}, "
              f"best={stats.best_individual}")

    best = evolver.evolve(seed_warriors=seeds, on_generation=on_gen)

    print(f"\n{'=' * 60}")
    print(f"  EVOLUTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Best warrior: {best.name}")
    print(f"  Fitness: {best.fitness:.1f}")
    print(f"  Generation: {best.generation}")
    print(f"  Battles: {best.battles_won}W / {best.battles_lost}L / {best.battles_drawn}D")
    print(f"  Win rate: {best.win_rate:.1%}")
    print(f"  Instructions: {len(best.genome)}")
    print()

    if args.output:
        evolver.save_best(args.output)
        print(f"  Saved to: {args.output}")
    else:
        print("  Warrior source:")
        print()
        print(best.to_source())

    # Show evolution history
    if evolver.history:
        print(f"\n  Evolution history:")
        for stat in evolver.history:
            print(f"    Gen {stat.generation:3d}: best={stat.best_fitness:.1f}, "
                  f"avg={stat.avg_fitness:.1f}, diversity={stat.diversity:.0%}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Create a template configuration file."""
    config = BattleConfig.create_template(args.output)
    print(f"Created template config at: {args.output}")
    print(f"\nEdit the file to customize, then run:")
    print(f"  python3 -m core_war.cli --config {args.output} battle")
    return 0


# ============================================================================
# Main CLI entry point
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="core-war",
        description="Core War — MARS simulator for Redcode warriors",
        epilog="Use 'core-war <command> --help' for command-specific help.",
    )
    parser.add_argument("--core-size", type=int, default=8000, help="Core memory size")
    parser.add_argument("--max-cycles", type=int, default=80000, help="Max cycles per round")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--rounds", type=int, default=10, help="Number of rounds")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to YAML/JSON config file (overrides CLI flags)")
    parser.add_argument("--log-level", type=str, default="WARNING",
                        help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--log-file", type=str, default=None,
                        help="Log file path")
    parser.add_argument("--output-format", type=str, default="table",
                        choices=["table", "json", "csv"],
                        help="Output format for results")
    parser.add_argument("--version", action="version", version="core-war 3.0.0")

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

    # Analyze command
    p_analyze = subparsers.add_parser("analyze", help="Analyze warrior strategy and vulnerabilities")
    p_analyze.add_argument("warrior", help="Warrior .red file")
    p_analyze.set_defaults(func=cmd_analyze)

    # Replay command
    p_replay = subparsers.add_parser("replay", help="Record and replay battles")
    p_replay.add_argument("warriors", nargs="*", help="Warrior .red files (for recording)")
    p_replay.add_argument("--replay-file", type=str, default=None,
                          help="File to save/load recording (JSON)")
    p_replay.add_argument("--record", action="store_true",
                          help="Record mode (save to replay-file)")
    p_replay.add_argument("--max-snapshots", type=int, default=10000,
                          help="Max snapshots to record")
    p_replay.set_defaults(func=cmd_replay)

    # Evolve command
    p_evolve = subparsers.add_parser("evolve", help="Evolve warriors using genetic algorithm")
    p_evolve.add_argument("--opponents", nargs="*", help="Opponent warrior files")
    p_evolve.add_argument("--warriors-dir", type=str, default=None,
                           help="Directory of warriors to use as opponents")
    p_evolve.add_argument("--seeds", nargs="*", help="Seed warrior files for initial population")
    p_evolve.add_argument("--population", type=int, default=20, help="Population size")
    p_evolve.add_argument("--generations", type=int, default=10, help="Number of generations")
    p_evolve.add_argument("--mutation-rate", type=float, default=0.15, help="Mutation rate (0-1)")
    p_evolve.add_argument("--output", type=str, default=None,
                           help="Output file for best warrior (.red)")
    p_evolve.set_defaults(func=cmd_evolve)

    # Config command
    p_config = subparsers.add_parser("config", help="Create a template config file")
    p_config.add_argument("output", help="Output path (.yaml or .json)")
    p_config.set_defaults(func=cmd_config)

    args = parser.parse_args(argv)

    # Load config file if specified
    if args.config:
        try:
            config = BattleConfig.from_file(args.config)
            # Override args with config values
            args.core_size = config.core_size
            args.max_cycles = config.max_cycles
            args.rounds = config.rounds
            args.seed = config.seed
            args.output_format = config.output_format
            args.log_level = config.log_level
            if config.warriors and hasattr(args, 'warriors') and not args.warriors:
                args.warriors = config.warriors
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1

    # Set up logging
    setup_logging(level=args.log_level, log_file=getattr(args, 'log_file', None))

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())