"""Mixed-integer linear programming via branch-and-bound + Gomory cuts.

Strategy
--------
* **Branch-and-bound**: recursively solve LP relaxations; when an integer
  variable has a fractional value, branch into two subproblems (floor /
  ceiling).  Best-first search with incumbent pruning keeps the tree small.
* **Gomory fractional cuts**: at an integer node, generate cutting planes
  from the simplex tableau rows of fractional basic variables to tighten
  the relaxation, accelerating convergence.
* **Pure-integer and mixed-integer** problems are both supported.
* **Search strategies**: best-first (default), depth-first, or
  breadth-first, selectable via the ``strategy`` parameter.
* **Node and time limits**: ``max_nodes`` caps the number of LP relaxations;
  ``time_limit`` (seconds) caps total wall-clock time.

This enhanced version adds real Gomory cut generation by leveraging the
``Tableau`` object exposed by ``SimplexSolver``, configurable search
strategies, and detailed node-exploitation logging.
"""

from __future__ import annotations

import heapq
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Literal

from .problem import LPProblem, LPResult, LPStatus
from .simplex import SimplexSolver, Tableau

__all__ = ["MILPSolver", "SearchStrategy"]

logger = logging.getLogger("simplex.integer")


class SearchStrategy(Enum):
    """Branch-and-bound tree exploration strategy."""

    BEST_FIRST = "best-first"   # explore node with best relaxation bound
    DEPTH_FIRST = "depth-first"  # dive deep quickly (good for incumbents)
    BREADTH_FIRST = "breadth-first"  # FIFO queue


@dataclass(order=True)
class _Node:
    """A branch-and-bound subproblem."""

    priority: tuple  # (bound key, node_id)
    node_id: int
    depth: int = 0
    bounds: dict = field(default_factory=dict, repr=False)
    parent_obj: float | None = None
    cuts: list = field(default_factory=list, repr=False)


