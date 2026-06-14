"""
Core CSP data structures.

Defines Variable, Constraint, and CSP classes that form the backbone
of the constraint satisfaction problem framework.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# Type aliases for clarity
Domain = Set[int]
Assignment = Dict[str, int]
ConstraintFn = Callable[[Assignment], bool]


class Variable:
    """A CSP variable with a name and associated domain.

    Attributes:
        name: Unique identifier for this variable.
        domain: Set of allowable values.
    """

    __slots__ = ("name", "domain")

    def __init__(self, name: str, domain: Optional[Iterable[int]] = None) -> None:
        self.name: str = name
        self.domain: Domain = set(domain) if domain is not None else set()

    def __repr__(self) -> str:
        return f"Variable({self.name!r}, domain={sorted(self.domain)})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Variable):
            return self.name == other.name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)


class Constraint:
    """A constraint over a set of variables.

    A constraint specifies which combinations of values are allowed
    for a subset of variables. It stores:
      - scope: the variable names involved
      - satisfied: a callable that takes an assignment dict and returns bool

    For binary constraints (scope size == 2), we also store an optimized
    pair-check function for use in AC-3.
    """

    __slots__ = ("scope", "satisfied", "pair_check")

    def __init__(
        self,
        scope: Iterable[str],
        satisfied: ConstraintFn,
        pair_check: Optional[Callable[[int, int], bool]] = None,
    ) -> None:
        self.scope: Tuple[str, ...] = tuple(scope)
        if len(self.scope) != len(set(self.scope)):
            raise ValueError(f"Duplicate variable in constraint scope: {self.scope}")
        self.satisfied: ConstraintFn = satisfied
        # Optional fast binary check: pair_check(xi, xj) -> bool
        self.pair_check: Optional[Callable[[int, int], bool]] = pair_check

    @property
    def arity(self) -> int:
        return len(self.scope)

    def is_binary(self) -> bool:
        return self.arity == 2

    def __repr__(self) -> str:
        return f"Constraint(scope={self.scope}, arity={self.arity})"


class CSP:
    """A Constraint Satisfaction Problem.

    Collects variables, their domains, and constraints. Provides methods
    to query neighbors, constraints on a variable, and to build a
    consistent assignment incrementally.

    Args:
        variables: List of Variable objects.
        constraints: List of Constraint objects.
    """

    def __init__(
        self,
        variables: Optional[List[Variable]] = None,
        constraints: Optional[List[Constraint]] = None,
    ) -> None:
        self.variables: Dict[str, Variable] = {}
        self.constraints: List[Constraint] = []
        self._var_constraints: Dict[str, List[Constraint]] = {}
        self._neighbors: Dict[str, Set[str]] = {}

        if variables:
            for v in variables:
                self.add_variable(v)
        if constraints:
            for c in constraints:
                self.add_constraint(c)

    def add_variable(self, var: Variable) -> None:
        """Add a variable to the CSP."""
        if var.name in self.variables:
            raise ValueError(f"Variable {var.name!r} already exists")
        self.variables[var.name] = var
        self._var_constraints[var.name] = []
        self._neighbors[var.name] = set()

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint to the CSP.

        Validates that all variables in the constraint scope exist.
        """
        for var_name in constraint.scope:
            if var_name not in self.variables:
                raise ValueError(
                    f"Constraint references unknown variable {var_name!r}"
                )
        self.constraints.append(constraint)
        # Index constraint by each variable in scope
        for var_name in constraint.scope:
            self._var_constraints[var_name].append(constraint)
        # Build neighbor map for binary constraints
        if constraint.is_binary():
            a, b = constraint.scope
            self._neighbors[a].add(b)
            self._neighbors[b].add(a)
        else:
            # For n-ary constraints, all pairs in scope are neighbors
            scope = list(constraint.scope)
            for i in range(len(scope)):
                for j in range(i + 1, len(scope)):
                    self._neighbors[scope[i]].add(scope[j])
                    self._neighbors[scope[j]].add(scope[i])

    def get_neighbors(self, var_name: str) -> Set[str]:
        """Return the set of variable names connected to var_name."""
        return self._neighbors.get(var_name, set())

    def get_constraints(self, var_name: str) -> List[Constraint]:
        """Return all constraints involving var_name."""
        return self._var_constraints.get(var_name, [])

    def get_binary_constraints(
        self, var_i: str, var_j: str
    ) -> List[Constraint]:
        """Return constraints that involve exactly var_i and var_j (in either order)."""
        result = []
        for c in self._var_constraints.get(var_i, []):
            if c.is_binary():
                a, b = c.scope
                if (a == var_i and b == var_j) or (a == var_j and b == var_i):
                    result.append(c)
        return result

    def get_domain(self, var_name: str) -> Domain:
        """Return the current domain of a variable."""
        return self.variables[var_name].domain

    def is_consistent(
        self, var_name: str, value: int, assignment: Assignment
    ) -> bool:
        """Check if assigning var_name=value is consistent with assignment."""
        test = dict(assignment)
        test[var_name] = value
        for constraint in self.get_constraints(var_name):
            # Only check constraints where all variables are assigned
            if all(v in test for v in constraint.scope):
                if not constraint.satisfied(test):
                    return False
        return True

    def copy_domains(self) -> Dict[str, Domain]:
        """Return a deep copy of all variable domains."""
        return {name: set(var.domain) for name, var in self.variables.items()}

    def restore_domains(self, domains: Dict[str, Domain]) -> None:
        """Restore domains from a saved copy."""
        for name, dom in domains.items():
            self.variables[name].domain = dom

    def __repr__(self) -> str:
        return (
            f"CSP(variables={len(self.variables)}, "
            f"constraints={len(self.constraints)})"
        )