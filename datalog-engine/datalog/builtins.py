"""Built-in predicates for the Datalog engine.

This module defines three families of built-ins:

* **Comparison** (binary, check-only): ``<``, ``>``, ``<=``, ``>=``,
  ``!=``, ``==``.  These succeed or fail but never bind variables.
* **Arithmetic** (ternary, binding): ``add``, ``sub``, ``mul``, ``div``,
  ``idiv``, ``mod``.  The third argument receives the result.
* **String** (ternary, binding): ``concat``, ``substr``, ``strlen``.
  ``concat(X, Y, Z)`` binds Z = X + Y; ``substr(X, S, Z)`` binds Z to
  the substring of X starting at S; ``strlen(X, Z)`` binds Z to the
  length of X.
* **Type-check** (unary, check-only): ``is_int``, ``is_float``,
  ``is_str``, ``is_bool``.

All built-ins are registered here so that the parser, the safety
checker, and the evaluator can discover them in one place.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .ast import Constant, Term, Variable
from .engine_types import Binding


# --------------------------------------------------------------------------- #
# Comparison built-ins (binary, check-only)                                   #
# --------------------------------------------------------------------------- #

BUILTIN_BINARY: Dict[str, Callable[[Any, Any], bool]] = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "!=": lambda a, b: a != b,
    "==": lambda a, b: a == b,
}

# --------------------------------------------------------------------------- #
# Arithmetic built-ins (ternary: two inputs, one output)                     #
# --------------------------------------------------------------------------- #

BUILTIN_ARITH: Dict[str, Callable[[Any, Any], Any]] = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b if b != 0 else None,
    "idiv": lambda a, b: a // b if b != 0 else None,
    "mod": lambda a, b: a % b if b != 0 else None,
}

# --------------------------------------------------------------------------- #
# String built-ins (ternary: two inputs, one output)                         #
# --------------------------------------------------------------------------- #

BUILTIN_STRING: Dict[str, Callable[[Any, Any], Any]] = {
    "concat": lambda a, b: str(a) + str(b),
    # For substr/strlen, only the first arg is the string; the second
    # arg is the start index (substr) or ignored (strlen).  Both bind
    # their output to the 3rd argument.
    "substr": lambda a, b: str(a)[b:] if isinstance(b, int) and b >= 0 else None,
    "strlen": lambda a, _b: len(str(a)),
}

# --------------------------------------------------------------------------- #
# Type-check built-ins (unary, check-only)                                   #
# --------------------------------------------------------------------------- #

BUILTIN_TYPECHECK: Dict[str, Callable[[Any], bool]] = {
    "is_int": lambda a: isinstance(a, int) and not isinstance(a, bool),
    "is_float": lambda a: isinstance(a, float),
    "is_str": lambda a: isinstance(a, str),
    "is_bool": lambda a: isinstance(a, bool),
}

# --------------------------------------------------------------------------- #
# Aggregation built-ins (special: operate over grouped bindings)             #
# --------------------------------------------------------------------------- #

BUILTIN_AGGREG: set = {"count", "sum", "min", "max", "avg"}


# --------------------------------------------------------------------------- #
# Registry helpers                                                           #
# --------------------------------------------------------------------------- #

def all_builtin_names() -> set:
    """Return the set of all built-in predicate names."""
    return (
        set(BUILTIN_BINARY)
        | set(BUILTIN_ARITH)
        | set(BUILTIN_STRING)
        | set(BUILTIN_TYPECHECK)
        | BUILTIN_AGGREG
    )


def is_comparison(pred: str) -> bool:
    return pred in BUILTIN_BINARY


def is_arithmetic(pred: str) -> bool:
    return pred in BUILTIN_ARITH


def is_string_builtin(pred: str) -> bool:
    return pred in BUILTIN_STRING


def is_typecheck(pred: str) -> bool:
    return pred in BUILTIN_TYPECHECK


def is_aggregate(pred: str) -> bool:
    return pred in BUILTIN_AGGREG


def is_binding_builtin(pred: str) -> bool:
    """True for built-ins that bind their output argument (arith/string)."""
    return pred in BUILTIN_ARITH or pred in BUILTIN_STRING


def is_check_builtin(pred: str) -> bool:
    """True for built-ins that only check, never bind (comparison/typecheck)."""
    return pred in BUILTIN_BINARY or pred in BUILTIN_TYPECHECK


def is_builtin(pred: str) -> bool:
    """True for any built-in predicate."""
    return (
        pred in BUILTIN_BINARY
        or pred in BUILTIN_ARITH
        or pred in BUILTIN_STRING
        or pred in BUILTIN_TYPECHECK
        or pred in BUILTIN_AGGREG
    )


# --------------------------------------------------------------------------- #
# Evaluator functions                                                        #
# --------------------------------------------------------------------------- #

def _resolve_value(term: Term, binding: Binding) -> Optional[Any]:
    """Resolve a term to its Python value, or None if unbound."""
    if isinstance(term, Constant):
        return term.value
    if isinstance(term, Variable):
        c = binding.get(term.name)
        return c.value if c is not None else None
    return None


def eval_comparison(pred: str, terms: Tuple[Term, ...], binding: Binding) -> bool:
    """Evaluate a binary comparison built-in. Both terms must be bound."""
    if pred not in BUILTIN_BINARY:
        return False
    if len(terms) != 2:
        from .errors import DatalogError
        raise DatalogError(
            f"builtin {pred} requires 2 arguments, got {len(terms)}"
        )
    vals: List[Any] = []
    for t in terms:
        if isinstance(t, Constant):
            vals.append(t.value)
        elif isinstance(t, Variable):
            if t.name not in binding:
                return False  # unbound → cannot evaluate, treat as fail
            vals.append(binding[t.name].value)
        else:
            return False
    try:
        return BUILTIN_BINARY[pred](vals[0], vals[1])
    except TypeError:
        return False


def eval_typecheck(pred: str, terms: Tuple[Term, ...], binding: Binding) -> bool:
    """Evaluate a unary type-check built-in."""
    if pred not in BUILTIN_TYPECHECK:
        return False
    if len(terms) != 1:
        from .errors import DatalogError
        raise DatalogError(
            f"builtin {pred} requires 1 argument, got {len(terms)}"
        )
    t = terms[0]
    if isinstance(t, Constant):
        val = t.value
    elif isinstance(t, Variable):
        if t.name not in binding:
            return False
        val = binding[t.name].value
    else:
        return False
    return BUILTIN_TYPECHECK[pred](val)


def eval_binding_builtin(
    pred: str, terms: Tuple[Term, ...], binding: Binding
) -> Optional[Binding]:
    """Evaluate an arithmetic or string built-in that binds its output.

    The first N-1 arguments are inputs (must be bound); the last argument
    is the output variable that receives the result. Returns an extended
    binding or None on failure (e.g. division by zero, invalid substring).
    """
    table = BUILTIN_ARITH if pred in BUILTIN_ARITH else BUILTIN_STRING
    if pred not in table:
        return None
    if len(terms) != 3:
        from .errors import DatalogError
        raise DatalogError(
            f"builtin {pred} requires 3 arguments, got {len(terms)}"
        )
    vals: List[Any] = []
    for t in terms[:2]:
        if isinstance(t, Constant):
            vals.append(t.value)
        elif isinstance(t, Variable):
            if t.name not in binding:
                return None
            vals.append(binding[t.name].value)
        else:
            return None
    try:
        result = table[pred](vals[0], vals[1])
    except (TypeError, ValueError, IndexError):
        return None
    if result is None:
        return None
    # Coerce float-but-integral results to int when inputs are all int
    if (
        isinstance(result, float)
        and result.is_integer()
        and all(isinstance(v, int) and not isinstance(v, bool) for v in vals)
    ):
        result = int(result)

    result_const = Constant(result)
    out_term = terms[2]

    if isinstance(out_term, Variable):
        if out_term.name in binding:
            if binding[out_term.name] != result_const:
                return None
            return binding
        b = dict(binding)
        b[out_term.name] = result_const
        return b
    elif isinstance(out_term, Constant):
        if out_term == result_const:
            return binding
        return None
    return None