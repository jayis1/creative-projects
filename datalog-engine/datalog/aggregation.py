"""Aggregation support for the Datalog engine.

Datalog with aggregation extends plain Datalog with aggregate predicates
that compute a value over a group of tuples.  The syntax is::

    head(X, AggVal) :- body(...), agg<func>(Y, AggVal).

For example::

    dept_count(Dept, N) :- employee(_, Dept, _), count(E, N).

This module provides:

* ``AggregateRule`` — a rule where one body literal is an aggregate.
* ``eval_aggregate_rule`` — evaluates such rules by grouping bindings on
  the non-aggregate variables and computing the aggregate per group.

Supported aggregate functions: ``count``, ``sum``, ``min``, ``max``,
``avg``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .ast import Atom, Constant, Literal, Rule, Variable
from .builtins import is_aggregate
from .engine_types import Binding
from .evaluation import BodyEvaluator, atom_to_tuple, resolve


def _agg_func(name: str, values: List[Any]) -> Optional[Any]:
    """Compute an aggregate over a list of Python values."""
    if not values:
        return None
    if name == "count":
        return len(values)
    if name == "sum":
        return sum(values)
    if name == "min":
        return min(values)
    if name == "max":
        return max(values)
    if name == "avg":
        return sum(values) / len(values)
    return None


def is_aggregate_rule(rule: Rule) -> bool:
    """True if the rule contains an aggregate literal in its body."""
    return any(
        is_aggregate(lit.atom.predicate)
        for lit in rule.body
        if lit.positive
    )


def eval_aggregate_rule(
    rule: Rule,
    evaluator: BodyEvaluator,
    get_relation_fn,
) -> Set[Tuple[Constant, ...]]:
    """Evaluate a rule containing exactly one aggregate literal.

    The rule body is split into:

    * The **group part**: all non-aggregate positive literals (and all
      negative/built-in literals).  These are evaluated normally to
      produce a set of bindings.
    * The **aggregate literal**: ``agg_func(InputVar, OutputVar)``.

    Bindings are grouped by the values of the head variables that are
    *not* the aggregate output.  Within each group, the aggregate
    function is applied to all values of the aggregate input variable.

    Returns a set of head tuples.
    """
    # Find the aggregate literal
    agg_idx: Optional[int] = None
    for i, lit in enumerate(rule.body):
        if lit.positive and is_aggregate(lit.atom.predicate):
            agg_idx = i
            break
    if agg_idx is None:
        # Shouldn't happen — caller checks is_aggregate_rule
        return set()

    agg_lit = rule.body[agg_idx]
    agg_pred = agg_lit.atom.predicate
    agg_terms = agg_lit.atom.terms
    if len(agg_terms) != 2:
        from .errors import DatalogError
        raise DatalogError(
            f"aggregate {agg_pred} requires 2 arguments "
            f"(input, output), got {len(agg_terms)}"
        )

    # Input variable and output variable
    input_term = agg_terms[0]
    output_term = agg_terms[1]
    if not isinstance(output_term, Variable):
        from .errors import DatalogError
        raise DatalogError(
            f"aggregate output must be a variable, got {output_term}"
        )

    # Body without the aggregate literal
    non_agg_body = [
        lit for i, lit in enumerate(rule.body) if i != agg_idx
    ]

    # Evaluate the non-aggregate part to get all bindings
    bindings = evaluator.eval_body(non_agg_body, {}, {})

    # Group by head variables (excluding the aggregate output)
    # Identify which head positions are the aggregate output
    head_output_positions: List[int] = []
    head_group_positions: List[int] = []
    for i, t in enumerate(rule.head.terms):
        if isinstance(t, Variable) and t.name == output_term.name:
            head_output_positions.append(i)
        else:
            head_group_positions.append(i)

    # Build groups: group key (from head group positions) → list of input values
    groups: Dict[Tuple, List[Any]] = {}
    # Also store the full binding for the first member of each group,
    # so we can build the head tuple from group-variable values.
    group_bindings: Dict[Tuple, Binding] = {}
    for b in bindings:
        # Compute the group key from the head's group positions
        key_parts: List[Any] = []
        valid = True
        for i in head_group_positions:
            t = rule.head.terms[i]
            if isinstance(t, Constant):
                key_parts.append(t.value)
            elif isinstance(t, Variable):
                c = b.get(t.name)
                if c is None:
                    valid = False
                    break
                key_parts.append(c.value)
            else:
                valid = False
                break
        if not valid:
            continue
        key = tuple(key_parts)

        # Get the aggregate input value
        if isinstance(input_term, Constant):
            val = input_term.value
        elif isinstance(input_term, Variable):
            c = b.get(input_term.name)
            if c is None:
                continue
            val = c.value
        else:
            continue
        groups.setdefault(key, []).append(val)
        if key not in group_bindings:
            group_bindings[key] = b

    # Compute the aggregate for each group and build head tuples
    results: Set[Tuple[Constant, ...]] = set()
    for key, values in groups.items():
        agg_result = _agg_func(agg_pred, values)
        if agg_result is None:
            continue
        # Coerce integral floats to int for cleaner output
        if (
            isinstance(agg_result, float)
            and agg_result.is_integer()
            and all(isinstance(v, int) and not isinstance(v, bool) for v in values)
        ):
            agg_result = int(agg_result)

        agg_const = Constant(agg_result)
        # Build the head tuple from the head terms
        tup: List[Constant] = []
        for t in rule.head.terms:
            if isinstance(t, Constant):
                tup.append(t)
            elif isinstance(t, Variable):
                if t.name == output_term.name:
                    tup.append(agg_const)
                else:
                    c = group_bindings[key].get(t.name)
                    if c is None:
                        # Try to find it from the key
                        break
                    tup.append(c)
            else:
                break
        if len(tup) == len(rule.head.terms):
            results.add(tuple(tup))

    return results