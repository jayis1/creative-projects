"""Body evaluation — evaluating rule bodies against relations.

This module implements the join-based evaluation of Datalog rule bodies:
given a list of literals and an initial binding, produce all satisfying
bindings.  Uses hash-indexed lookups for positive atoms, checks for
negated atoms, evaluates built-in predicates, and supports semi-naive
delta evaluation for recursive rules.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from .ast import Atom, Constant, Literal, Term, Variable
from .builtins import (
    BUILTIN_ARITH,
    BUILTIN_STRING,
    eval_binding_builtin,
    eval_comparison,
    eval_typecheck,
    is_aggregate,
    is_arithmetic,
    is_builtin,
    is_string_builtin,
    is_typecheck,
)
from .engine_types import Binding
from .relation import Relation_


# --------------------------------------------------------------------------- #
# Unification & resolution helpers                                           #
# --------------------------------------------------------------------------- #

def resolve(term: Term, binding: Binding) -> Optional[Constant]:
    """Resolve a term to a constant given a binding, or None if unbound."""
    if isinstance(term, Constant):
        return term
    if isinstance(term, Variable):
        return binding.get(term.name)
    return None


def unify_atom(
    atom: Atom, tup: Tuple[Constant, ...], binding: Binding
) -> Optional[Binding]:
    """Try to unify an atom's terms with a concrete tuple.

    Returns a new (extended) binding on success, or None on failure.
    """
    if atom.arity != len(tup):
        return None
    b: Binding = dict(binding)
    for term, val in zip(atom.terms, tup):
        if isinstance(term, Constant):
            if term != val:
                return None
        elif isinstance(term, Variable):
            if term.name in b:
                if b[term.name] != val:
                    return None
            else:
                b[term.name] = val
        else:
            return None
    return b


def atom_to_tuple(
    atom: Atom, binding: Binding
) -> Optional[Tuple[Constant, ...]]:
    """Ground an atom using a binding → tuple of constants, or None."""
    out: List[Constant] = []
    for term in atom.terms:
        c = resolve(term, binding)
        if c is None:
            return None
        out.append(c)
    return tuple(out)


def var_positions(
    atom: Atom, vars_of_interest: Iterable[str]
) -> Tuple[int, ...]:
    """Positions in the atom's term list where the given variables appear."""
    vs = set(vars_of_interest)
    return tuple(
        i
        for i, t in enumerate(atom.terms)
        if isinstance(t, Variable) and t.name in vs
    )


# --------------------------------------------------------------------------- #
# Body evaluator                                                             #
# --------------------------------------------------------------------------- #

class BodyEvaluator:
    """Evaluates rule bodies against stored relations.

    This class is instantiated by the engine and delegates relation
    lookups to callback functions, keeping it decoupled from the
    engine's internal storage layout.
    """

    def __init__(
        self,
        get_relation_fn,  # Callable[[str], Optional[Relation_]]
    ) -> None:
        self._get_relation = get_relation_fn

    # -- public API --

    def eval_body(
        self,
        body: List[Literal],
        binding: Binding,
        deltas: Dict[str, Relation_],
        force_delta_idx: Optional[int] = None,
        delta_rel: Optional[Relation_] = None,
    ) -> List[Binding]:
        """Evaluate a rule body, returning all satisfying bindings."""
        return self._eval_body_from(
            body, 0, [binding], deltas, force_delta_idx, delta_rel
        )

    def eval_positive(
        self, atom: Atom, rel: Relation_, binding: Binding
    ) -> List[Binding]:
        """Evaluate a positive atom against a relation.

        Uses hash-indexed lookup on bound positions for efficiency.
        If the atom is ground, checks membership directly.
        """
        if atom.is_ground():
            tup = tuple(atom.terms)
            if tup in rel:
                return [binding]
            return []

        bound_positions: List[int] = []
        bound_vals: List[Constant] = []
        for i, term in enumerate(atom.terms):
            if isinstance(term, Constant):
                bound_positions.append(i)
                bound_vals.append(term)
            elif isinstance(term, Variable):
                if term.name in binding:
                    bound_positions.append(i)
                    bound_vals.append(binding[term.name])

        candidates: Iterable[Tuple[Constant, ...]]
        if bound_positions:
            positions = tuple(bound_positions)
            key = tuple(bound_vals)
            candidates = rel.lookup(positions, key)
        else:
            candidates = rel.tuples

        results: List[Binding] = []
        for tup in candidates:
            b = unify_atom(atom, tup, binding)
            if b is not None:
                results.append(b)
        return results

    # -- internal --

    def _eval_body_from(
        self,
        body: List[Literal],
        idx: int,
        bindings: List[Binding],
        deltas: Dict[str, Relation_],
        force_delta_idx: Optional[int],
        delta_rel: Optional[Relation_],
    ) -> List[Binding]:
        if idx >= len(body):
            return bindings
        lit = body[idx]
        results: List[Binding] = []
        use_delta = force_delta_idx == idx
        for b in bindings:
            results.extend(
                self._eval_literal(lit, b, deltas, use_delta, delta_rel)
            )
        return self._eval_body_from(
            body, idx + 1, results, deltas, force_delta_idx, delta_rel
        )

    def _eval_literal(
        self,
        lit: Literal,
        binding: Binding,
        deltas: Dict[str, Relation_],
        use_delta: bool,
        delta_rel: Optional[Relation_],
    ) -> List[Binding]:
        pred = lit.atom.predicate

        # Arithmetic / string built-ins (binding, cannot be negated)
        if is_arithmetic(pred) or is_string_builtin(pred):
            if not lit.positive:
                from .errors import DatalogError
                raise DatalogError(
                    f"builtin {pred} cannot be negated"
                )
            result = eval_binding_builtin(pred, lit.atom.terms, binding)
            if result is not None:
                return [result]
            return []

        # Type-check built-ins (check-only)
        if is_typecheck(pred):
            if lit.positive:
                if eval_typecheck(pred, lit.atom.terms, binding):
                    return [binding]
                return []
            else:
                if not eval_typecheck(pred, lit.atom.terms, binding):
                    return [binding]
                return []

        # Comparison built-ins (check-only): <, >, <=, >=, !=, ==
        if is_builtin(pred) and not is_arithmetic(pred) and not is_string_builtin(pred) and not is_typecheck(pred) and not is_aggregate(pred):
            # This is a comparison built-in
            if lit.positive:
                if eval_comparison(pred, lit.atom.terms, binding):
                    return [binding]
                return []
            else:
                if not eval_comparison(pred, lit.atom.terms, binding):
                    return [binding]
                return []

        # Aggregate built-ins — handled specially by the engine, not here.
        if is_aggregate(pred):
            from .errors import DatalogError
            raise DatalogError(
                f"aggregate {pred} must be used in aggregate rules, "
                f"not in regular body evaluation"
            )

        # Regular predicate: select relation source
        if use_delta and delta_rel is not None:
            rel = delta_rel
        else:
            rel = self._get_relation(pred)

        if rel is None:
            if lit.positive:
                return []
            else:
                # not (empty relation) → succeeds with current binding
                return [binding]

        if lit.positive:
            return self.eval_positive(lit.atom, rel, binding)
        else:
            # Negated literal: succeeds if no tuple matches under binding.
            matches = self.eval_positive(lit.atom, rel, binding)
            if matches:
                return []
            return [binding]