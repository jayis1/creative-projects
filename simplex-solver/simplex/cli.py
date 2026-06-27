"""Command-line interface for simplex-solver.

Subcommands
-----------
solve        Solve an LP/MILP given as a Python expression or MPS/LP file.
sensitivity  Run post-optimality sensitivity analysis.
mps-info     Inspect an MPS file.
convert      Convert between problem formats (JSON ↔ MPS ↔ LP).
batch        Solve multiple problem files in one invocation.
config       Display or initialise a solver configuration file.
validate     Validate a problem file and report issues.
version      Print version.

The ``solve`` subcommand accepts a JSON problem spec, an MPS file, or an
LP file (detected by extension).  JSON specs use the schema::

    {
      "name": "diet",
      "objective": "min",
      "variables": ["x", "y"],
      "objective_coeffs": {"x": 2, "y": 3},
      "constraints": [
        {"coeffs": {"x": 1, "y": 1}, "relation": ">=", "rhs": 10, "name": "c0"}
      ],
      "bounds": {"x": [0, null]},
      "integer": []
    }

Run with ``--pretty`` for a human-readable summary including duals,
``--table`` for a boxed table report, or ``--json`` (default) for JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from fractions import Fraction
from typing import Any

from .problem import LPProblem, LPResult, LPStatus
from .simplex import SimplexSolver
from .integer import MILPSolver, SearchStrategy
from .mps import read_mps, write_mps
from .formatting import read_lp, write_lp, format_result, format_tableau
from .sensitivity import analyse
from .config import SolverConfig, load_config, save_config, DEFAULT_CONFIG_PATH
from .logging_utils import configure_logging

__all__ = ["main"]

logger = logging.getLogger("simplex.cli")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _build_problem_from_json(spec: dict) -> LPProblem:
    """Construct an :class:`LPProblem` from a JSON-style dict."""
    objective = spec.get("objective", "max")
    variables = tuple(spec["variables"])
    obj_coeffs = {k: Fraction(v) for k, v in spec.get("objective_coeffs", {}).items()}
    constraints = []
    for c in spec.get("constraints", []):
        constraints.append({
            "coeffs": {k: Fraction(v) for k, v in c["coeffs"].items()},
            "relation": c["relation"],
            "rhs": Fraction(c["rhs"]),
            "name": c.get("name"),
        })
    bounds = {}
    for v, (lo, hi) in spec.get("bounds", {}).items():
        lo = None if lo is None else Fraction(lo)
        hi = None if hi is None else Fraction(hi)
        bounds[v] = (lo, hi)
    integer = set(spec.get("integer", []))
    return LPProblem(
        name=spec.get("name", "lp"),
        objective=objective,
        variables=variables,
        objective_coeffs=obj_coeffs,
        constraints=constraints,
        bounds=bounds,
        integer=integer,
    )


def _problem_to_json(problem: LPProblem) -> dict:
    return {
        "name": problem.name,
        "objective": problem.objective,
        "variables": list(problem.variables),
        "objective_coeffs": {k: str(v) for k, v in problem.objective_coeffs.items()},
        "constraints": [
            {
                "coeffs": {k: str(v) for k, v in c["coeffs"].items()},
                "relation": c["relation"],
                "rhs": str(c["rhs"]),
                "name": c.get("name"),
            }
            for c in problem.constraints
        ],
        "bounds": {k: (str(lo) if lo is not None else None,
                       str(hi) if hi is not None else None)
                   for k, (lo, hi) in problem.bounds.items()},
        "integer": sorted(problem.integer),
    }


def _load_problem(path: str) -> LPProblem:
    """Load a problem from JSON, MPS, or LP file based on extension."""
    if path.endswith((".mps", ".mps.gz")):
        return read_mps(path)
    if path.endswith((".lp", ".lp.gz")):
        return read_lp(path)
    with open(path) as fh:
        spec = json.load(fh)
    return _build_problem_from_json(spec)


def _format_result(res: LPResult, problem: LPProblem, fmt: str) -> str:
    """Format a solve result in the requested output format."""
    if fmt == "table":
        return format_result(res, problem)
    if fmt == "text" or fmt == "pretty":
        lines = []
        lines.append(f"Status: {res.status.value}")
        if res.status is LPStatus.OPTIMAL:
            lines.append(f"Objective ({problem.objective}): {res.objective_value:.6g}")
            lines.append("Solution:")
            for v in problem.variables:
                lines.append(f"  {v} = {res.solution.get(v, 0):.6g}")
            if res.duals:
                lines.append("Duals (shadow prices):")
                for cname, val in res.duals.items():
                    lines.append(f"  {cname} = {val:.6g}")
            if res.reduced_costs:
                lines.append("Reduced costs:")
                for v in problem.variables:
                    rc = res.reduced_costs.get(v, 0)
                    lines.append(f"  {v} = {rc:.6g}")
            if res.basis:
                lines.append(f"Basis: {', '.join(res.basis)}")
            if res.message:
                lines.append(f"Note: {res.message}")
        else:
            lines.append(f"Message: {res.message}")
        return "\n".join(lines)
    # Default: JSON.
    out = {
        "status": res.status.value,
        "objective_value": res.objective_value,
        "solution": res.solution,
        "duals": res.duals,
        "reduced_costs": res.reduced_costs,
        "iterations": res.iterations,
        "basis": res.basis,
        "message": res.message,
    }
    return json.dumps(out, indent=2, default=str)


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def _cmd_mps_info(args: argparse.Namespace) -> int:
    problem = read_mps(args.input)
    print(f"Name: {problem.name}")
    print(f"Objective: {problem.objective}")
    print(f"Variables ({len(problem.variables)}): {', '.join(problem.variables)}")
    print(f"Constraints: {len(problem.constraints)}")
    for i, c in enumerate(problem.constraints):
        cname = c.get("name", f"c{i}")
        terms = " + ".join(f"{c['coeffs'].get(v, 0)}*{v}" for v in problem.variables if c["coeffs"].get(v, 0))
        print(f"  {cname}: {terms} {c['relation']} {c['rhs']}")
    if problem.integer:
        print(f"Integer variables: {', '.join(sorted(problem.integer))}")
    if problem.bounds:
        print("Bounds:")
        for v in problem.variables:
            lo, hi = problem.bounds.get(v, (Fraction(0), None))
            print(f"  {v}: [{lo}, {hi}]")
    return 0


def _cmd_version(_: argparse.Namespace) -> int:
    from . import __version__
    print(f"simplex-solver {__version__}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate a problem file and report any issues."""
    problem = _load_problem(args.input)
    errors = problem.validate()
    if not errors:
        print(f"OK: {problem.name} — {problem.num_vars()} variables, "
              f"{problem.num_constraints()} constraints")
        if problem.integer:
            print(f"  Integer variables: {', '.join(sorted(problem.integer))}")
        return 0
    print(f"INVALID: {len(errors)} error(s)")
    for e in errors:
        print(f"  - {e}")
    return 1


