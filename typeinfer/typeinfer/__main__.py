"""CLI entry point: ``python -m typeinfer [OPTIONS] "<expression>"``.

Uses argparse for robust flag parsing.  Supports config files, file input,
JSON output mode, and an interactive REPL.

Examples::

    # Basic inference
    python -m typeinfer "\\x. x"
    python -m typeinfer --builtins "1 + 2"

    # From file
    python -m typeinfer --file program.tc

    # JSON output (for tooling integration)
    python -m typeinfer --json "\\x. x"

    # Step-by-step trace
    python -m typeinfer --explain "let id = \\x. x in id 42"

    # With config file
    python -m typeinfer --config .typeinfer.json "1 + 2"

    # Interactive REPL
    python -m typeinfer --repl
"""

from __future__ import annotations

import argparse
import json
import sys
import logging

from . import (
    infer, infer_with_trace, parse, type_to_string,
    InferError, ParserError, LexerError,
    __version__,
)
from .config import Config, load_config, ConfigError, default_config

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse argument parser."""
    p = argparse.ArgumentParser(
        prog="typeinfer",
        description="Hindley-Milner type inference engine (Algorithm W) "
                    "for a small lambda calculus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  typeinfer "λx. x"                     # a -> a\n'
            '  typeinfer -b "1 + 2 * 3"               # Int\n'
            '  typeinfer --explain "let id = \\x. x in id 42"\n'
            '  typeinfer --file program.tc            # infer from file\n'
            '  typeinfer --repl                        # interactive mode\n'
        ),
    )
    p.add_argument(
        "expression",
        nargs="?",
        help='Expression to infer (e.g. "λx. x")',
    )
    p.add_argument(
        "-b", "--builtins",
        action="store_true",
        default=None,
        help="load built-in primitives (+, -, *, /, <, >, ==, List, Maybe, "
             "Either, String ops, pair ops, IO ops)",
    )
    p.add_argument(
        "-e", "--explain",
        action="store_true",
        default=None,
        help="print step-by-step inference trace",
    )
    p.add_argument(
        "--ast",
        action="store_true",
        help="print the parsed AST instead of the type",
    )
    p.add_argument(
        "--repl",
        action="store_true",
        help="start an interactive REPL",
    )
    p.add_argument(
        "--file", "-f",
        metavar="PATH",
        help="read expression from a file",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="output result as JSON (for tooling integration)",
    )
    p.add_argument(
        "--config",
        metavar="PATH",
        help="load configuration from a JSON/TOML/YAML file",
    )
    p.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="set the logging level (default: WARNING)",
    )
    p.add_argument(
        "--no-builtins",
        action="store_true",
        help="explicitly disable built-in primitives (overrides config)",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"typeinfer {__version__}",
    )
    return p


def _repl(config: Config) -> int:
    """Interactive REPL: read a line, infer & print the type.

    Commands:
        :t <expr>  — infer and print the type
        :e <expr>  — infer and print the trace + type
        :b         — toggle built-in primitives on/off
        :q         — quit
        :h         — help
        :c <file>  — load a config file
    """
    print(f"typeinfer {__version__} REPL")
    print(":q to quit, :t <expr> for type, :e <expr> for trace, :h for help")
    use_builtins = config.builtins
    explain = config.explain

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in (":q", ":quit"):
            break
        if line == ":h" or line == ":help":
            print("Commands:")
            print("  :t <expr>  — infer and print the type")
            print("  :e <expr>  — infer and print the trace + type")
            print("  :b         — toggle built-in primitives on/off")
            print("  :c <file>  — load a config file")
            print("  :q         — quit")
            continue
        if line == ":b":
            use_builtins = not use_builtins
            print(f"builtins: {'on' if use_builtins else 'off'}")
            continue
        if line.startswith(":c "):
            cfg_path = line[3:].strip()
            try:
                new_config = load_config(cfg_path)
                config = new_config
                use_builtins = config.builtins
                explain = config.explain
                print(f"loaded config from {cfg_path}")
            except ConfigError as e:
                print(f"config error: {e}", file=sys.stderr)
            continue

        trace = explain
        src = line
        if line.startswith(":t "):
            src = line[3:]
            trace = False
        elif line.startswith(":e "):
            src = line[3:]
            trace = True

        try:
            if trace:
                t, steps = infer_with_trace(src, use_builtins=use_builtins)
                for s in steps:
                    print(f"  {s}")
                print(f"=> {type_to_string(t)}")
            else:
                t = infer(src, use_builtins=use_builtins)
                print(type_to_string(t))
        except (LexerError, ParserError, InferError) as e:
            print(f"error: {e}", file=sys.stderr)
    return 0


def _ast_to_string(node, indent: int = 0) -> str:
    """Pretty-print an AST node as a tree."""
    pad = "  " * indent
    cls = type(node).__name__
    if isinstance(node, dict):  # pragma: no cover
        return f"{pad}{node}"
    if not hasattr(node, "__dataclass_fields__"):
        return f"{pad}{node!r}"
    fields = []
    for fname in node.__dataclass_fields__:
        val = getattr(node, fname)
        if hasattr(val, "__dataclass_fields__"):
            fields.append(f"{fname}:\n{_ast_to_string(val, indent + 1)}")
        elif isinstance(val, tuple) and val and hasattr(val[0], "__dataclass_fields__"):
            inner = "\n".join(_ast_to_string(v, indent + 1) for v in val)
            fields.append(f"{fname}:\n{inner}")
        else:
            fields.append(f"{fname}={val!r}")
    return f"{pad}{cls}({', '.join(fields)})"


def main(argv=None) -> int:
    """Main CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()
    args = parser.parse_args(argv)

    # Load config file if specified
    config = default_config()
    if args.config:
        try:
            config = load_config(args.config)
        except ConfigError as e:
            print(f"config error: {e}", file=sys.stderr)
            return 2

    # Apply command-line overrides
    if args.builtins is not None:
        config.builtins = True
    elif args.no_builtins:
        config.builtins = False
    if args.explain is not None:
        config.explain = True
    if args.log_level is not None:
        config.log_level = args.log_level

    # Apply logging
    level = getattr(logging, config.log_level.upper(), logging.WARNING)
    logging.getLogger("typeinfer").setLevel(level)
    if level <= logging.DEBUG:
        logging.basicConfig(level=level, format="%(name)s: %(message)s")

    # Start REPL
    if args.repl:
        return _repl(config)

    # Get the source expression
    source = None
    if args.file:
        try:
            with open(args.file, "r") as f:
                source = f.read().strip()
        except OSError as e:
            print(f"error reading file: {e}", file=sys.stderr)
            return 1
    elif args.expression:
        source = args.expression

    if source is None:
        parser.print_help()
        return 1

    try:
        if args.ast:
            ast = parse(source)
            print(_ast_to_string(ast))
            return 0

        if config.explain:
            t, steps = infer_with_trace(source, use_builtins=config.builtins)
            if args.json:
                result = {
                    "type": type_to_string(t),
                    "trace": steps,
                }
                print(json.dumps(result, indent=2))
            else:
                for s in steps:
                    print(f"  {s}")
                print(f"=> {type_to_string(t)}")
        else:
            t = infer(source, use_builtins=config.builtins)
            if args.json:
                print(json.dumps({"type": type_to_string(t)}))
            else:
                print(type_to_string(t))
        return 0
    except (LexerError, ParserError, InferError) as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())