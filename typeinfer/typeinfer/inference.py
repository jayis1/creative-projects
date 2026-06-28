"""Algorithm W — Hindley-Milner type inference.

The inference algorithm walks the AST and produces:

* the inferred *type* of the expression
* a *substitution* that makes the typing judgements consistent

The public entry point is :func:`infer`, which returns the principal type
of an expression (as a `Type`).

Supported AST nodes:
    EInt, EBool, EString, EVar, ELam (with optional param type),
    EApp, ELet (with optional var type), ELetMulti (parallel let),
    EIf, ETuple, EList (list literal), EMatch (pattern matching),
    EDataDecl (algebraic data type declarations).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .types import (
    TVar, TCon, TFun, Scheme,
    INT, BOOL, STRING, UNIT,
    free_type_vars, free_env_vars,
    type_to_string, resolve_type,
)
from .parser import (
    EInt, EBool, EString, EVar, ELam, EApp, ELet, ELetMulti, EIf, ETuple,
    EList, EMatch, EDataDecl,
    PVar, PConstr, PInt, PString, PWild, PTuple,
)
from .unify import (
    unify, apply_subst, apply_subst_env, apply_subst_scheme,
    compose_subst, UnificationError,
)

logger = logging.getLogger(__name__)


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
    # User-defined data types (name -> TCon template)
    data_types: Dict[str, TCon] = field(default_factory=dict)

    # -- fresh variable generation ----------------------------------------
    def fresh(self) -> TVar:
        v = TVar(self.counter)
        self.counter += 1
        logger.debug("fresh TVar(%d)", v.id)
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
        logger.debug("trace: %s", msg)


def _instantiate_type(t: object, mapping: Dict[int, object]) -> object:
    if isinstance(t, TVar):
        return mapping.get(t.id, t)
    if isinstance(t, TCon):
        return TCon(t.name, tuple(_instantiate_type(a, mapping) for a in t.args))
    if isinstance(t, TFun):
        return TFun(_instantiate_type(t.param, mapping), _instantiate_type(t.ret, mapping))
    raise TypeError(f"not a type: {t!r}")


# ---------------------------------------------------------------------------
# Pattern matching — extract variables and types from patterns
# ---------------------------------------------------------------------------

def _pattern_vars(pat: object) -> List[str]:
    """Return all variable names bound by a pattern."""
    if isinstance(pat, PVar):
        return [pat.name]
    if isinstance(pat, PWild):
        return []
    if isinstance(pat, PConstr):
        vs: List[str] = []
        for a in pat.args:
            vs.extend(_pattern_vars(a))
        return vs
    if isinstance(pat, PTuple):
        vs = []
        for a in pat.items:
            vs.extend(_pattern_vars(a))
        return vs
    # PInt, PString bind nothing
    return []


def _infer_pattern(
    ctx: InferContext,
    pat: object,
    expected_type: object,
    subst: Dict[int, object],
) -> Tuple[Dict[int, object], Dict[str, Scheme]]:
    """Infer the types of variables bound by *pat* given that the
    scrutinee has type *expected_type* (already after applying *subst*).

    Returns (updated_subst, bindings) where *bindings* maps variable names
    to monomorphic type schemes.
    """
    bindings: Dict[str, Scheme] = {}

    if isinstance(pat, PWild):
        return subst, bindings

    if isinstance(pat, PVar):
        t = apply_subst(subst, expected_type)
        bindings[pat.name] = Scheme([], t)
        return subst, bindings

    if isinstance(pat, PInt):
        s = unify(apply_subst(subst, expected_type), INT)
        return compose_subst(s, subst), bindings

    if isinstance(pat, PString):
        s = unify(apply_subst(subst, expected_type), STRING)
        return compose_subst(s, subst), bindings

    if isinstance(pat, PTuple):
        # The scrutinee must be a tuple of matching arity
        expected = apply_subst(subst, expected_type)
        if len(pat.items) == 0:
            s = unify(expected, UNIT)
            return compose_subst(s, subst), bindings
        # Create fresh expected types for each element
        elem_types = [ctx.fresh() for _ in pat.items]
        tuple_type = TCon("Tuple", tuple(elem_types))
        s = unify(expected, tuple_type)
        subst = compose_subst(s, subst)
        for p, et in zip(pat.items, elem_types):
            subst, b = _infer_pattern(ctx, p, et, subst)
            bindings.update(b)
        return subst, bindings

    if isinstance(pat, PConstr):
        # Look up the constructor in the environment
        expected = apply_subst(subst, expected_type)
        if pat.name not in ctx.env:
            raise InferError(f"Unknown constructor: {pat.name}")
        # Instantiate the constructor's scheme
        constr_scheme = ctx.env[pat.name]
        constr_type = ctx.instantiate(constr_scheme)
        # The constructor is a function from arg types to the result type
        # We unify the result of the constructor with expected_type
        result_type = constr_type
        # Fold over args: result_type = arg1 -> arg2 -> ... -> result
        arg_types: List[object] = []
        for ap in pat.args:
            # result_type must be a function: arg_type -> rest
            arg_t = ctx.fresh()
            ret_t = ctx.fresh()
            s = unify(result_type, TFun(arg_t, ret_t))
            subst = compose_subst(s, subst)
            result_type = apply_subst(subst, ret_t)
            arg_types.append(apply_subst(subst, arg_t))

        # Now unify the final result_type with expected
        s = unify(apply_subst(subst, result_type), expected)
        subst = compose_subst(s, subst)

        # Recurse into sub-patterns
        for ap, at in zip(pat.args, arg_types):
            subst, b = _infer_pattern(ctx, ap, at, subst)
            bindings.update(b)

        return subst, bindings

    raise InferError(f"Cannot infer pattern: {pat!r}")


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
    if isinstance(expr, EString):
        ctx._trace_step(f"string literal {expr.value!r} : String")
        return STRING, {}
    if isinstance(expr, EVar):
        if expr.name not in ctx.env:
            raise InferError(f"Unbound variable: {expr.name!r}")
        sc = ctx.env[expr.name]
        t = ctx.instantiate(sc)
        ctx._trace_step(f"variable {expr.name} : {type_to_string(t)}")
        return t, {}
    if isinstance(expr, ELam):
        # \x. body  ==>  x: T fresh, infer body under (env + x: T)
        if expr.param_type is not None:
            # Resolve the type annotation
            tv_map: Dict[str, TVar] = {}
            param_t = resolve_type(expr.param_type, ctx.fresh, tv_map, ctx.data_types)
        else:
            tv = ctx.fresh()
            param_t = tv
        new_env = dict(ctx.env)
        new_env[expr.param] = Scheme([], param_t)
        saved = ctx.env
        ctx.env = new_env
        try:
            body_t, s = _infer(ctx, expr.body)
        finally:
            ctx.env = saved
        resolved_param_t = apply_subst(s, param_t)
        result = TFun(resolved_param_t, body_t)
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
    if isinstance(expr, ELetMulti):
        return _infer_let_multi(ctx, expr)
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
    if isinstance(expr, EList):
        # [e1, e2, ...] -> List<a> where all elements have type a
        # [] -> List<a> (polymorphic empty list)
        if len(expr.items) == 0:
            elem_tv = ctx.fresh()
            result = TCon("List", (elem_tv,))
            ctx._trace_step("empty list [] : List<a>")
            return result, {}
        elem_types: List[object] = []
        s: Dict[int, object] = {}
        for item in expr.items:
            it, si = _infer(ctx, item)
            ctx.env = apply_subst_env(si, ctx.env)
            s = compose_subst(si, s)
            elem_types.append(it)
        # Unify all element types
        elem_types = [apply_subst(s, it) for it in elem_types]
        unified_elem = elem_types[0]
        for et in elem_types[1:]:
            s_unify = unify(unified_elem, et)
            s = compose_subst(s_unify, s)
            unified_elem = apply_subst(s, unified_elem)
        result = TCon("List", (apply_subst(s, unified_elem),))
        ctx._trace_step(f"list : {type_to_string(result)}")
        return result, s
    if isinstance(expr, EMatch):
        return _infer_match(ctx, expr)
    if isinstance(expr, EDataDecl):
        return _infer_data_decl(ctx, expr)
    raise InferError(f"Cannot infer type for node {expr!r}")


def _infer_let(ctx: InferContext, expr: ELet) -> Tuple[object, Dict[int, object]]:
    val_t, s1 = _infer(ctx, expr.value)
    ctx.env = apply_subst_env(s1, ctx.env)
    # Apply type annotation if provided
    if expr.var_type is not None:
        tv_map: Dict[str, TVar] = {}
        annotated_t = resolve_type(expr.var_type, ctx.fresh, tv_map, ctx.data_types)
        s_ann = unify(apply_subst(s1, val_t), annotated_t)
        s1 = compose_subst(s_ann, s1)
        ctx.env = apply_subst_env(s1, ctx.env)
        val_t = apply_subst(s1, val_t)
    # generalise the bound type
    scheme = ctx.generalise(apply_subst(s1, val_t))
    # Render the scheme nicely: use scheme_to_string so quantified vars
    # get named a, b, … rather than printing raw ids like ∀0.
    from .types import scheme_to_string
    ctx._trace_step(f"let {expr.name} = ... : {scheme_to_string(scheme)}")
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

    # Apply type annotation if provided
    if expr.var_type is not None:
        tv_map: Dict[str, TVar] = {}
        annotated_t = resolve_type(expr.var_type, ctx.fresh, tv_map, ctx.data_types)
        s_ann = unify(apply_subst(s1, val_t), annotated_t)
        s1 = compose_subst(s_ann, s1)
        ctx.env = apply_subst_env(s1, ctx.env)
        val_t = apply_subst(s1, val_t)

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


def _infer_let_multi(
    ctx: InferContext, expr: ELetMulti
) -> Tuple[object, Dict[int, object]]:
    """Parallel let bindings: let x = e1 and y = e2 in body.

    Each binding is inferred under the *original* environment (not the
    bindings of the other parallel lets), and then all are generalised
    together. This is like Haskell's ``let x = ... and y = ... in ...``.
    """
    saved_env = ctx.env
    schemes: Dict[str, Scheme] = {}
    s_total: Dict[int, object] = {}

    for name, value, var_type in expr.bindings:
        # Infer under the saved (original) env with accumulated substitution
        ctx.env = apply_subst_env(s_total, saved_env)
        val_t, s_i = _infer(ctx, value)
        s_total = compose_subst(s_i, s_total)
        ctx.env = apply_subst_env(s_total, saved_env)

        # Apply type annotation
        if var_type is not None:
            tv_map: Dict[str, TVar] = {}
            annotated_t = resolve_type(var_type, ctx.fresh, tv_map, ctx.data_types)
            s_ann = unify(apply_subst(s_total, val_t), annotated_t)
            s_total = compose_subst(s_ann, s_total)
            ctx.env = apply_subst_env(s_total, saved_env)
            val_t = apply_subst(s_total, val_t)

        resolved_val_t = apply_subst(s_total, val_t)
        scheme = ctx.generalise(resolved_val_t)
        schemes[name] = scheme

    # Add all schemes to the environment
    new_env = dict(apply_subst_env(s_total, saved_env))
    new_env.update(schemes)
    ctx.env = new_env
    try:
        body_t, s_body = _infer(ctx, expr.body)
    finally:
        ctx.env = saved_env
    s = compose_subst(s_body, s_total)
    return apply_subst(s, body_t), s


def _infer_match(
    ctx: InferContext, expr: EMatch
) -> Tuple[object, Dict[int, object]]:
    """Type inference for match expressions.

    Each alternative pattern is matched against the scrutinee type,
    binding variables, and the result type of all alternatives must unify.
    """
    scrut_t, s1 = _infer(ctx, expr.scrutinee)
    ctx.env = apply_subst_env(s1, ctx.env)

    result_tv = ctx.fresh()
    s_total = s1

    for pat, body_expr in expr.alts:
        # Infer the pattern: what types do the bound variables get?
        s_pat, bindings = _infer_pattern(ctx, pat, scrut_t, s_total)
        s_total = s_pat
        ctx.env = apply_subst_env(s_total, ctx.env)

        # Add pattern bindings to the environment
        new_env = dict(ctx.env)
        new_env.update(bindings)
        saved = ctx.env
        ctx.env = new_env
        try:
            body_t, s_body = _infer(ctx, body_expr)
        finally:
            ctx.env = saved

        s_total = compose_subst(s_body, s_total)
        ctx.env = apply_subst_env(s_total, ctx.env)

        # Unify body type with result type
        s_res = unify(apply_subst(s_total, body_t), apply_subst(s_total, result_tv))
        s_total = compose_subst(s_res, s_total)
        ctx.env = apply_subst_env(s_total, ctx.env)

    result = apply_subst(s_total, result_tv)
    ctx._trace_step(f"match : {type_to_string(result)}")
    return result, s_total


def _infer_data_decl(
    ctx: InferContext, expr: EDataDecl
) -> Tuple[object, Dict[int, object]]:
    """Type inference for data declarations.

    ``data List<a> = Nil | Cons a (List<a>) in body``

    This:
    1. Creates type-variable mappings for the type parameters.
    2. Registers the data type in ctx.data_types.
    3. Creates constructor schemes and adds them to the environment.
    4. Infers the body type.
    """
    # 1. Create type-variable mapping for the type parameters
    tv_map: Dict[str, TVar] = {}
    type_args = []
    for param_name in expr.type_params:
        tv = ctx.fresh()
        tv_map[param_name] = tv
        type_args.append(tv)

    # 2. Register the data type
    type_con = TCon(expr.type_name, tuple(type_args))
    ctx.data_types[expr.type_name] = type_con

    # 3. Create constructor schemes
    new_env = dict(ctx.env)
    for constr_name, arg_type_anns in expr.constructors:
        if arg_type_anns is not None:
            # Constructor with explicit argument types
            arg_types = [
                resolve_type(a, ctx.fresh, dict(tv_map), ctx.data_types)
                for a in arg_type_anns
            ]
            # Result type is the data type
            result_type = TCon(
                expr.type_name,
                tuple(tv_map[p] for p in expr.type_params),
            )
            # Fold into function type: arg1 -> arg2 -> ... -> result
            constr_type = result_type
            for at in reversed(arg_types):
                constr_type = TFun(at, constr_type)
            # Generalise over the type parameter vars
            quantified = sorted(free_type_vars(constr_type) & set(
                v.id for v in tv_map.values()
            ))
            scheme = Scheme(quantified, constr_type)
        else:
            # Constructor with no explicit args — nullary constructor
            # We need to figure out the type. For now, treat as polymorphic
            # with the data type's type parameters.
            result_type = TCon(
                expr.type_name,
                tuple(tv_map[p] for p in expr.type_params),
            )
            quantified = sorted(free_type_vars(result_type))
            scheme = Scheme(quantified, result_type)

        new_env[constr_name] = scheme

    # 4. Infer the body
    saved = ctx.env
    ctx.env = new_env
    try:
        body_t, s = _infer(ctx, expr.body)
    finally:
        ctx.env = saved

    ctx._trace_step(f"data {expr.type_name} : {type_to_string(body_t)}")
    return body_t, s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def infer(
    source_or_ast,
    *,
    env: Optional[Dict[str, Scheme]] = None,
    use_builtins: bool = False,
    data_types: Optional[Dict[str, TCon]] = None,
) -> object:
    """Infer the principal type of *source_or_ast*.

    If a string is given it is parsed first; if an AST node is given it is
    used directly.  An optional initial *env* of type schemes may be supplied
    to provide built-in identifiers.  When *use_builtins* is True the standard
    primitive environment (arithmetic/comparison/boolean operators, List,
    Maybe) is loaded.  *data_types* registers user-defined types for
    annotation resolution.
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
    if data_types:
        ctx.data_types.update(data_types)
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
    data_types: Optional[Dict[str, TCon]] = None,
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
    if data_types:
        ctx.data_types.update(data_types)
    try:
        t, s = _infer(ctx, ast)
    except UnificationError as e:
        raise InferError(_format_unify_error(e)) from e
    return apply_subst(s, t), list(ctx.trace)


def _format_unify_error(e: UnificationError) -> str:
    """Produce a human-friendly message from a UnificationError.

    The UnificationError stores the two types as ``e.t1`` and ``e.t2``,
    and the original message (including any reason) in ``e.args[0]``.
    We re-render the types with pretty names and append the reason if one
    was provided.
    """
    try:
        t1 = type_to_string(e.t1)
        t2 = type_to_string(e.t2)
    except Exception:
        t1, t2 = str(e.t1), str(e.t2)
    # The original args[0] is "Cannot unify X with Y: <reason>".
    # Extract the reason portion (after the colon) if present.
    reason = ""
    if e.args:
        msg = e.args[0]
        # Try to extract a reason after the last colon
        if ": " in msg:
            reason = msg.rsplit(": ", 1)[-1]
    if reason:
        return f"Cannot unify {t1} with {t2}: {reason}"
    return f"Cannot unify {t1} with {t2}"