"""Command-line interface for the mini-Prolog engine."""

from __future__ import annotations

import sys
import argparse
from prolog_engine.engine import Engine
from prolog_engine.builtins import register_builtins
from prolog_engine.parser import Parser
from prolog_engine.ast_nodes import term_to_str, variables_in, Query


def run_repl(engine: Engine) -> None:
    """Run an interactive Prolog REPL."""
    print("mini-Prolog Engine v1.0.0")
    print("Type queries as '?- goal.' or clauses as 'head :- body.'")
    print("Type 'quit.' or Ctrl-D to exit.")
    print()

    while True:
        try:
            line = input("?- " if not _in_clause_mode() else "   ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        line = line.strip()
        if not line:
            continue
        if line.lower() in ("quit.", "exit.", "halt."):
            break

        # Try to parse and execute
        try:
            if line.startswith("?-"):
                # Query mode
                parser = Parser.from_source(line)
                query = parser.parse_query()
                _run_query(engine, query)
            elif line.endswith("."):
                # Could be a clause or a query
                parser = Parser.from_source(line)
                # Try as query first
                try:
                    query = parser.parse_query()
                    _run_query(engine, query)
                except Exception:
                    # Try as clause
                    parser2 = Parser.from_source(line)
                    program = parser2.parse_program()
                    engine.load_program(program)
                    print(f"Loaded {len(program.clauses)} clause(s).")
            else:
                # Treat as incomplete — for now just try
                parser = Parser.from_source(line + ".")
                try:
                    query = parser.parse_query()
                    _run_query(engine, query)
                except Exception:
                    parser2 = Parser.from_source(line + ".")
                    program = parser2.parse_program()
                    engine.load_program(program)
                    print(f"Loaded {len(program.clauses)} clause(s).")
        except Exception as e:
            print(f"Error: {e}")


def _in_clause_mode() -> bool:
    """Check if we're in the middle of entering a clause (simplified)."""
    return False


def _run_query(engine: Engine, query: Query) -> None:
    """Run a query and display results."""
    found = False
    for subst in engine.execute(query):
        found = True
        solution = engine.format_solution(subst, query.goals)
        if solution == "yes":
            print("yes")
        else:
            print(solution + " ;")
    if not found:
        print("no")
    else:
        print("")  # blank line after results


def run_file(engine: Engine, filepath: str) -> None:
    """Load and execute a Prolog source file."""
    with open(filepath, "r") as f:
        source = f.read()
    engine.load_source(source)
    print(f"Loaded {len(engine.clauses)} clause(s) from {filepath}")


def run_query(engine: Engine, query_str: str) -> None:
    """Execute a single query string."""
    parser = Parser.from_source(query_str)
    query = parser.parse_query()
    _run_query(engine, query)


def main() -> None:
    """Entry point for the prolog-engine CLI."""
    parser = argparse.ArgumentParser(
        description="Mini-Prolog logic programming engine",
        prog="prolog-engine",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Prolog source files to load",
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Execute a query string",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive REPL after loading files",
    )

    args = parser.parse_args()

    engine = Engine()
    register_builtins(engine)

    # Load files
    for filepath in args.files:
        try:
            run_file(engine, filepath)
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error loading {filepath}: {e}", file=sys.stderr)
            sys.exit(1)

    # Run query if provided
    if args.query:
        try:
            run_query(engine, args.query)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Start REPL if interactive or no files/query
    if args.interactive or (not args.files and not args.query):
        run_repl(engine)


if __name__ == "__main__":
    main()