"""Command-line interface for the Datalog engine.

Usage::

    python -m datalog.cli program.dl
    python -m datalog.cli program.dl --query "path(a, Y)"
    python -m datalog.cli --repl
    cat facts.dl | python -m datalog.cli -
"""

from __future__ import annotations

import argparse
import sys
from typing import List

from .engine import Engine, DatalogError
from .parser import parse, ParseError, LexError


def _format_binding(binding: dict) -> str:
    parts = []
    for k in sorted(binding):
        v = binding[k]
        if isinstance(v, str):
            parts.append(f"{k} = {v}")
        else:
            parts.append(f"{k} = {v}")
    return ", ".join(parts)


def _load_files(engine: Engine, files: List[str]) -> None:
    for f in files:
        if f == "-":
            src = sys.stdin.read()
        else:
            with open(f, "r") as fh:
                src = fh.read()
        engine.add_source(src)


def _run_query(engine: Engine, q: str) -> None:
    try:
        results = engine.query(q)
    except (DatalogError, ParseError, LexError) as e:
        print(f"error: {e}", file=sys.stderr)
        return
    if not results:
        print("false.")
    else:
        for r in results:
            print(f"{_format_binding(r)}")
        print(f"({len(results)} answer{'s' if len(results) != 1 else ''})")


def repl(engine: Engine) -> None:
    """Interactive read-eval-print loop."""
    print("datalog-engine REPL. Type :help for commands, :quit to exit.")
    buffer = ""
    while True:
        try:
            line = input("dl> " if not buffer else "...   ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        stripped = line.strip()
        if not buffer:
            if stripped == ":quit":
                break
            if stripped == ":help":
                print("Commands:")
                print("  :help            Show this help")
                print("  :quit            Exit the REPL")
                print("  :preds           List all predicates")
                print("  :rel NAME        Show all tuples of predicate NAME")
                print("  :reset           Clear all facts and rules")
                print("Statements end with '.' — queries start with ?-")
                continue
            if stripped == ":preds":
                for p in engine.predicates():
                    print(f"  {p}/{engine._pred_arity.get(p, '?')}")
                continue
            if stripped.startswith(":rel "):
                name = stripped[5:].strip()
                for tup in engine.relation(name):
                    print(f"  {tup}")
                continue
            if stripped == ":reset":
                engine.__init__()
                print("engine reset.")
                continue
        buffer += line + "\n"
        # Check if statement is complete (ends with .)
        if buffer.rstrip().endswith("."):
            try:
                prog = parse(buffer)
                if prog.queries:
                    for q in prog.queries:
                        _run_query(engine, str(q.atom))
                else:
                    engine.add_source(buffer)
                buffer = ""
            except (ParseError, LexError, DatalogError) as e:
                print(f"error: {e}", file=sys.stderr)
                buffer = ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="datalog",
        description="Datalog deductive database engine",
    )
    parser.add_argument("files", nargs="*", help="Datalog source files (use - for stdin)")
    parser.add_argument("--query", "-q", help="Query to run after loading files")
    parser.add_argument("--repl", action="store_true", help="Start interactive REPL")
    parser.add_argument("--show", metavar="PRED", help="Show all tuples of predicate PRED after loading")
    args = parser.parse_args(argv)

    engine = Engine()

    if args.files:
        try:
            _load_files(engine, args.files)
        except (DatalogError, ParseError, LexError, FileNotFoundError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if args.query:
        _run_query(engine, args.query)

    if args.show:
        for tup in engine.relation(args.show):
            print(tup)

    if args.repl or (not args.files and not args.query and not args.show):
        repl(engine)

    return 0


if __name__ == "__main__":
    sys.exit(main())