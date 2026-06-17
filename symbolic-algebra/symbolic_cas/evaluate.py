"""Numerical evaluation and integration."""

from __future__ import annotations

import math
from typing import Dict, Optional, Union

from symbolic_cas.expr import Expr, Num, Sym, UnaryOp, BinOp, Func, Pow


def evaluate(expr: Expr, mapping: Dict[str, Union[int, float]]) -> Union[int, float]:
    """Numerically evaluate the expression with the given variable bindings."""
    if isinstance(expr, Num):
        return expr.value

    if isinstance(expr, Sym):
        if expr.name in mapping:
            return mapping[expr.name]
        raise ValueError(f"Unbound variable: {expr.name}")

    if isinstance(expr, UnaryOp) and expr.op == '-':
        return -evaluate(expr.operand, mapping)

    if isinstance(expr, BinOp):
        left_val = evaluate(expr.left, mapping)
        right_val = evaluate(expr.right, mapping)
        if expr.op == '+':
            return left_val + right_val
        if expr.op == '-':
            return left_val - right_val
        if expr.op == '*':
            return left_val * right_val
        if expr.op == '/':
            return left_val / right_val

    if isinstance(expr, Pow):
        base_val = evaluate(expr.base, mapping)
        exp_val = evaluate(expr.exponent, mapping)
        result = base_val ** exp_val
        if isinstance(result, complex):
            raise ValueError(f"Complex result from ({base_val})^({exp_val}); complex numbers not supported")
        return result

    if isinstance(expr, Func):
        arg_val = evaluate(expr.arg, mapping)
        func_map = {
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'exp': math.exp, 'ln': math.log, 'sqrt': math.sqrt,
            'abs': abs, 'log2': math.log2, 'log10': math.log10,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
            'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
            'ceil': math.ceil, 'floor': math.floor,
            'sign': lambda x: 1 if x > 0 else (-1 if x < 0 else 0),
        }
        if expr.name in func_map:
            return func_map[expr.name](arg_val)
        raise ValueError(f"Cannot evaluate function: {expr.name}")

    raise ValueError(f"Cannot evaluate: {type(expr).__name__}")


def numerical_integrate(expr: Expr, var: str, a: float, b: float, n: int = 1000) -> float:
    """
    Numerically integrate ``expr`` from ``a`` to ``b`` using Simpson's rule.

    Uses n intervals (must be even). Higher n gives better accuracy.
    """
    if n % 2 != 0:
        n += 1  # Simpson's rule requires even number of intervals

    h = (b - a) / n
    total = 0.0

    # Evaluate at endpoints
    try:
        total += expr.evaluate({var: a})
    except (ValueError, ZeroDivisionError, OverflowError):
        pass
    try:
        total += expr.evaluate({var: b})
    except (ValueError, ZeroDivisionError, OverflowError):
        pass

    # Interior points
    for i in range(1, n):
        x_i = a + i * h
        try:
            val = expr.evaluate({var: x_i})
            if math.isnan(val) or math.isinf(val):
                continue
            if i % 2 == 0:
                total += 2 * val
            else:
                total += 4 * val
        except (ValueError, ZeroDivisionError, OverflowError):
            continue

    return total * h / 3