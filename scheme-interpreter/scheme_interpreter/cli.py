"""Command-line interface for the Scheme interpreter."""

from __future__ import annotations

import sys
import argparse
from .interpreter import Interpreter, SchemeError, SchemeExit
from .parser import ParseError
from .lexer import LexError
from .types import scheme_repr, Unspecified
from .repl import run_repl


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scheme interpreter — run scripts or start a REPL")
    parser.add_argument("file", nargs="?", help="Scheme script to run")
    parser.add_argument("-e", "--eval", dest="eval_expr", metavar="EXPR",
                        help="Evaluate expression and print result")
    parser.add_argument("-l", "--load", dest="load_file", metavar="FILE",
                        help="Load a Scheme file before evaluating")
    parser.add_argument("--no-repl", action="store_true",
                        help="Don't start REPL after running script")
    args = parser.parse_args(argv)

    interp = Interpreter()
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