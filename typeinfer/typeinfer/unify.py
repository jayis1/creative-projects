"""Robinson unification over the HM type language.

A *substitution* is a mapping from type-variable ids to types.

The two core operations are:

* ``unify(a, b)`` — produce a substitution S such that  S(a) == S(b).
* ``apply_subst(s, t)`` — apply substitution *s* to type *t*.

We always include the *occurs check* to prevent the construction of infinite
types such as  ``a = a -> a``.
"""

from __future__ import annotations

from typing import Dict, Set

from .types import TVar, TCon, TFun, free_type_vars


# A substitution maps TVar ids -> Type.
Subst = Dict[int, object]


class UnificationError(Exception):
    """Raised when two types cannot be unified."""

    def __init__(self, t1: object, t2: object, reason: str = ""):
        self.t1 = t1
        self.t2 = t2
        super().__init__(f"Cannot unify {t1} with {t2}" + (f": {reason}" if reason else ""))


def occurs(vid: int, t: object) -> bool:
    """Occurs check: does TVar *vid* appear inside type *t*?"""
    return vid in free_type_vars(t)


def apply_subst(s: Subst, t: object) -> object:
    """Apply substitution *s* to type *t*, recursively."""
    if isinstance(t, TVar):
        if t.id in s:
            return apply_subst(s, s[t.id])
        return t
    if isinstance(t, TCon):
        return TCon(t.name, tuple(apply_subst(s, a) for a in t.args))
    if isinstance(t, TFun):
        return TFun(apply_subst(s, t.param), apply_subst(s, t.ret))
    raise TypeError(f"not a type: {t!r}")


def apply_subst_scheme(s: Subst, sc) -> "Scheme":  # noqa: F821
    """Apply *s* to a scheme, leaving quantified variables untouched."""
    from .types import Scheme
    s2 = {k: v for k, v in s.items() if k not in sc.vars}
    return Scheme(list(sc.vars), apply_subst(s2, sc.type))


def apply_subst_env(s: Subst, env: Dict[str, "Scheme"]) -> Dict[str, "Scheme"]:
    return {name: apply_subst_scheme(s, sc) for name, sc in env.items()}


def compose_subst(s1: Subst, s2: Subst) -> Subst:
    """Compose two substitutions:  (s1 ∘ s2)(t) = s1(s2(t)).

    s2 is applied first, then s1.  Variables in dom(s2) that are mapped by s1
    are removed from the result domain.
    """
    result: Subst = {}
    for k, v in s2.items():
        result[k] = apply_subst(s1, v)
    # now add bindings from s1 that are not in dom(s2)
    for k, v in s1.items():
        if k not in result:
            result[k] = v
    return result


def unify(t1: object, t2: object) -> Subst:
    """Unify two types, returning the most general unifier substitution."""
    # Function types
    if isinstance(t1, TFun) and isinstance(t2, TFun):
        s1 = unify(t1.param, t2.param)
        s2 = unify(apply_subst(s1, t1.ret), apply_subst(s1, t2.ret))
        return compose_subst(s2, s1)

    # Type constructors
    if isinstance(t1, TCon) and isinstance(t2, TCon):
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            raise UnificationError(t1, t2, "different type constructors")
        s: Subst = {}
        for a1, a2 in zip(t1.args, t2.args):
            s = compose_subst(unify(apply_subst(s, a1), apply_subst(s, a2)), s)
        return s

    # Type variable (left)
    if isinstance(t1, TVar):
        return _bind(t1.id, t2)

    # Type variable (right)
    if isinstance(t2, TVar):
        return _bind(t2.id, t1)

    raise UnificationError(t1, t2, "incompatible type shapes")


def _bind(vid: int, t: object) -> Subst:
    """Bind type variable *vid* to type *t*, with occurs check."""
    if isinstance(t, TVar) and t.id == vid:
        return {}  # reflexive
    if occurs(vid, t):
        raise UnificationError(TVar(vid), t, "occurs check failed (infinite type)")
    return {vid: t}