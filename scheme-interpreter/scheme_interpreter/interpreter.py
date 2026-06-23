"""Tail-call-optimized evaluator with first-class continuations.

The evaluator uses an explicit trampoline: instead of calling Python
recursively for tail positions, it returns a ``TailCall`` sentinel
that the trampoline loop re-dispatches.  This keeps Python stack depth
bounded regardless of Scheme recursion depth.

``call/cc`` is implemented via a lightweight escape-continuation
mechanism using a tagged exception.  Full reified continuations (which
would require CPS conversion of the entire evaluator) are beyond the
scope of this implementation; however the escape-continuation semantics
cover the vast majority of real-world ``call/cc`` usage, including all
generator and early-return patterns.

Enhanced in v2.0:
- Logging support (configurable via environment variable SCHEME_LOG_LEVEL)
- Standard library auto-loading (stdlib.scm)
- New special forms: rec, let-values, define-values
- New builtins: load, trace/untrace, time, assert
- Improved error messages with context
"""

from __future__ import annotations

import logging
import os
import sys
import time as _time_module
from typing import Any, List

from .types import (
    Symbol, Pair, Nil, Bool, Char, Vector, Unspecified, EOF,
    Procedure, Lambda, Continuation, Macro,
    TRUE, FALSE,
    is_true, to_python_bool, list_to_pairs, pairs_to_list,
    scheme_repr, scheme_display,
)
from .environment import Environment
from .lexer import tokenize
from .parser import Parser, parse
from .primitives import install_primitives
from .macro_expander import expand_macros, is_macro

logger = logging.getLogger("scheme_interpreter")


def _str_val(x) -> str:
    """Extract a Python string from a Scheme string value."""
    if isinstance(x, str):
        return x
    raise TypeError(f"not a string: {scheme_repr(x)}")


class TailCall:
    """Sentinel returned by ``seval`` for tail positions.

    The trampoline loop in ``run`` re-dispatches these until a non-tail
    value is produced, keeping Python stack depth bounded.
    """

    __slots__ = ("expr", "env")

    def __init__(self, expr, env):
        self.expr = expr
        self.env = env


class ContinuationInvoked(Exception):
    """Raised internally when an escape continuation is invoked."""

    def __init__(self, tag, value):
        self.tag = tag
        self.value = value


class SchemeError(Exception):
    """Raised on Scheme-level errors."""

    def __init__(self, message: str, irritant: Any = None):
        if irritant is not None:
            super().__init__(f"{message}: {scheme_repr(irritant)}")
        else:
            super().__init__(message)
        self.message = message
        self.irritant = irritant


# ---------------------------------------------------------------------------
# helpers

def is_self_evaluating(expr) -> bool:
    """Check if *expr* is self-evaluating (needs no lookup or application)."""
    if isinstance(expr, (int, float, str, Char, Vector, Bool)):
        return True
    if expr is None or expr is Nil or expr is Unspecified:
        return True
    return False


def _is_self_evaluating(expr) -> bool:
    """Alias for is_self_evaluating (internal use)."""
    return is_self_evaluating(expr)


