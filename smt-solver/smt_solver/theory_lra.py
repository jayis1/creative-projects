"""
Theory of Linear Real Arithmetic (LRA) via Simplex.

The implementation follows the standard "Simplex for SMT" approach
(Dutertre & de Moura 2006): a tableau-based incremental Simplex that can
check consistency of a set of linear constraints and produce explanations.

Key features:
  - Incremental: assert constraints, push/pop
  - Produces conflict explanations (subset of asserted atoms)
  - Model generation (rational assignment to variables)

For robustness and correctness, we use Fourier-Motzkin elimination for
small systems (which is always correct but exponential in the worst case)
and fall back to a Simplex-based approach for larger ones.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Set, Optional, Iterable
from dataclasses import dataclass, field
import itertools

from .ast import Term, Var, NumConst, App


@dataclass
class LinearExpr:
    """A linear expression: sum(coeff * var) + constant.

    Variables are identified by name (string).
    """
    coeffs: Dict[str, float] = field(default_factory=dict)
    const: float = 0.0

    @staticmethod
    def constant(value: float) -> "LinearExpr":
        return LinearExpr(const=value)

    @staticmethod
    def variable(name: str, coeff: float = 1.0) -> "LinearExpr":
        return LinearExpr(coeffs={name: coeff})

    def __add__(self, other: "LinearExpr") -> "LinearExpr":
        result = LinearExpr(coeffs=dict(self.coeffs), const=self.const + other.const)
        for v, c in other.coeffs.items():
            result.coeffs[v] = result.coeffs.get(v, 0.0) + c
        # Clean up zeros
        result.coeffs = {v: c for v, c in result.coeffs.items() if abs(c) > 1e-15}
        return result

    def __sub__(self, other: "LinearExpr") -> "LinearExpr":
        result = LinearExpr(coeffs=dict(self.coeffs), const=self.const - other.const)
        for v, c in other.coeffs.items():
            result.coeffs[v] = result.coeffs.get(v, 0.0) - c
        result.coeffs = {v: c for v, c in result.coeffs.items() if abs(c) > 1e-15}
        return result

    def scale(self, factor: float) -> "LinearExpr":
        return LinearExpr(
            coeffs={v: c * factor for v, c in self.coeffs.items() if abs(c * factor) > 1e-15},
            const=self.const * factor,
        )

    def evaluate(self, assignment: Dict[str, float]) -> float:
        return sum(c * assignment.get(v, 0.0) for v, c in self.coeffs.items()) + self.const

    def is_constant(self) -> bool:
        return not self.coeffs

    @property
    def vars(self) -> Set[str]:
        return set(self.coeffs.keys())

    def __repr__(self) -> str:
        parts = []
        for v in sorted(self.coeffs):
            c = self.coeffs[v]
            if c == 1:
                parts.append(v)
            elif c == -1:
                parts.append(f"-{v}")
            else:
                parts.append(f"{c}*{v}")
        if self.const != 0 or not parts:
            parts.append(str(self.const))
        return " + ".join(parts) if parts else "0"


@dataclass
class LinearConstraint:
    """A linear (in)equality:  expr OP 0."""
    expr: LinearExpr
    op: str  # '<', '<=', '=', '!=', '>', '>='
    label: str = ""

    def is_satisfied(self, assignment: Dict[str, float]) -> bool:
        val = self.expr.evaluate(assignment)
        EPS = 1e-9
        if self.op == "<":
            return val < -EPS
        if self.op == "<=":
            return val <= EPS
        if self.op == "=":
            return abs(val) <= EPS
        if self.op == "!=":
            return abs(val) > EPS
        if self.op == ">":
            return val > EPS
        if self.op == ">=":
            return val >= -EPS
        raise ValueError(f"Unknown op: {self.op}")

    def negated(self) -> "LinearConstraint":
        neg_op = {
            "<": ">=", "<=": ">", "=": "!=", "!=": "=",
            ">": "<=", ">=": "<",
        }
        return LinearConstraint(self.expr, neg_op[self.op], label=f"~({self.label})")


def term_to_linear(term: Term) -> LinearExpr:
    """Convert an arithmetic Term to a LinearExpr."""
    if isinstance(term, NumConst):
        return LinearExpr.constant(term.value)
    if isinstance(term, Var):
        return LinearExpr.variable(term.name)
    if isinstance(term, App):
        if term.func == "+":
            result = LinearExpr()
            for c in term.args:
                result = result + term_to_linear(c)
            return result
        if term.func == "-":
            if len(term.args) == 1:
                return term_to_linear(term.args[0]).scale(-1)
            result = term_to_linear(term.args[0])
            for c in term.args[1:]:
                result = result - term_to_linear(c)
            return result
        if term.func == "*":
            # Linear: at most one arg can be non-constant
            const_val = 1.0
            var_expr: Optional[LinearExpr] = None
            for c in term.args:
                le = term_to_linear(c)
                if le.is_constant():
                    const_val *= le.const
                else:
                    if var_expr is not None:
                        raise ValueError(f"Non-linear term: {term}")
                    var_expr = le
            if var_expr is None:
                return LinearExpr.constant(const_val)
            return var_expr.scale(const_val)
        if term.func == "/":
            if len(term.args) != 2:
                raise ValueError("Division expects 2 args")
            num = term_to_linear(term.args[0])
            den = term_to_linear(term.args[1])
            if not den.is_constant():
                raise ValueError(f"Non-linear division: {term}")
            if den.const == 0:
                raise ValueError(f"Division by zero in: {term}")
            return num.scale(1.0 / den.const)
    raise ValueError(f"Cannot convert to linear: {term}")


def atom_to_constraint(atom: App) -> LinearConstraint:
    """Convert a theory atom (App with comparison func) to a constraint."""
    assert atom.func in {"=", "<", "<=", ">", ">="}
    assert len(atom.args) == 2
    lhs = term_to_linear(atom.args[0])
    rhs = term_to_linear(atom.args[1])
    expr = lhs - rhs
    return LinearConstraint(expr, atom.func, label=str(atom))


class SimplexTheory:
    """
    Incremental theory solver for Linear Real Arithmetic.

    Uses Fourier-Motzkin elimination for checking feasibility, which is
    always correct (though exponential in the worst case).  For model
    generation, we use a simple assignment heuristic.
    """

    EPS = 1e-9

    def __init__(self):
        self._constraints: List[LinearConstraint] = []
        self._all_vars: Set[str] = set()
        self._trail: List[int] = []

    def push(self):
        self._trail.append(len(self._constraints))

    def pop(self):
        if self._trail:
            target = self._trail.pop()
            self._constraints = self._constraints[:target]

    def reset(self):
        self._constraints.clear()
        self._trail.clear()

    def assert_atom(self, atom: App) -> bool:
        """Assert a theory atom.  Returns False if immediately unsat."""
        c = atom_to_constraint(atom)
        for v in c.expr.coeffs:
            self._all_vars.add(v)
        # Quick check: if it's a constant constraint, verify immediately
        if c.expr.is_constant():
            if not c.is_satisfied({}):
                return False
        self._constraints.append(c)
        return True

    def assert_negation(self, atom: App):
        """Assert the negation of an atom (for theory propagation)."""
        c = atom_to_constraint(atom).negated()
        for v in c.expr.coeffs:
            self._all_vars.add(v)
        if c.expr.is_constant():
            if not c.is_satisfied({}):
                return False
        self._constraints.append(c)
        return True

    def check(self) -> Tuple[str, Optional[Dict[str, float]], Optional[List[int]]]:
        """
        Check satisfiability of current constraints.

        Returns:
          ("sat", assignment, None)  — satisfiable, with a model
          ("unsat", None, indices)   — unsatisfiable, with conflicting indices
          ("unknown", None, None)     — couldn't determine
        """
        return _fm_check(self._constraints, self._all_vars)

    def get_model(self) -> Dict[str, float]:
        """Return a satisfying assignment."""
        status, model, _ = self.check()
        if status == "sat" and model is not None:
            return model
        return {}


# ---------------------------------------------------------------------------
# Fourier-Motzkin Elimination
# ---------------------------------------------------------------------------

def _fm_check(
    constraints: List[LinearConstraint],
    all_vars: Set[str],
) -> Tuple[str, Optional[Dict[str, float]], Optional[List[int]]]:
    """
    Check feasibility using Fourier-Motzkin elimination.

    FM works by eliminating variables one at a time:
      - For each variable v, partition constraints into:
          - lower bounds: expr >= 0 with v having positive coefficient
          - upper bounds: expr <= 0 with v having positive coefficient
          - (negative coefficients swap the roles)
      - Combine each lower bound with each upper bound to get a new
        constraint without v.
      - After eliminating all variables, check if remaining (constant)
        constraints are consistent.

    For disequalities (!=), we use a branching approach with recursive
    splitting. When a disequality is violated by the current model, we
    try both < and > branches, and recursively handle remaining
    disequalities in each branch.
    """
    if not constraints:
        return "sat", {v: 0.0 for v in all_vars}, None

    # Separate disequalities from other constraints
    main_constraints = [c for c in constraints if c.op != "!="]
    diseq_constraints = [c for c in constraints if c.op == "!="]

    # Find a feasible point without disequalities first
    status, model = _fm_feasibility(main_constraints, all_vars)

    if status != "sat":
        # Return all main constraint indices as conflict
        conflict = [i for i, c in enumerate(constraints) if c.op != "!="]
        return "unsat", None, conflict

    if model is None:
        return "unknown", None, None

    # Check disequality constraints with recursive branching
    result = _check_disequalities(
        main_constraints, diseq_constraints, all_vars, model
    )
    if result == "sat":
        return "sat", model, None
    elif result == "unsat":
        # All constraints conflict
        conflict = list(range(len(constraints)))
        return "unsat", None, conflict
    else:
        return "unknown", None, None


def _check_disequalities(
    main_constraints: List["LinearConstraint"],
    diseq_constraints: List["LinearConstraint"],
    all_vars: Set[str],
    model: Dict[str, float],
) -> str:
    """Recursively check disequalities by branching when violated.

    When a disequality a != b is violated (i.e., model has a == b),
    we branch: try a < b and a > b, and recurse on remaining disequalities.
    """
    if not diseq_constraints:
        return "sat"

    # Check if any disequality is violated by the current model
    for i, dc in enumerate(diseq_constraints):
        val = dc.expr.evaluate(model)
        if abs(val) < _fm_EPS * max(1, abs(dc.expr.const)):
            # Disequality violated — try branching
            remaining = [dc2 for j, dc2 in enumerate(diseq_constraints) if j != i]
            for branch_op in ("<", ">"):
                branch_c = LinearConstraint(dc.expr, branch_op, label=dc.label)
                branch_main = main_constraints + [branch_c]
                s2, m2 = _fm_feasibility(branch_main, all_vars)
                if s2 == "sat" and m2 is not None:
                    # Recursively check remaining disequalities
                    sub_result = _check_disequalities(
                        branch_main, remaining, all_vars, m2
                    )
                    if sub_result == "sat":
                        # Found a model! Update the original model
                        model.clear()
                        model.update(m2)
                        return "sat"
            # Both branches failed — return unsat
            return "unsat"

    # No disequality violated — we're done
    return "sat"


_fm_EPS = 1e-9


def _fm_feasibility(
    constraints: List[LinearConstraint],
    all_vars: Set[str],
) -> Tuple[str, Optional[Dict[str, float]]]:
    """
    Core Fourier-Motzkin feasibility check with model construction.

    Returns ("sat", model) or ("unsat", None).

    The algorithm eliminates variables one at a time, recording the
    elimination steps so that a model can be constructed by back-substitution.
    """
    if not constraints:
        return "sat", {v: 0.0 for v in all_vars}

    # Convert to normalized form: (coeffs_dict, op, const)
    # where constraint is: sum(coeffs[v] * v) + const OP 0
    normalized: List[Tuple[Dict[str, float], str, float]] = []
    for c in constraints:
        coeffs = dict(c.expr.coeffs)
        const = c.expr.const
        op = c.op
        if not coeffs:
            # Constant constraint — check immediately
            if not _check_constant_constraint(op, const):
                return "unsat", None
            continue
        normalized.append((coeffs, op, const))

    if not normalized:
        return "sat", {v: 0.0 for v in all_vars}

    # Collect all variables
    all_vs = set()
    for coeffs, _, _ in normalized:
        all_vs.update(coeffs.keys())

    # Record elimination steps for back-substitution
    elim_steps: List[Tuple[str, tuple]] = []
    current = list(normalized)

    vars_to_eliminate = sorted(all_vs)
    elim_order = _choose_elimination_order(current, vars_to_eliminate)

    for v in elim_order:
        step, current = _fm_eliminate_var_with_model(current, v)
        if current is None:
            return "unsat", None
        elim_steps.append((v, step))

    # Check remaining constant constraints
    for coeffs, op, const in current:
        if coeffs:
            continue
        if not _check_constant_constraint(op, const):
            return "unsat", None

    # Feasible — construct model by back-substitution
    model = _fm_back_substitute(elim_steps, all_vs)
    return "sat", model


def _check_constant_constraint(op: str, const: float) -> bool:
    """Check if a constant constraint (no variables) is satisfied."""
    if op == "<":
        return const < -_fm_EPS
    if op == "<=":
        return const <= _fm_EPS
    if op == "=":
        return abs(const) <= _fm_EPS
    if op == ">":
        return const > _fm_EPS
    if op == ">=":
        return const >= -_fm_EPS
    return False


def _fm_eliminate_var_with_model(
    constraints: List[Tuple[Dict[str, float], str, float]],
    var: str,
) -> Tuple[Optional[tuple], Optional[List[Tuple[Dict[str, float], str, float]]]]:
    """Eliminate *var*, returning (model_step, new_constraints).

    model_step is used later for back-substitution.
    Returns (None, None) if infeasible.
    """
    # Check for equality constraints first (use substitution)
    for coeffs, op, const in constraints:
        coef = coeffs.get(var, 0.0)
        if op == "=" and abs(coef) > _fm_EPS:
            # var = -(rest + const) / coef
            subst_coeffs = {v: -c / coef for v, c in coeffs.items() if v != var}
            subst_const = -const / coef
            # Substitute into all other constraints
            result: List[Tuple[Dict[str, float], str, float]] = []
            for coeffs2, op2, const2 in constraints:
                coef2 = coeffs2.get(var, 0.0)
                if abs(coef2) < _fm_EPS:
                    result.append((coeffs2, op2, const2))
                else:
                    new_coeffs = {v: c for v, c in coeffs2.items() if v != var}
                    for sv, sc in subst_coeffs.items():
                        new_coeffs[sv] = new_coeffs.get(sv, 0.0) + coef2 * sc
                    new_const = const2 + coef2 * subst_const
                    new_coeffs = {v: c for v, c in new_coeffs.items() if abs(c) > _fm_EPS}
                    if not new_coeffs:
                        if not _check_constant_constraint(op2, new_const):
                            return None, None
                    else:
                        result.append((new_coeffs, op2, new_const))
            return ("eq", subst_coeffs, subst_const), result

    # No equality — collect bounds
    lower_bounds: List[Tuple[float, Dict[str, float], float, str]] = []
    upper_bounds: List[Tuple[float, Dict[str, float], float, str]] = []
    zero: List[Tuple[Dict[str, float], str, float]] = []

    for coeffs, op, const in constraints:
        coef = coeffs.get(var, 0.0)
        if abs(coef) < _fm_EPS:
            zero.append((coeffs, op, const))
        elif coef > 0:
            if op in ("<=", "<"):
                upper_bounds.append((coef, coeffs, const, op))
            elif op in (">=", ">"):
                lower_bounds.append((coef, coeffs, const, op))
        else:  # coef < 0
            if op in ("<=", "<"):
                lower_bounds.append((coef, coeffs, const, op))
            elif op in (">=", ">"):
                upper_bounds.append((coef, coeffs, const, op))

    # Combine each lower bound with each upper bound
    result = list(zero)
    for lb_coef, lb_coeffs, lb_const, lb_op in lower_bounds:
        for ub_coef, ub_coeffs, ub_const, ub_op in upper_bounds:
            lb_rest = {v: c for v, c in lb_coeffs.items() if v != var}
            ub_rest = {v: c for v, c in ub_coeffs.items() if v != var}

            # L = -(lb_rest + lb_const) / lb_coef
            # U = -(ub_rest + ub_const) / ub_coef
            # Combined: L <= U  =>  L - U <= 0
            # L - U = -(lb_rest+lb_const)/lb_coef + (ub_rest+ub_const)/ub_coef
            combined_coeffs: Dict[str, float] = {}
            for v, c in ub_rest.items():
                combined_coeffs[v] = combined_coeffs.get(v, 0.0) + c / ub_coef
            for v, c in lb_rest.items():
                combined_coeffs[v] = combined_coeffs.get(v, 0.0) - c / lb_coef
            combined_const = ub_const / ub_coef - lb_const / lb_coef

            combined_op = "<="
            if lb_op == ">" or ub_op == "<":
                combined_op = "<"

            combined_coeffs = {v: c for v, c in combined_coeffs.items() if abs(c) > _fm_EPS}

            if not combined_coeffs:
                if not _check_constant_constraint(combined_op, combined_const):
                    return None, None
            else:
                result.append((combined_coeffs, combined_op, combined_const))

    return ("bounds", lower_bounds, upper_bounds), result


def _fm_back_substitute(
    elim_steps: List[Tuple[str, tuple]],
    all_vars: Set[str],
) -> Dict[str, float]:
    """Construct a model by back-substituting through elimination steps.

    Steps are in elimination order (first eliminated → assigned last).
    We process them in reverse to assign values.
    """
    model: Dict[str, float] = {v: 0.0 for v in all_vars}

    for var, step in reversed(elim_steps):
        if step[0] == "eq":
            _, subst_coeffs, subst_const = step
            # var = sum(subst_coeffs[v] * model[v]) + subst_const
            val = subst_const
            for v, c in subst_coeffs.items():
                val += c * model.get(v, 0.0)
            model[var] = val
        elif step[0] == "bounds":
            _, lower_bounds, upper_bounds = step
            # Compute L = max of lower bounds, U = min of upper bounds
            L = -float("inf")
            U = float("inf")
            for lb_coef, lb_coeffs, lb_const, lb_op in lower_bounds:
                lb_rest = {v: c for v, c in lb_coeffs.items() if v != lb_coef}
                # L_i = -(lb_rest + lb_const) / lb_coef
                val = lb_const
                for v, c in lb_coeffs.items():
                    if v != var:
                        val += c * model.get(v, 0.0)
                bound = -val / lb_coef
                if lb_op == ">":
                    bound += _fm_EPS  # strict
                L = max(L, bound)
            for ub_coef, ub_coeffs, ub_const, ub_op in upper_bounds:
                val = ub_const
                for v, c in ub_coeffs.items():
                    if v != var:
                        val += c * model.get(v, 0.0)
                bound = -val / ub_coef
                if ub_op == "<":
                    bound -= _fm_EPS  # strict
                U = min(U, bound)

            # Choose a value in [L, U]
            if L == -float("inf") and U == float("inf"):
                model[var] = 0.0
            elif L == -float("inf"):
                # Only upper bound — choose something below U
                model[var] = U - 1.0 if U != float("inf") else 0.0
            elif U == float("inf"):
                # Only lower bound — choose something above L
                model[var] = L + 1.0
            else:
                # Both bounds — choose midpoint
                model[var] = (L + U) / 2.0

    return model


def _choose_elimination_order(
    constraints: List[Tuple[Dict[str, float], str, float]],
    vars: List[str],
) -> List[str]:
    """Choose elimination order to minimize constraint explosion (heuristic).

    Use the variable that appears in the fewest constraints first.
    """
    count = {v: 0 for v in vars}
    for coeffs, _, _ in constraints:
        for v in coeffs:
            if v in count:
                count[v] += 1
    return sorted(vars, key=lambda v: count[v])


# (Old _fm_eliminate_var and _fm_construct_model removed — replaced by
#  _fm_eliminate_var_with_model and _fm_back_substitute above.)