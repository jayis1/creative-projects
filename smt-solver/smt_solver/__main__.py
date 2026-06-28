"""Command-line interface for the SMT solver."""

from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path

from .solver import Solver, SMTResult
from .parser import parse_script
from .exceptions import SMTError, ParseError
from . import __version__


def run_file(path: str, print_model: bool = False, verbose: bool = False) -> SMTResult:
    """Run the solver on an SMT-LIB file."""
    content = Path(path).read_text()
    solver = Solver()
    solver.parse_and_assert(content)
    result = solver.check()
    print(result)
    if result == "sat" and print_model:
        model = solver.get_model()
        if model:
            print("(:model")
            print(model.to_smt())
            print(")")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="smt-solver",
        description="DPLL(T) SMT solver with EUF and LRA theories",
    )
    parser.add_argument("file", nargs="?", help="SMT-LIB input file")
    parser.add_argument("--version", action="version", version=f"smt-solver {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--model", action="store_true", help="Print model when sat")
    parser.add_argument("-e", "--expr", help="Assert a single expression")
    parser.add_argument(
        "--check", choices=["sat", "unsat", "unknown"],
        help="Expected result (for testing)",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.expr:
        solver = Solver()
        text = f"(declare-const x Real) (assert {args.expr})"
        solver.parse_and_assert(text)
        result = solver.check()
        print(result)
        if args.check:
            if result != args.check:
                print(f"EXPECTED: {args.check}", file=sys.stderr)
                return 1
        return 0

    if args.file:
        result = run_file(args.file, print_model=args.model, verbose=args.verbose)
        if args.check:
            if result != args.check:
                print(f"EXPECTED: {args.check}", file=sys.stderr)
                return 1
        return 0

    # No file — read from stdin
    content = sys.stdin.read()
    if content.strip():
        solver = Solver()
        solver.parse_and_assert(content)
        result = solver.check()
        print(result)
        if result == "sat" and args.model:
            model = solver.get_model()
            if model:
                print("(:model")
                print(model.to_smt())
                print(")")
    return 0


if __name__ == "__main__":
    sys.exit(main())