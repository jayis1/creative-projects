"""Command-line interface for simplex-solver.

Subcommands
-----------
solve        Solve an LP/MILP given as Python expression or MPS file.
sensitivity  Run post-optimality sensitivity analysis.
mps-info     Inspect an MPS file.
version      Print version.

The ``solve`` subcommand accepts a JSON problem spec or an MPS file (detected
by extension).  JSON specs use the schema::

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

Run with ``--pretty`` for a human-readable summary including duals.
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from typing import Any

from .problem import LPProblem, LPResult, LPStatus
from .simplex import SimplexSolver
from .integer import MILPSolver
from .mps import read_mps, write_mps
from .sensitivity import analyse

__all__ = ["main"]


def _build_problem_from_json(spec: dict) -> LPProblem:
    """Construct an :class:`LPProblem` from a JSON-style dict."""
    def _frac(v: Any) -> Fraction:
        if v is None:
            return None
        return Fraction(v)
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


def _format_result(res: LPResult, problem: LPProblem, pretty: bool) -> str:
    if pretty:
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
    else:
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


def _cmd_mps_info(args: argparse.Namespace) -> int:
    problem = read_mps(args.input)
    print(f"Name: {problem.name}")
    print(f"Objective: {problem.objective}")
    print(f"Variables ({len(problem.variables)}): {', '.join(problem.variables)}")
    print(f"Constraints: {len(problem.constraints)}")
    if problem.integer:
        print(f"Integer variables: {', '.join(sorted(problem.integer))}")
    return 0


def _cmd_version(_: argparse.Namespace) -> int:
    from . import __version__
    print(f"simplex-solver {__version__}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate a problem file and report any issues."""
    if args.input.endswith(".mps") or args.input.endswith(".mps.gz"):
        problem = read_mps(args.input)
    else:
        with open(args.input) as fh:
            spec = json.load(fh)
        problem = _build_problem_from_json(spec)
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


def _cmd_solve(args: argparse.Namespace) -> int:
    if args.input.endswith(".mps") or args.input.endswith(".mps.gz"):
        problem = read_mps(args.input)
    else:
        with open(args.input) as fh:
            spec = json.load(fh)
        problem = _build_problem_from_json(spec)
    # Validate before solving to catch issues early.
    errors = problem.validate()
    if errors and not args.force:
        print("Problem validation errors (use --force to solve anyway):")
        for e in errors:
            print(f"  - {e}")
        return 1
    if problem.is_integer() or args.milp:
        res = MILPSolver(max_nodes=args.max_nodes, max_iter=args.max_iter).solve(problem)
    else:
        res = SimplexSolver(max_iter=args.max_iter, bland=not args.dantzig).solve(problem)
    print(_format_result(res, problem, args.pretty))
    if args.sensitivity and res.status is LPStatus.OPTIMAL:
        rep = analyse(problem, res)
        print("\nSensitivity Analysis:")
        print("Objective coefficient ranges:")
        for v, (lo, hi) in rep.obj_coeff_ranges.items():
            print(f"  {v}: [{lo:.6g}, {hi:.6g}]")
        print("RHS ranges:")
        for c, (lo, hi) in rep.rhs_ranges.items():
            print(f"  {c}: [{lo:.6g}, {hi:.6g}]")
    return 0 if res.status is LPStatus.OPTIMAL else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="simplex-solver",
        description="Exact linear & integer programming via the Simplex method.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_solve = sub.add_parser("solve", help="Solve an LP/MILP from JSON or MPS.")
    p_solve.add_argument("input", help="Path to .json or .mps file")
    p_solve.add_argument("--milp", action="store_true", help="Force MILP (branch-and-bound).")
    p_solve.add_argument("--pretty", action="store_true", help="Human-readable output.")
    p_solve.add_argument("--sensitivity", action="store_true", help="Run sensitivity analysis.")
    p_solve.add_argument("--dantzig", action="store_true", help="Use Dantzig's rule (most positive rc).")
    p_solve.add_argument("--force", action="store_true", help="Solve even if validation fails.")
    p_solve.add_argument("--max-nodes", type=int, default=10000)
    p_solve.add_argument("--max-iter", type=int, default=10000)
    p_solve.set_defaults(func=_cmd_solve)

    p_info = sub.add_parser("mps-info", help="Inspect an MPS file.")
    p_info.add_argument("input", help="Path to .mps file")
    p_info.set_defaults(func=_cmd_mps_info)

    p_val = sub.add_parser("validate", help="Validate a problem file.")
    p_val.add_argument("input", help="Path to .json or .mps file")
    p_val.set_defaults(func=_cmd_validate)

    p_ver = sub.add_parser("version", help="Print version.")
    p_ver.set_defaults(func=_cmd_version)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())