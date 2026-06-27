"""Sensitivity / post-optimality analysis for solved LPs.

Given an optimal :class:`LPResult`, :func:`analyse` computes:

* **Objective coefficient ranges** — for each structural variable, the
  interval of objective-coefficient values over which the current basis
  remains optimal (recompute reduced costs and find where they hit zero).
* **Right-hand-side ranges** — for each constraint, the interval of rhs
  values over which the current basis remains feasible (shadow price
  unchanged), computed via the basis inverse.

This is *approximate*: we re-solve a sequence of perturbed LPs and detect the
first basis change by comparing the returned basis.  Exact ranges would
require direct tableau access; this keeps the module decoupled.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .problem import LPProblem, LPResult, LPStatus
from .simplex import SimplexSolver

__all__ = ["SensitivityReport", "analyse"]


@dataclass
class SensitivityReport:
    """Sensitivity analysis result."""

    obj_coeff_ranges: dict[str, tuple[float, float]] = None
    rhs_ranges: dict[str, tuple[float, float]] = None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SensitivityReport(obj_ranges={self.obj_coeff_ranges}, "
            f"rhs_ranges={self.rhs_ranges})"
        )


def analyse(problem: LPProblem, result: LPResult, solver: SimplexSolver | None = None) -> SensitivityReport:
    """Compute sensitivity ranges by perturbation."""
    solver = solver or SimplexSolver()
    # Objective coefficient ranges: perturb each coefficient by ±δ.
    obj_ranges: dict[str, tuple[float, float]] = {}
    for v in problem.variables:
        c0 = problem.objective_coeffs.get(v, Fraction(0))
        base_basis = tuple(result.basis)
        # search downward (decrease c)
        lo = None
        step = Fraction(1)
        cur = c0
        for _ in range(200):
            cur -= step
            p2 = _clone_with_coeff(problem, v, cur)
            r = solver.solve(p2)
            if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
                lo = float(cur)
                step *= 2  # accelerate
            else:
                # binary-search refine between cur+step and cur
                lo = _bisect_basis_change(solver, problem, v, c0, -1, base_basis)
                break
        if lo is None:
            lo = float("-inf")
        # search upward
        hi = None
        step = Fraction(1)
        cur = c0
        for _ in range(200):
            cur += step
            p2 = _clone_with_coeff(problem, v, cur)
            r = solver.solve(p2)
            if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
                hi = float(cur)
                step *= 2
            else:
                hi = _bisect_basis_change(solver, problem, v, c0, +1, base_basis)
                break
        if hi is None:
            hi = float("inf")
        obj_ranges[v] = (lo, hi)
    # RHS ranges.
    rhs_ranges: dict[str, tuple[float, float]] = {}
    for i, con in enumerate(problem.constraints):
        cname = con.get("name", f"c{i}")
        b0 = Fraction(con["rhs"])
        base_basis = tuple(result.basis)
        lo = None
        step = Fraction(1)
        cur = b0
        for _ in range(200):
            cur -= step
            p2 = _clone_with_rhs(problem, i, cur)
            r = solver.solve(p2)
            if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
                lo = float(cur)
                step *= 2
            else:
                lo = _bisect_rhs_change(solver, problem, i, b0, -1, base_basis)
                break
        if lo is None:
            lo = float("-inf")
        hi = None
        step = Fraction(1)
        cur = b0
        for _ in range(200):
            cur += step
            p2 = _clone_with_rhs(problem, i, cur)
            r = solver.solve(p2)
            if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
                hi = float(cur)
                step *= 2
            else:
                hi = _bisect_rhs_change(solver, problem, i, b0, +1, base_basis)
                break
        if hi is None:
            hi = float("inf")
        rhs_ranges[cname] = (lo, hi)
    return SensitivityReport(obj_coeff_ranges=obj_ranges, rhs_ranges=rhs_ranges)


def _clone_with_coeff(p: LPProblem, v: str, c: Fraction) -> LPProblem:
    import copy
    q = copy.deepcopy(p)
    q.objective_coeffs[v] = c
    return q


def _clone_with_rhs(p: LPProblem, idx: int, b: Fraction) -> LPProblem:
    import copy
    q = copy.deepcopy(p)
    q.constraints[idx]["rhs"] = b
    return q


def _bisect_basis_change(solver: SimplexSolver, p: LPProblem, v: str,
                         c0: Fraction, direction: int, base_basis: tuple) -> float:
    """Binary-search for the coefficient of v at which the basis changes."""
    lo, hi = Fraction(0), Fraction(1)
    # expand hi until basis changes
    for _ in range(60):
        c = c0 + direction * hi
        p2 = _clone_with_coeff(p, v, c)
        r = solver.solve(p2)
        if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
            lo = hi
            hi *= 2
        else:
            break
    # bisection between c0+dir*lo and c0+dir*hi
    a, b = lo, hi
    for _ in range(60):
        mid = (a + b) / 2
        c = c0 + direction * mid
        p2 = _clone_with_coeff(p, v, c)
        r = solver.solve(p2)
        if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
            a = mid
        else:
            b = mid
    return float(c0 + direction * a)


def _bisect_rhs_change(solver: SimplexSolver, p: LPProblem, idx: int,
                       b0: Fraction, direction: int, base_basis: tuple) -> float:
    lo, hi = Fraction(0), Fraction(1)
    for _ in range(60):
        b = b0 + direction * hi
        p2 = _clone_with_rhs(p, idx, b)
        r = solver.solve(p2)
        if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
            lo = hi
            hi *= 2
        else:
            break
    a, b = lo, hi
    for _ in range(60):
        mid = (a + b) / 2
        bb = b0 + direction * mid
        p2 = _clone_with_rhs(p, idx, bb)
        r = solver.solve(p2)
        if r.status is LPStatus.OPTIMAL and tuple(r.basis) == base_basis:
            a = mid
        else:
            b = mid
    return float(b0 + direction * a)