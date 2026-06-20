"""Command-line interface for the Datalog engine.

Usage::

    python -m datalog.cli program.dl
    python -m datalog.cli program.dl --query "path(a, Y)"
    python -m datalog.cli program.dl --explain path
    python -m datalog.cli program.dl --export state.json
    python -m datalog.cli program.dl --format table --query "path(a,Y)"
    python -m datalog.cli --config datalog.toml
    python -m datalog.cli --repl
    cat facts.dl | python -m datalog.cli -
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from .config import EngineConfig, load_config, ConfigurationError
from .engine import Engine, DatalogError
from .errors import SafetyError, StratificationError
from .output import format_results, format_binding
from .parser import parse, ParseError, LexError

logger = logging.getLogger("datalog.cli")


def _load_files(engine: Engine, files: List[str]) -> None:
    """Load one or more .dl source files into the engine."""
    for f in files:
        if f == "-":
            src = sys.stdin.read()
        else:
            with open(f, "r") as fh:
                src = fh.read()
        engine.add_source(src)


def _run_query(
    engine: Engine, q: str, fmt: str = "binding"
) -> int:
    """Run a single query and print results. Returns answer count."""
    try:
        results = engine.query(q)
    except (DatalogError, ParseError, LexError) as e:
        print(f"error: {e}", file=sys.stderr)
        return -1
    print(format_results(results, fmt))
    return len(results) if results else 0


def _run_multiple_queries(
    engine: Engine, queries: List[str], fmt: str = "binding"
) -> None:
    """Run multiple queries in sequence."""
    for q in queries:
        print(f"?- {q}")
        _run_query(engine, q, fmt)
        print()


def repl(engine: Engine) -> None:
    """Interactive read-eval-print loop.

    Supports:
    - Loading facts and rules (terminated by '.')
    - Queries (starting with ?- or bare atoms)
    - Meta-commands starting with ':'
    """
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
                print("  :explain NAME    Explain predicate NAME")
                print("  :rules           List all rules")
                print("  :export FILE     Export state to JSON file")
                print("  :import FILE     Import state from JSON file")
                print("  :stats           Show engine statistics")
                print("  :reset           Clear all facts and rules")
                print("Statements end with '.' — queries start with ?-")
                continue
            if stripped == ":preds":
                for p in engine.predicates():
                    print(f"  {p}/{engine.arity(p)}")
                continue
            if stripped.startswith(":rel "):
                name = stripped[5:].strip()
                for tup in engine.relation(name):
                    print(f"  {tup}")
                continue
            if stripped.startswith(":explain"):
                parts = stripped.split(None, 1)
                name = parts[1].strip() if len(parts) > 1 else ""
                if name:
                    print(engine.explain(name))
                else:
                    print("Usage: :explain PREDICATE")
                continue
            if stripped == ":rules":
                for r in engine.rules():
                    print(f"  {r}")
                continue
            if stripped.startswith(":export"):
                parts = stripped.split(None, 1)
                if len(parts) < 2:
                    print("Usage: :export FILENAME")
                    continue
                filename = parts[1].strip()
                try:
                    with open(filename, "w") as fh:
                        fh.write(engine.to_json())
                    print(f"Exported to {filename}")
                except OSError as e:
                    print(f"error: {e}", file=sys.stderr)
                continue
            if stripped.startswith(":import"):
                parts = stripped.split(None, 1)
                if len(parts) < 2:
                    print("Usage: :import FILENAME")
                    continue
                filename = parts[1].strip()
                try:
                    with open(filename, "r") as fh:
                        engine.from_json(fh.read())
                    print(f"Imported from {filename}")
                except (OSError, DatalogError) as e:
                    print(f"error: {e}", file=sys.stderr)
                continue
            if stripped == ":stats":
                for k, v in engine.stats().items():
                    print(f"  {k}: {v}")
                continue
            if stripped == ":reset":
                engine.clear()
                print("engine reset.")
                continue
        buffer += line + "\n"
        if buffer.rstrip().endswith("."):
            try:
                prog = parse(buffer)
                if prog.queries:
                    for q in prog.queries:
                        _run_query(engine, str(q.atom))
                else:
                    engine.add_source(buffer)
            except (ParseError, LexError, DatalogError) as e:
                print(f"error: {e}", file=sys.stderr)
            buffer = ""


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="datalog",
        description="Datalog deductive database engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  datalog program.dl -q "ancestor(tom, X)"
  datalog program.dl --format table -q "path(a, Y)"
  datalog program.dl --explain path
  datalog program.dl --export state.json
  datalog --config datalog.toml
  datalog --repl
  cat facts.dl | datalog -
""",
    )
    parser.add_argument(
        "files", nargs="*", help="Datalog source files (use - for stdin)"
    )
    parser.add_argument(
        "--query", "-q", action="append", default=[],
        help="Query to run after loading files (can repeat)",
    )
    parser.add_argument(
        "--repl", action="store_true", help="Start interactive REPL"
    )
    parser.add_argument(
        "--show", metavar="PRED",
        help="Show all tuples of predicate PRED after loading",
    )
    parser.add_argument(
        "--explain", metavar="PRED",
        help="Explain a predicate (rules, stratum, extension)",
    )
    parser.add_argument(
        "--export", metavar="FILE",
        help="Export EDB facts + rules to JSON file",
    )
    parser.add_argument(
        "--import", dest="import_file", metavar="FILE",
        help="Import JSON state before loading files",
    )
    parser.add_argument(
        "--config", metavar="FILE",
        help="Load configuration from JSON/TOML/YAML file",
    )
    parser.add_argument(
        "--format", choices=["binding", "table", "json", "csv"],
        default="binding",
        help="Output format for query results (default: binding)",
    )
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Logging verbosity (default: WARNING)",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print engine statistics after running queries",
    )
    args = parser.parse_args(argv)

    # Load config file if specified, otherwise build from CLI args
    if args.config:
        try:
            config = load_config(args.config)
        except ConfigurationError as e:
            print(f"config error: {e}", file=sys.stderr)
            return 1
    else:
        config = EngineConfig(
            log_level=args.log_level,
            output_format=args.format,
        )

    # CLI args override config where applicable
    log_level = args.log_level or config.log_level
    logging.basicConfig(level=getattr(logging, log_level, logging.WARNING))
    output_format = args.format if args.format != "binding" else config.output_format

    engine = Engine(config=config)

    # Import JSON state first (before files, so files can override)
    import_file = args.import_file
    if import_file:
        try:
            with open(import_file, "r") as fh:
                engine.from_json(fh.read())
        except (OSError, DatalogError) as e:
            print(f"error importing: {e}", file=sys.stderr)
            return 1

    # Load files (from config or CLI args)
    files = args.files if args.files else config.files
    if files:
        try:
            _load_files(engine, files)
        except (DatalogError, ParseError, LexError, OSError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    # Run queries (from config or CLI args)
    queries = args.query if args.query else config.queries
    if queries:
        _run_multiple_queries(engine, queries, output_format)

    if args.show:
        for tup in engine.relation(args.show):
            print(tup)

    if args.explain:
        print(engine.explain(args.explain))

    # Explain predicates from config
    for pred in config.explain_predicates:
        print(engine.explain(pred))

    if args.export:
        try:
            with open(args.export, "w") as fh:
                fh.write(engine.to_json())
            print(f"Exported to {args.export}", file=sys.stderr)
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if config.export_file and not args.export:
        try:
            with open(config.export_file, "w") as fh:
                fh.write(engine.to_json())
            print(f"Exported to {config.export_file}", file=sys.stderr)
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if args.stats:
        print("\nEngine statistics:")
        for k, v in engine.stats().items():
            print(f"  {k}: {v}")

    # Start REPL if requested, or if no other action was specified
    no_action = (
        not files
        and not queries
        and not args.show
        and not args.explain
        and not args.export
        and not import_file
        and not args.stats
        and not config.explain_predicates
    )
    if args.repl or no_action:
        repl(engine)

    return 0


if __name__ == "__main__":
    sys.exit(main())