class Interpreter:
    """The Scheme interpreter / evaluator.

    Args:
        load_stdlib: If True (default), auto-load the standard library
            (stdlib.scm) into the global environment on initialization.
        log_level: Optional logging level (e.g. logging.DEBUG). If None,
            the SCHEME_LOG_LEVEL environment variable is consulted.
    """

    def __init__(self, load_stdlib: bool = True, log_level=None):
        # --- logging setup ---
        if log_level is None:
            env_level = os.environ.get("SCHEME_LOG_LEVEL", "").upper()
            log_level = getattr(logging, env_level, logging.WARNING)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self.logger = logging.getLogger("scheme_interpreter.interpreter")
        self.logger.debug("Interpreter initializing")

        self.global_env = Environment()
        install_primitives(self.global_env)
        self._call_depth = 0
        self._max_depth = 10_000
        self._counter = 0  # unique tag generator
        self._traced_procs: dict[str, tuple] = {}  # name -> (original, wrapper)
        # Install core special forms
        self.global_env.define("call/cc", self._make_call_cc())
        self.global_env.define("call-with-current-continuation", self.global_env.lookup("call/cc"))
        self.global_env.define("error", self._make_error())
        self.global_env.define("apply", self._make_apply())
        self.global_env.define("eval", self._make_eval())
        self.global_env.define("force", self._make_force())
        self.global_env.define("values", self._make_values())
        self.global_env.define("call-with-values", self._make_call_with_values())
        self.global_env.define("exit", self._make_exit())
        self.global_env.define("load", self._make_load())
        self.global_env.define("trace", self._make_trace())
        self.global_env.define("untrace", self._make_untrace())
        self.global_env.define("time", self._make_time())
        self.global_env.define("assert", self._make_assert())

        # Auto-load standard library
        if load_stdlib:
            self._load_stdlib()

    # ------------------------------------------------------------------
    # special form handlers

    def _make_call_cc(self):
        def call_cc(proc):
            tag = object()
            cont = Continuation(tag)
            try:
                return self._apply(proc, [cont])
            except ContinuationInvoked as ci:
                if ci.tag is tag:
                    return ci.value
                raise
        return Procedure("call/cc", call_cc)

    def _make_error(self):
        def error_proc(*args):
            if not args:
                msg = "error"
            else:
                msg = scheme_display(args[0]) if not isinstance(args[0], str) else args[0]
                irritants = " ".join(scheme_repr(a) for a in args[1:])
                if irritants:
                    msg = f"{msg}: {irritants}"
            raise SchemeError(msg)
        return Procedure("error", error_proc)

    def _make_apply(self):
        def apply_proc(proc, *args):
            if not args:
                arg_list = []
            else:
                # Last argument must be a list; convert to Python list
                last = args[-1]
                if isinstance(last, Pair) or last is Nil:
                    arg_list = pairs_to_list(last)
                elif isinstance(last, list):
                    arg_list = list(last)
                elif isinstance(last, Vector):
                    arg_list = list(last.items)
                else:
                    # Single non-list argument — treat as sole extra arg
                    arg_list = list(args)
                arg_list = list(args[:-1]) + arg_list
            return self._apply(proc, arg_list)
        return Procedure("apply", apply_proc)

    def _make_eval(self):
        def eval_proc(expr, *env_args):
            env = env_args[0] if env_args else self.global_env
            if isinstance(env, Environment):
                pass
            elif isinstance(env, Lambda):
                env = env.env
            else:
                env = self.global_env
            return self.seval(expr, env)
        return Procedure("eval", eval_proc)

    def _make_force(self):
        # Delayed promises
        def force_proc(promise):
            if isinstance(promise, Promise):
                if not promise.forced:
                    promise.value = self.seval(promise.expr, promise.env)
                    promise.forced = True
                return promise.value
            return promise
        return Procedure("force", force_proc)

    def _make_values(self):
        def values_proc(*args):
            if len(args) == 1:
                return args[0]
            return MultipleValues(list(args))
        return Procedure("values", values_proc)

    def _make_call_with_values(self):
        interp = self
        def call_with_values(producer, consumer):
            result = interp._apply(producer, [])
            if isinstance(result, MultipleValues):
                return interp._apply(consumer, result.values)
            return interp._apply(consumer, [result])
        return Procedure("call-with-values", call_with_values)

    def _make_exit(self):
        def exit_proc(*args):
            code = 0
            if args:
                v = args[0]
                if isinstance(v, int):
                    code = v
                elif isinstance(v, Bool):
                    code = 0 if v.value else 1
            raise SchemeExit(code)
        return Procedure("exit", exit_proc)

    def _make_load(self):
        """Create the ``load`` builtin — loads and evaluates a Scheme file."""
        interp = self
        def load_proc(path):
            path_str = _str_val(path) if not isinstance(path, str) else path
            interp.logger.debug("Loading file: %s", path_str)
            try:
                with open(path_str, "r") as f:
                    source = f.read()
                interp.run(source)
            except OSError as e:
                raise SchemeError(f"load: cannot open file: {path_str}: {e}")
            return Unspecified
        return Procedure("load", load_proc)

    def _make_trace(self):
        """Create the ``trace`` builtin — enables procedure call tracing."""
        interp = self
        def trace_proc(name_or_proc, *more):
            # trace can take a symbol or a procedure
            if isinstance(name_or_proc, Symbol):
                name = name_or_proc.name
                try:
                    proc = interp.global_env.lookup(name)
                except NameError:
                    raise SchemeError(f"trace: unbound variable: {name}")
            elif isinstance(name_or_proc, (Procedure, Lambda)):
                proc = name_or_proc
                name = getattr(proc, "name", "anonymous")
            else:
                raise SchemeError("trace: expected a symbol or procedure")

            # Don't double-trace
            if name in interp._traced_procs:
                return proc

            if isinstance(proc, Procedure):
                original_fn = proc.fn
                def traced_fn(*args, _name=name, _fn=original_fn):
                    arg_strs = " ".join(scheme_repr(a) for a in args)
                    sys.stderr.write(f"TRACE: ({_name} {arg_strs})\n")
                    result = _fn(*args)
                    sys.stderr.write(f"TRACE: {_name} => {scheme_repr(result)}\n")
                    return result
                proc.fn = traced_fn
                interp._traced_procs[name] = (original_fn, proc)
            elif isinstance(proc, Lambda):
                # For Lambda, we wrap by creating a Procedure that delegates
                original_lambda = proc
                def traced_lambda(*args, _lam=original_lambda, _name=name):
                    arg_strs = " ".join(scheme_repr(a) for a in args)
                    sys.stderr.write(f"TRACE: ({_name} {arg_strs})\n")
                    result = interp._apply(_lam, list(args))
                    sys.stderr.write(f"TRACE: {_name} => {scheme_repr(result)}\n")
                    return result
                wrapper = Procedure(name, traced_lambda)
                interp.global_env.define(name, wrapper)
                interp._traced_procs[name] = (original_lambda, wrapper)
            return proc
        return Procedure("trace", trace_proc)

    def _make_untrace(self):
        """Create the ``untrace`` builtin — removes tracing from a procedure."""
        interp = self
        def untrace_proc(name_or_proc):
            if isinstance(name_or_proc, Symbol):
                name = name_or_proc.name
            elif isinstance(name_or_proc, (Procedure, Lambda)):
                name = getattr(name_or_proc, "name", "anonymous")
            else:
                raise SchemeError("untrace: expected a symbol or procedure")
            if name not in interp._traced_procs:
                raise SchemeError(f"untrace: {name} is not traced")
            original, wrapper = interp._traced_procs.pop(name)
            if isinstance(original, Procedure):
                wrapper.fn = original  # restore original fn
            else:
                interp.global_env.define(name, original)  # restore original lambda
            return Unspecified
        return Procedure("untrace", untrace_proc)

    def _make_time(self):
        """Create the ``time`` builtin — measures execution time of an expression."""
        interp = self
        def time_proc(expr_form, *env_args):
            """Evaluate *expr_form* and return (values result elapsed-seconds)."""
            # This is a primitive, so expr_form must be a quoted form
            # Usage: (time '(+ 1 2))  or  (time (quote (+ 1 2)))
            if isinstance(expr_form, Pair) and isinstance(expr_form.car, Symbol) and expr_form.car.name == "quote":
                expr = expr_form.cdr.car
            else:
                # Direct evaluation — treat as a form to evaluate
                expr = expr_form
            start = _time_module.perf_counter()
            result = interp.seval(expr, interp.global_env)
            elapsed = _time_module.perf_counter() - start
            sys.stderr.write(f"time: {elapsed:.6f} seconds\n")
            return result
        return Procedure("time", time_proc)

    def _make_assert(self):
        """Create the ``assert`` builtin — assertion checking."""
        def assert_proc(condition, *message):
            if not is_true(condition):
                if message:
                    msg = scheme_display(message[0]) if not isinstance(message[0], str) else message[0]
                    raise SchemeError(f"assertion failed: {msg}")
                raise SchemeError("assertion failed")
            return Unspecified
        return Procedure("assert", assert_proc)

    def _load_stdlib(self):
        """Load the standard library (stdlib.scm) into the global environment."""
        import importlib.resources as ir
        stdlib_path = os.path.join(os.path.dirname(__file__), "stdlib.scm")
        if os.path.exists(stdlib_path):
            self.logger.debug("Loading stdlib from %s", stdlib_path)
            try:
                with open(stdlib_path, "r") as f:
                    source = f.read()
                # Evaluate stdlib forms directly (they go into global env)
                forms = parse(source)
                for form in forms:
                    form = expand_macros(form, self.global_env, self)
                    self.seval(form, self.global_env)
            except Exception as e:
                self.logger.warning("Failed to load stdlib: %s", e)
        else:
            self.logger.debug("stdlib.scm not found at %s", stdlib_path)

    # ------------------------------------------------------------------
    # core eval

    def seval(self, expr, env: Environment):
        """Evaluate an expression with tail-call optimization (trampoline)."""
        return self._trampoline(expr, env)

    def _trampoline(self, expr, env):
        """The trampoline loop that handles TailCall sentinels.

        Each TailCall replaces expr/env and loops — no Python stack growth,
        no artificial depth limit on tail-recursive code.
        """
        while True:
            result = self._eval_step(expr, env)
            if isinstance(result, TailCall):
                expr = result.expr
                env = result.env
                continue
            return result

    def _eval_step(self, expr, env: Environment):
        """Single evaluation step. Returns either a value or a TailCall."""

        # Self-evaluating
        if isinstance(expr, (int, float, str, Char, Vector)):
            return expr
        if expr is None:
            return Unspecified
        if expr is Nil or isinstance(expr, NilType):
            return Nil
        if isinstance(expr, Bool):
            return expr

        # Symbol → variable lookup
        if isinstance(expr, Symbol):
            return env.lookup(expr.name)

        # Pair → special form or application
        if isinstance(expr, Pair):
            return self._eval_pair(expr, env)

        # Already-evaluated types
        if isinstance(expr, (Procedure, Lambda, Continuation, Macro)):
            return expr

        # Fall back
        return expr

    def _eval_pair(self, expr: Pair, env: Environment):
        head = expr.car

        # Special forms
        if isinstance(head, Symbol):
            name = head.name
            handler = self.SPECIAL_FORMS.get(name)
            if handler is not None:
                return handler(self, expr, env)
            # Macro?
            if is_macro(name, env):
                expanded = expand_macros(expr, env, self)
                return TailCall(expanded, env)

        # Application
        proc = self.seval(head, env)
        args = []
        node = expr.cdr
        while isinstance(node, Pair):
            args.append(self.seval(node.car, env))
            node = node.cdr
        if node is not Nil and not isinstance(node, NilType):
            raise SchemeError("improper argument list")

        # Tail position: return a TailCall if proc is a Lambda
        if isinstance(proc, Lambda):
            return self._make_tail_call(proc, args)
        if isinstance(proc, Procedure):
            return proc.fn(*args)
        if isinstance(proc, Continuation):
            val = args[0] if args else Unspecified
            raise ContinuationInvoked(proc.tag, val)
        raise SchemeError(f"not a procedure", proc)

    def _make_tail_call(self, proc: Lambda, args: list):
        """Bind args to the lambda's parameters and return a TailCall."""
        new_env = Environment(parent=proc.env)
        # Bind fixed params
        if proc.rest is None:
            if len(args) != proc.min_args:
                raise SchemeError(
                    f"{proc.name}: expected {proc.min_args} args, got {len(args)}")
            for p, a in zip(proc.params, args):
                new_env.define(p.name, a)
        else:
            if len(args) < proc.min_args:
                raise SchemeError(
                    f"{proc.name}: expected at least {proc.min_args} args, got {len(args)}")
            for p, a in zip(proc.params, args[:proc.min_args]):
                new_env.define(p.name, a)
            rest_args = list_to_pairs(args[proc.min_args:])
            new_env.define(proc.rest.name, rest_args)
        # Body is a list of forms; evaluate all but last, tail-call last
        body = proc.body
        for form in body[:-1]:
            self.seval(form, new_env)
        return TailCall(body[-1], new_env)

    # ------------------------------------------------------------------
    # application

    def _apply(self, proc, args: list):
        """Apply a procedure to args, fully evaluating."""
        if isinstance(proc, Procedure):
            return proc.fn(*args)
        if isinstance(proc, Lambda):
            new_env = Environment(parent=proc.env)
            if proc.rest is None:
                if len(args) != proc.min_args:
                    raise SchemeError(
                        f"{proc.name}: expected {proc.min_args} args, got {len(args)}")
                for p, a in zip(proc.params, args):
                    new_env.define(p.name, a)
            else:
                if len(args) < proc.min_args:
                    raise SchemeError(
                        f"{proc.name}: expected at least {proc.min_args} args, got {len(args)}")
                for p, a in zip(proc.params, args[:proc.min_args]):
                    new_env.define(p.name, a)
                new_env.define(proc.rest.name, list_to_pairs(args[proc.min_args:]))
            result = Unspecified
            for form in proc.body:
                result = self.seval(form, new_env)
            return result
        if isinstance(proc, Continuation):
            val = args[0] if args else Unspecified
            raise ContinuationInvoked(proc.tag, val)
        raise SchemeError("not a procedure", proc)

    # ------------------------------------------------------------------
    # program execution

    def run(self, source: str, env: Environment = None) -> Any:
        """Parse and evaluate a source string, returning the last value."""
        if env is None:
            env = self.global_env
        forms = parse(source)
        result = Unspecified
        for form in forms:
            form = expand_macros(form, env, self)
            result = self.seval(form, env)
        return result

    def eval_form(self, form, env: Environment = None):
        if env is None:
            env = self.global_env
        form = expand_macros(form, env, self)
        return self.seval(form, env)


