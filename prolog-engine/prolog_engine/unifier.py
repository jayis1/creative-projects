"""Unification algorithm for the mini-Prolog engine.

Implements Robinson's unification algorithm with occurs-check,
plus helpers for applying and composing substitutions.
"""

from __future__ import annotations

from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Term, substitute,
)


class UnificationError(Exception):
    """Raised when two terms cannot be unified."""
    pass


class Substitution:
    """A mapping from Variables to Terms (a substitution / binding environment)."""

    def __init__(self, mapping: dict | None = None):
        self._mapping: dict[Variable, Term] = dict(mapping) if mapping else {}

    def __getitem__(self, var: Variable) -> Term:
        return self._mapping[var]

    def __setitem__(self, var: Variable, term: Term) -> None:
        self._mapping[var] = term

    def __contains__(self, var: Variable) -> bool:
        return var in self._mapping

    def __len__(self) -> int:
        return len(self._mapping)

    def __bool__(self) -> bool:
        return bool(self._mapping)

    def items(self):
        return self._mapping.items()

    def copy(self) -> "Substitution":
        return Substitution(dict(self._mapping))

    def apply(self, term: Term) -> Term:
        """Apply this substitution to a term, chasing variable bindings."""
        return substitute(term, self._mapping)

    def compose(self, other: "Substitution") -> "Substitution":
        """Compose two substitutions: apply other to all terms in self, then merge."""
        result = Substitution()
        # Apply other to all values in self
        for var, term in self._mapping.items():
            result[var] = other.apply(term)
        # Add all bindings from other whose variables are not in self
        for var, term in other._mapping.items():
            if var not in self._mapping:
                result[var] = term
        return result

    def restrict(self, variables: set[Variable]) -> "Substitution":
        """Restrict substitution to only contain bindings for the given variables."""
        return Substitution({v: t for v, t in self._mapping.items() if v in variables})

    def __repr__(self) -> str:
        pairs = ", ".join(f"{v.name}={t}" for v, t in self._mapping.items())
        return f"Substitution({{{pairs}}})"


class Unifier:
    """Robinson's unification algorithm with occurs-check."""

    @staticmethod
    def unify(t1: Term, t2: Term, subst: Substitution | None = None) -> Substitution:
        """
        Unify two terms under the given substitution.

        Returns a new substitution that makes t1 and t2 equal.
        Raises UnificationError if the terms cannot be unified.
        """
        if subst is None:
            subst = Substitution()

        t1 = subst.apply(t1)
        t2 = subst.apply(t2)

        # Same term → succeed
        if t1 == t2:
            return subst

        # Variable cases
        if isinstance(t1, Variable):
            return Unifier._unify_variable(t1, t2, subst)
        if isinstance(t2, Variable):
            return Unifier._unify_variable(t2, t1, subst)

        # Both compounds
        if isinstance(t1, Compound) and isinstance(t2, Compound):
            if t1.name != t2.name or t1.arity != t2.arity:
                raise UnificationError(
                    f"Cannot unify {t1} with {t2}: "
                    f"name/arity mismatch ({t1.name}/{t1.arity} vs {t2.name}/{t2.arity})"
                )
            for a1, a2 in zip(t1.args, t2.args):
                subst = Unifier.unify(a1, a2, subst)
            return subst

        # Incompatible types or values
        raise UnificationError(f"Cannot unify {t1} with {t2}")

    @staticmethod
    def _unify_variable(var: Variable, term: Term, subst: Substitution) -> Substitution:
        """Unify a variable with a term, performing occurs-check."""
        # If term is also a variable, apply substitution first
        if isinstance(term, Variable):
            if var == term:
                return subst
            # Both are unbound variables
            subst[var] = term
            return subst

        # Occurs check: variable must not appear in term
        if Unifier._occurs(var, term, subst):
            raise UnificationError(
                f"Occurs check failed: {var.name} appears in {term}"
            )

        subst[var] = term
        return subst

    @staticmethod
    def _occurs(var: Variable, term: Term, subst: Substitution) -> bool:
        """Check if var occurs in term (after applying subst)."""
        term = subst.apply(term)
        if isinstance(term, Variable):
            return var == term
        if isinstance(term, Compound):
            return any(Unifier._occurs(var, arg, subst) for arg in term.args)
        return False

    @staticmethod
    def match(pattern: Term, term: Term) -> Substitution | None:
        """
        One-way pattern matching (no instantiation of 'term' variables).
        Returns substitution if pattern matches term, or None.
        """
        try:
            return Unifier.unify(pattern, term)
        except UnificationError:
            return None