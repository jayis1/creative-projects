"""
Command-line interface for the Rete engine.

Usage
-----
    # Run a JSON rule file and print results
    python -m rete.cli run rules.json

    # Run and save final facts
    python -m rete.cli run rules.json --save-facts out.json

    # Show the agenda without firing
    python -m rete.cli agenda rules.json

    # Validate a rule file
    python -m rete.cli validate rules.json

    # REPL: interactively assert/retract facts and fire rules
    python -m rete.cli repl rules.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution
from .exceptions import ReteError
from .serialization import load_engine, save_facts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rete",
        description="Rete forward-chaining rule inference engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Load a JSON rule file and fire rules")
    p_run.add_argument("file", help="JSON rule/fact file")
    p_run.add_argument("--strategy", default="refc",
                       choices=["fifo", "lifo", "priority", "recent", "refc"])
    p_run.add_argument("--max-steps", type=int, default=100000)
    p_run.add_argument("--save-facts", help="Save final facts to JSON file")
    p_run.add_argument("--trace", action="store_true",
                       help="Print a trace of each firing")
    p_run.add_argument("--log-level", default="WARNING",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    # agenda
    p_ag = sub.add_parser("agenda", help="Show the current agenda without firing")
    p_ag.add_argument("file", help="JSON rule/fact file")

    # validate
    p_val = sub.add_parser("validate", help="Validate a JSON rule file")
    p_val.add_argument("file", help="JSON rule file")

    # repl
    p_repl = sub.add_parser("repl", help="Interactive REPL")
    p_repl.add_argument("file", help="JSON rule/fact file")
    p_repl.add_argument("--strategy", default="refc",
                        choices=["fifo", "lifo", "priority", "recent", "refc"])

    # version
    sub.add_parser("version", help="Print version")

    return parser


def _strategy_from_str(s: str) -> ConflictResolution:
    return {
        "fifo": ConflictResolution.FIFO,
        "lifo": ConflictResolution.LIFO,
        "priority": ConflictResolution.PRIORITY,
        "recent": ConflictResolution.RECENT,
        "refc": ConflictResolution.REFC,
    }[s]


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

    n = eng.run()
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
        from .serialization import load_json
        rules, facts = load_json(args.file)
        print(f"OK: {len(rules)} rule(s), {len(facts)} fact(s).")
        for r in rules:
            print(f"  Rule '{r.name}': {len(r.conditions)} condition(s), "
                  f"{len(r.actions)} action(s), priority={r.priority}")
        return 0
    except (ReteError, FileNotFoundError) as e:
        print(f"Invalid: {e}", file=sys.stderr)
        return 1


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
        elif cmd == "assert":
            if len(parts) < 2:
                print("Usage: assert <type> key=val ...")
                continue
            ftype = parts[1]
            fields = {}
            for p in parts[2:]:
                if "=" in p:
                    k, v = p.split("=", 1)
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
            for rname, s in eng.get_stats().items():
                print(f"  {rname}: fires={s['fires']}, "
                      f"activations={s['activations']}")
        else:
            print(f"Unknown command: {cmd}")

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
    elif args.command == "repl":
        return cmd_repl(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())