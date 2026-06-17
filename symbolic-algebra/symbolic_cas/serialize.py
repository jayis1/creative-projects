"""Serialization: convert expressions to/from dictionaries and JSON."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from symbolic_cas.expr import Expr, Num, Sym, BinOp, UnaryOp, Func, Pow


def to_dict(expr: Expr) -> Dict[str, Any]:
    """
    Serialize an expression to a dictionary representation.

    This is useful for JSON export, network transmission, or storage.

    Examples
    --------
    >>> from symbolic_cas import parse, to_dict
    >>> expr = parse("sin(x)^2 + 1")
    >>> d = to_dict(expr)
    >>> d['type']
    'BinOp'
    """
    if isinstance(expr, Num):
        return {'type': 'Num', 'value': expr.value}
    if isinstance(expr, Sym):
        return {'type': 'Sym', 'name': expr.name}
    if isinstance(expr, BinOp):
        return {
            'type': 'BinOp',
            'op': expr.op,
            'left': to_dict(expr.left),
            'right': to_dict(expr.right),
        }
    if isinstance(expr, UnaryOp):
        return {
            'type': 'UnaryOp',
            'op': expr.op,
            'operand': to_dict(expr.operand),
        }
    if isinstance(expr, Func):
        return {
            'type': 'Func',
            'name': expr.name,
            'arg': to_dict(expr.arg),
        }
    if isinstance(expr, Pow):
        return {
            'type': 'Pow',
            'base': to_dict(expr.base),
            'exponent': to_dict(expr.exponent),
        }
    raise ValueError(f"Cannot serialize expression type: {type(expr).__name__}")


def from_dict(data: Dict[str, Any]) -> Expr:
    """
    Deserialize an expression from a dictionary representation.

    Examples
    --------
    >>> from symbolic_cas import from_dict
    >>> d = {'type': 'Num', 'value': 42}
    >>> from_dict(d)
    Num(42)
    """
    typ = data['type']

    if typ == 'Num':
        return Num(data['value'])
    if typ == 'Sym':
        return Sym(data['name'])
    if typ == 'BinOp':
        return BinOp(data['op'], from_dict(data['left']), from_dict(data['right']))
    if typ == 'UnaryOp':
        return UnaryOp(data['op'], from_dict(data['operand']))
    if typ == 'Func':
        return Func(data['name'], from_dict(data['arg']))
    if typ == 'Pow':
        return Pow(from_dict(data['base']), from_dict(data['exponent']))

    raise ValueError(f"Unknown expression type: {typ}")


def to_json(expr: Expr, indent: Optional[int] = None) -> str:
    """Serialize an expression to a JSON string."""
    return json.dumps(to_dict(expr), indent=indent)


def from_json(json_str: str) -> Expr:
    """Deserialize an expression from a JSON string."""
    return from_dict(json.loads(json_str))