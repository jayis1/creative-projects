"""Calculus operations: differentiation and Taylor series."""

from __future__ import annotations

import math
from typing import Dict, FrozenSet, Optional, Union

from symbolic_cas.expr import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow, _wrap,
)


def differentiate(expr: Expr, var: str) -> Expr:
    """Symbolically differentiate ``expr`` with respect to ``var``."""
    if isinstance(expr, Num):
        return Num(0)

    if isinstance(expr, Sym):
        return Num(1) if expr.name == var else Num(0)

    if isinstance(expr, UnaryOp) and expr.op == '-':
        return UnaryOp('-', differentiate(expr.operand, var))

    if isinstance(expr, BinOp):
        if expr.op == '+':
            return BinOp('+', differentiate(expr.left, var), differentiate(expr.right, var))
        if expr.op == '-':
            return BinOp('-', differentiate(expr.left, var), differentiate(expr.right, var))
        if expr.op == '*':
            # Product rule: d(uv) = u'v + uv'
            u, v = expr.left, expr.right
            du, dv = differentiate(u, var), differentiate(v, var)
            return BinOp('+', BinOp('*', du, v), BinOp('*', u, dv))
        if expr.op == '/':
            # Quotient rule: d(u/v) = (u'v - uv') / v^2
            u, v = expr.left, expr.right
            du, dv = differentiate(u, var), differentiate(v, var)
            return BinOp('/', BinOp('-', BinOp('*', du, v), BinOp('*', u, dv)), Pow(v, Num(2)))

    if isinstance(expr, Pow):
        base, exp = expr.base, expr.exponent
        from symbolic_cas.substitute import collect_symbols
        base_has_var = var in collect_symbols(base)
        exp_has_var = var in collect_symbols(exp)

        if not base_has_var and not exp_has_var:
            return Num(0)

        if base_has_var and not exp_has_var:
            # Power rule: d(u^n) = n * u^(n-1) * u'
            du = differentiate(base, var)
            return BinOp('*', BinOp('*', exp, Pow(base, BinOp('-', exp, Num(1)))), du)

        if not base_has_var and exp_has_var:
            # d(a^v) = a^v * ln(a) * v'
            dv = differentiate(exp, var)
            return BinOp('*', BinOp('*', expr, Func('ln', base)), dv)

        # General case: d(u^v) = u^v * (v' * ln(u) + v * u'/u)
        du = differentiate(base, var)
        dv = differentiate(exp, var)
        return BinOp('*', expr, BinOp('+', BinOp('*', dv, Func('ln', base)), BinOp('*', exp, BinOp('/', du, base))))

    if isinstance(expr, Func):
        arg = expr.arg
        darg = differentiate(arg, var)
        name = expr.name

        if name == 'sin':
            return BinOp('*', Func('cos', arg), darg)
        if name == 'cos':
            return BinOp('*', UnaryOp('-', Func('sin', arg)), darg)
        if name == 'tan':
            return BinOp('*', Pow(Func('cos', arg), Num(-2)), darg)
        if name == 'exp':
            return BinOp('*', expr, darg)
        if name == 'ln':
            return BinOp('*', BinOp('/', Num(1), arg), darg)
        if name == 'sqrt':
            return BinOp('*', BinOp('/', Num(1), BinOp('*', Num(2), Func('sqrt', arg))), darg)
        if name == 'abs':
            # d(|x|) = sign(x) * x'
            return BinOp('*', Func('sign', arg), darg)
        if name == 'asin':
            return BinOp('*', BinOp('/', Num(1), Func('sqrt', BinOp('-', Num(1), Pow(arg, Num(2))))), darg)
        if name == 'acos':
            return BinOp('*', UnaryOp('-', BinOp('/', Num(1), Func('sqrt', BinOp('-', Num(1), Pow(arg, Num(2)))))), darg)
        if name == 'atan':
            return BinOp('*', BinOp('/', Num(1), BinOp('+', Num(1), Pow(arg, Num(2)))), darg)
        if name == 'sinh':
            return BinOp('*', Func('cosh', arg), darg)
        if name == 'cosh':
            return BinOp('*', Func('sinh', arg), darg)
        if name == 'tanh':
            return BinOp('*', BinOp('-', Num(1), Pow(Func('tanh', arg), Num(2))), darg)
        if name == 'log':
            return BinOp('*', BinOp('/', Num(1), arg), darg)
        if name == 'log2':
            return BinOp('*', BinOp('/', Num(1), BinOp('*', arg, Func('ln', Num(2)))), darg)
        if name == 'log10':
            return BinOp('*', BinOp('/', Num(1), BinOp('*', arg, Func('ln', Num(10)))), darg)

        raise ValueError(f"Differentiation not implemented for function: {name}")

    raise ValueError(f"Differentiation not implemented for: {type(expr).__name__}")


def taylor_series(expr: Expr, var: str, point: Union[int, float] = 0, order: int = 5) -> Expr:
    """
    Compute the Taylor series expansion of ``expr`` around ``point`` up to ``order`` terms.

    The Taylor series of f(x) around x=a is:
        f(x) = Σ [f^(n)(a) / n!] * (x - a)^n

    Returns a symbolic expression representing the polynomial approximation.
    """
    from symbolic_cas.simplify import simplify

    h = Sym(var)
    delta = BinOp('-', h, Num(point)) if point != 0 else h

    result: Optional[Expr] = None
    derivative = expr
    factorial = 1

    for n_iter in range(order + 1):
        if n_iter == 0:
            f_n_a = expr
        else:
            derivative = differentiate(derivative, var)
            f_n_a = derivative

        # Substitute x = point to get f^(n)(a)
        try:
            val = f_n_a.substitute({var: Num(point)}).simplify()
        except (ValueError, ZeroDivisionError, OverflowError):
            val = Num(0)

        if n_iter > 0:
            factorial *= n_iter

        if isinstance(val, Num) and val.value == 0:
            continue

        coeff = simplify(BinOp('/', val, Num(factorial)))

        if n_iter == 0:
            term = coeff
        elif point == 0:
            term = simplify(BinOp('*', coeff, Pow(h, Num(n_iter))))
        else:
            term = simplify(BinOp('*', coeff, Pow(delta, Num(n_iter))))

        if result is None:
            result = term
        else:
            result = BinOp('+', result, term)

    return simplify(result) if result is not None else Num(0)