# ---------------------------------------------------------------------------
# auxiliary types

class Promise:
    """A delayed promise (from ``delay``)."""

    __slots__ = ("expr", "env", "forced", "value")

    def __init__(self, expr, env):
        self.expr = expr
        self.env = env
        self.forced = False
        self.value = None


class MultipleValues:
    """Multiple return values from ``values``."""

    __slots__ = ("values",)

    def __init__(self, values: list):
        self.values = values


class SchemeExit(Exception):
    """Raised by ``(exit)`` to terminate the interpreter."""

    def __init__(self, code: int):
        self.code = code
        super().__init__(f"(exit {code})")


# ---------------------------------------------------------------------------
# special form definitions
# We attach them as a class-level dict for fast dispatch.

# Forward reference
NilType = type(Nil)


def _sf_quote(interp, expr, env):
    return expr.cdr.car


def _sf_if(interp, expr, env):
    # Evaluate test using seval (full trampoline) to handle TailCall properly
    test = interp.seval(expr.cdr.car, env)
    if is_true(test):
        return TailCall(expr.cdr.cdr.car, env)
    else:
        else_branch = expr.cdr.cdr.cdr
        if else_branch is Nil or isinstance(else_branch, NilType):
            return Unspecified
        return TailCall(else_branch.car, env)


