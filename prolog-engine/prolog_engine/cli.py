"""Command-line interface for the mini-Prolog engine.

Provides an interactive REPL with:
- Readline support (history, line editing)
- Colorized output (optional, auto-detected)
- Multi-line input for incomplete clauses/queries
- Consult/1 support for loading files from within the REPL
- Help system
- Statistics command
- Trace toggle
"""

from __future__ import annotations

import os
import sys
import argparse
import readline
from pathlib import Path

from prolog_engine.engine import Engine, EngineError
from prolog_engine.builtins import register_builtins
from prolog_engine.parser import Parser, ParseError
from prolog_engine.lexer import LexerError
from prolog_engine.ast_nodes import term_to_str, variables_in, Query
from prolog_engine.config import EngineConfig, load_config

# ANSI color codes
class Colors:
    """Simple ANSI color helper for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    @staticmethod
    def supports_color() -> bool:
        """Check if the terminal supports color output."""
        if os.environ.get("NO_COLOR"):
            return False
        if not hasattr(sys.stdout, "isatty"):
            return False
        return sys.stdout.isatty()

    @staticmethod
    def colorize(text: str, code: str) -> str:
        """Wrap text in ANSI color codes if supported."""
        if Colors.supports_color():
            return f"{code}{text}{Colors.RESET}"
        return text


def setup_readline(history_file: str | None = None) -> None:
    """Configure readline for the REPL.

    Args:
        history_file: Path to the history file. None to disable history.
    """
    if history_file:
        expanded = os.path.expanduser(history_file)
        try:
            readline.read_history_file(expanded)
        except FileNotFoundError:
            pass
        except PermissionError:
            return
        readline.set_history_length(1000)

        import atexit
        def save_history():
            try:
                os.makedirs(os.path.dirname(expanded), exist_ok=True)
                readline.write_history_file(expanded)
            except (OSError, PermissionError):
                pass
        atexit.register(save_history)

    readline.parse_and_bind("tab: complete")


class PrologREPL:
    """Interactive Prolog REPL with readline support and colorized output.

    Features:
    - Multi-line input for incomplete clauses/queries
    - Colorized yes/no/solution output
    - Built-in commands: help, trace, listing, statistics, consult
    - Readline history and tab completion
    """

    PROMPT_PRIMARY = "?- "
    PROMPT_CONTINUE = "   "
    VERSION = "2.0.0"

    def __init__(self, engine: Engine, config: EngineConfig | None = None):
        self.engine = engine
        self.config = config or EngineConfig()
        self._buffer: list[str] = []
        self._in_multiline = False

    def run(self) -> None:
        """Start the interactive REPL loop."""
        Colors.colorize("", Colors.RESET)  # Initialize color detection

        print(Colors.colorize(f"mini-Prolog Engine v{self.VERSION}", Colors.BOLD + Colors.CYAN))
        print("Type queries as '?- goal.' or clauses as 'head :- body.'")
        print("Type 'help.' for available commands, 'quit.' or Ctrl-D to exit.")
        print()

        while True:
            try:
                prompt = self.PROMPT_CONTINUE if self._in_multiline else self.PROMPT_PRIMARY
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print()
                break

            line = line.strip()
            if not line:
                continue

            # Handle built-in REPL commands
            if self._handle_command(line):
                continue

            self._buffer.append(line)
            full_input = " ".join(self._buffer)

            # Check if the input is complete (ends with a period)
            if not full_input.rstrip().endswith("."):
                self._in_multiline = True
                continue

            self._in_multiline = False
            self._buffer.clear()

            # Try to process the input
            try:
                self._process_input(full_input)
            except (LexerError, ParseError) as e:
                print(Colors.colorize(f"Syntax error: {e}", Colors.RED))
            except EngineError as e:
                print(Colors.colorize(f"Engine error: {e}", Colors.RED))
            except Exception as e:
                print(Colors.colorize(f"Error: {e}", Colors.RED))

    def _handle_command(self, line: str) -> bool:
        """Handle special REPL commands. Returns True if command was handled."""
        cmd = line.lower().rstrip(".")

        if cmd in ("quit", "exit", "halt"):
            raise SystemExit(0)

        if cmd == "help":
            self._print_help()
            return True

        if cmd == "trace":
            self.engine._trace = not self.engine._trace
            state = "on" if self.engine._trace else "off"
            print(Colors.colorize(f"Trace mode: {state}", Colors.YELLOW))
            return True

        if cmd == "listing":
            self._print_listing()
            return True

        if cmd == "statistics":
            self._print_statistics()
            return True

        if cmd == "reset":
            self.engine.clear()
            print(Colors.colorize("Database cleared.", Colors.GREEN))
            return True

        if cmd.startswith("consult(") or cmd.startswith("load("):
            # Extract filename from consult(filename) or load(filename)
            try:
                inner = line.rstrip(".")
                # Remove consult( or load( prefix and ) suffix
                if inner.startswith("consult("):
                    fname = inner[len("consult("):-1].strip("'\"")
                elif inner.startswith("load("):
                    fname = inner[len("load("):-1].strip("'\"")
                else:
                    return False
                self._load_file(fname)
            except Exception as e:
                print(Colors.colorize(f"Error loading file: {e}", Colors.RED))
            return True

        return False

    def _print_help(self) -> None:
        """Print help information."""
        help_text = f"""
{Colors.colorize('mini-Prolog Engine Commands:', Colors.BOLD + Colors.CYAN)}

  {Colors.colorize('help.', Colors.GREEN)}          Show this help message
  {Colors.colorize('trace.', Colors.GREEN)}         Toggle trace mode on/off
  {Colors.colorize('listing.', Colors.GREEN)}       Show all loaded clauses
  {Colors.colorize('statistics.', Colors.GREEN)}    Show engine statistics
  {Colors.colorize('reset.', Colors.GREEN)}         Clear the database
  {Colors.colorize("consult('file').", Colors.GREEN)} Load a Prolog source file
  {Colors.colorize('quit.', Colors.GREEN)}          Exit the REPL (also: exit, halt)

