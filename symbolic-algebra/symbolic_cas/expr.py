"""
Expression AST nodes for the symbolic algebra system.

All nodes are immutable and hashable. Operations return new expressions
(functional style).
"""

from __future__ import annotations

import re
import math
from abc import ABC, abstractmethod
from typing import Dict, FrozenSet, List, Optional, Tuple, Union


class Expr(ABC):
    """Base class for all symbolic expressions. Immutable and hashable."""

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def __eq__(self, other: object) -> bool: ...

    @abstractmethod
    def __hash__(self) -> int: ...

    def __add__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('+', self, other)

    def __radd__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('+', other, self)

    def __sub__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('-', self, other)

    def __rsub__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('-', other, self)

    def __mul__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('*', self, other)

    def __rmul__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('*', other, self)

    def __truediv__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('/', self, other)

    def __rtruediv__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return BinOp('/', other, self)

    def __pow__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return Pow(self, other)

    def __rpow__(self, other: Union['Expr', int, float]) -> 'Expr':
        other = _wrap(other)
        return Pow(other, self)

    def __neg__(self) -> 'Expr':
        return UnaryOp('-', self)

    def __pos__(self) -> 'Expr':
        return self

    def __abs__(self) -> 'Expr':
        return Func('abs', self)

    def diff(self, var: Union[str, 'Sym']) -> 'Expr':
        """Compute the symbolic derivative with respect to ``var``."""
        from symbolic_cas.calculus import differentiate
        var_name = var.name if isinstance(var, Sym) else var
        return differentiate(self, var_name)

    def simplify(self) -> 'Expr':
        """Simplify this expression."""
        from symbolic_cas.simplify import simplify
        return simplify(self)

    def expand(self) -> 'Expr':
        """Expand this expression (distribute multiplication)."""
        from symbolic_cas.simplify import expand_expr
        return expand_expr(self)

    def substitute(self, mapping: Dict[Union[str, 'Sym'], Union['Expr', int, float]]) -> 'Expr':
        """Substitute symbols with expressions."""
        from symbolic_cas.substitute import substitute
        new_map = {}
        for k, v in mapping.items():
            name = k.name if isinstance(k, Sym) else k
            new_map[name] = _wrap(v)
        return substitute(self, new_map)

    def evaluate(self, mapping: Optional[Dict[Union[str, 'Sym'], Union[int, float]]] = None) -> Union[int, float]:
        """Numerically evaluate the expression."""
        from symbolic_cas.evaluate import evaluate
        if mapping is None:
            mapping = {}
        new_map = {}
        for k, v in mapping.items():
            name = k.name if isinstance(k, Sym) else k
            new_map[name] = v
        return evaluate(self, new_map)

    def symbols(self) -> FrozenSet[str]:
        """Return the set of symbol names in this expression."""
        from symbolic_cas.substitute import collect_symbols
        return collect_symbols(self)

    def to_latex(self) -> str:
        """Convert this expression to LaTeX."""
        from symbolic_cas.display import to_latex
        return to_latex(self)

    def solve(self, var: Union[str, 'Sym']) -> List['Expr']:
        """Solve this expression == 0 for the given variable."""
        from symbolic_cas.solve import solve
        var_name = var.name if isinstance(var, Sym) else var
        return solve(self, var_name)

    def taylor(self, var: Union[str, 'Sym'], point: Union[int, float] = 0, order: int = 5) -> 'Expr':
        """Compute the Taylor series expansion around ``point`` up to ``order`` terms."""
        from symbolic_cas.calculus import taylor_series
        var_name = var.name if isinstance(var, Sym) else var
        return taylor_series(self, var_name, point, order)

    def integrate(self, var: Union[str, 'Sym'], a: Union[int, float], b: Union[int, float], n: int = 1000) -> float:
        """Numerically integrate this expression from a to b using Simpson's rule."""
        from symbolic_cas.evaluate import numerical_integrate
        var_name = var.name if isinstance(var, Sym) else var
        return numerical_integrate(self, var_name, a, b, n)

    def factor(self, var: Union[str, 'Sym']) -> 'Expr':
        """Factor out common terms involving ``var``."""
        from symbolic_cas.simplify import factor
        var_name = var.name if isinstance(var, Sym) else var
        return factor(self, var_name)

    def newton_solve(self, var: Union[str, 'Sym'], x0: float = 0.0, tol: float = 1e-10, max_iter: int = 100) -> float:
        """Find a root using Newton's method starting from x0."""
        from symbolic_cas.solve import newton_method
        var_name = var.name if isinstance(var, Sym) else var
        return newton_method(self, var_name, x0, tol, max_iter)

    def limit(self, var: Union[str, 'Sym'], point: Union[int, float, str] = 0,
              direction: str = 'both') -> Optional[float]:
        """Compute the limit as var approaches point."""
        from symbolic_cas.limits import limit as compute_limit
        var_name = var.name if isinstance(var, Sym) else var
        return compute_limit(self, var_name, point, direction)

    def pretty(self) -> str:
        """Pretty-print this expression with minimal parentheses."""
        from symbolic_cas.display import pretty_print
        return pretty_print(self)

    def depth(self) -> int:
        """Return the depth of the expression tree."""
        if isinstance(self, (Num, Sym)):
            return 1
        if isinstance(self, UnaryOp):
            return 1 + self.operand.depth()
        if isinstance(self, Func):
            return 1 + self.arg.depth()
        if isinstance(self, BinOp):
            return 1 + max(self.left.depth(), self.right.depth())
        if isinstance(self, Pow):
            return 1 + max(self.base.depth(), self.exponent.depth())
        return 1

    def size(self) -> int:
        """Return the number of nodes in the expression tree."""
        if isinstance(self, (Num, Sym)):
            return 1
        if isinstance(self, UnaryOp):
            return 1 + self.operand.size()
        if isinstance(self, Func):
            return 1 + self.arg.size()
        if isinstance(self, BinOp):
            return 1 + self.left.size() + self.right.size()
        if isinstance(self, Pow):
            return 1 + self.base.size() + self.exponent.size()
        return 1