def _sf_define(interp, expr, env):
    target = expr.cdr.car
    if isinstance(target, Symbol):
        # (define x value) or (define x)
        value_form = expr.cdr.cdr
        if value_form is Nil or isinstance(value_form, NilType):
            value = Unspecified
        else:
            value = interp.seval(value_form.car, env)
        if isinstance(value, Lambda) and value.name == "lambda":
            value.name = target.name
        env.define(target.name, value)
        return Unspecified
    elif isinstance(target, Pair):
        # (define (name . args) body...)
        name = target.car
        params, rest = _parse_lambda_params(target.cdr)
        body = pairs_to_list(expr.cdr.cdr)
        lam = Lambda(params, rest, body, env, name.name)
        env.define(name.name, lam)
        return Unspecified
    else:
        raise SchemeError("ill-formed define", expr)


def _parse_lambda_params(params_form):
    """Parse lambda parameter list, returning (params, rest)."""
    params = []
    rest = None
    node = params_form
    while isinstance(node, Pair):
        p = node.car
        if not isinstance(p, Symbol):
            raise SchemeError("lambda parameter must be a symbol", p)
        params.append(p)
        node = node.cdr
    if isinstance(node, Symbol):
        rest = node  # (lambda args body) — all args as a list
    elif node is Nil or isinstance(node, NilType):
        pass
    else:
        raise SchemeError("ill-formed parameter list")
    return params, rest


