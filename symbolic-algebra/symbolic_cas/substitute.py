"""Substitution and symbol collection."""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional

from symbolic_cas.expr import Expr, Num, Sym, UnaryOp, BinOp, Func, Pow


def substitute(expr: Expr, mapping: Dict[str, Expr]) -> Expr:
    """Substitute symbols in ``expr`` with expressions from ``mapping``."""
    if isinstance(expr, Num):
        return expr

    if isinstance(expr, Sym):
        return mapping.get(expr.name, expr)

    if isinstance(expr, UnaryOp):
        return UnaryOp(expr.op, substitute(expr.operand, mapping))

    if isinstance(expr, BinOp):
        return BinOp(expr.op, substitute(expr.left, mapping), substitute(expr.right, mapping))

    if isinstance(expr, Pow):
        return Pow(substitute(expr.base, mapping), substitute(expr.exponent, mapping))

    if isinstance(expr, Func):
        return Func(expr.name, substitute(expr.arg, mapping))

    raise ValueError(f"Cannot substitute in: {type(expr).__name__}")


def collect_symbols(expr: Expr) -> FrozenSet[str]:
    """Collect all symbol names in the expression."""
    if isinstance(expr, Num):
        return frozenset()
    if isinstance(expr, Sym):
        return frozenset({expr.name})
    if isinstance(expr, UnaryOp):
        return collect_symbols(expr.operand)
    if isinstance(expr, BinOp):
        return collect_symbols(expr.left) | collect_symbols(expr.right)
    if isinstance(expr, Pow):
        return collect_symbols(expr.base) | collect_symbols(expr.exponent)
    if isinstance(expr, Func):
        return collect_symbols(expr.arg)
    return frozenset()