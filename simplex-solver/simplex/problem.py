"""Linear programming problem representation.

An :class:`LPProblem` encodes a linear program in standard form::

    maximize   c^T x
    subject to   A x  (=, <=, >=)  b
                x >= 0   (optionally relaxed for free variables)

All coefficients are stored as :class:`fractions.Fraction` so the solver
operates with *exact* rational arithmetic — no floating-point roundoff
pollution during pivoting.  This module also defines the :class:`LPResult`
container and :class:`LPStatus` enum returned by the solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Iterable, Sequence

__all__ = ["LPStatus", "LPResult", "LPProblem"]


class LPStatus(Enum):
    """Outcome of a simplex solve."""

    OPTIMAL = "optimal"
    UNBOUNDED = "unbounded"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"          # reserved for branch-and-bound limits
    NUMERICAL = "numerical"       # reserved for breakdown guards


@dataclass
class LPResult:
    """Solution of a linear program."""

    status: LPStatus
    objective_value: float | None = None
    solution: dict[str, float] = field(default_factory=dict)
    # shadow prices / dual values for each constraint (indexed by name)
    duals: dict[str, float] = field(default_factory=dict)
    # reduced costs for each structural variable
    reduced_costs: dict[str, float] = field(default_factory=dict)
    # number of simplex pivots performed (excludes Phase-I cleanup)
    iterations: int = 0
    # internal tableau snapshot — useful for advanced users / debugging
    basis: list[str] = field(default_factory=list)
    message: str = ""

    def __bool__(self) -> bool:  # convenience: "did we find an optimum?"
        return self.status is LPStatus.OPTIMAL

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        if self.status is LPStatus.OPTIMAL:
            return (
                f"LPResult(OPTIMAL, obj={self.objective_value:.6g}, "
                f"iters={self.iterations})"
            )
        return f"LPResult({self.status.name}, msg={self.message!r})"


@dataclass
class LPProblem:
    """A linear program in standard form.

    Parameters
    ----------
    name : str
        Human-readable problem name.
    objective : str
        ``"max"`` or ``"min"``.
    variables : sequence of str
        Ordered names of the decision variables.  Names must be valid
        identifiers (letters/digits/underscore, must not start with a digit).
    objective_coeffs : dict[str, int|str|Fraction]
        Coefficients of the objective row, keyed by variable name.
        Variables absent from the mapping default to zero.
    constraints : list of dict
        Each constraint dict has the keys:

        ``coeffs`` : dict[str, coeff]
            Left-hand-side coefficients.
        ``relation`` : ``"<="`` | ``"="`` | ``">="``
        ``rhs`` : int|str|Fraction
            Right-hand-side constant.
        ``name`` : str, optional
            Constraint identifier for dual reporting.
    bounds : dict[str, tuple]
        Lower/upper bounds per variable.  ``(lo, hi)`` where ``lo``/``hi``
        may be ``None`` for ±∞.  Variables not listed default to ``(0, None)``
        i.e. non-negative.  Use ``bounds={"x": (None, None)}`` for a free
        variable.
    integer : set[str]
        Names of integer-restricted variables (mixed-integer LP).
    """

    name: str = "lp"
    objective: str = "max"
    variables: tuple[str, ...] = ()
    objective_coeffs: dict[str, Fraction] = field(default_factory=dict)
    constraints: list[dict] = field(default_factory=list)
    bounds: dict[str, tuple] = field(default_factory=dict)
    integer: set[str] = field(default_factory=set)

    # ------------------------------------------------------------------ #
    # construction helpers
    # ------------------------------------------------------------------ #
    def __post_init__(self) -> None:
        self.objective = self.objective.lower()
        if self.objective not in ("max", "min"):
            raise ValueError(f"objective must be 'max' or 'min', got {self.objective!r}")
        if not self.variables:
            raise ValueError("at least one variable is required")
        self._validate_names(self.variables)
        # coerce objective coefficients to Fraction
        coerced: dict[str, Fraction] = {}
        for v, c in self.objective_coeffs.items():
            if v not in self.variables:
                raise ValueError(f"unknown objective variable {v!r}")
            coerced[v] = Fraction(c)
        # ensure every variable has an objective entry (default 0)
        for v in self.variables:
            coerced.setdefault(v, Fraction(0))
        self.objective_coeffs = coerced
        # normalise bounds
        norm_bounds: dict[str, tuple] = {}
        for v in self.variables:
            lo, hi = self.bounds.get(v, (Fraction(0), None))
            lo = None if lo is None else Fraction(lo)
            hi = None if hi is None else Fraction(hi)
            norm_bounds[v] = (lo, hi)
        self.bounds = norm_bounds
        # normalise integer set
        self.integer = {v for v in self.integer if v in self.variables}
        # validate & normalise constraints lazily — done in solver so we can
        # report richer errors; but we do a cheap sanity pass here.
        for i, c in enumerate(self.constraints):
            if "relation" not in c:
                raise ValueError(f"constraint {i} missing 'relation'")
            if c["relation"] not in ("<=", "=", ">="):
                raise ValueError(
                    f"constraint {i} has bad relation {c['relation']!r}"
                )

    @staticmethod
    def _validate_names(names: Iterable[str]) -> None:
        import re
        pat = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        for n in names:
            if not pat.match(n):
                raise ValueError(f"invalid variable name {n!r}")
            if n.startswith("_slack") or n.startswith("_art"):
                raise ValueError(
                    f"variable name {n!r} collides with internal namespace"
                )

    # ------------------------------------------------------------------ #
    # convenience builders
    # ------------------------------------------------------------------ #
    def num_constraints(self) -> int:
        return len(self.constraints)

    def num_vars(self) -> int:
        return len(self.variables)

    def is_integer(self) -> bool:
        return bool(self.integer)

    def add_constraint(self, coeffs: dict, relation: str, rhs, name: str | None = None) -> None:
        if relation not in ("<=", "=", ">="):
            raise ValueError(f"bad relation {relation!r}")
        c = {"coeffs": dict(coeffs), "relation": relation, "rhs": Fraction(rhs)}
        if name is not None:
            c["name"] = name
        self.constraints.append(c)

    def add_var(self, name: str, lb=None, ub=None, integer: bool = False) -> None:
        """Append a new decision variable at the end of the variable order."""
        self._validate_names([name])
        self.variables = tuple([*self.variables, name])
        lb = None if lb is None else Fraction(lb)
        ub = None if ub is None else Fraction(ub)
        self.bounds[name] = (lb, ub)
        if integer:
            self.integer.add(name)
        self.objective_coeffs.setdefault(name, Fraction(0))

    # ------------------------------------------------------------------ #
    # validation
    # ------------------------------------------------------------------ #
    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty if valid).

        Checks performed:
        * All constraint coefficients reference declared variables.
        * Bounds are consistent (lb <= ub when both are finite).
        * Integer variables have integer bounds (or None).
        * Constraint names are unique (if provided).
        * No duplicate variable names.
        """
        errors: list[str] = []
        var_set = set(self.variables)
        if len(var_set) != len(self.variables):
            errors.append("duplicate variable names in problem")
        # bounds consistency
        for v in self.variables:
            lo, hi = self.bounds.get(v, (Fraction(0), None))
            if lo is not None and hi is not None and lo > hi:
                errors.append(f"variable {v!r}: lower bound {lo} > upper bound {hi}")
            if v in self.integer:
                if lo is not None and lo != int(lo):
                    errors.append(f"integer variable {v!r} has non-integer lower bound {lo}")
                if hi is not None and hi != int(hi):
                    errors.append(f"integer variable {v!r} has non-integer upper bound {hi}")
        # constraint coefficients
        seen_names: set[str] = set()
        for i, c in enumerate(self.constraints):
            cname = c.get("name")
            if cname is not None:
                if cname in seen_names:
                    errors.append(f"constraint {i}: duplicate name {cname!r}")
                seen_names.add(cname)
            for vname in c.get("coeffs", {}):
                if vname not in var_set:
                    errors.append(f"constraint {i}: unknown variable {vname!r}")
            # check rhs is a number
            if "rhs" not in c:
                errors.append(f"constraint {i}: missing 'rhs'")
        return errors