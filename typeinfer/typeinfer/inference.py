"""Algorithm W — Hindley-Milner type inference.

The inference algorithm walks the AST and produces:

* the inferred *type* of the expression
* a *substitution* that makes the typing judgements consistent

The public entry point is :func:`infer`, which returns the principal type
of an expression (as a `Type`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .types import (
    TVar, TCon, TFun, Scheme,
    INT, BOOL, STRING, UNIT,
    free_type_vars, free_env_vars,
    type_to_string,
)
from .parser import EInt, EBool, EVar, ELam, EApp, ELet, EIf
from .unify import (
    unify, apply_subst, apply_subst_env, apply_subst_scheme,
    compose_subst, UnificationError,
)


class InferError(Exception):
    """Raised when type inference fails."""


@dataclass
class InferContext:
    """Mutable context used during inference — fresh-variable supply and
    the initial type environment."""

    counter: int = 0
    env: Dict[str, Scheme] = field(default_factory=dict)

    # -- fresh variable generation ----------------------------------------
    def fresh(self) -> TVar:
        v = TVar(self.counter)
        self.counter += 1
        return v

    # -- generalisation ---------------------------------------------------
    def generalise(self, t: object) -> Scheme:
        """Generalise *t* over variables not free in the environment."""
        env_vars = free_env_vars(self.env)
        quantified = sorted(free_type_vars(t) - env_vars)
        return Scheme(quantified, t)

    # -- instantiation ----------------------------------------------------
    def instantiate(self, sc: Scheme) -> object:
        """Instantiate a scheme by replacing quantified vars with fresh
        type variables."""
        mapping: Dict[int, object] = {v: self.fresh() for v in sc.vars}
        return _instantiate_type(sc.type, mapping)


def _instantiate_type(t: object, mapping: Dict[int, object]) -> object:
    if isinstance(t, TVar):
        return mapping.get(t.id, t)
    if isinstance(t, TCon):
        return TCon(t.name, tuple(_instantiate_type(a, mapping) for a in t.args))
    if isinstance(t, TFun):
        return TFun(_instantiate_type(t.param, mapping), _instantiate_type(t.ret, mapping))
    raise TypeError(f"not a type: {t!r}")


# ---------------------------------------------------------------------------
# Algorithm W
# ---------------------------------------------------------------------------

def _infer(ctx: InferContext, expr) -> Tuple[object, Dict[int, object]]:
    """Return (type, substitution) for *expr* under ctx.env."""
    if isinstance(expr, EInt):
        return INT, {}
    if isinstance(expr, EBool):
        return BOOL, {}
    if isinstance(expr, EVar):
        if expr.name not in ctx.env:
            raise InferError(f"Unbound variable: {expr.name!r}")
        return ctx.instantiate(ctx.env[expr.name]), {}
    if isinstance(expr, ELam):
        # \x. body  ==>  x: T fresh, infer body under (env + x: T)
        tv = ctx.fresh()
        new_env = dict(ctx.env)
        new_env[expr.param] = Scheme([], tv)
        saved = ctx.env
        ctx.env = new_env
        try:
            body_t, s = _infer(ctx, expr.body)
        finally:
            ctx.env = saved
        return TFun(apply_subst(s, tv), body_t), s
    if isinstance(expr, EApp):
        # infer fn type, infer arg type, unify fn with (arg -> fresh)
        fn_t, s1 = _infer(ctx, expr.fn)
        ctx.env = apply_subst_env(s1, ctx.env)
        arg_t, s2 = _infer(ctx, expr.arg)
        ctx.env = apply_subst_env(s2, ctx.env)
        ret_tv = ctx.fresh()
        s3 = unify(apply_subst(s2, fn_t), TFun(arg_t, ret_tv))
        s = compose_subst(s3, compose_subst(s2, s1))
        return apply_subst(s3, ret_tv), s
    if isinstance(expr, ELet):
        if expr.is_rec:
            return _infer_let_rec(ctx, expr)
        return _infer_let(ctx, expr)
    if isinstance(expr, EIf):
        cond_t, s1 = _infer(ctx, expr.cond)
        ctx.env = apply_subst_env(s1, ctx.env)
        s_cond = unify(cond_t, BOOL)
        s = compose_subst(s_cond, s1)
        ctx.env = apply_subst_env(s_cond, ctx.env)
        then_t, s2 = _infer(ctx, expr.then)
        ctx.env = apply_subst_env(s2, ctx.env)
        els_t, s3 = _infer(ctx, expr.els)
        ctx.env = apply_subst_env(s3, ctx.env)
        s_branch = unify(apply_subst(s3, then_t), els_t)
        s = compose_subst(s_branch, compose_subst(s3, compose_subst(s2, s)))
        return apply_subst(s_branch, els_t), s
    raise InferError(f"Cannot infer type for node {expr!r}")


def _infer_let(ctx: InferContext, expr: ELet) -> Tuple[object, Dict[int, object]]:
    val_t, s1 = _infer(ctx, expr.value)
    ctx.env = apply_subst_env(s1, ctx.env)
    # generalise the bound type
    scheme = ctx.generalise(apply_subst(s1, val_t))
    new_env = dict(ctx.env)
    new_env[expr.name] = scheme
    saved = ctx.env
    ctx.env = new_env
    try:
        body_t, s2 = _infer(ctx, expr.body)
    finally:
        ctx.env = saved
    s = compose_subst(s2, s1)
    return body_t, s


def _infer_let_rec(ctx: InferContext, expr: ELet) -> Tuple[object, Dict[int, object]]:
    r"""let rec f = \x. ... in body

    We add f : T_fresh (monomorphic) to the environment while inferring the
    value, then generalise.
    """
    tv = ctx.fresh()
    new_env = dict(ctx.env)
    new_env[expr.name] = Scheme([], tv)
    saved = ctx.env
    ctx.env = new_env
    try:
        val_t, s1 = _infer(ctx, expr.value)
    finally:
        ctx.env = saved
    # unify the fresh var with the inferred value type
    s_rec = unify(apply_subst(s1, tv), val_t)
    s1 = compose_subst(s_rec, s1)
    ctx.env = apply_subst_env(s1, ctx.env)
    scheme = ctx.generalise(apply_subst(s1, val_t))
    body_env = dict(ctx.env)
    body_env[expr.name] = scheme
    saved = ctx.env
    ctx.env = body_env
    try:
        body_t, s2 = _infer(ctx, expr.body)
    finally:
        ctx.env = saved
    s = compose_subst(s2, s1)
    return body_t, s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def infer(source_or_ast, *, env: Optional[Dict[str, Scheme]] = None) -> object:
    """Infer the principal type of *source_or_ast*.

    If a string is given it is parsed first; if an AST node is given it is
    used directly.  An optional initial *env* of type schemes may be supplied
    to provide built-in identifiers.
    """
    if isinstance(source_or_ast, str):
        from .parser import parse
        ast = parse(source_or_ast)
    else:
        ast = source_or_ast
    ctx = InferContext(env=dict(env) if env else {})
    try:
        t, s = _infer(ctx, ast)
    except UnificationError as e:
        raise InferError(str(e)) from e
    return apply_subst(s, t)