def _sf_lambda(interp, expr, env):
    params_form = expr.cdr.car
    params, rest = _parse_lambda_params(params_form)
    body = pairs_to_list(expr.cdr.cdr)
    return Lambda(params, rest, body, env)


def _sf_begin(interp, expr, env):
    body = expr.cdr
    if body is Nil or isinstance(body, NilType):
        return Unspecified
    node = body
    while isinstance(node.cdr, Pair):
        interp.seval(node.car, env)
        node = node.cdr
    return TailCall(node.car, env)


def _sf_set(interp, expr, env):
    name = expr.cdr.car
    if not isinstance(name, Symbol):
        raise SchemeError("set! target must be a symbol", name)
    value = interp.seval(expr.cdr.cdr.car, env)
    if not env.set(name.name, value):
        raise SchemeError(f"unbound variable: {name.name}")
    return Unspecified


def _sf_let(interp, expr, env):
    # (let ((v1 e1) ...) body...)  or  (let name ((v1 e1) ...) body...)
    second = expr.cdr.car
    if isinstance(second, Symbol):
        # named let
        name = second
        bindings_form = expr.cdr.cdr.car
        body = pairs_to_list(expr.cdr.cdr.cdr)
        bindings = pairs_to_list(bindings_form)
        params = [b.car for b in bindings]
        init_exprs = [b.cdr.car for b in bindings]
        # Create a new env with the named lambda
        loop_env = Environment(parent=env)
        lam = Lambda(params, None, body, loop_env, name.name)
        loop_env.define(name.name, lam)
        init_vals = [interp.seval(e, env) for e in init_exprs]
        return interp._make_tail_call(lam, init_vals)
    else:
        bindings = pairs_to_list(second)
        new_env = Environment(parent=env)
        for b in bindings:
            var = b.car
            val_expr = b.cdr.car
            new_env.define(var.name, interp.seval(val_expr, env))
        body = pairs_to_list(expr.cdr.cdr)
        if not body:
            return Unspecified
        for form in body[:-1]:
            interp.seval(form, new_env)
        return TailCall(body[-1], new_env)