def _cmd_solve(args: argparse.Namespace, cfg: SolverConfig) -> int:
    """Solve a problem from a file."""
    problem = _load_problem(args.input)
    # Validate before solving to catch issues early.
    errors = problem.validate()
    if errors and not args.force:
        print("Problem validation errors (use --force to solve anyway):")
        for e in errors:
            print(f"  - {e}")
        return 1
    # Determine output format: CLI flag overrides config.
    fmt = args.output_format or cfg.output_format
    if args.pretty:
        fmt = "text"
    if args.table:
        fmt = "table"
    if args.json:
        fmt = "json"
    max_iter = args.max_iter or cfg.max_iter
    max_nodes = args.max_nodes or cfg.max_nodes
    bland = args.bland if args.bland is not None else cfg.bland
    do_sensitivity = args.sensitivity or cfg.sensitivity

    if problem.is_integer() or args.milp:
        strategy = args.strategy or cfg.extra.get("strategy", "best-first")
        res = MILPSolver(
            max_nodes=max_nodes, max_iter=max_iter, bland=bland,
            use_cuts=cfg.use_cuts, eps=cfg.eps, strategy=strategy,
            time_limit=args.time_limit, verbose=args.verbose,
        ).solve(problem)
    else:
        res = SimplexSolver(max_iter=max_iter, bland=bland).solve(problem)
    print(_format_result(res, problem, fmt))
    if do_sensitivity and res.status is LPStatus.OPTIMAL:
        rep = analyse(problem, res)
        print("\nSensitivity Analysis:")
        print("Objective coefficient ranges:")
        for v, (lo, hi) in rep.obj_coeff_ranges.items():
            print(f"  {v}: [{lo:.6g}, {hi:.6g}]")
        print("RHS ranges:")
        for c, (lo, hi) in rep.rhs_ranges.items():
            print(f"  {c}: [{lo:.6g}, {hi:.6g}]")
    return 0 if res.status is LPStatus.OPTIMAL else 1


