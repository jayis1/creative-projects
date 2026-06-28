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
from .parser import EInt, EBool, EVar, ELam, EApp, ELet, EIf, ETuple
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
    # Trace of inference steps for the --explain mode.
    trace: List[str] = field(default_factory=list)

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

    # -- trace helpers ----------------------------------------------------
    def _trace_step(self, msg: str) -> None:
        self.trace.append(msg)


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
        ctx._trace_step(f"int literal {expr.value} : Int")
        return INT, {}
    if isinstance(expr, EBool):
        ctx._trace_step(f"bool literal {expr.value} : Bool")
        return BOOL, {}
    if isinstance(expr, EVar):
        if expr.name not in ctx.env:
            raise InferError(f"Unbound variable: {expr.name!r}")
        sc = ctx.env[expr.name]
        t = ctx.instantiate(sc)
        ctx._trace_step(f"variable {expr.name} : {type_to_string(t)}")
        return t, {}
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
        param_t = apply_subst(s, tv)
        result = TFun(param_t, body_t)
        ctx._trace_step(f"lambda \\{expr.param}. ... : {type_to_string(result)}")
        return result, s
    if isinstance(expr, EApp):
        # infer fn type, infer arg type, unify fn with (arg -> fresh)
        fn_t, s1 = _infer(ctx, expr.fn)
        ctx.env = apply_subst_env(s1, ctx.env)
        arg_t, s2 = _infer(ctx, expr.arg)
        ctx.env = apply_subst_env(s2, ctx.env)
        ret_tv = ctx.fresh()
        s3 = unify(apply_subst(s2, fn_t), TFun(arg_t, ret_tv))
        s = compose_subst(s3, compose_subst(s2, s1))
        result = apply_subst(s3, ret_tv)
        ctx._trace_step(f"application : {type_to_string(result)}")
        return result, s
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
        result = apply_subst(s_branch, els_t)
        ctx._trace_step(f"if : {type_to_string(result)}")
        return result, s
    if isinstance(expr, ETuple):
        # ()        -> Unit
        # (a, b, c) -> Tuple<a, b, c>
        if len(expr.items) == 0:
            ctx._trace_step("unit () : Unit")
            return UNIT, {}
        item_types: List[object] = []
        s: Dict[int, object] = {}
        for item in expr.items:
            it, si = _infer(ctx, item)
            ctx.env = apply_subst_env(si, ctx.env)
            s = compose_subst(si, s)
            item_types.append(it)
        # Apply the full substitution to all items so they're consistent.
        item_types = [apply_subst(s, it) for it in item_types]
        result = TCon("Tuple", tuple(item_types))
        ctx._trace_step(f"tuple : {type_to_string(result)}")
        return result, s
    raise InferError(f"Cannot infer type for node {expr!r}")


def _infer_let(ctx: InferContext, expr: ELet) -> Tuple[object, Dict[int, object]]:
    val_t, s1 = _infer(ctx, expr.value)
    ctx.env = apply_subst_env(s1, ctx.env)
    # generalise the bound type
    scheme = ctx.generalise(apply_subst(s1, val_t))
    ctx._trace_step(
        f"let {expr.name} = ... : {scheme.vars and '∀' or ''}"
        f"{' '.join(str(v) for v in scheme.vars)} . {type_to_string(scheme.type)}"
        if scheme.vars else f"let {expr.name} = ... : {type_to_string(scheme.type)}"
    )
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

def infer(
    source_or_ast,
    *,
    env: Optional[Dict[str, Scheme]] = None,
    use_builtins: bool = False,
) -> object:
    """Infer the principal type of *source_or_ast*.

    If a string is given it is parsed first; if an AST node is given it is
    used directly.  An optional initial *env* of type schemes may be supplied
    to provide built-in identifiers.  When *use_builtins* is True the standard
    primitive environment (arithmetic/comparison/boolean operators, List,
    Maybe) is loaded.
    """
    if isinstance(source_or_ast, str):
        from .parser import parse
        ast = parse(source_or_ast)
    else:
        ast = source_or_ast
    initial_env: Dict[str, Scheme] = {}
    if use_builtins:
        from .primitives import default_env
        initial_env.update(default_env())
    if env:
        initial_env.update(env)
    ctx = InferContext(env=initial_env)
    try:
        t, s = _infer(ctx, ast)
    except UnificationError as e:
        raise InferError(_format_unify_error(e)) from e
    return apply_subst(s, t)


def infer_with_trace(
    source_or_ast,
    *,
    env: Optional[Dict[str, Scheme]] = None,
    use_builtins: bool = False,
) -> Tuple[object, List[str]]:
    """Like `infer` but also returns the list of trace messages produced
    during inference (useful for the ``--explain`` CLI flag)."""
    if isinstance(source_or_ast, str):
        from .parser import parse
        ast = parse(source_or_ast)
    else:
        ast = source_or_ast
    initial_env: Dict[str, Scheme] = {}
    if use_builtins:
        from .primitives import default_env
        initial_env.update(default_env())
    if env:
        initial_env.update(env)
    ctx = InferContext(env=initial_env)
    try:
        t, s = _infer(ctx, ast)
    except UnificationError as e:
        raise InferError(_format_unify_error(e)) from e
    return apply_subst(s, t), list(ctx.trace)


def _format_unify_error(e: UnificationError) -> str:
    """Produce a human-friendly message from a UnificationError."""
    try:
        t1 = type_to_string(e.t1)
        t2 = type_to_string(e.t2)
    except Exception:
        t1, t2 = str(e.t1), str(e.t2)
    base = f"Cannot unify {t1} with {t2}"
    if e.args and len(e.args) > 1:
        return f"{base} ({e.args[1]})" if len(e.args) > 1 else base
    return base