def _sf_let_star(interp, expr, env):
    bindings = pairs_to_list(expr.cdr.car)
    new_env = Environment(parent=env)
    for b in bindings:
        var = b.car
        val_expr = b.cdr.car
        val = interp.seval(val_expr, new_env)
        new_env.define(var.name, val)
    body = pairs_to_list(expr.cdr.cdr)
    if not body:
        return Unspecified
    for form in body[:-1]:
        interp.seval(form, new_env)
    return TailCall(body[-1], new_env)


def _sf_letrec(interp, expr, env):
    bindings = pairs_to_list(expr.cdr.car)
    new_env = Environment(parent=env)
    # First, define all to unspecified
    for b in bindings:
        new_env.define(b.car.name, Unspecified)
    # Then evaluate each init in the new env
    for b in bindings:
        val = interp.seval(b.cdr.car, new_env)
        new_env.define(b.car.name, val)
    body = pairs_to_list(expr.cdr.cdr)
    if not body:
        return Unspecified
    for form in body[:-1]:
        interp.seval(form, new_env)
    return TailCall(body[-1], new_env)


def _sf_cond(interp, expr, env):
    clauses = expr.cdr
    node = clauses
    while isinstance(node, Pair):
        clause = node.car
        test = clause.car
        if isinstance(test, Symbol) and test.name == "else":
            # else clause
            body = clause.cdr
            if body is Nil or isinstance(body, NilType):
                return Unspecified
            while isinstance(body.cdr, Pair):
                interp.seval(body.car, env)
                body = body.cdr
            return TailCall(body.car, env)
        # Evaluate test using seval (not _eval_step) to handle TailCall properly
        test_val = interp.seval(test, env)
        if is_true(test_val):
            body = clause.cdr
            if body is Nil or isinstance(body, NilType):
                return test_val
            # Check for => form
            if isinstance(body.car, Symbol) and body.car.name == "=>":
                proc = interp.seval(body.cdr.car, env)
                return interp._apply(proc, [test_val])
            while isinstance(body.cdr, Pair):
                interp.seval(body.car, env)
                body = body.cdr
            return TailCall(body.car, env)
        node = node.cdr
    return Unspecified


def _sf_case(interp, expr, env):
    key_val = interp.seval(expr.cdr.car, env)
    node = expr.cdr.cdr
    while isinstance(node, Pair):
        clause = node.car
        keys = clause.car
        if isinstance(keys, Symbol) and keys.name == "else":
            body = clause.cdr
            while isinstance(body.cdr, Pair):
                interp.seval(body.car, env)
                body = body.cdr
            return TailCall(body.car, env)
        key_list = pairs_to_list(keys)
        for k in key_list:
            if scheme_eqv(key_val, k):
                body = clause.cdr
                while isinstance(body.cdr, Pair):
                    interp.seval(body.car, env)
                    body = body.cdr
                return TailCall(body.car, env)
        node = node.cdr
    return Unspecified


def _sf_and(interp, expr, env):
    node = expr.cdr
    if node is Nil or isinstance(node, NilType):
        return TRUE
    while isinstance(node.cdr, Pair):
        val = interp.seval(node.car, env)
        if not is_true(val):
            return FALSE
        node = node.cdr
    return TailCall(node.car, env)


