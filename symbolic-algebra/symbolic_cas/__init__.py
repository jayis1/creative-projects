"""
symbolic_cas — A Symbolic Algebra System (Computer Algebra System)
====================================================================

A pure-Python symbolic algebra system supporting:
- Expression parsing, differentiation, simplification
- Equation solving, Taylor series, numerical integration
- Newton's method, factorization, pretty-printing, LaTeX output
- Limits, expression comparison, serialization
- Interactive REPL and CLI interface

Example usage::

    from symbolic_cas import parse, x, sin, cos, exp

    f = parse("sin(x)^2 + cos(x)^2")
    print(f.simplify())  # 1

    df = parse("x^3 + 2*x").diff('x').simplify()
    print(df)  # (3 * (x^2)) + 2
"""

__version__ = "2.0.0"
__author__ = "Hermes Agent"

from symbolic_cas.expr import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow,
    x, y, z, t, n, pi, e,
    sym, num, sin, cos, tan, exp, ln, sqrt, abs_expr,
)
from symbolic_cas.parser import parse
from symbolic_cas.calculus import differentiate, taylor_series
from symbolic_cas.simplify import simplify, expand_expr, factor
from symbolic_cas.solve import solve, newton_method
from symbolic_cas.evaluate import evaluate, numerical_integrate
from symbolic_cas.display import to_latex, pretty_print
from symbolic_cas.substitute import substitute, collect_symbols
from symbolic_cas.limits import limit
from symbolic_cas.serialize import to_dict, from_dict

__all__ = [
    'Expr', 'Num', 'Sym', 'BinOp', 'UnaryOp', 'Func', 'Pow',
    'parse', 'simplify', 'differentiate', 'expand_expr',
    'substitute', 'evaluate', 'collect_symbols', 'to_latex', 'solve',
    'taylor_series', 'numerical_integrate', 'newton_method',
    'factor', 'pretty_print', 'limit',
    'to_dict', 'from_dict',
    'x', 'y', 'z', 't', 'n', 'pi', 'e',
    'sym', 'num', 'sin', 'cos', 'tan', 'exp', 'ln', 'sqrt', 'abs_expr',
]