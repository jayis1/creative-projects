r"""Built-in type environments and primitive operators.

Provides a ready-to-use typing environment for common primitive operations
so that expressions such as ``1 + 2`` or ``(\x. x == 0) 5`` can be inferred
without the user having to supply bindings manually.
"""

from __future__ import annotations

from typing import Dict

from .types import TVar, TCon, TFun, Scheme, INT, BOOL, STRING


def _mono(t) -> Scheme:
    """A monomorphic (no quantifiers) scheme wrapping type *t*."""
    return Scheme([], t)


def _poly(vars_ids, t) -> Scheme:
    """A polymorphic scheme quantifying over *vars_ids*."""
    return Scheme(list(vars_ids), t)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def primitives_env() -> Dict[str, Scheme]:
    """Return a typing environment containing standard primitive operators.

    Arithmetic (Int -> Int -> Int):
        +  -  *  /

    Comparison (Int -> Int -> Bool):
        <  >  <=  >=

    Equality (a -> a -> Bool) — polymorphic but *not* generalised per-call;
    we model equality as ``a -> a -> Bool`` quantified once::

        ==  !=

    Boolean ops (Bool -> Bool -> Bool):
        &&  ||

    Conversions:
        not : Bool -> Bool
        neg : Int -> Int          (unary minus)
    """
    a = 0  # placeholder var id; schemes quantify by id, instantiation replaces

    env: Dict[str, Scheme] = {}

    # arithmetic — monomorphic Int
    for op in ("+", "-", "*", "/"):
        env[op] = _mono(TFun(INT, TFun(INT, INT)))

    # comparison — monomorphic Int
    for op in ("<", ">", "<=", ">="):
        env[op] = _mono(TFun(INT, TFun(INT, BOOL)))

    # polymorphic equality  forall a. a -> a -> Bool
    env["=="] = _poly([a], TFun(TVar(a), TFun(TVar(a), BOOL)))
    env["!="] = _poly([a], TFun(TVar(a), TFun(TVar(a), BOOL)))

    # boolean ops
    env["&&"] = _mono(TFun(BOOL, TFun(BOOL, BOOL)))
    env["||"] = _mono(TFun(BOOL, TFun(BOOL, BOOL)))
    env["not"] = _mono(TFun(BOOL, BOOL))

    # unary minus as a function: neg 5
    env["neg"] = _mono(TFun(INT, INT))

    return env


# ---------------------------------------------------------------------------
# ADT stubs (for future use / user extension)
# ---------------------------------------------------------------------------

def list_env() -> Dict[str, Scheme]:
    """Return scheme bindings for a polymorphic List ADT.

    Models::

        Nil   : forall a. List<a>
        Cons  : forall a. a -> List<a> -> List<a>
    """
    a = 0
    List_a = TCon("List", (TVar(a),))
    return {
        "Nil": _poly([a], List_a),
        "Cons": _poly([a], TFun(TVar(a), TFun(List_a, List_a))),
    }


def maybe_env() -> Dict[str, Scheme]:
    """Return scheme bindings for a polymorphic Maybe ADT::

        Nothing : forall a. Maybe<a>
        Just    : forall a. a -> Maybe<a>
    """
    a = 0
    Maybe_a = TCon("Maybe", (TVar(a),))
    return {
        "Nothing": _poly([a], Maybe_a),
        "Just": _poly([a], TFun(TVar(a), Maybe_a)),
    }


def default_env() -> Dict[str, Scheme]:
    """Combine primitives + List + Maybe into one environment."""
    env: Dict[str, Scheme] = {}
    env.update(primitives_env())
    env.update(list_env())
    env.update(maybe_env())
    return env