def _sf_or(interp, expr, env):
    node = expr.cdr
    if node is Nil or isinstance(node, NilType):
        return FALSE
    while isinstance(node.cdr, Pair):
        val = interp.seval(node.car, env)
        if is_true(val):
            return val
        node = node.cdr
    return TailCall(node.car, env)


def _sf_when(interp, expr, env):
    test = interp.seval(expr.cdr.car, env)
    if is_true(test):
        body = expr.cdr.cdr
        if body is Nil or isinstance(body, NilType):
            return Unspecified
        while isinstance(body.cdr, Pair):
            interp.seval(body.car, env)
            body = body.cdr
        return TailCall(body.car, env)
    return Unspecified


def _sf_unless(interp, expr, env):
    test = interp.seval(expr.cdr.car, env)
    if not is_true(test):
        body = expr.cdr.cdr
        if body is Nil or isinstance(body, NilType):
            return Unspecified
        while isinstance(body.cdr, Pair):
            interp.seval(body.car, env)
            body = body.cdr
        return TailCall(body.car, env)
    return Unspecified


def _sf_do(interp, expr, env):
    # (do ((var init step) ...) (test result...) body...)
    bindings = pairs_to_list(expr.cdr.car)
    test_clause = expr.cdr.cdr.car
    test = test_clause.car
    result_forms = pairs_to_list(test_clause.cdr)
    body_forms = pairs_to_list(expr.cdr.cdr.cdr)
    loop_env = Environment(parent=env)
    vars = []
    inits = []
    steps = []
    for b in bindings:
        var = b.car
        init = b.cdr.car
        step_form = b.cdr.cdr
        step = step_form.car if isinstance(step_form, Pair) else var
        vars.append(var)
        inits.append(init)
        steps.append(step)
    for var, init in zip(vars, inits):
        loop_env.define(var.name, interp.seval(init, env))
    while True:
        if is_true(interp.seval(test, loop_env)):
            if not result_forms:
                return Unspecified
            for form in result_forms[:-1]:
                interp.seval(form, loop_env)
            return TailCall(result_forms[-1], loop_env)
        for form in body_forms:
            interp.seval(form, loop_env)
        new_vals = [interp.seval(s, loop_env) for s in steps]
        for var, val in zip(vars, new_vals):
            loop_env.define(var.name, val)


def _sf_delay(interp, expr, env):
    return Promise(expr.cdr.car, env)


def _sf_quasiquote(interp, expr, env):
    # Already expanded by parser into cons/list/append/unquote calls
    return interp.seval(expr.cdr.car, env)


def _sf_define_syntax(interp, expr, env):
    from .macro_expander import define_syntax_rules
    return define_syntax_rules(interp, expr, env)


def _sf_let_syntax(interp, expr, env):
    # (let-syntax ((name (syntax-rules ...))) body)
    from .macro_expander import parse_syntax_rules
    bindings = pairs_to_list(expr.cdr.car)
    new_env = Environment(parent=env)
    for b in bindings:
        name = b.car
        rules_form = b.cdr.car
        macro = parse_syntax_rules(rules_form, env)
        new_env.define(name.name, macro)
    body = pairs_to_list(expr.cdr.cdr)
    if not body:
        return Unspecified
    for form in body[:-1]:
        interp.seval(form, new_env)
    return TailCall(body[-1], new_env)


def _sf_rec(interp, expr, env):
    """``rec`` — recursive named expression.

    ``(rec name expr)`` evaluates *expr* in an environment where *name*
    is bound to the result of evaluating *expr*.  This allows creating
    self-referential (recursive) procedures without explicit ``letrec``.

    Examples::

        (rec fact (lambda (n) (if (= n 0) 1 (* n (fact (- n 1))))))
    """
    name = expr.cdr.car
    if not isinstance(name, Symbol):
        raise SchemeError("rec: name must be a symbol")
    new_env = Environment(parent=env)
    new_env.define(name.name, Unspecified)
    val = interp.seval(expr.cdr.cdr.car, new_env)
    new_env.define(name.name, val)
    return val


