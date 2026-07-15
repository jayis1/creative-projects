"""
Command-line interface for the Rete engine.

Usage
-----
    # Run a JSON/YAML rule file and print results
    python -m rete.cli run rules.json
    python -m rete.cli run rules.yaml --trace

    # Run and save final facts
    python -m rete.cli run rules.json --save-facts out.json

    # Show the agenda without firing
    python -mrete.cli agenda rules.json

    # Validate a rule file
    python -m rete.cli validate rules.json

    # Show network structure
    python -m rete.cli network rules.json --dot

    # Interactive REPL
    python -m rete.cli repl rules.json

    # Show engine stats
    python -m rete.cli stats rules.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import (
    Engine,
    Fact,
    Rule,
    Condition,
    Var,
    Const,
    ConflictResolution,
)
from .exceptions import ReteError
from .serialization import load_file, load_engine, save_facts


_STRATEGY_MAP = {
    "fifo": ConflictResolution.FIFO,
    "lifo": ConflictResolution.LIFO,
    "priority": ConflictResolution.PRIORITY,
    "recent": ConflictResolution.RECENT,
    "refc": ConflictResolution.REFC,
    "priority-refc": ConflictResolution.PRIORITY_REFC,
}


def _strategy_from_str(s: str) -> ConflictResolution:
    try:
        return _STRATEGY_MAP[s]
    except KeyError:
        raise ValueError(
            f"unknown strategy: {s!r}. "
            f"Choices: {list(_STRATEGY_MAP.keys())}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rete",
        description="Rete forward-chaining rule inference engine",
        epilog="Run `rete <command> -h` for command-specific help.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Load a rule file and fire rules")
    p_run.add_argument("file", help="Rule file (JSON or YAML)")
    p_run.add_argument(
        "--strategy", default="refc",
        choices=list(_STRATEGY_MAP.keys()),
        help="Conflict resolution strategy (default: refc)",
    )
    p_run.add_argument("--max-steps", type=int, default=100000)
    p_run.add_argument("--save-facts", help="Save final facts to JSON file")
    p_run.add_argument(
        "--trace", action="store_true",
        help="Print a trace of each firing",
    )
    p_run.add_argument(
        "--log-level", default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    # agenda
    p_ag = sub.add_parser(
        "agenda", help="Show the current agenda without firing"
    )
    p_ag.add_argument("file", help="Rule file (JSON or YAML)")

    # validate
    p_val = sub.add_parser("validate", help="Validate a rule file")
    p_val.add_argument("file", help="Rule file (JSON or YAML)")

    # network
    p_net = sub.add_parser(
        "network", help="Show or export the Rete network structure"
    )
    p_net.add_argument("file", help="Rule file (JSON or YAML)")
    p_net.add_argument(
        "--dot", action="store_true",
        help="Output Graphviz DOT format",
    )
    p_net.add_argument(
        "--summary", action="store_true",
        help="Output a JSON summary of the network",
    )

    # repl
    p_repl = sub.add_parser("repl", help="Interactive REPL")
    p_repl.add_argument("file", help="Rule file (JSON or YAML)")
    p_repl.add_argument(
        "--strategy", default="refc",
        choices=list(_STRATEGY_MAP.keys()),
    )

    # stats
    p_stats = sub.add_parser(
        "stats", help="Show engine statistics after running"
    )
    p_stats.add_argument("file", help="Rule file (JSON or YAML)")
    p_stats.add_argument(
        "--strategy", default="refc",
        choices=list(_STRATEGY_MAP.keys()),
    )

    # version
    sub.add_parser("version", help="Print version")

    return parser


# --------------------------------------------------------------------------- #
#  Command handlers
# --------------------------------------------------------------------------- #


def cmd_run(args) -> int:
    try:
        eng = load_engine(
            args.file,
            strategy=_strategy_from_str(args.strategy),
            max_steps=args.max_steps,
            log_level=args.log_level,
        )
    except (ReteError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.trace:
        eng.enable_tracing()

    try:
        n = eng.run()
    except ReteError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Fired {n} rule(s).")
    print(f"Working memory: {eng.fact_count()} fact(s).")

    if args.trace:
        for entry in eng.get_trace():
            print(f"  Step {entry['step']}: {entry['rule']} "
                  f"bindings={entry['bindings']}")

    if args.save_facts:
        save_facts(eng, args.save_facts)
        print(f"Facts saved to {args.save_facts}")

    return 0


def cmd_agenda(args) -> int:
    try:
        eng = load_engine(args.file)
    except (ReteError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    ag = eng.agenda()
    if not ag:
        print("Agenda is empty.")
    else:
        print(f"Agenda ({len(ag)} item(s)):")
        for rname, bindings in ag:
            print(f"  {rname}: {bindings}")
    return 0


def cmd_validate(args) -> int:
    try:
        rules, facts = load_file(args.file)
        print(f"OK: {len(rules)} rule(s), {len(facts)} fact(s).")
        for r in rules:
            print(f"  Rule '{r.name}': {len(r.conditions)} condition(s), "
                  f"{len(r.actions)} action(s), priority={r.priority}")
        if facts:
            print(f"  Facts:")
            for f in facts:
                print(f"    {f}")
        return 0
    except (ReteError, FileNotFoundError) as e:
        print(f"Invalid: {e}", file=sys.stderr)
        return 1


def cmd_network(args) -> int:
    try:
        eng = load_engine(args.file)
    except (ReteError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.dot:
        print(eng.to_dot())
    elif args.summary:
        import json
        summary = eng.network_summary()
        print(json.dumps(summary, indent=2, default=str))
    else:
        # Default: human-readable summary
        summary = eng.network_summary()
        print(f"Rete Network Summary")
        print(f"  Rules:          {summary['rules']}")
        print(f"  Alpha nodes:    {summary['alpha_nodes']}")
        print(f"  Prod nodes:     {summary['production_nodes']}")
        print(f"  Facts:          {summary['facts']}")
        print(f"  Strategy:       {summary['strategy']}")
        print(f"  Max steps:       {summary['max_steps']}")
        print()
        print("Rule details:")
        for rname, info in summary["rule_details"].items():
            print(f"  {rname}:")
            print(f"    conditions:      {info['conditions']}")
            print(f"    actions:         {info['actions']}")
            print(f"    priority:        {info['priority']}")
            print(f"    join_nodes:      {info['join_nodes']}")
            print(f"    instantiations:  {info['instantiations']}")
    return 0


def cmd_stats(args) -> int:
    try:
        eng = load_engine(
            args.file,
            strategy=_strategy_from_str(args.strategy),
        )
    except (ReteError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    eng.run()
    stats = eng.get_stats()
    if not stats:
        print("No rules fired.")
        return 0

    print(f"{'Rule':<20} {'Fires':>8} {'Activations':>12}")
    print("-" * 42)
    for rname, s in stats.items():
        print(f"{rname:<20} {s['fires']:>8} {s['activations']:>12}")
    print(f"\nTotal firings: {sum(s['fires'] for s in stats.values())}")
    print(f"Working memory: {eng.fact_count()} fact(s)")
    return 0


def cmd_repl(args) -> int:
    try:
        eng = load_engine(
            args.file,
            strategy=_strategy_from_str(args.strategy),
        )
    except (ReteError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print("Rete REPL. Commands:")
    print("  assert <type> key=val key=val ...")
    print("  retract <type> key=val ...")
    print("  run [N]")
    print("  agenda")
    print("  facts [type]")
    print("  stats")
    print("  network")
    print("  rules")
    print("  query <type> key=val ...")
    print("  help")
    print("  quit")

    while True:
        try:
            line = input("rete> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "quit":
            break
        elif cmd == "help":
            print("Commands: assert, retract, run, agenda, facts, stats, "
                  "network, rules, query, quit")
        elif cmd == "assert":
            if len(parts) < 2:
                print("Usage: assert <type> key=val ...")
                continue
            ftype = parts[1]
            fields = {}
            for p in parts[2:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    # Try to convert to int/float
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                    fields[k] = v
            eng.assert_fact(Fact(ftype, **fields))
            print(f"Asserted {ftype}({fields})")
        elif cmd == "retract":
            if len(parts) < 2:
                print("Usage: retract <type> key=val ...")
                continue
            ftype = parts[1]
            fields = {}
            for p in parts[2:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    fields[k] = v
            matches = eng.query(ftype, **fields)
            for f in matches:
                eng.retract_fact(f)
            print(f"Retracted {len(matches)} fact(s)")
        elif cmd == "run":
            n = int(parts[1]) if len(parts) > 1 else None
            fired = eng.run(max_steps=n) if n else eng.run()
            print(f"Fired {fired} rule(s).")
        elif cmd == "agenda":
            ag = eng.agenda()
            for rname, bindings in ag:
                print(f"  {rname}: {bindings}")
            if not ag:
                print("  (empty)")
        elif cmd == "facts":
            if len(parts) > 1:
                for f in eng.facts_of_type(parts[1]):
                    print(f"  {f}")
            else:
                for f in eng.facts:
                    print(f"  {f}")
        elif cmd == "stats":
            stats = eng.get_stats()
            for rname, s in stats.items():
                print(f"  {rname}: fires={s['fires']}, "
                      f"activations={s['activations']}")
            if not stats:
                print("  (no rules)")
        elif cmd == "network":
            summary = eng.network_summary()
            print(f"  Rules: {summary['rules']}, "
                  f"Alpha: {summary['alpha_nodes']}, "
                  f"Facts: {summary['facts']}")
        elif cmd == "rules":
            for rname in eng.rules:
                print(f"  {rname}")
        elif cmd == "query":
            if len(parts) < 2:
                print("Usage: query <type> key=val ...")
                continue
            ftype = parts[1]
            fields = {}
            for p in parts[2:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    fields[k] = v
            results = eng.query(ftype, **fields)
            for f in results:
                print(f"  {f}")
            if not results:
                print("  (none)")
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")

    return 0


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        from . import __version__
        print(f"rete-network {__version__}")
        return 0
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "agenda":
        return cmd_agenda(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "network":
        return cmd_network(args)
    elif args.command == "repl":
        return cmd_repl(args)
    elif args.command == "stats":
        return cmd_stats(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())