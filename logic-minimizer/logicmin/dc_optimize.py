"""
Don't-care assignment optimization.

After two-level minimization, the don't-care set can be *assigned* to either
the on-set or the off-set to minimize the resulting cover cost.  This module
provides:

* ``assign_dontcares(func)`` — greedily assign each don't-care to minimize
  the final cover cost (tries both assignments and picks the better one).
* ``minimize_with_dc_optimization(func, minimizer='qm')`` — run QM or
  Espresso with optimized don't-care assignment.
* ``DCAssignmentResult`` — result dataclass with the assigned function,
  original cost, optimized cost, and the assignment map.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from .boolean import BooleanFunction, cube_covers
from .quine_mccluskey import QuineMcCluskey, MinimizationResult
from .espresso import Espresso


@dataclass
class DCAssignmentResult:
    """Result of don't-care assignment optimization."""

    original_func: BooleanFunction
    assigned_func: BooleanFunction
    assignment: Dict[int, int]  # dc minterm → 0 or 1
    original_cost: int
    optimized_cost: int
    original_sop: str
    optimized_sop: str
    improvement: int

    def __repr__(self) -> str:
        return (
            f"DCAssignmentResult(original_cost={self.original_cost}, "
            f"optimized_cost={self.optimized_cost}, "
            f"improvement={self.improvement})"
        )


def assign_dontcares(
    func: BooleanFunction,
    minimizer: str = "qm",
) -> DCAssignmentResult:
    """Optimize don't-care assignment to minimize cover cost.

    For each don't-care minterm, try assigning it to the on-set or off-set
    and measure the resulting minimization cost.  Use a greedy approach:

    1. Run minimization on the original function (DC as DC).
    2. For each DC minterm, try adding it to the on-set and measure the cost
       change.
    3. Assign DCs to whichever set reduces the cost most.

    Parameters
    ----------
    func : BooleanFunction
        The function with don't-cares to optimize.
    minimizer : str
        "qm" for Quine–McCluskey (exact), "espresso" for heuristic.

    Returns
    -------
    DCAssignmentResult
    """
    if not func.dontcare:
        # No don't-cares to assign
        result = _run_minimize(func, minimizer)
        return DCAssignmentResult(
            original_func=func,
            assigned_func=func,
            assignment={},
            original_cost=result.n_literals,
            optimized_cost=result.n_literals,
            original_sop=result.sop,
            optimized_sop=result.sop,
            improvement=0,
        )

    # Original minimization (with don't-cares as don't-cares)
    original_result = _run_minimize(func, minimizer)
    original_cost = original_result.n_literals

    # Greedy: try assigning all DCs to on-set, all to off-set,
    # and individual assignments
    best_minterms: Set[int] = set(func.minterms)
    best_cost = original_cost
    best_sop = original_result.sop
    assignment: Dict[int, int] = {}

    # Try all DCs assigned to on-set
    func_all_on = BooleanFunction(
        n_vars=func.n_vars,
        minterms=func.minterms | func.dontcare,
        dontcare=set(),
        name=func.name,
    )
    result_all_on = _run_minimize(func_all_on, minimizer)
    if result_all_on.n_literals < best_cost:
        best_cost = result_all_on.n_literals
        best_minterms = set(func_all_on.minterms)
        best_sop = result_all_on.sop
        assignment = {dc: 1 for dc in func.dontcare}

    # Try all DCs assigned to off-set (i.e., remove them entirely)
    func_all_off = BooleanFunction(
        n_vars=func.n_vars,
        minterms=func.minterms,
        dontcare=set(),
        name=func.name,
    )
    result_all_off = _run_minimize(func_all_off, minimizer)
    if result_all_off.n_literals < best_cost:
        best_cost = result_all_off.n_literals
        best_minterms = set(func_all_off.minterms)
        best_sop = result_all_off.sop
        assignment = {dc: 0 for dc in func.dontcare}

    # Individual greedy assignment: for each DC, try adding to on-set
    # if it reduces cost
    sorted_dc = sorted(func.dontcare)
    current_minterms = set(best_minterms)
    current_dc = set(func.dontcare) - set(current_minterms)
    current_cost = best_cost

    for dc in sorted_dc:
        if dc not in current_dc:
            continue
        # Try adding this DC to the on-set
        trial_minterms = current_minterms | {dc}
        trial_dc = current_dc - {dc}
        trial_func = BooleanFunction(
            n_vars=func.n_vars,
            minterms=trial_minterms,
            dontcare=trial_dc,
            name=func.name,
        )
        trial_result = _run_minimize(trial_func, minimizer)
        if trial_result.n_literals < current_cost:
            current_minterms = trial_minterms
            current_dc = trial_dc
            current_cost = trial_result.n_literals
            best_sop = trial_result.sop
            assignment[dc] = 1

    if current_cost < best_cost:
        best_cost = current_cost
        best_minterms = current_minterms

    # Build the assigned function
    assigned_func = BooleanFunction(
        n_vars=func.n_vars,
        minterms=best_minterms,
        dontcare=set(),
        name=func.name,
    )

    return DCAssignmentResult(
        original_func=func,
        assigned_func=assigned_func,
        assignment=assignment,
        original_cost=original_cost,
        optimized_cost=best_cost,
        original_sop=original_result.sop,
        optimized_sop=best_sop,
        improvement=original_cost - best_cost,
    )


def _run_minimize(func: BooleanFunction, minimizer: str) -> MinimizationResult:
    """Run the specified minimizer and return the result."""
    if minimizer == "qm":
        qm = QuineMcCluskey(func.n_vars)
        return qm.minimize(func)
    elif minimizer == "espresso":
        esp = Espresso(func.n_vars)
        return esp.minimize(func)
    else:
        raise ValueError(f"unknown minimizer {minimizer!r}")


def minimize_with_dc_optimization(
    func: BooleanFunction,
    minimizer: str = "qm",
) -> DCAssignmentResult:
    """Convenience wrapper for :func:`assign_dontcares`."""
    return assign_dontcares(func, minimizer=minimizer)