class Num(Expr):
    """A numeric constant."""

    def __init__(self, value: Union[int, float]):
        if isinstance(value, float) and value == int(value):
            value = int(value)
        self.value = value

    def __str__(self):
        if isinstance(self.value, float):
            return f"{self.value}"
        return str(self.value)

    def __eq__(self, other):
        return isinstance(other, Num) and self.value == other.value

    def __hash__(self):
        return hash(('Num', self.value))

    def __repr__(self):
        return f"Num({self.value})"


class Sym(Expr):
    """A symbolic variable."""

    def __init__(self, name: str):
        if not re.match(r'^[a-zA-Z_]\w*$', name):
            raise ValueError(f"Invalid symbol name: {name}")
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Sym) and self.name == other.name

    def __hash__(self):
        return hash(('Sym', self.name))

    def __repr__(self):
        return f"Sym('{self.name}')"


class BinOp(Expr):
    """Binary operation: +, -, *, /"""

    VALID_OPS = frozenset(['+', '-', '*', '/'])

    def __init__(self, op: str, left: Expr, right: Expr):
        if op not in self.VALID_OPS:
            raise ValueError(f"Invalid binary operator: {op}")
        self.op = op
        self.left = left
        self.right = right

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"

    def __eq__(self, other):
        return (isinstance(other, BinOp) and self.op == other.op
                and self.left == other.left and self.right == other.right)

    def __hash__(self):
        return hash(('BinOp', self.op, self.left, self.right))

    def __repr__(self):
        return f"BinOp('{self.op}', {self.left!r}, {self.right!r})"


class UnaryOp(Expr):
    """Unary operation: -"""

    VALID_OPS = frozenset(['-'])

    def __init__(self, op: str, operand: Expr):
        if op not in self.VALID_OPS:
            raise ValueError(f"Invalid unary operator: {op}")
        self.op = op
        self.operand = operand

    def __str__(self):
        return f"(-{self.operand})"

    def __eq__(self, other):
        return (isinstance(other, UnaryOp) and self.op == other.op
                and self.operand == other.operand)

    def __hash__(self):
        return hash(('UnaryOp', self.op, self.operand))

    def __repr__(self):
        return f"UnaryOp('{self.op}', {self.operand!r})"


class Func(Expr):
    """A function call: sin, cos, exp, ln, sqrt, abs, etc."""

    KNOWN_FUNCS = frozenset([
        'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
        'asin', 'acos', 'atan', 'atan2',
        'sinh', 'cosh', 'tanh',
        'exp', 'ln', 'log', 'log2', 'log10',
        'sqrt', 'abs', 'ceil', 'floor',
        'sign', 'factorial',
    ])

    def __init__(self, name: str, arg: Expr):
        if name not in self.KNOWN_FUNCS:
            raise ValueError(f"Unknown function: {name}")
        self.name = name
        self.arg = arg

    def __str__(self):
        return f"{self.name}({self.arg})"

    def __eq__(self, other):
        return (isinstance(other, Func) and self.name == other.name
                and self.arg == other.arg)

    def __hash__(self):
        return hash(('Func', self.name, self.arg))

    def __repr__(self):
        return f"Func('{self.name}', {self.arg!r})"


class Pow(Expr):
    """Exponentiation: base^exponent"""

    def __init__(self, base: Expr, exponent: Expr):
        self.base = base
        self.exponent = exponent

    def __str__(self):
        return f"({self.base}^{self.exponent})"

    def __eq__(self, other):
        return (isinstance(other, Pow) and self.base == other.base
                and self.exponent == other.exponent)

    def __hash__(self):
        return hash(('Pow', self.base, self.exponent))

    def __repr__(self):
        return f"Pow({self.base!r}, {self.exponent!r})"


# ──────────────────────────── Helper ────────────────────────────

def _wrap(x: Union[Expr, int, float]) -> Expr:
    """Convert a Python numeric to a Num expression."""
    if isinstance(x, Expr):
        return x
    if isinstance(x, (int, float)):
        return Num(x)
    raise TypeError(f"Cannot convert {type(x)} to Expr")


# ──────────────────────────── Pre-defined symbols ────────────────────────────

x = Sym('x')
y = Sym('y')
z = Sym('z')
t = Sym('t')
n = Sym('n')
pi = Num(math.pi)
e = Num(math.e)


def sym(name: str) -> Sym:
    """Create a symbol."""
    return Sym(name)


def num(value: Union[int, float]) -> Num:
    """Create a numeric constant."""
    return Num(value)


def sin(expr: Union[Expr, int, float]) -> Func:
    return Func('sin', _wrap(expr))


def cos(expr: Union[Expr, int, float]) -> Func:
    return Func('cos', _wrap(expr))


def tan(expr: Union[Expr, int, float]) -> Func:
    return Func('tan', _wrap(expr))


def exp(expr: Union[Expr, int, float]) -> Func:
    return Func('exp', _wrap(expr))


def ln(expr: Union[Expr, int, float]) -> Func:
    return Func('ln', _wrap(expr))


def sqrt(expr: Union[Expr, int, float]) -> Func:
    return Func('sqrt', _wrap(expr))


def abs_expr(expr: Union[Expr, int, float]) -> Func:
    return Func('abs', _wrap(expr))