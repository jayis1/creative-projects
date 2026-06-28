"""Command-line interface for the SMT solver.

Usage:
  smt-solver [OPTIONS] [FILE]

Options:
  --model          Print the model when result is sat
  --check EXPECT   Expected result (sat/unsat/unknown), exits 1 on mismatch
  --stats          Print solver statistics
  --verbose        Verbose output (debug logging)
  --logic LOGIC    Set the SMT logic
  --config FILE    Load configuration from a file
  --batch DIR      Run all .smt2 files in a directory
  --version        Show version and exit
"""

from __future__ import annotations

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import List, Tuple

from .solver import Solver, SMTResult
from .parser import parse_script
from .exceptions import SMTError, ParseError
from . import __version__


def run_file(
    path: str,
    print_model: bool = False,
    verbose: bool = False,
    show_stats: bool = False,
    logic: str | None = None,
) -> Tuple[SMTResult, Solver]:
    """Run the solver on an SMT-LIB file.

    Args:
        path: Path to the SMT-LIB file.
        print_model: If True, print the model when result is sat.
        verbose: If True, enable debug logging.
        show_stats: If True, print solver statistics.
        logic: Optional logic identifier.

    Returns:
        Tuple of (result_string, solver_instance).
    """
    content = Path(path).read_text()
    solver = Solver(logic=logic)
    solver.parse_and_assert(content)
    result = solver.check()
    print(result)
    if result == "sat" and print_model:
        model = solver.get_model()
        if model:
            print("(:model")
            print(model.to_smt())
            print(")")
    if show_stats:
        print("(;stats")
        print(solver.stats)
        print(";)")
    return result, solver


def run_batch(
    directory: str,
    show_stats: bool = False,
    verbose: bool = False,
) -> int:
    """Run the solver on all .smt2 files in a directory.

    Returns the number of failures (mismatched expected results).
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        return 1

    files = sorted(dir_path.glob("*.smt2"))
    if not files:
        print(f"No .smt2 files found in {directory}", file=sys.stderr)
        return 0

    print(f"Running {len(files)} files in {directory}...")
    print("-" * 60)

    passed = 0
    failed = 0
    errors = 0

    for f in files:
        try:
            content = f.read_text()
            solver = Solver()
            solver.parse_and_assert(content)
            result = solver.check()
            # Try to extract expected result from comments
            expected = _extract_expected(content)
            status = "✓" if not expected or result == expected else "✗"
            if expected and result != expected:
                failed += 1
                status_str = f"{status} {result} (expected {expected})"
            else:
                passed += 1
                status_str = f"{status} {result}" + (f" (expected {expected})" if expected else "")
            print(f"  {f.name:40s} {status_str}")
        except Exception as e:
            errors += 1
            print(f"  {f.name:40s} ERROR: {e}")

    print("-" * 60)
    print(f"Passed: {passed}, Failed: {failed}, Errors: {errors}")
    return failed + errors


def _extract_expected(content: str) -> str | None:
    """Try to extract expected result from file comments.

    Looks for lines starting with '; expected:' or '; expected:'.
    Returns the first match found.
    """
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith(";") and "expected:" in line.lower():
            for result in ("unsat", "sat", "unknown"):
                if result in line.lower():
                    return result
    return None


def main(argv: List[str] | None = None) -> int:
    """Main CLI entry point.

    Returns 0 on success, 1 on error or mismatch.
    """
    parser = argparse.ArgumentParser(
        prog="smt-solver",
        description="DPLL(T) SMT solver with EUF, LRA, and String theories",
    )
    parser.add_argument("file", nargs="?", help="SMT-LIB input file")
    parser.add_argument("--version", action="version", version=f"smt-solver {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--model", action="store_true", help="Print model when sat")
    parser.add_argument("-s", "--stats", action="store_true", help="Print solver statistics")
    parser.add_argument("-e", "--expr", help="Assert a single expression")
    parser.add_argument(
        "--check", choices=["sat", "unsat", "unknown"],
        help="Expected result (for testing)",
    )
    parser.add_argument("--logic", help="Set the SMT logic (e.g. LRA, QF_UF)")
    parser.add_argument("--config", help="Load configuration from JSON file")
    parser.add_argument("--batch", help="Run all .smt2 files in a directory")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")

    # Load config if specified
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config = json.loads(config_path.read_text())
            if "logic" in config and not args.logic:
                args.logic = config["logic"]
            if "verbose" in config and not args.verbose:
                args.verbose = config["verbose"]

    # Batch mode
    if args.batch:
        return run_batch(args.batch, show_stats=args.stats, verbose=args.verbose)

    if args.expr:
        solver = Solver(logic=args.logic)
        text = f"(declare-const x Real) (assert {args.expr})"
        solver.parse_and_assert(text)
        result = solver.check()
        print(result)
        if args.stats:
            print(solver.stats)
        if args.check:
            if result != args.check:
                print(f"EXPECTED: {args.check}", file=sys.stderr)
                return 1
        return 0

    if args.file:
        result, solver = run_file(
            args.file,
            print_model=args.model,
            verbose=args.verbose,
            show_stats=args.stats,
            logic=args.logic,
        )
        if args.check:
            if result != args.check:
                print(f"EXPECTED: {args.check}", file=sys.stderr)
                return 1
        return 0

    # No file — read from stdin
    content = sys.stdin.read()
    if content.strip():
        solver = Solver(logic=args.logic)
        solver.parse_and_assert(content)
        result = solver.check()
        print(result)
        if result == "sat" and args.model:
            model = solver.get_model()
            if model:
                print("(:model")
                print(model.to_smt())
                print(")")
        if args.stats:
            print(solver.stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())