def _cmd_convert(args: argparse.Namespace) -> int:
    """Convert between problem file formats."""
    problem = _load_problem(args.input)
    out_format = args.to_format or _detect_format(args.output)
    if out_format == "mps":
        write_mps(problem, args.output)
    elif out_format == "lp":
        write_lp(problem, args.output)
    elif out_format == "json":
        with open(args.output, "w") as fh:
            json.dump(_problem_to_json(problem), fh, indent=2, default=str)
    else:
        print(f"Unknown output format: {out_format}")
        return 1
    print(f"Converted {args.input} → {args.output} ({out_format})")
    return 0


def _detect_format(path: str) -> str:
    if path.endswith((".mps", ".mps.gz")):
        return "mps"
    if path.endswith((".lp", ".lp.gz")):
        return "lp"
    return "json"


def _cmd_batch(args: argparse.Namespace, cfg: SolverConfig) -> int:
    """Solve multiple problem files and print a summary."""
    import glob
    files: list[str] = []
    for pattern in args.inputs:
        files.extend(sorted(glob.glob(pattern)))
    if not files:
        print("No matching files found.")
        return 1
    results_summary = []
    overall_ok = True
    for f in files:
        try:
            problem = _load_problem(f)
            if problem.is_integer():
                res = MILPSolver(
                    max_nodes=args.max_nodes or cfg.max_nodes,
                    max_iter=args.max_iter or cfg.max_iter,
                    bland=cfg.bland,
                ).solve(problem)
            else:
                res = SimplexSolver(
                    max_iter=args.max_iter or cfg.max_iter,
                    bland=cfg.bland,
                ).solve(problem)
            status_str = res.status.value
            obj = res.objective_value if res.objective_value is not None else "—"
            results_summary.append((f, status_str, obj))
            if res.status is not LPStatus.OPTIMAL:
                overall_ok = False
        except Exception as exc:
            results_summary.append((f, "error", str(exc)))
            overall_ok = False
    # Print summary table.
    print(f"{'File':<40s} {'Status':<12s} {'Objective':<20s}")
    print("-" * 72)
    for fname, status, obj in results_summary:
        print(f"{fname:<40s} {status:<12s} {str(obj):<20s}")
    return 0 if overall_ok else 1


def _cmd_config(args: argparse.Namespace) -> int:
    """Display or initialise a solver configuration file."""
    if args.init:
        path = args.path or str(DEFAULT_CONFIG_PATH)
        cfg = SolverConfig()
        if args.set:
            for key_val in args.set:
                if "=" not in key_val:
                    print(f"Invalid --set value: {key_val!r} (use key=value)")
                    return 1
                key, val = key_val.split("=", 1)
                # Try to parse as JSON, fall back to string.
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    pass
                if hasattr(cfg, key):
                    setattr(cfg, key, val)
                else:
                    cfg.extra[key] = val
        save_config(cfg, path)
        print(f"Configuration written to {path}")
        return 0
    # Display current config.
    cfg = load_config(args.path)
    print(json.dumps(cfg.to_dict(), indent=2, default=str))
    return 0


