"""
Command-line interface for the CDCL SAT Solver.

Provides a comprehensive CLI with subcommands for solving, generating,
validating, and counting SAT instances.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from cdcl_sat.solver import Solver
from cdcl_sat.config import SolverConfig
from cdcl_sat.generator import (
    generate_php,
    generate_random_cnf,
    generate_chain,
    generate_tseitin,
    generate_mutilated_chessboard,
    generate_graph_coloring,
    write_dimacs,
)
from cdcl_sat.utils import read_dimacs_file, write_dimacs_model, validate_dimacs, count_satisfying_assignments


def cmd_solve(args):
    """Solve a DIMACS CNF file."""
    config = SolverConfig()

    # Load config file if specified
    if args.config:
        config = SolverConfig.from_json(args.config)
        print(f"c Loaded config from {args.config}")

    # Override with CLI arguments
    if args.restart:
        config.restart_strategy = args.restart
    if args.timeout:
        config.time_limit = args.timeout
    config.verbose = args.verbose
    config.preprocess = args.preprocess
    if args.proof:
        config.proof_file = args.proof
    if args.output:
        config.model_file = args.output

    print(f"c CDCL SAT Solver v2.0.0")
    print(f"c Reading {args.input}...")
    solver = Solver.from_file(args.input)
    config.apply_to_solver(solver)

    print(f"c Variables: {solver.num_vars}")
    print(f"c Clauses: {len(solver.clauses)}")

    if args.preprocess:
        print("c Preprocessing...")
        ok = solver.preprocess()
        print(f"c After preprocessing: {solver.num_vars} vars, {len(solver.clauses)} clauses, ok={ok}")

    start_time = time.time()
    result = solver.solve(time_limit=config.time_limit)
    elapsed = time.time() - start_time

    if config.verbose >= 1:
        print(f"c {solver.stats}")

    if result is True:
        print("s SATISFIABLE")
        model = solver.get_model()
        # Print model
        line = "v "
        for lit in sorted(model, key=lambda x: abs(x)):
            line += str(lit) + " "
            if len(line) > 70:
                print(line.rstrip())
                line = "v "
        if line.strip() != "v":
            print(line.rstrip() + " 0")
        if args.output:
            write_dimacs_model(model, solver.num_vars, args.output)
            print(f"c Model written to {args.output}")
    elif result is False:
        print("s UNSATISFIABLE")
    else:
        print("s UNKNOWN")
        print("c Time limit reached")

    solver.close_proof()
    print(f"c Elapsed time: {elapsed:.3f}s")

    # Output stats as JSON if requested
    if args.stats_json:
        stats = solver.get_stats().summary()
        stats["result"] = "SAT" if result is True else ("UNSAT" if result is False else "UNKNOWN")
        stats["num_vars"] = solver.num_vars
        stats["num_clauses"] = len(solver.clauses)
        stats["elapsed_seconds"] = round(elapsed, 4)
        with open(args.stats_json, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"c Stats written to {args.stats_json}")


def cmd_generate(args):
    """Generate a CNF instance."""
    if args.type == "php":
        num_vars, clauses = generate_php(args.n, args.m)
    elif args.type == "random":
        num_vars, clauses = generate_random_cnf(args.vars, args.clauses, args.k, args.seed)
    elif args.type == "chain":
        num_vars, clauses = generate_chain(args.vars)
    elif args.type == "tseitin":
        num_vars, clauses = generate_tseitin(args.vars)
    elif args.type == "chessboard":
        num_vars, clauses = generate_mutilated_chessboard(args.n)
    elif args.type == "coloring":
        num_vars, clauses = generate_graph_coloring(
            args.nodes, args.colors, args.edge_prob, args.seed
        )
    else:
        print(f"Unknown type: {args.type}", file=sys.stderr)
        sys.exit(1)

    content = write_dimacs(num_vars, clauses, args.output)
    if args.output:
        print(f"c Generated {args.type}: {num_vars} vars, {len(clauses)} clauses → {args.output}", file=sys.stderr)
    else:
        print(content)


def cmd_validate(args):
    """Validate a DIMACS CNF file."""
    with open(args.input, "r") as f:
        text = f.read()

    issues = validate_dimacs(text)
    if issues:
        print(f"Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("No issues found. DIMACS file is valid.")


def cmd_count(args):
    """Count satisfying assignments (brute force, small instances only)."""
    solver = Solver.from_file(args.input)

    # Extract clauses as lists
    clauses = [clause.lits for clause in solver.clauses]

    print(f"c Counting satisfying assignments for {solver.num_vars} variables...")
    if solver.num_vars > 20:
        print("c Warning: Instance has > 20 variables. Brute force may be slow.")
        if not args.force:
            print("c Use --force to proceed anyway.")
            sys.exit(1)

    count = count_satisfying_assignments(solver.num_vars, clauses, max_count=args.max)
    if count >= args.max:
        print(f"s AT LEAST {args.max} solutions")
    else:
        print(f"s EXACTLY {count} solutions")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="cdcl-sat",
        description="CDCL SAT Solver — Conflict-Driven Clause Learning with VSIDS and Restarts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve a DIMACS file
  cdcl-sat solve problem.cnf

  # Solve with preprocessing and stats
  cdcl-sat solve problem.cnf --preprocess -v 1

  # Generate a pigeonhole instance
  cdcl-sat generate --type php --n 4 --m 3 -o php_4_3.cnf

  # Validate a DIMACS file
  cdcl-sat validate problem.cnf

  # Count solutions (small instances)
  cdcl-sat count problem.cnf
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Solve subcommand
    solve_parser = subparsers.add_parser("solve", help="Solve a DIMACS CNF file")
    solve_parser.add_argument("input", help="DIMACS CNF input file")
    solve_parser.add_argument("-t", "--timeout", type=float, default=0,
                              help="Time limit in seconds (0 = unlimited)")
    solve_parser.add_argument("-v", "--verbose", type=int, default=0,
                              help="Verbosity level (0=silent, 1=stats, 2=trace)")
    solve_parser.add_argument("-p", "--proof", type=str, default=None,
                              help="Write DRAT proof to file")
    solve_parser.add_argument("-o", "--output", type=str, default=None,
                              help="Write model to file (if SAT)")
    solve_parser.add_argument("-r", "--restart", type=str, default=None,
                              choices=["luby", "geometric"],
                              help="Restart strategy")
    solve_parser.add_argument("--preprocess", action="store_true",
                              help="Run preprocessing before solving")
    solve_parser.add_argument("--config", type=str, default=None,
                              help="Load solver config from JSON file")
    solve_parser.add_argument("--stats-json", type=str, default=None,
                              help="Write statistics to JSON file")
    solve_parser.set_defaults(func=cmd_solve)

    # Generate subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate CNF benchmark instances")
    gen_parser.add_argument("--type", choices=["php", "random", "chain", "tseitin", "chessboard", "coloring"],
                            required=True, help="Type of instance to generate")
    gen_parser.add_argument("-o", "--output", type=str, default=None,
                            help="Output file (default: stdout)")
    gen_parser.add_argument("--n", type=int, default=4, help="Number of pigeons (PHP) or board size")
    gen_parser.add_argument("--m", type=int, default=3, help="Number of holes (PHP)")
    gen_parser.add_argument("--vars", type=int, default=50, help="Number of variables (random/chain/tseitin)")
    gen_parser.add_argument("--clauses", type=int, default=200, help="Number of clauses (random)")
    gen_parser.add_argument("--k", type=int, default=3, help="Clause length (random)")
    gen_parser.add_argument("--seed", type=int, default=None, help="Random seed")
    gen_parser.add_argument("--nodes", type=int, default=10, help="Number of nodes (coloring)")
    gen_parser.add_argument("--colors", type=int, default=3, help="Number of colors (coloring)")
    gen_parser.add_argument("--edge-prob", type=float, default=0.5, help="Edge probability (coloring)")
    gen_parser.set_defaults(func=cmd_generate)

    # Validate subcommand
    val_parser = subparsers.add_parser("validate", help="Validate a DIMACS CNF file")
    val_parser.add_argument("input", help="DIMACS CNF input file")
    val_parser.set_defaults(func=cmd_validate)

    # Count subcommand
    count_parser = subparsers.add_parser("count", help="Count satisfying assignments (brute force)")
    count_parser.add_argument("input", help="DIMACS CNF input file")
    count_parser.add_argument("--max", type=int, default=65536,
                               help="Maximum count before stopping")
    count_parser.add_argument("--force", action="store_true",
                              help="Force counting even for > 20 variables")
    count_parser.set_defaults(func=cmd_count)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)