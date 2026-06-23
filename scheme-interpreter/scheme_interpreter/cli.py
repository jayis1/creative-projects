"""Command-line interface for the Scheme interpreter.

Enhanced CLI with:
- File execution, expression evaluation, file loading
- --no-stdlib: skip loading the standard library
- --no-repl: exit after script execution
- --trace: enable tracing output
- --version: show version
- --config: load a JSON/TOML config file
- --log-level: set logging verbosity
"""

from __future__ import annotations

import sys
import argparse
import json
import logging
import os
from .interpreter import Interpreter, SchemeError, SchemeExit
from .parser import ParseError
from .lexer import LexError
from .types import scheme_repr, Unspecified
from .repl import run_repl


def _load_config(path: str) -> dict:
    """Load a JSON or TOML configuration file.

    Args:
        path: Path to the config file. If it ends with .toml, TOML is used;
              otherwise JSON is assumed.

    Returns:
        A dictionary of configuration options.
    """
    with open(path, "r") as f:
        content = f.read()
    if path.endswith(".toml"):
        try:
            import tomllib  # Python 3.11+
            return tomllib.loads(content)
        except ImportError:
            try:
                import tomli
                return tomli.loads(content)
            except ImportError:
                # Fallback: minimal TOML parsing for simple key=value
                config = {}
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        config[key] = val
                return config
    return json.loads(content)


def main(argv=None):
    """Main CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="Scheme interpreter — run scripts or start a REPL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  scheme                          Start interactive REPL
  scheme script.scm               Run a script, then enter REPL
  scheme script.scm --no-repl     Run a script and exit
  scheme -e '(+ 1 2 3)'           Evaluate an expression
  scheme -l stdlib.scm script.scm Load a file, then run a script
  scheme --version                Show version

Environment variables:
  SCHEME_LOG_LEVEL  Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
""",
    )
    parser.add_argument("file", nargs="?", help="Scheme script to run")
    parser.add_argument("-e", "--eval", dest="eval_expr", metavar="EXPR",
                        help="Evaluate expression and print result")
    parser.add_argument("-l", "--load", dest="load_file", metavar="FILE",
                        help="Load a Scheme file before evaluating")
    parser.add_argument("--no-repl", action="store_true",
                        help="Don't start REPL after running script")
    parser.add_argument("--no-stdlib", action="store_true",
                        help="Don't auto-load the standard library (stdlib.scm)")
    parser.add_argument("--version", action="store_true",
                        help="Show version and exit")
    parser.add_argument("--config", dest="config_file", metavar="FILE",
                        help="Load a JSON/TOML configuration file")
    parser.add_argument("--log-level", dest="log_level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="WARNING",
                        help="Set logging verbosity (default: WARNING)")
    args = parser.parse_args(argv)

    if args.version:
        from . import __version__
        print(f"scheme-interpreter v{__version__}")
        return 0

    # Parse config file
    config = {}
    if args.config_file:
        try:
            config = _load_config(args.config_file)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1

    # Determine log level
    log_level_name = config.get("log_level", args.log_level)
    log_level = getattr(logging, log_level_name, logging.WARNING)

    # Determine stdlib loading
    load_stdlib = not args.no_stdlib and not config.get("no_stdlib", False)

    interp = Interpreter(load_stdlib=load_stdlib, log_level=log_level)
    from .primitives import set_global_interpreter
    set_global_interpreter(interp)

    if args.load_file:
        try:
            with open(args.load_file) as f:
                interp.run(f.read())
        except (SchemeError, ParseError, LexError) as e:
            print(f"Error loading {args.load_file}: {e}", file=sys.stderr)
            return 1

    if args.eval_expr:
        try:
            result = interp.run(args.eval_expr)
            if result is not Unspecified and result is not None:
                print(scheme_repr(result))
        except SchemeExit as e:
            return e.code
        except (SchemeError, ParseError, LexError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    if args.file:
        try:
            with open(args.file) as f:
                source = f.read()
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        try:
            interp.run(source)
        except SchemeExit as e:
            return e.code
        except (SchemeError, ParseError, LexError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if args.no_repl:
            return 0

    return run_repl()


if __name__ == "__main__":
    sys.exit(main())