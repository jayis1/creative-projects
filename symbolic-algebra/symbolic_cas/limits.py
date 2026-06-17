"""Limit computation: symbolic and numerical limits."""

from __future__ import annotations

import math
from typing import Optional, Union

from symbolic_cas.expr import Expr, Num, Sym, BinOp, UnaryOp, Func, Pow


def limit(expr: Expr, var: str, point: Union[int, float, str] = 0,
          direction: str = 'both') -> Optional[float]:
    """
    Compute the limit of ``expr`` as ``var`` approaches ``point``.

    Parameters
    ----------
    expr : Expr
        The expression to compute the limit of.
    var : str
        The variable name.
    point : int, float, or str
        The value the variable approaches. Use 'inf' or '-inf' for infinity.
    direction : str
        'both' (default), 'left', or 'right'.

    Returns
    -------
    float or None
        The computed limit, or None if it doesn't exist.

    Examples
    --------
    >>> from symbolic_cas import parse
    >>> parse("sin(x)/x").limit('x', 0)  # Returns 1.0
    >>> parse("1/x").limit('x', 'inf')    # Returns 0.0
    """
    # Handle infinity limits
    if isinstance(point, str):
        if point in ('inf', '+inf', 'infinity'):
            return _limit_at_infinity(expr, var)
        elif point in ('-inf', '-infinity'):
            return _limit_at_infinity(expr, var, negative=True)

    point_val = float(point)

    if direction == 'both':
        left_val = _numerical_limit(expr, var, point_val, from_left=True)
        right_val = _numerical_limit(expr, var, point_val, from_left=False)

        if left_val is None and right_val is None:
            return None
        if left_val is None or right_val is None:
            return left_val if left_val is not None else right_val
        if math.isclose(left_val, right_val, rel_tol=1e-6, abs_tol=1e-10):
            return left_val
        return None  # Limit doesn't exist (left != right)

    elif direction == 'left':
        return _numerical_limit(expr, var, point_val, from_left=True)
    elif direction == 'right':
        return _numerical_limit(expr, var, point_val, from_left=False)
    else:
        raise ValueError(f"Invalid direction: {direction}. Use 'both', 'left', or 'right'.")


def _numerical_limit(expr: Expr, var: str, point: float,
                     from_left: bool = False) -> Optional[float]:
    """
    Compute limit numerically by evaluating the expression at points
    approaching `point` from the specified direction.
    """
    epsilon_values = [1e-2, 1e-4, 1e-6, 1e-8, 1e-10, 1e-12]
    results = []

    for eps in epsilon_values:
        x_val = point - eps if from_left else point + eps
        try:
            val = expr.evaluate({var: x_val})
            if math.isnan(val) or math.isinf(val):
                results.append(None)
            else:
                results.append(val)
        except (ValueError, ZeroDivisionError, OverflowError):
            results.append(None)

    # Filter out None values
    valid = [r for r in results if r is not None]

    if len(valid) < 2:
        # Try to check if all invalid results are the same kind of infinity
        inf_results = [r for r in results if r is not None]
        if not inf_results:
            return None

    # Check convergence: last few values should be close
    if len(valid) >= 3:
        # Check if last 3 values are converging
        diffs = [abs(valid[i] - valid[i-1]) for i in range(1, len(valid))]
        if diffs[-1] < 1e-4 * max(1, abs(valid[-1])):
            return valid[-1]

    if len(valid) >= 2:
        # Check if last 2 are very close
        if math.isclose(valid[-1], valid[-2], rel_tol=1e-6, abs_tol=1e-10):
            return valid[-1]

    if valid:
        return valid[-1]

    return None


def _limit_at_infinity(expr: Expr, var: str, negative: bool = False) -> Optional[float]:
    """Compute the limit as var → ∞ or var → -∞."""
    # Evaluate at increasingly large values
    test_points = [10, 100, 1000, 10000, 100000]

    if negative:
        test_points = [-x for x in test_points]

    results = []
    for x_val in test_points:
        try:
            val = expr.evaluate({var: float(x_val)})
            if math.isnan(val):
                results.append(None)
            else:
                results.append(val)
        except (ValueError, ZeroDivisionError, OverflowError):
            results.append(None)

    valid = [r for r in results if r is not None]

    if not valid:
        return None

    # Check if converging
    if len(valid) >= 3:
        diffs = [abs(valid[i] - valid[i-1]) for i in range(1, len(valid))]
        if diffs[-1] < 1e-4 * max(1, abs(valid[-1])):
            return valid[-1]

    # Check if approaching infinity
    if len(valid) >= 2:
        if all(math.isinf(v) for v in valid[-2:]):
            return valid[-1]
        if math.isclose(valid[-1], valid[-2], rel_tol=1e-4, abs_tol=1e-8):
            return valid[-1]

    return valid[-1] if valid else None