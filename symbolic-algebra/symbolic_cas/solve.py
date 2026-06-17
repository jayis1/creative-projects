"""Equation solving: linear, quadratic, polynomial roots, Newton's method."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from symbolic_cas.expr import Expr, Num, Sym, BinOp, UnaryOp, Func, Pow
from symbolic_cas.simplify import simplify


def solve(expr: Expr, var: str) -> List[Expr]:
    """
    Solve expr == 0 for the given variable.

    Supports:
    - Linear equations: ax + b = 0
    - Quadratic equations: ax² + bx + c = 0
    - Higher-degree polynomials with rational roots (rational root theorem)
    """
    # Simplify first
    expr = simplify(expr)

    # Collect coefficients of the polynomial in `var`
    coeffs = _collect_polynomial_coeffs(expr, var)

    if coeffs is None:
        raise ValueError(f"Cannot solve: expression is not a polynomial in {var}")

    degree = max(coeffs.keys())
    if degree == 0:
        # Constant equation: c = 0
        if isinstance(coeffs[0], Num) and coeffs[0].value == 0:
            raise ValueError("Equation is trivially true (0 = 0), infinite solutions")
        raise ValueError("No solution (constant ≠ 0)")

    if degree == 1:
        # ax + b = 0 => x = -b/a
        a = coeffs.get(1, Num(0))
        b = coeffs.get(0, Num(0))
        a_val = _to_float(a)
        b_val = _to_float(b)
        if a_val is not None and b_val is not None:
            result = -b_val / a_val
            if result == int(result):
                result = int(result)
            return [Num(result)]
        return [simplify(BinOp('/', UnaryOp('-', b), a))]

    if degree == 2:
        # ax^2 + bx + c = 0
        a = coeffs.get(2, Num(0))
        b = coeffs.get(1, Num(0))
        c = coeffs.get(0, Num(0))
        a_val = _to_float(a)
        b_val = _to_float(b)
        c_val = _to_float(c)

        if a_val is not None and b_val is not None and c_val is not None:
            disc = b_val**2 - 4*a_val*c_val
            if disc < 0:
                return []  # No real solutions
            elif disc == 0:
                root = -b_val / (2 * a_val)
                if root == int(root):
                    root = int(root)
                return [Num(root)]
            else:
                sqrt_disc = math.sqrt(disc)
                r1 = (-b_val + sqrt_disc) / (2 * a_val)
                r2 = (-b_val - sqrt_disc) / (2 * a_val)
                if r1 == int(r1):
                    r1 = int(r1)
                if r2 == int(r2):
                    r2 = int(r2)
                return [Num(r1), Num(r2)]

    # For higher degrees, try rational root theorem
    if degree <= 4 and all(i in coeffs and isinstance(coeffs[i], Num) for i in range(degree + 1)):
        c0 = int(coeffs[0].value) if isinstance(coeffs[0].value, int) else None
        cn = int(coeffs[degree].value) if isinstance(coeffs[degree].value, int) else None
        if c0 is not None and cn is not None and cn != 0:
            candidates = _rational_root_candidates(abs(c0), abs(cn))
            roots = []
            for cand in candidates:
                val = _eval_poly(coeffs, cand)
                if abs(val) < 1e-10:
                    roots.append(Num(cand))
                    if cand != 0:
                        val_neg = _eval_poly(coeffs, -cand)
                        if abs(val_neg) < 1e-10:
                            roots.append(Num(-cand))
            return list(set(roots))

    raise ValueError(f"Cannot solve polynomial of degree {degree} in general")


def _to_float(expr: Expr) -> Optional[float]:
    """Try to convert an expression to a float."""
    if isinstance(expr, Num):
        return float(expr.value)
    return None


def _eval_poly(coeffs: Dict[int, Expr], x: float) -> float:
    """Evaluate a polynomial given as coefficient dict at x."""
    result = 0.0
    for deg, coeff_expr in coeffs.items():
        c = _to_float(coeff_expr)
        if c is None:
            raise ValueError("Non-numeric coefficient")
        result += c * (x ** deg)
    return result


def _rational_root_candidates(p: int, q: int) -> List[float]:
    """
    Generate candidate rational roots ±(p_i/q_j) for polynomial with
    leading coefficient q and constant term p.
    """
    p_divisors = set()
    for i in range(1, abs(p) + 1):
        if p % i == 0:
            p_divisors.add(i)

    q_divisors = set()
    for i in range(1, abs(q) + 1):
        if q % i == 0:
            q_divisors.add(i)

    # Generate all ±(p_div/q_div) candidates
    candidates = set()
    for pi in p_divisors:
        for qi in q_divisors:
            val = pi / qi
            candidates.add(val)
            candidates.add(-val)

    return sorted(candidates)


def _collect_polynomial_coeffs(expr: Expr, var: str) -> Optional[Dict[int, Expr]]:
    """
    Collect polynomial coefficients for ``var`` in ``expr``.
    Returns a dict mapping degree -> coefficient, or None if not a polynomial.
    """
    expr = simplify(expr)

    # Check if expr is constant (no var)
    if var not in _collect_symbols_expr(expr):
        return {0: expr}

    if isinstance(expr, Sym):
        if expr.name == var:
            return {0: Num(0), 1: Num(1)}
        return {0: expr}

    if isinstance(expr, Num):
        return {0: expr}

    if isinstance(expr, BinOp):
        if expr.op == '+':
            left_coeffs = _collect_polynomial_coeffs(expr.left, var)
            right_coeffs = _collect_polynomial_coeffs(expr.right, var)
            if left_coeffs is None or right_coeffs is None:
                return None
            result = dict(left_coeffs)
            for deg, coeff in right_coeffs.items():
                if deg in result:
                    result[deg] = simplify(BinOp('+', result[deg], coeff))
                else:
                    result[deg] = coeff
            return result

        if expr.op == '-':
            left_coeffs = _collect_polynomial_coeffs(expr.left, var)
            right_coeffs = _collect_polynomial_coeffs(expr.right, var)
            if left_coeffs is None or right_coeffs is None:
                return None
            result = dict(left_coeffs)
            for deg, coeff in right_coeffs.items():
                if deg in result:
                    result[deg] = simplify(BinOp('-', result[deg], coeff))
                else:
                    result[deg] = simplify(UnaryOp('-', coeff))
            return result

        if expr.op == '*':
            left_coeffs = _collect_polynomial_coeffs(expr.left, var)
            right_coeffs = _collect_polynomial_coeffs(expr.right, var)
            if left_coeffs is None or right_coeffs is None:
                return None
            result = {}
            for d1, c1 in left_coeffs.items():
                for d2, c2 in right_coeffs.items():
                    deg = d1 + d2
                    term = simplify(BinOp('*', c1, c2))
                    if deg in result:
                        result[deg] = simplify(BinOp('+', result[deg], term))
                    else:
                        result[deg] = term
            return result

    if isinstance(expr, Pow):
        if isinstance(expr.base, Sym) and expr.base.name == var:
            if isinstance(expr.exponent, Num):
                n = expr.exponent.value
                if isinstance(n, int) and n >= 0:
                    return {0: Num(0), n: Num(1)}
            return None

    if isinstance(expr, UnaryOp) and expr.op == '-':
        inner_coeffs = _collect_polynomial_coeffs(expr.operand, var)
        if inner_coeffs is None:
            return None
        return {deg: simplify(UnaryOp('-', coeff)) for deg, coeff in inner_coeffs.items()}

    return None


def _collect_symbols_expr(expr: Expr) -> frozenset:
    """Helper to collect symbols without importing from substitute module to avoid circular imports."""
    if isinstance(expr, Num):
        return frozenset()
    if isinstance(expr, Sym):
        return frozenset({expr.name})
    if isinstance(expr, UnaryOp):
        return _collect_symbols_expr(expr.operand)
    if isinstance(expr, BinOp):
        return _collect_symbols_expr(expr.left) | _collect_symbols_expr(expr.right)
    if isinstance(expr, Pow):
        return _collect_symbols_expr(expr.base) | _collect_symbols_expr(expr.exponent)
    if isinstance(expr, Func):
        return _collect_symbols_expr(expr.arg)
    return frozenset()


# ──────────────────────────── Newton's Method ────────────────────────────

def newton_method(expr: Expr, var: str, x0: float = 0.0, tol: float = 1e-10, max_iter: int = 100) -> float:
    """
    Find a root of expr == 0 using Newton's method.

    Starting from x0, iterates: x_{n+1} = x_n - f(x_n) / f'(x_n)
    Raises ValueError if convergence fails.
    """
    from symbolic_cas.calculus import differentiate

    derivative = differentiate(expr, var)

    x = x0
    for _ in range(max_iter):
        try:
            f_val = expr.evaluate({var: x})
            df_val = derivative.evaluate({var: x})
        except (ValueError, ZeroDivisionError, OverflowError):
            raise ValueError(f"Newton's method failed: evaluation error at {var}={x}")

        if df_val == 0:
            raise ValueError(f"Newton's method failed: zero derivative at {var}={x}")

        x_new = x - f_val / df_val

        if math.isnan(x_new) or math.isinf(x_new):
            raise ValueError(f"Newton's method diverged at {var}={x}")

        if abs(x_new - x) < tol:
            return x_new

        x = x_new

    raise ValueError(f"Newton's method did not converge after {max_iter} iterations (last value: {x})")