{Colors.colorize('Prolog Syntax:', Colors.BOLD + Colors.CYAN)}

  {Colors.colorize('?- query.', Colors.YELLOW)}     Execute a query
  {Colors.colorize('fact.', Colors.YELLOW)}          Assert a fact
  {Colors.colorize('head :- body.', Colors.YELLOW)}  Assert a rule

{Colors.colorize('Built-in Predicates:', Colors.BOLD + Colors.CYAN)}

  Unification:    =/2, \\=/2, ==/2, \\==/2
  Arithmetic:     is/2, </2, >/2, =</2, >=/2
  Type checking:  var/1, nonvar/1, atom/1, number/1, compound/1, ...
  Control flow:   !/0, not/1, \\+/1, once/1, forall/2, repeat/0
  Lists:          member/2, append/3, length/2, sort/2, ...
  Meta-logical:   findall/3, bagof/3, setof/3, copy_term/2
  Dynamic DB:     assertz/1, asserta/1, retract/1, clause/2
  I/O:            write/1, writeln/1, nl/0, write_canonical/1
"""
        print(help_text)

    def _print_listing(self) -> None:
        """Print all loaded clauses."""
        if not self.engine.clauses:
            print(Colors.colorize("(database is empty)", Colors.DIM))
            return
        for clause in self.engine.clauses:
            print(f"  {clause}")

    def _print_statistics(self) -> None:
        """Print engine statistics."""
        stats = self.engine.statistics()
        print(Colors.colorize("Engine Statistics:", Colors.BOLD + Colors.CYAN))
        print(f"  Clauses loaded:    {stats['clauses']}")
        print(f"  Built-in predicates: {stats['builtins']}")
        print(f"  Max depth:         {stats['max_depth']}")
        print(f"  Max solutions:     {stats['max_solutions']}")
        print(f"  Trace mode:        {'on' if stats['trace'] else 'off'}")
        if stats['predicates']:
            print(f"  Predicates:")
            for name_arity, count in sorted(stats['predicates'].items()):
                print(f"    {name_arity}: {count} clause(s)")

    def _load_file(self, filepath: str) -> None:
        """Load a Prolog source file."""
        try:
            self.engine.load_file(filepath)
            print(Colors.colorize(
                f"Loaded {len(self.engine.clauses)} clause(s) from {filepath}",
                Colors.GREEN
            ))
        except FileNotFoundError:
            print(Colors.colorize(f"File not found: {filepath}", Colors.RED))

    def _process_input(self, full_input: str) -> None:
        """Process a complete input line (clause or query)."""
        # Strip leading ?- if present
        stripped = full_input.strip()
        if stripped.startswith("?-"):
            # Query mode
            parser = Parser.from_source(stripped)
            query = parser.parse_query()
            self._run_query(query)
        else:
            # Try as clause first, then as query
            try:
                parser = Parser.from_source(stripped)
                program = parser.parse_program()
                self.engine.load_program(program)
                print(Colors.colorize(
                    f"Loaded {len(program.clauses)} clause(s).",
                    Colors.GREEN
                ))
            except Exception:
                # Try as query
                try:
                    parser = Parser.from_source(stripped)
                    query = parser.parse_query()
                    self._run_query(query)
                except Exception as e:
                    print(Colors.colorize(f"Error: {e}", Colors.RED))

    def _run_query(self, query: Query) -> None:
        """Run a query and display results."""
        found = False
        for subst in self.engine.execute(query):
            found = True
            solution = self.engine.format_solution(subst, query.goals)
            if solution == "yes":
                print(Colors.colorize("yes", Colors.GREEN))
            else:
                print(Colors.colorize(solution + " ;", Colors.YELLOW))
        if not found:
            print(Colors.colorize("no", Colors.RED))
        else:
            print()  # blank line after results


def run_repl(engine: Engine, config: EngineConfig | None = None) -> None:
    """Run an interactive Prolog REPL.

    Args:
        engine: The Prolog engine instance.
        config: Optional configuration for readline history, etc.
    """
    cfg = config or EngineConfig()
    if cfg.repl_history_file:
        setup_readline(cfg.repl_history_file)
    repl = PrologREPL(engine, cfg)
    repl.run()


def run_file(engine: Engine, filepath: str) -> None:
    """Load and execute a Prolog source file.

    Args:
        engine: The Prolog engine instance.
        filepath: Path to the .pl file.
    """
    engine.load_file(filepath)
    print(f"Loaded {len(engine.clauses)} clause(s) from {filepath}")


def run_query(engine: Engine, query_str: str) -> None:
    """Execute a single query string.

    Args:
        engine: The Prolog engine instance.
        query_str: Prolog query string.
    """
    parser = Parser.from_source(query_str)
    query = parser.parse_query()
    found = False
    for subst in engine.execute(query):
        found = True
        solution = engine.format_solution(subst, query.goals)
        print(solution if solution == "yes" else solution + " ;")
    if not found:
        print("no")


def main() -> None:
    """Entry point for the prolog-engine CLI."""
    arg_parser = argparse.ArgumentParser(
        description="mini-Prolog Engine — a logic programming engine in Python",
        prog="prolog-engine",
    )
    arg_parser.add_argument(
        "files",
        nargs="*",
        help="Prolog source files to load (.pl, .prolog)",
    )
    arg_parser.add_argument(
        "-q", "--query",
        type=str,
        help="Execute a query string (e.g., '?- father(X, Y).')",
    )
    arg_parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive REPL after loading files",
    )
    arg_parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable trace mode for debugging",
    )
    arg_parser.add_argument(
        "--max-depth",
        type=int,
        default=1000,
        help="Maximum inference depth (default: 1000)",
    )
    arg_parser.add_argument(
        "--max-solutions",
        type=int,
        default=10000,
        help="Maximum number of solutions (default: 10000)",
    )
    arg_parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a configuration file (.yml, .json, .toml)",
    )
    arg_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {PrologREPL.VERSION}",
    )

    args = arg_parser.parse_args()

    # Handle no-color
    if args.no_color:
        os.environ["NO_COLOR"] = "1"

    # Load configuration
    if args.config:
        config = EngineConfig.from_file(args.config)
    else:
        config = load_config()

    # Override config with CLI args
    config.max_depth = args.max_depth
    config.max_solutions = args.max_solutions
    config.trace = args.trace or config.trace

    # Create engine
    engine = Engine(
        max_depth=config.max_depth,
        max_solutions=config.max_solutions,
        trace=config.trace,
    )
    register_builtins(engine)

    # Load files
    for filepath in args.files:
        try:
            engine.load_file(filepath)
            print(f"Loaded {filepath}")
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
        if not args.interactive:
            return

    # Start REPL if interactive or no files/query
    if args.interactive or (not args.files and not args.query):
        try:
            run_repl(engine, config)
        except SystemExit:
            pass
        except KeyboardInterrupt:
            print("\nGoodbye!")


if __name__ == "__main__":
    main()