"""Built-in type environments and primitive operators.

Provides a ready-to-use typing environment for common primitive operations
so that expressions such as ``1 + 2`` or ``(\\x. x == 0) 5`` can be inferred
without the user having to supply bindings manually.

Available environments:
    * :func:`primitives_env` — arithmetic, comparison, equality, boolean
    * :func:`list_env` — Nil / Cons constructors for the List ADT
    * :func:`maybe_env` — Nothing / Just constructors for the Maybe ADT
    * :func:`string_env` — string primitives (length, concat, append)
    * :func:`pair_env` — fst / snd for tuples
    * :func:`either_env` — Left / Right constructors for the Either ADT
    * :func:`default_env` — all of the above combined
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


def either_env() -> Dict[str, Scheme]:
    """Return scheme bindings for a polymorphic Either ADT::

        Left  : forall a b. a -> Either<a, b>
        Right : forall a b. b -> Either<a, b>
    """
    a, b = 0, 1
    Either_ab = TCon("Either", (TVar(a), TVar(b)))
    return {
        "Left": _poly([a, b], TFun(TVar(a), Either_ab)),
        "Right": _poly([a, b], TFun(TVar(b), Either_ab)),
    }


# ---------------------------------------------------------------------------
# String primitives
# ---------------------------------------------------------------------------

def string_env() -> Dict[str, Scheme]:
    """Return scheme bindings for string primitives::

        length   : String -> Int
        concat   : String -> String -> String
        append   : String -> String -> String
        reverse  : String -> String
        toUpper  : String -> String
        toLower  : String -> String
        substring: Int -> Int -> String -> String
        charAt   : Int -> String -> Int  (character code)
    """
    env: Dict[str, Scheme] = {}

    env["length"] = _mono(TFun(STRING, INT))
    env["concat"] = _mono(TFun(STRING, TFun(STRING, STRING)))
    env["append"] = _mono(TFun(STRING, TFun(STRING, STRING)))
    env["reverse"] = _mono(TFun(STRING, STRING))
    env["toUpper"] = _mono(TFun(STRING, STRING))
    env["toLower"] = _mono(TFun(STRING, STRING))
    # substring: Int -> Int -> String -> String
    env["substring"] = _mono(TFun(INT, TFun(INT, TFun(STRING, STRING))))
    # charAt: Int -> String -> Int (returns char code)
    env["charAt"] = _mono(TFun(INT, TFun(STRING, INT)))

    return env


# ---------------------------------------------------------------------------
# Tuple / pair primitives
# ---------------------------------------------------------------------------

def pair_env() -> Dict[str, Scheme]:
    """Return scheme bindings for pair primitives::

        fst : forall a b. (a, b) -> a
        snd : forall a b. (a, b) -> b
    """
    a, b = 0, 1
    Pair_ab = TCon("Tuple", (TVar(a), TVar(b)))
    return {
        "fst": _poly([a, b], TFun(Pair_ab, TVar(a))),
        "snd": _poly([a, b], TFun(Pair_ab, TVar(b))),
    }


# ---------------------------------------------------------------------------
# IO primitives (typing only — no side effects in a pure type system)
# ---------------------------------------------------------------------------

def io_env() -> Dict[str, Scheme]:
    """Return scheme bindings for IO primitives (typing only)::

        print   : Int -> Unit
        printS  : String -> Unit
        printB  : Bool -> Unit
        read    : Unit -> Int
        readS   : Unit -> String
    """
    env: Dict[str, Scheme] = {}
    from .types import UNIT
    env["print"] = _mono(TFun(INT, UNIT))
    env["printS"] = _mono(TFun(STRING, UNIT))
    env["printB"] = _mono(TFun(BOOL, UNIT))
    env["read"] = _mono(TFun(UNIT, INT))
    env["readS"] = _mono(TFun(UNIT, STRING))
    return env


# ---------------------------------------------------------------------------
# Combined default environment
# ---------------------------------------------------------------------------

def default_env() -> Dict[str, Scheme]:
    """Combine primitives + List + Maybe + Either + string + pair + io
    into one environment."""
    env: Dict[str, Scheme] = {}
    env.update(primitives_env())
    env.update(list_env())
    env.update(maybe_env())
    env.update(either_env())
    env.update(string_env())
    env.update(pair_env())
    env.update(io_env())
    return env