# --------------------------------------------------------------------------- #
# main entry point
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="simplex-solver",
        description="Exact linear & integer programming via the Simplex method.",
    )
    parser.add_argument("--config", "-c", help="Path to config file (JSON/TOML/YAML).")
    parser.add_argument("--log-level", default=None,
                        help="Logging level (DEBUG/INFO/WARNING/ERROR).")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable INFO-level logging.")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress all output except errors.")
    sub = parser.add_subparsers(dest="command", required=True)

    # solve
    p_solve = sub.add_parser("solve", help="Solve an LP/MILP from JSON, MPS, or LP.")
    p_solve.add_argument("input", help="Path to .json, .mps, or .lp file")
    p_solve.add_argument("--milp", action="store_true", help="Force MILP (branch-and-bound).")
    p_solve.add_argument("--pretty", action="store_true", help="Human-readable output.")
    p_solve.add_argument("--table", action="store_true", help="Boxed table output.")
    p_solve.add_argument("--json", action="store_true", help="JSON output (default).")
    p_solve.add_argument("--output-format", choices=["json", "text", "table"],
                         default=None, help="Output format (overrides config).")
    p_solve.add_argument("--sensitivity", action="store_true", help="Run sensitivity analysis.")
    p_solve.add_argument("--dantzig", action="store_true", help="Use Dantzig's rule (most positive rc).")
    p_solve.add_argument("--bland", action="store_true", default=None,
                         help="Use Bland's rule (default).")
    p_solve.add_argument("--force", action="store_true", help="Solve even if validation fails.")
    p_solve.add_argument("--max-nodes", type=int, default=None)
    p_solve.add_argument("--max-iter", type=int, default=None)
    p_solve.add_argument("--strategy", choices=["best-first", "depth-first", "breadth-first"],
                         default=None, help="MILP search strategy.")
    p_solve.add_argument("--time-limit", type=float, default=None,
                         help="Wall-clock time limit in seconds (MILP).")
    p_solve.add_argument("--verbose", action="store_true", help="Verbose MILP logging.")
    p_solve.set_defaults(func=_cmd_solve)

    # convert
    p_conv = sub.add_parser("convert", help="Convert between problem formats.")
    p_conv.add_argument("input", help="Input file (.json/.mps/.lp)")
    p_conv.add_argument("output", help="Output file (.json/.mps/.lp)")
    p_conv.add_argument("--to", dest="to_format", choices=["json", "mps", "lp"],
                        default=None, help="Output format (auto-detected from extension).")
    p_conv.set_defaults(func=_cmd_convert)

    # batch
    p_batch = sub.add_parser("batch", help="Solve multiple problem files.")
    p_batch.add_argument("inputs", nargs="+", help="File patterns to solve.")
    p_batch.add_argument("--max-nodes", type=int, default=None)
    p_batch.add_argument("--max-iter", type=int, default=None)
    p_batch.set_defaults(func=_cmd_batch)

    # config
    p_cfg = sub.add_parser("config", help="Display or initialise solver configuration.")
    p_cfg.add_argument("--init", action="store_true", help="Write a default config file.")
    p_cfg.add_argument("--path", default=None, help="Config file path.")
    p_cfg.add_argument("--set", action="append", help="Set a config key (key=value).")
    p_cfg.set_defaults(func=_cmd_config)

    # mps-info
    p_info = sub.add_parser("mps-info", help="Inspect an MPS file.")
    p_info.add_argument("input", help="Path to .mps file")
    p_info.set_defaults(func=_cmd_mps_info)

    # validate
    p_val = sub.add_parser("validate", help="Validate a problem file.")
    p_val.add_argument("input", help="Path to .json, .mps, or .lp file")
    p_val.set_defaults(func=_cmd_validate)

    # version
    p_ver = sub.add_parser("version", help="Print version.")
    p_ver.set_defaults(func=_cmd_version)

    args = parser.parse_args(argv)

    # Configure logging.
    log_level = "WARNING"
    if args.quiet:
        log_level = "ERROR"
    elif args.verbose or getattr(args, "verbose", False):
        log_level = "INFO"
    if args.log_level:
        log_level = args.log_level
    configure_logging(log_level)

    # Load config.
    cfg = load_config(args.config)
    if args.log_level:
        cfg.log_level = args.log_level

    # Dispatch.
    func = args.func
    import inspect
    sig = inspect.signature(func)
    if "cfg" in sig.parameters:
        return func(args, cfg)
    return func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())