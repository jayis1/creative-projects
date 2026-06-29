"""
Command-line interface for the Forth interpreter.

Usage examples::

    forth                          # interactive REPL
    forth -e '5 DUP * . CR'        # evaluate a code string
    forth -f examples/primes.fs    # execute a file
    forth -f program.fs --debug    # run with debug logging
    forth -e '1 2 + .' --no-banner # suppress banner
    forth --version                # print version
    forth -f prog.fs --stack-size 50000  # set max stack depth
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from forth.core import ForthError, ForthInterpreter

VERSION = "3.0.0"


def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load a JSON or YAML configuration file.

    Supported keys: ``max_recursion``, ``max_stack``, ``debug``, ``no_banner``.

    Returns an empty dict if no path is given or the file is missing.
    """
    if config_path is None:
        return {}
    path = Path(config_path)
    if not path.exists():
        print(f"Warning: config file not found: {config_path}", file=sys.stderr)
        return {}
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            print("Warning: PyYAML not installed; cannot read YAML config", file=sys.stderr)
            return {}
        return yaml.safe_load(text)
    return json.loads(text)


def _setup_logging(debug: bool = False) -> None:
    """Configure the ``forth`` logger."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def create_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the Forth CLI."""
    parser = argparse.ArgumentParser(
        prog="forth",
        description="A stack-based Forth interpreter in pure Python.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  forth                           Start interactive REPL
  forth -e '5 DUP * . CR'          Evaluate inline code
  forth -f examples/primes.fs      Execute a Forth source file
  forth -f prog.fs --debug         Run with debug logging
  forth --version                  Print version and exit
  forth -c config.json -e '42 . '  Use config file

Configuration file (JSON or YAML) supports:
  {
    "max_recursion": 1000,
    "max_stack": 50000,
    "debug": false,
    "no_banner": false
  }
""",
    )
    parser.add_argument(
        "-e", "--eval", metavar="CODE",
        help="evaluate Forth code string and exit",
    )
    parser.add_argument(
        "-f", "--file", metavar="FILE",
        help="execute a Forth source file and exit",
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true",
        help="start interactive REPL (default if no -e or -f)",
    )
    parser.add_argument(
        "-c", "--config", metavar="CONFIG",
        help="path to JSON or YAML configuration file",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="enable debug logging",
    )
    parser.add_argument(
        "--no-banner", action="store_true",
        help="suppress the REPL banner",
    )
    parser.add_argument(
        "--stack-size", type=int, default=10_000, metavar="N",
        help="maximum data-stack depth (default: 10000)",
    )
    parser.add_argument(
        "--max-recursion", type=int, default=500, metavar="N",
        help="maximum recursion depth (default: 500)",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"forth-interpreter {VERSION}",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point.  *argv* defaults to ``sys.argv[1:]``."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Load config file (CLI flags override)
    config = _load_config(args.config)

    debug = args.debug or config.get("debug", False)
    _setup_logging(debug)

    no_banner = args.no_banner or config.get("no_banner", False)
    max_stack = args.stack_size or config.get("max_stack", 10_000)
    max_recursion = args.max_recursion or config.get("max_recursion", 500)

    interp = ForthInterpreter(
        max_recursion=max_recursion,
        max_stack=max_stack,
    )

    if args.eval:
        try:
            interp.eval(args.eval)
        except ForthError as e:
            print(f"? {e}", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(filepath) as f:
            try:
                interp.eval(f.read())
            except ForthError as e:
                print(f"? {e}", file=sys.stderr)
                sys.exit(1)
    elif args.interactive or not (args.eval or args.file):
        _run_repl(interp, no_banner)


def _run_repl(interp: ForthInterpreter, no_banner: bool) -> None:
    """Run the interactive REPL."""
    from forth import __version__
    if not no_banner:
        interp.emit_line(f"Forth Interpreter v{__version__} — type BYE to exit, WORDS for word list")
    while True:
        interp.emit("ok ")
        try:
            line = sys.stdin.readline()
            if not line:
                break
            interp.eval(line)
        except ForthError as e:
            interp.emit_line(f"? {e}")
            interp._reset_state()
        except SystemExit:
            break
        except KeyboardInterrupt:
            interp.emit_line("\ninterrupted")
            interp._reset_state()