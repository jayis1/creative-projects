"""Type representations for the Hindley-Milner system.

We model types as a small algebraic data structure:

    type Type = TVar | TCon | TFun
    type Scheme = Forall [TVar] Type

A *type variable* (TVar) is a placeholder that may be unified with another
type.  A *type constructor* (TCon) is a concrete named type such as ``Int``
or ``Bool``.  A *function type* (TFun) is the arrow ``a -> b``.

A *type scheme* (Scheme) generalises a type by quantifying over a set of
type variables, e.g.  ``forall a. a -> a``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class TVar:
    """A type variable, identified by a unique integer id."""

    id: int

    def __str__(self) -> str:
        return _tvar_name(self.id)

    def __repr__(self) -> str:  # pragma: no cover - debugging only
        return f"TVar({self.id})"


@dataclass(frozen=True)
class TCon:
    """A concrete (nullary) type constructor, e.g. Int / Bool / String."""

    name: str
    args: tuple = field(default_factory=tuple)

    def __str__(self) -> str:
        if self.args:
            inner = ", ".join(str(a) for a in self.args)
            return f"{self.name}<{inner}>"
        return self.name

    def __repr__(self) -> str:  # pragma: no cover
        return f"TCon({self.name!r}, {self.args!r})"


@dataclass(frozen=True)
class TFun:
    """A function type ``param -> ret``."""

    param: object  # Type
    ret: object    # Type

    def __str__(self) -> str:
        p = _paren_if_fun(self.param)
        return f"{p} -> {self.ret}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"TFun({self.param!r}, {self.ret!r})"


# ---------------------------------------------------------------------------
# Type schemes (quantified types)
# ---------------------------------------------------------------------------

@dataclass
class Scheme:
    """A generalised type scheme: ``forall vars. type``."""

    vars: List[int]   # ids of quantified TVars
    type: object      # the underlying Type

    def __str__(self) -> str:
        if not self.vars:
            return str(self.type)
        names = " ".join(_tvar_name(v) for v in self.vars)
        return f"∀ {names}. {self.type}"


# ---------------------------------------------------------------------------
# Built-in type constants
# ---------------------------------------------------------------------------

INT = TCon("Int")
BOOL = TCon("Bool")
STRING = TCon("String")
UNIT = TCon("Unit")


# ---------------------------------------------------------------------------
# Variable naming — produce stable lowercase letters a, b, c, … a1, b1, …
# ---------------------------------------------------------------------------

_TVAR_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _tvar_name(vid: int) -> str:
    """Map a type-variable id to a printable name like ``a``, ``b``, …"""
    letter = _TVAR_LETTERS[vid % len(_TVAR_LETTERS)]
    suffix = vid // len(_TVAR_LETTERS)
    return f"{letter}{suffix}" if suffix else letter


def _paren_if_fun(t: object) -> str:
    """Wrap a function type in parentheses when it appears in argument
    position, so that ``(a -> b) -> c`` is unambiguous."""
    return f"({t})" if isinstance(t, TFun) else str(t)


# ---------------------------------------------------------------------------
# Free type variables
# ---------------------------------------------------------------------------

def free_type_vars(t: object) -> Set[int]:
    """Return the set of TVar ids occurring in *t*."""
    if isinstance(t, TVar):
        return {t.id}
    if isinstance(t, TCon):
        s: Set[int] = set()
        for a in t.args:
            s |= free_type_vars(a)
        return s
    if isinstance(t, TFun):
        return free_type_vars(t.param) | free_type_vars(t.ret)
    raise TypeError(f"not a type: {t!r}")


def free_scheme_vars(sc: Scheme) -> Set[int]:
    """Free type vars in a scheme = free vars of type minus quantified vars."""
    return free_type_vars(sc.type) - set(sc.vars)


def free_env_vars(env: Dict[str, Scheme]) -> Set[int]:
    """Union of free type vars across all schemes in *env*."""
    s: Set[int] = set()
    for sc in env.values():
        s |= free_scheme_vars(sc)
    return s


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def type_to_string(t: object) -> str:
    """Render a type (possibly with TVar ids) as a readable string."""
    # Renumber free variables to sequential a, b, c … for nicer output.
    renamed = _renumber_type(t)
    return str(renamed)


def scheme_to_string(sc: Scheme) -> str:
    """Render a type scheme, renaming all type variables to a, b, c ….

    Quantified variables are listed in the ``∀`` header; free variables
    get names that continue the sequence after the quantified ones so
    there is no clash.
    """
    if not sc.vars:
        return type_to_string(sc.type)
    # Build a single consistent mapping: quantified vars first (a, b, …),
    # then free vars (continuing the alphabet).
    mapping: Dict[int, str] = {}
    for v in sc.vars:
        mapping[v] = _tvar_name(len(mapping))
    # Add free vars in sorted order for determinism
    free = sorted(free_type_vars(sc.type) - set(sc.vars))
    for v in free:
        mapping.setdefault(v, _tvar_name(len(mapping)))
    body = _apply_names(sc.type, mapping)
    names = " ".join(mapping[v] for v in sc.vars)
    return f"∀ {names}. {body}"


def _renumber_type(t: object, mapping: Optional[Dict[int, int]] = None) -> object:
    """Return a copy of *t* with TVar ids renumbered sequentially."""
    if mapping is None:
        mapping = {}
    if isinstance(t, TVar):
        if t.id not in mapping:
            mapping[t.id] = len(mapping)
        return TVar(mapping[t.id])
    if isinstance(t, TCon):
        return TCon(t.name, tuple(_renumber_type(a, mapping) for a in t.args))
    if isinstance(t, TFun):
        return TFun(_renumber_type(t.param, mapping), _renumber_type(t.ret, mapping))
    raise TypeError(f"not a type: {t!r}")


def _apply_names(t: object, mapping: Dict[int, str]) -> str:
    if isinstance(t, TVar):
        return mapping.get(t.id, str(t))
    if isinstance(t, TCon):
        if t.args:
            inner = ", ".join(_apply_names(a, mapping) for a in t.args)
            return f"{t.name}<{inner}>"
        return t.name
    if isinstance(t, TFun):
        p = f"({_apply_names(t.param, mapping)})" if isinstance(t.param, TFun) else _apply_names(t.param, mapping)
        return f"{p} -> {_apply_names(t.ret, mapping)}"
    raise TypeError(f"not a type: {t!r}")