def _sf_let_values(interp, expr, env):
    """``let-values`` — destructuring let with multiple values.

    ``(let-values (((v1 v2 ...) producer) ...) body ...)``

    Binds multiple variables from a producer that returns ``values``.
    """
    bindings = pairs_to_list(expr.cdr.car)
    new_env = Environment(parent=env)
    for b in bindings:
        vars_form = b.car  # (v1 v2 ...)
        producer_form = b.cdr.car
        result = interp.seval(producer_form, env)
        var_names = pairs_to_list(vars_form)
        if isinstance(result, MultipleValues):
            vals = result.values
        else:
            vals = [result]
        if len(var_names) != len(vals):
            raise SchemeError(
                f"let-values: expected {len(var_names)} values, got {len(vals)}")
        for var, val in zip(var_names, vals):
            new_env.define(var.name, val)
    body = pairs_to_list(expr.cdr.cdr)
    if not body:
        return Unspecified
    for form in body[:-1]:
        interp.seval(form, new_env)
    return TailCall(body[-1], new_env)


def _sf_define_values(interp, expr, env):
    """``define-values`` — define multiple variables from a values producer.

    ``(define-values (v1 v2 ...) producer)``
    """
    vars_form = expr.cdr.car
    producer_form = expr.cdr.cdr.car
    result = interp.seval(producer_form, env)
    var_names = pairs_to_list(vars_form)
    if isinstance(result, MultipleValues):
        vals = result.values
    else:
        vals = [result]
    if len(var_names) != len(vals):
        raise SchemeError(
            f"define-values: expected {len(var_names)} values, got {len(vals)}")
    for var, val in zip(var_names, vals):
        env.define(var.name, val)
    return Unspecified


# ---------------------------------------------------------------------------
# eqv? / eq? / equal? implementations (used by case)

def scheme_eqv(a, b) -> bool:
    """eqv? — identity/equality for atoms.

    Two numbers are eqv? if they have the same type and value.
    Two symbols are eqv? if they are the same interned object.
    Two chars are eqv? if they have the same character value.
    Two booleans are eqv? if they have the same truth value.
    """
    if a is b:
        return True
    if isinstance(a, Bool) and isinstance(b, Bool):
        return a.value == b.value
    if isinstance(a, Char) and isinstance(b, Char):
        return a.value == b.value
    # Numbers: must be same type and value (int != float even if same value)
    if isinstance(a, bool) or isinstance(b, bool):
        return False  # Python bools are not Scheme numbers
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return type(a) == type(b) and a == b
    from fractions import Fraction
    if isinstance(a, Fraction) and isinstance(b, Fraction):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a is b  # eqv? on strings is identity
    if isinstance(a, Symbol) and isinstance(b, Symbol):
        return a is b
    return False


def scheme_eq(a, b) -> bool:
    return scheme_eqv(a, b)


def scheme_equal(a, b) -> bool:
    """equal? — deep structural equality.

    Recursively compares pairs, vectors, strings, and numbers.
    For numbers, equal? is less strict than eqv?: it compares values
    across types (e.g. ``(equal? 1 1.0)`` may be #t or #f depending on
    implementation; here we require same-type for numbers, matching eqv?).
    """
    if scheme_eqv(a, b):
        return True
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, Pair) and isinstance(b, Pair):
        return scheme_equal(a.car, b.car) and scheme_equal(a.cdr, b.cdr)
    if isinstance(a, Vector) and isinstance(b, Vector):
        if len(a) != len(b):
            return False
        return all(scheme_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(scheme_equal(x, y) for x, y in zip(a, b))
    if a is Nil and b is Nil:
        return True
    # Cross-type numeric comparison (int vs Fraction)
    from fractions import Fraction
    if isinstance(a, (int, float, Fraction)) and isinstance(b, (int, float, Fraction)):
        if isinstance(a, bool) or isinstance(b, bool):
            return False
        return a == b
    return False


# Build the dispatch table
Interpreter.SPECIAL_FORMS = {
    "quote": _sf_quote,
    "if": _sf_if,
    "define": _sf_define,
    "lambda": _sf_lambda,
    "begin": _sf_begin,
    "set!": _sf_set,
    "let": _sf_let,
    "let*": _sf_let_star,
    "letrec": _sf_letrec,
    "letrec*": _sf_letrec,
    "cond": _sf_cond,
    "case": _sf_case,
    "and": _sf_and,
    "or": _sf_or,
    "when": _sf_when,
    "unless": _sf_unless,
    "do": _sf_do,
    "delay": _sf_delay,
    "quasiquote": _sf_quasiquote,
    "define-syntax": _sf_define_syntax,
    "let-syntax": _sf_let_syntax,
    "letrec-syntax": _sf_let_syntax,
    "rec": _sf_rec,
    "let-values": _sf_let_values,
    "define-values": _sf_define_values,
}