class MILPSolver:
    """Branch-and-bound solver for (mixed-)integer LPs.

    Parameters
    ----------
    max_nodes : int
        Maximum number of LP relaxations to solve.
    max_iter : int
        Simplex iteration cap per relaxation.
    use_cuts : bool
        If True, generate Gomory fractional cuts at integer nodes.
    bland : bool
        Use Bland's rule in the underlying simplex.
    eps : float
        Tolerance for integrality and bound checks (exact ``Fraction`` cmp
        used internally; eps only governs float comparisons on extracted
        values).
    strategy : str | SearchStrategy
        Tree exploration strategy: ``"best-first"`` (default),
        ``"depth-first"``, or ``"breadth-first"``.
    time_limit : float | None
        Maximum wall-clock seconds.  ``None`` means no limit.
    verbose : bool
        If True, log node exploration at INFO level.
    """

    def __init__(
        self,
        max_nodes: int = 10_000,
        max_iter: int = 10_000,
        use_cuts: bool = True,
        bland: bool = True,
        eps: float = 1e-7,
        strategy: str | SearchStrategy = "best-first",
        time_limit: float | None = None,
        verbose: bool = False,
    ) -> None:
        self.max_nodes = max_nodes
        self.max_iter = max_iter
        self.use_cuts = use_cuts
        self.bland = bland
        self.eps = eps
        if isinstance(strategy, str):
            strategy = SearchStrategy(strategy)
        self.strategy = strategy
        self.time_limit = time_limit
        self.verbose = verbose
        self._node_counter = 0
        self.nodes_explored = 0
        self.cuts_generated = 0
        self._start_time: float = 0.0

    # ------------------------------------------------------------------ #
    # public
    # ------------------------------------------------------------------ #
    def _new_node(self, priority: tuple, bounds: dict, depth: int = 0,
                  parent_obj: float | None = None,
                  cuts: list | None = None) -> _Node:
        self._node_counter += 1
        return _Node(
            priority=priority,
            node_id=self._node_counter,
            depth=depth,
            bounds=bounds,
            parent_obj=parent_obj,
            cuts=cuts or [],
        )

    def _is_integer(self, val: float) -> bool:
        return abs(val - round(val)) <= self.eps

    def _apply_bounds(self, problem: LPProblem, extra: dict) -> LPProblem:
        """Return a *copy* of ``problem`` with additional bounds applied.

        Each entry in ``extra`` tightens the variable's bounds: the new
        lower bound is the max of the current and the extra lower bound,
        and the new upper bound is the min of the current and the extra
        upper bound.  A value of ``None`` means "no constraint in that
        direction".
        """
        import copy
        p = copy.deepcopy(problem)
        for v, (lo, hi) in extra.items():
            cur_lo, cur_hi = p.bounds.get(v, (Fraction(0), None))
            new_lo = cur_lo if lo is None else (lo if cur_lo is None else max(cur_lo, lo))
            new_hi = cur_hi if hi is None else (hi if cur_hi is None else min(cur_hi, hi))
            p.bounds[v] = (new_lo, new_hi)
        return p

    def _apply_cuts(self, problem: LPProblem, cuts: list[dict]) -> LPProblem:
        """Return a copy of ``problem`` with additional cutting-plane constraints."""
        import copy
        p = copy.deepcopy(problem)
        for i, cut in enumerate(cuts):
            p.constraints.append({
                "coeffs": dict(cut["coeffs"]),
                "relation": cut["relation"],
                "rhs": cut["rhs"],
                "name": f"_gomory_{self._node_counter}_{i}",
            })
        return p

    def _gomory_cuts(self, problem: LPProblem, tableau: Tableau,
                     int_vars: set[str]) -> list[dict]:
        """Generate Gomory fractional cuts from the final simplex tableau.

        For each basic variable that is integer-restricted and has a
        fractional value, the cut is::

            sum_j  f(a_{ij}) * x_j  >=  f(b_i)

        where ``f()`` is the fractional-part function and ``j`` ranges over
        non-basic columns.  This is the classic Gomory fractional cut
        derived from the optimal simplex tableau row of a fractional
        integer variable.

        Only structural (non-slack, non-artificial) non-basic variables
        appear in the cut; slack/surplus variables are handled implicitly
        because they represent constraint activity.

        Returns a list of constraint dicts suitable for
        :meth:`_apply_cuts`.
        """
        cuts: list[dict] = []
        if not int_vars:
            return cuts
        # Map original var names → tableau column indices.
        var_to_col: dict[str, int] = {}
        for j, v in enumerate(tableau.vars):
            if v.src is not None and v.name in int_vars:
                # Only register the primary (non-flipped, non-neg) column.
                if v.partner is None and not v.name.endswith("_flip"):
                    var_to_col.setdefault(v.name, j)

        for i, bidx in enumerate(tableau.basis):
            bvar = tableau.vars[bidx]
            # The basic variable must be an integer-restricted structural var
            # and have a fractional value.
            if bvar.src is None or bvar.name not in int_vars:
                continue
            rhs_val = tableau.rhs[i]
            frac_rhs = rhs_val - int(rhs_val)  # Fractional part (exact)
            if frac_rhs == 0:
                continue  # Already integer — no cut needed.
            # Build the cut: sum_j f(a_ij) * x_j >= f(b_i)
            # where f() maps to [0, 1) and a_ij are the row coefficients
            # of non-basic variables.
            cut_coeffs: dict[str, Fraction] = {}
            for j in tableau.nonbasis:
                a_ij = tableau.rows[i].get(j, Fraction(0))
                # Fractional part of a_ij (exact, in [0, 1)).
                f_a = a_ij - int(a_ij)
                if f_a < 0:
                    f_a += 1  # Ensure in [0, 1)
                if f_a == 0:
                    continue
                nv = tableau.vars[j]
                # Map non-basic column back to an original variable name.
                orig_name = self._col_to_orig_name(tableau, j)
                if orig_name is None:
                    continue
                cut_coeffs[orig_name] = cut_coeffs.get(orig_name, Fraction(0)) + f_a
            if not cut_coeffs:
                continue
            cuts.append({
                "coeffs": cut_coeffs,
                "relation": ">=",
                "rhs": frac_rhs,
            })
        return cuts

    def _col_to_orig_name(self, tableau: Tableau, j: int) -> str | None:
        """Map a tableau column index back to an original variable name."""
        v = tableau.vars[j]
        if v.src is not None and not v.name.endswith("_neg") and not v.name.endswith("_flip"):
            return v.name
        if v.partner is not None:
            # Free-variable split: the partner is the positive part.
            partner_var = tableau.vars[v.partner]
            return partner_var.name
        if v.name.endswith("_flip"):
            # Flipped variable: original name is prefix before "_flip".
            return v.name[:-5]
        return None

    def solve(self, problem: LPProblem) -> LPResult:
        """Solve the (mixed-)integer program.

        Returns an :class:`LPResult` with ``status`` set to
        :attr:`LPStatus.OPTIMAL` if an integer-feasible optimum was found,
        :attr:`LPStatus.INFEASIBLE` if no feasible integer solution exists,
        or :attr:`LPStatus.TIMEOUT` if a node/time limit was reached before
        proving optimality.
        """
        if not problem.integer:
            # Pure LP — no branching needed.
            return SimplexSolver(max_iter=self.max_iter, bland=self.bland).solve(problem)
        self._start_time = time.time()
        self._node_counter = 0
        self.nodes_explored = 0
        self.cuts_generated = 0
        sense = problem.objective
        best_obj: float | None = None
        best_sol: dict[str, float] | None = None
        found_feasible = False
        timed_out = False

        if self.strategy is SearchStrategy.BEST_FIRST:
            heap: list[_Node] = []
            root = self._new_node(priority=(float("-inf"), 0), bounds={})
            heapq.heappush(heap, root)
            pop = lambda: heapq.heappop(heap)  # noqa: E731
            push = lambda n: heapq.heappush(heap, n)  # noqa: E731
        elif self.strategy is SearchStrategy.DEPTH_FIRST:
            stack: list[_Node] = []
            root = self._new_node(priority=(float("-inf"), 0), bounds={})
            stack.append(root)
            pop = lambda: stack.pop()  # noqa: E731
            push = lambda n: stack.append(n)  # noqa: E731
        else:  # BREADTH_FIRST
            from collections import deque
            queue: deque[_Node] = deque()
            root = self._new_node(priority=(float("-inf"), 0), bounds={})
            queue.append(root)
            pop = lambda: queue.popleft()  # noqa: E731
            push = lambda n: queue.append(n)  # noqa: E731

        while True:
            try:
                node = pop()
            except IndexError:
                break
            if self.nodes_explored >= self.max_nodes:
                timed_out = True
                break
            if self.time_limit is not None and time.time() - self._start_time > self.time_limit:
                timed_out = True
                break
            self.nodes_explored += 1
            if self.verbose:
                logger.info("Exploring node %d (depth %d)", node.node_id, node.depth)
            # Prune if best-bound can't beat incumbent.
            node_bound = -node.priority[0]
            if best_obj is not None:
                if sense == "max" and node_bound <= best_obj + self.eps:
                    continue
                if sense == "min" and node_bound >= best_obj - self.eps:
                    continue
            # Solve relaxation.
            sub = self._apply_bounds(problem, node.bounds)
            if node.cuts:
                sub = self._apply_cuts(sub, node.cuts)
            res = SimplexSolver(max_iter=self.max_iter, bland=self.bland).solve(sub)
            if res.status is not LPStatus.OPTIMAL:
                continue  # infeasible / unbounded → prune
            obj = res.objective_value
            # Prune by bound.
            if best_obj is not None:
                if sense == "max" and obj <= best_obj + self.eps:
                    continue
                if sense == "min" and obj >= best_obj - self.eps:
                    continue
            # Check integrality of integer variables.
            frac_var = None
            frac_val = None
            for v in problem.integer:
                val = res.solution.get(v, 0.0)
                if not self._is_integer(val):
                    frac_var = v
                    frac_val = val
                    break
            if frac_var is None:
                # Integer feasible — update incumbent.
                if (best_obj is None
                    or (sense == "max" and obj > best_obj + self.eps)
                    or (sense == "min" and obj < best_obj - self.eps)):
                    best_obj = obj
                    best_sol = dict(res.solution)
                    found_feasible = True
                    if self.verbose:
                        logger.info("New incumbent: obj=%s (node %d)", best_obj, node.node_id)
                continue
            # Branch on frac_var.
            import math
            floor_v = math.floor(frac_val)
            ceil_v = floor_v + 1
            # left child: x <= floor
            left_bounds = dict(node.bounds)
            cur_lo, cur_hi = sub.bounds.get(frac_var, (Fraction(0), None))
            left_hi = cur_hi if cur_hi is not None else floor_v
            left_hi = min(left_hi, floor_v)
            left_bounds[frac_var] = (cur_lo, left_hi)
            # right child: x >= ceil
            right_bounds = dict(node.bounds)
            right_lo = ceil_v if cur_lo is None else max(cur_lo, ceil_v)
            right_bounds[frac_var] = (right_lo, cur_hi)

            # Gomory cuts: generate from the current tableau if enabled.
            child_cuts = []
            if self.use_cuts and not node.cuts:
                # Re-solve to get the tableau (SimplexSolver.solve doesn't
                # expose it; we rebuild for cut generation).
                try:
                    tab = Tableau.from_problem(sub)
                    if tab.artificial_indices:
                        tab.run_phase_one(max_iter=self.max_iter, bland=self.bland)
                    tab.solve(max_iter=self.max_iter, bland=self.bland)
                    child_cuts = self._gomory_cuts(sub, tab, problem.integer)
                    self.cuts_generated += len(child_cuts)
                except Exception:
                    child_cuts = []

            # Push children.
            # For all strategies, the priority's first element stores the
            # relaxation objective (negated for max) so that pruning works
            # correctly.  The difference between strategies is the tie-breaker:
            # best-first uses node_id (smallest = best bound first),
            # depth-first uses -node_id (newest = deepest first),
            # breadth-first uses node_id (oldest = shallowest first).
            if self.strategy is SearchStrategy.BEST_FIRST:
                left_node = self._new_node(
                    priority=(-obj, self._node_counter), bounds=left_bounds,
                    depth=node.depth + 1, parent_obj=obj, cuts=child_cuts)
                right_node = self._new_node(
                    priority=(-obj, self._node_counter), bounds=right_bounds,
                    depth=node.depth + 1, parent_obj=obj, cuts=child_cuts)
            elif self.strategy is SearchStrategy.DEPTH_FIRST:
                # Use -node_id so newer (deeper) nodes are popped first.
                left_node = self._new_node(
                    priority=(-obj, -self._node_counter), bounds=left_bounds,
                    depth=node.depth + 1, parent_obj=obj, cuts=child_cuts)
                right_node = self._new_node(
                    priority=(-obj, -self._node_counter), bounds=right_bounds,
                    depth=node.depth + 1, parent_obj=obj, cuts=child_cuts)
            else:  # BREADTH_FIRST — same as best-first for the heap, but
                # the pop function uses FIFO (deque.popleft) instead of
                # heapq.heappop, so the priority ordering is irrelevant.
                left_node = self._new_node(
                    priority=(-obj, self._node_counter), bounds=left_bounds,
                    depth=node.depth + 1, parent_obj=obj, cuts=child_cuts)
                right_node = self._new_node(
                    priority=(-obj, self._node_counter), bounds=right_bounds,
                    depth=node.depth + 1, parent_obj=obj, cuts=child_cuts)
            push(left_node)
            push(right_node)

        if not found_feasible:
            if timed_out:
                return LPResult(
                    status=LPStatus.TIMEOUT,
                    message=f"node/time limit reached ({self.nodes_explored} nodes)",
                    iterations=self.nodes_explored,
                )
            return LPResult(status=LPStatus.INFEASIBLE,
                             message="no integer feasible solution found")
        result = LPResult(
            status=LPStatus.OPTIMAL if not timed_out else LPStatus.TIMEOUT,
            objective_value=best_obj,
            solution=best_sol or {},
            iterations=self.nodes_explored,
            message=(
                f"branch-and-bound: {self.nodes_explored} nodes, "
                f"{self.cuts_generated} cuts"
                + (" [timed out]" if timed_out else "")
            ),
        )
        return result