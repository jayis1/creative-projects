"""Simplification, expansion, and factorization of expressions."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Union

from symbolic_cas.expr import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow, _wrap,
)


def simplify(expr: Expr) -> Expr:
    """Simplify an expression by applying algebraic rules iteratively, including trig identities."""
    prev = None
    current = expr
    for _ in range(20):  # max iterations to prevent infinite loops
        simplified = _simplify_once(current)
        simplified = _simplify_trig(simplified)
        if simplified == current or simplified == prev:
            break
        prev = current
        current = simplified
    return current


def _simplify_once(expr: Expr) -> Expr:
    """One pass of simplification."""
    if isinstance(expr, (Num, Sym)):
        return expr

    if isinstance(expr, UnaryOp) and expr.op == '-':
        inner = _simplify_once(expr.operand)
        # Double negation: -(-x) = x
        if isinstance(inner, UnaryOp) and inner.op == '-':
            return inner.operand
        # -0 = 0
        if isinstance(inner, Num) and inner.value == 0:
            return Num(0)
        # -(num) = Num(-value)
        if isinstance(inner, Num):
            return Num(-inner.value)
        return UnaryOp('-', inner)

    if isinstance(expr, Pow):
        base = _simplify_once(expr.base)
        exp = _simplify_once(expr.exponent)

        # x^0 = 1
        if isinstance(exp, Num) and exp.value == 0:
            return Num(1)
        # x^1 = x
        if isinstance(exp, Num) and exp.value == 1:
            return base
        # 0^x = 0 (for x > 0); note: 0^0 = 1 is handled by x^0 = 1 above
        if isinstance(base, Num) and base.value == 0:
            if isinstance(exp, Num) and exp.value <= 0:
                return Pow(base, exp)
            if not isinstance(exp, Num):
                return Num(0)
            return Num(0)
        # 1^x = 1
        if isinstance(base, Num) and base.value == 1:
            return Num(1)
        # num^num = evaluate
        if isinstance(base, Num) and isinstance(exp, Num):
            try:
                result = base.value ** exp.value
                if isinstance(result, complex):
                    return Pow(base, exp)
                if result == int(result):
                    result = int(result)
                return Num(result)
            except (OverflowError, ZeroDivisionError, ValueError):
                return Pow(base, exp)
        return Pow(base, exp)

    if isinstance(expr, Func):
        arg = _simplify_once(expr.arg)
        # Evaluate known functions on constants
        if isinstance(arg, Num):
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
                try:
                    result = func_map[expr.name](arg.value)
                    if isinstance(result, float) and result == int(result) and not math.isnan(result) and not math.isinf(result):
                        result = int(result)
                    return Num(result)
                except (ValueError, OverflowError, ZeroDivisionError):
                    pass
        return Func(expr.name, arg)

    if isinstance(expr, BinOp):
        left = _simplify_once(expr.left)
        right = _simplify_once(expr.right)
        op = expr.op

        # Constant folding: both sides are numbers
        if isinstance(left, Num) and isinstance(right, Num):
            try:
                if op == '+':
                    return Num(left.value + right.value)
                if op == '-':
                    return Num(left.value - right.value)
                if op == '*':
                    return Num(left.value * right.value)
                if op == '/':
                    if right.value == 0:
                        return BinOp('/', left, right)  # don't divide by zero
                    result = left.value / right.value
                    if result == int(result):
                        result = int(result)
                    return Num(result)
            except (OverflowError, ZeroDivisionError):
                pass

        # Additive identities
        if op == '+':
            if isinstance(left, Num) and left.value == 0:
                return right
            if isinstance(right, Num) and right.value == 0:
                return left
            # x + (-y) = x - y
            if isinstance(right, UnaryOp) and right.op == '-':
                return _simplify_once(BinOp('-', left, right.operand))
            # (-x) + y = y - x
            if isinstance(left, UnaryOp) and left.op == '-':
                return _simplify_once(BinOp('-', right, left.operand))

        if op == '-':
            if isinstance(right, Num) and right.value == 0:
                return left
            if isinstance(left, Num) and left.value == 0:
                return _simplify_once(UnaryOp('-', right))
            # x - x = 0
            if left == right:
                return Num(0)
            # x - (-y) = x + y
            if isinstance(right, UnaryOp) and right.op == '-':
                return _simplify_once(BinOp('+', left, right.operand))

        # Multiplicative identities
        if op == '*':
            if isinstance(left, Num) and left.value == 0:
                return Num(0)
            if isinstance(right, Num) and right.value == 0:
                return Num(0)
            if isinstance(left, Num) and left.value == 1:
                return right
            if isinstance(right, Num) and right.value == 1:
                return left
            # x * (-1) = -x
            if isinstance(left, Num) and left.value == -1:
                return _simplify_once(UnaryOp('-', right))
            if isinstance(right, Num) and right.value == -1:
                return _simplify_once(UnaryOp('-', left))
            # x * x = x^2
            if left == right:
                return _simplify_once(Pow(left, Num(2)))
            # num * (num * x) = (num1*num2) * x — associate constants
            if isinstance(left, Num) and isinstance(right, BinOp) and right.op == '*':
                if isinstance(right.left, Num):
                    return _simplify_once(BinOp('*', Num(left.value * right.left.value), right.right))
                if isinstance(right.right, Num):
                    return _simplify_once(BinOp('*', Num(left.value * right.right.value), right.left))
            if isinstance(right, Num) and isinstance(left, BinOp) and left.op == '*':
                if isinstance(left.left, Num):
                    return _simplify_once(BinOp('*', Num(right.value * left.left.value), left.right))
                if isinstance(left.right, Num):
                    return _simplify_once(BinOp('*', Num(right.value * left.right.value), left.left))

        # Division simplifications
        if op == '/':
            if isinstance(left, Num) and left.value == 0:
                return Num(0)
            if isinstance(right, Num) and right.value == 1:
                return left
            # x / (-1) = -x
            if isinstance(right, Num) and right.value == -1:
                return _simplify_once(UnaryOp('-', left))
            # x / x = 1
            if left == right:
                return Num(1)
            # (num * x) / num
            if isinstance(right, Num) and isinstance(left, BinOp) and left.op == '*':
                if isinstance(left.left, Num):
                    return _simplify_once(BinOp('*', Num(left.left.value / right.value), left.right))
                if isinstance(left.right, Num):
                    return _simplify_once(BinOp('*', Num(left.right.value / right.value), left.left))

        return BinOp(op, left, right)

    return expr


def _simplify_trig(expr: Expr) -> Expr:
    """
    Apply trigonometric identity simplifications:
    - sin²x + cos²x = 1
    - tan(x) = sin(x)/cos(x)
    - 1 - sin²x = cos²x
    - 1 - cos²x = sin²x
    """
    if isinstance(expr, BinOp) and expr.op == '+':
        left = _simplify_trig(expr.left)
        right = _simplify_trig(expr.right)
        result = _check_trig_identity(left, right)
        if result is not None:
            return result
        return BinOp('+', left, right)

    if isinstance(expr, BinOp) and expr.op == '-':
        left = _simplify_trig(expr.left)
        right = _simplify_trig(expr.right)
        # Check for 1 - sin²x = cos²x and 1 - cos²x = sin²x
        if isinstance(left, Num) and left.value == 1:
            if isinstance(right, Pow) and isinstance(right.base, Func):
                if right.base.name == 'sin' and isinstance(right.exponent, Num) and right.exponent.value == 2:
                    return Pow(Func('cos', right.base.arg), Num(2))
                if right.base.name == 'cos' and isinstance(right.exponent, Num) and right.exponent.value == 2:
                    return Pow(Func('sin', right.base.arg), Num(2))
        return BinOp('-', left, right)

    return expr


def _check_trig_identity(left: Expr, right: Expr) -> Optional[Expr]:
    """Check if left + right matches sin²x + cos²x = 1 or similar."""
    left_info = _extract_trig_squared(left)
    right_info = _extract_trig_squared(right)

    if left_info and right_info:
        l_name, l_arg, l_coeff = left_info
        r_name, r_arg, r_coeff = right_info

        if l_arg == r_arg and l_coeff == r_coeff:
            if (l_name == 'sin' and r_name == 'cos') or (l_name == 'cos' and r_name == 'sin'):
                if l_coeff == 1:
                    return Num(1)

    return None


def _extract_trig_squared(expr: Expr) -> Optional[Tuple[str, str, Union[int, float]]]:
    """Extract (func_name, arg_str, coefficient) from expressions like sin²x, 2*sin²x."""
    if isinstance(expr, Pow) and isinstance(expr.base, Func) and isinstance(expr.exponent, Num):
        if expr.exponent.value == 2 and expr.base.name in ('sin', 'cos', 'tan'):
            return (expr.base.name, str(expr.base.arg), 1)

    if isinstance(expr, BinOp) and expr.op == '*':
        if isinstance(expr.left, Num) and isinstance(expr.right, Pow):
            if isinstance(expr.right.base, Func) and isinstance(expr.right.exponent, Num):
                if expr.right.exponent.value == 2 and expr.right.base.name in ('sin', 'cos', 'tan'):
                    return (expr.right.base.name, str(expr.right.base.arg), expr.left.value)

    return None


# ──────────────────────────── Expansion ────────────────────────────

def expand_expr(expr: Expr) -> Expr:
    """Expand an expression by distributing multiplication over addition."""
    if isinstance(expr, (Num, Sym)):
        return expr

    if isinstance(expr, UnaryOp):
        inner = expand_expr(expr.operand)
        if expr.op == '-' and isinstance(inner, BinOp) and inner.op == '+':
            return expand_expr(BinOp('+', UnaryOp('-', inner.left), UnaryOp('-', inner.right)))
        if expr.op == '-' and isinstance(inner, BinOp) and inner.op == '-':
            return expand_expr(BinOp('+', UnaryOp('-', inner.left), inner.right))
        return UnaryOp(expr.op, inner)

    if isinstance(expr, Pow):
        base = expand_expr(expr.base)
        exp = expand_expr(expr.exponent)
        # (a + b)^2 = a^2 + 2ab + b^2
        if isinstance(exp, Num) and exp.value == 2 and isinstance(base, BinOp) and base.op == '+':
            a, b = base.left, base.right
            return expand_expr(BinOp('+', BinOp('+', Pow(a, Num(2)), BinOp('*', BinOp('*', Num(2), a), b)), Pow(b, Num(2))))
        return Pow(base, exp)

    if isinstance(expr, Func):
        return Func(expr.name, expand_expr(expr.arg))

    if isinstance(expr, BinOp):
        left = expand_expr(expr.left)
        right = expand_expr(expr.right)
        op = expr.op

        if op == '+':
            return BinOp('+', left, right)

        if op == '-':
            return BinOp('-', left, right)

        if op == '*':
            # Distribute: a * (b + c) = a*b + a*c
            if isinstance(right, BinOp) and right.op == '+':
                return expand_expr(BinOp('+', BinOp('*', left, right.left), BinOp('*', left, right.right)))
            if isinstance(right, BinOp) and right.op == '-':
                return expand_expr(BinOp('-', BinOp('*', left, right.left), BinOp('*', left, right.right)))
            if isinstance(left, BinOp) and left.op == '+':
                return expand_expr(BinOp('+', BinOp('*', left.left, right), BinOp('*', left.right, right)))
            if isinstance(left, BinOp) and left.op == '-':
                return expand_expr(BinOp('-', BinOp('*', left.left, right), BinOp('*', left.right, right)))
            return BinOp('*', left, right)

        if op == '/':
            return BinOp('/', left, right)

        return BinOp(op, left, right)

    return expr


# ──────────────────────────── Factorization ────────────────────────────

def factor(expr: Expr, var: str) -> Expr:
    """
    Factor out common terms involving ``var`` from a sum expression.

    For example: 2*x + 4*x^2 → x * (2 + 4*x) or similar factored forms.
    Attempts to extract common polynomial factors.
    """
    expr = simplify(expr)

    # Only factor sums
    if not isinstance(expr, BinOp) or expr.op != '+':
        return expr

    terms = _collect_additive_terms(expr)

    if len(terms) < 2:
        return expr

    parsed_terms = []
    for term in terms:
        parsed_terms.append(_parse_multiplicative_factors(term))

    if len(parsed_terms) < 2:
        return expr

    # Find intersection of all factor sets (common factors)
    common_factors: Dict[Tuple, int] = {}

    for base_key, exp in parsed_terms[0].items():
        common_factors[base_key] = exp

    for i in range(1, len(parsed_terms)):
        term_factors = parsed_terms[i]
        new_common = {}
        for base_key, exp in common_factors.items():
            if base_key in term_factors:
                new_common[base_key] = min(exp, term_factors[base_key])
        common_factors = new_common

    if not common_factors:
        return expr  # No common factors found

    # Build common factor expression
    common_expr: Optional[Expr] = None
    for base_key, exp in common_factors.items():
        base_expr = _key_to_expr(base_key)
        factor_term = Pow(base_expr, Num(exp)) if exp > 1 else base_expr
        if common_expr is None:
            common_expr = factor_term
        else:
            common_expr = BinOp('*', common_expr, factor_term)

    # Build reduced terms
    reduced_terms = []
    for term, parsed in zip(terms, parsed_terms):
        remaining: Optional[Expr] = None
        for base_key, exp in parsed.items():
            if base_key in common_factors:
                reduced_exp = exp - common_factors[base_key]
                if reduced_exp > 0:
                    base_expr = _key_to_expr(base_key)
                    factor_term = Pow(base_expr, Num(reduced_exp)) if reduced_exp > 1 else base_expr
                    if remaining is None:
                        remaining = factor_term
                    else:
                        remaining = BinOp('*', remaining, factor_term)
            else:
                base_expr = _key_to_expr(base_key)
                factor_term = Pow(base_expr, Num(exp)) if exp > 1 else base_expr
                if remaining is None:
                    remaining = factor_term
                else:
                    remaining = BinOp('*', remaining, factor_term)

        if remaining is None:
            reduced_terms.append(Num(1))
        else:
            reduced_terms.append(remaining)

    # Build result: common_expr * (sum of reduced_terms)
    sum_expr: Expr = reduced_terms[0]
    for rt in reduced_terms[1:]:
        sum_expr = BinOp('+', sum_expr, rt)

    result = BinOp('*', common_expr, sum_expr)
    return simplify(result)


def _collect_additive_terms(expr: Expr) -> List[Expr]:
    """Collect all additive terms from a sum expression."""
    if isinstance(expr, BinOp) and expr.op == '+':
        return _collect_additive_terms(expr.left) + _collect_additive_terms(expr.right)
    return [expr]


def _parse_multiplicative_factors(expr: Expr) -> Dict[Tuple, int]:
    """Parse an expression into a dict of (type, value) -> exponent for factoring."""
    factors: Dict[Tuple, int] = {}

    if isinstance(expr, Num):
        key = ('num', expr.value)
        factors[key] = factors.get(key, 0) + 1
        return factors

    if isinstance(expr, Sym):
        key = ('sym', expr.name)
        factors[key] = factors.get(key, 0) + 1
        return factors

    if isinstance(expr, Pow):
        base_key = _expr_to_key(expr.base)
        if base_key is not None:
            if isinstance(expr.exponent, Num):
                factors[base_key] = factors.get(base_key, 0) + int(expr.exponent.value)
                return factors

    if isinstance(expr, BinOp) and expr.op == '*':
        left_factors = _parse_multiplicative_factors(expr.left)
        right_factors = _parse_multiplicative_factors(expr.right)
        for key, exp in right_factors.items():
            left_factors[key] = left_factors.get(key, 0) + exp
        return left_factors

    # For any other expression, treat it as an opaque factor
    key = _expr_to_key(expr)
    if key is not None:
        factors[key] = factors.get(key, 0) + 1
    return factors


def _expr_to_key(expr: Expr) -> Optional[Tuple]:
    """Convert an expression to a hashable key for factoring."""
    if isinstance(expr, Num):
        return ('num', expr.value)
    if isinstance(expr, Sym):
        return ('sym', expr.name)
    if isinstance(expr, Func):
        arg_key = _expr_to_key(expr.arg)
        if arg_key is not None:
            return ('func', expr.name, arg_key)
    if isinstance(expr, Pow):
        base_key = _expr_to_key(expr.base)
        exp_key = _expr_to_key(expr.exponent)
        if base_key is not None and exp_key is not None:
            return ('pow', base_key, exp_key)
    if isinstance(expr, BinOp):
        left_key = _expr_to_key(expr.left)
        right_key = _expr_to_key(expr.right)
        if left_key is not None and right_key is not None:
            return ('binop', expr.op, left_key, right_key)
    return None


def _key_to_expr(key: Tuple) -> Expr:
    """Convert a key back to an expression."""
    if key[0] == 'num':
        return Num(key[1])
    if key[0] == 'sym':
        return Sym(key[1])
    if key[0] == 'func':
        return Func(key[1], _key_to_expr(key[2]))
    if key[0] == 'pow':
        return Pow(_key_to_expr(key[1]), _key_to_expr(key[2]))
    if key[0] == 'binop':
        return BinOp(key[1], _key_to_expr(key[2]), _key_to_expr(key[3]))
    raise ValueError(f"Cannot convert key to expression: {key}")