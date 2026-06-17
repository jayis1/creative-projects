"""
symbolic.py — A Symbolic Algebra System
========================================

A computer algebra system (CAS) that supports:
- Expression parsing from strings (with proper operator precedence)
- Symbolic differentiation (partial derivatives)
- Expression simplification (constant folding, identity elimination, algebraic simplification, trig identities)
- Equation solving (linear, quadratic, polynomial roots, Newton's method)
- Expression expansion (distributive law)
- Taylor series expansion
- Numerical integration (Simpson's rule)
- Factorization (common factor extraction)
- Pretty-printing (minimal parentheses)
- LaTeX output
- Substitution and evaluation

Architecture:
- `Expr` is the base class for all expression nodes (immutable, hashable)
- `Num`, `Sym`, `BinOp`, `UnaryOp`, `Func`, `Pow` are concrete expression types
- All operations return new expressions (functional style)
- The parser builds an AST from infix notation strings

Author: Hermes Agent
"""

from __future__ import annotations
import math
import re
from abc import ABC, abstractmethod
from typing import Dict, FrozenSet, List, Optional, Tuple, Union

# ──────────────────────────── Expression AST ────────────────────────────

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
        """Compute the symbolic derivative with respect to `var`."""
        if isinstance(var, Sym):
            var_name = var.name
        else:
            var_name = var
        return differentiate(self, var_name)

    def simplify(self) -> 'Expr':
        """Simplify this expression."""
        return simplify(self)

    def expand(self) -> 'Expr':
        """Expand this expression (distribute multiplication)."""
        return expand_expr(self)

    def substitute(self, mapping: Dict[Union[str, 'Sym'], Union['Expr', int, float]]) -> 'Expr':
        """Substitute symbols with expressions."""
        new_map = {}
        for k, v in mapping.items():
            name = k.name if isinstance(k, Sym) else k
            new_map[name] = _wrap(v)
        return substitute(self, new_map)

    def evaluate(self, mapping: Optional[Dict[Union[str, 'Sym'], Union[int, float]]] = None) -> Union[int, float]:
        """Numerically evaluate the expression."""
        if mapping is None:
            mapping = {}
        new_map = {}
        for k, v in mapping.items():
            name = k.name if isinstance(k, Sym) else k
            new_map[name] = v
        return evaluate(self, new_map)

    def symbols(self) -> FrozenSet[str]:
        """Return the set of symbol names in this expression."""
        return collect_symbols(self)

    def to_latex(self) -> str:
        """Convert this expression to LaTeX."""
        return to_latex(self)

    def solve(self, var: Union[str, 'Sym']) -> List['Expr']:
        """Solve this expression == 0 for the given variable."""
        if isinstance(var, Sym):
            var_name = var.name
        else:
            var_name = var
        return solve(self, var_name)

    def taylor(self, var: Union[str, 'Sym'], point: Union[int, float] = 0, order: int = 5) -> 'Expr':
        """Compute the Taylor series expansion around `point` up to `order` terms."""
        if isinstance(var, Sym):
            var_name = var.name
        else:
            var_name = var
        return taylor_series(self, var_name, point, order)

    def integrate(self, var: Union[str, 'Sym'], a: Union[int, float], b: Union[int, float], n: int = 1000) -> float:
        """Numerically integrate this expression from a to b using Simpson's rule."""
        if isinstance(var, Sym):
            var_name = var.name
        else:
            var_name = var
        return numerical_integrate(self, var_name, a, b, n)

    def factor(self, var: Union[str, 'Sym']) -> 'Expr':
        """Factor out common terms involving `var`."""
        if isinstance(var, Sym):
            var_name = var.name
        else:
            var_name = var
        return factor(self, var_name)

    def newton_solve(self, var: Union[str, 'Sym'], x0: float = 0.0, tol: float = 1e-10, max_iter: int = 100) -> float:
        """Find a root using Newton's method starting from x0."""
        if isinstance(var, Sym):
            var_name = var.name
        else:
            var_name = var
        return newton_method(self, var_name, x0, tol, max_iter)

    def pretty(self) -> str:
        """Pretty-print this expression with minimal parentheses."""
        return pretty_print(self)


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


# ──────────────────────────── Differentiation ────────────────────────────

def differentiate(expr: Expr, var: str) -> Expr:
    """Symbolically differentiate `expr` with respect to `var`."""
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
            # log = ln
            return BinOp('*', BinOp('/', Num(1), arg), darg)
        if name == 'log2':
            return BinOp('*', BinOp('/', Num(1), BinOp('*', arg, Func('ln', Num(2)))), darg)
        if name == 'log10':
            return BinOp('*', BinOp('/', Num(1), BinOp('*', arg, Func('ln', Num(10)))), darg)

        raise ValueError(f"Differentiation not implemented for function: {name}")

    raise ValueError(f"Differentiation not implemented for: {type(expr).__name__}")


# ──────────────────────────── Simplification ────────────────────────────

def simplify(expr: Expr) -> Expr:
    """Simplify an expression by applying algebraic rules iteratively, including trig identities."""
    prev = None
    current = expr
    # Iterate until stable (fixed point)
    for _ in range(20):  # max iterations to prevent infinite loops
        simplified = _simplify_once(current)
        # Also apply trig identities
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
        # 0^x = 0 (for x > 0)
        if isinstance(base, Num) and base.value == 0:
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


# ──────────────────────────── Expansion ────────────────────────────

def expand_expr(expr: Expr) -> Expr:
    """Expand an expression by distributing multiplication over addition."""
    if isinstance(expr, (Num, Sym)):
        return expr

    if isinstance(expr, UnaryOp):
        inner = expand_expr(expr.operand)
        if expr.op == '-' and isinstance(inner, BinOp) and inner.op == '+':
            # -(a + b) = -a + (-b)
            return expand_expr(BinOp('+', UnaryOp('-', inner.left), UnaryOp('-', inner.right)))
        if expr.op == '-' and isinstance(inner, BinOp) and inner.op == '-':
            # -(a - b) = -a + b
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
            # Collect like terms: (a + bx) + (c + dx) = (a+c) + (b+d)x
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
            # a / (b + c) stays as is
            return BinOp('/', left, right)

        return BinOp(op, left, right)

    return expr


# ──────────────────────────── Substitution & Evaluation ────────────────────────────

def substitute(expr: Expr, mapping: Dict[str, Expr]) -> Expr:
    """Substitute symbols in `expr` with expressions from `mapping`."""
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
        return base_val ** exp_val

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


# ──────────────────────────── Symbol Collection ────────────────────────────

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


# ──────────────────────────── LaTeX Output ────────────────────────────

def to_latex(expr: Expr) -> str:
    """Convert an expression to a LaTeX string."""
    if isinstance(expr, Num):
        v = expr.value
        if isinstance(v, float) and v < 0:
            return f"\\left({v}\\right)"
        if isinstance(v, int) and v < 0:
            return f"\\left({v}\\right)"
        return str(v)

    if isinstance(expr, Sym):
        return expr.name

    if isinstance(expr, UnaryOp) and expr.op == '-':
        inner = to_latex(expr.operand)
        if isinstance(expr.operand, (BinOp,)):
            return f"-\\left({inner}\\right)"
        return f"-{inner}"

    if isinstance(expr, BinOp):
        left = to_latex(expr.left)
        right = to_latex(expr.right)
        if expr.op == '+':
            return f"{left} + {right}"
        if expr.op == '-':
            return f"{left} - {right}"
        if expr.op == '*':
            # Omit multiplication dot when appropriate
            if isinstance(expr.right, (Num, Sym, Func, Pow)):
                return f"{left} \\cdot {right}"
            return f"{left} \\cdot {right}"
        if expr.op == '/':
            return f"\\frac{{{left}}}{{{right}}}"

    if isinstance(expr, Pow):
        base = to_latex(expr.base)
        exp = to_latex(expr.exponent)
        if isinstance(expr.base, (BinOp, UnaryOp)):
            return f"\\left({base}\\right)^{{{exp}}}"
        return f"{{{base}}}^{{{exp}}}"

    if isinstance(expr, Func):
        arg = to_latex(expr.arg)
        if expr.name == 'sqrt':
            return f"\\sqrt{{{arg}}}"
        if expr.name == 'abs':
            return f"\\left|{arg}\\right|"
        if expr.name == 'ln':
            return f"\\ln\\left({arg}\\right)"
        if expr.name == 'exp':
            return f"e^{{{arg}}}"
        if expr.name == 'sin':
            return f"\\sin\\left({arg}\\right)"
        if expr.name == 'cos':
            return f"\\cos\\left({arg}\\right)"
        if expr.name == 'tan':
            return f"\\tan\\left({arg}\\right)"
        return f"\\operatorname{{{expr.name}}}\\left({arg}\\right)"

    return str(expr)


# ──────────────────────────── Equation Solving ────────────────────────────

def solve(expr: Expr, var: str) -> List[Expr]:
    """
    Solve expr == 0 for the given variable.

    Supports:
    - Linear equations: ax + b = 0
    - Quadratic equations: ax^2 + bx + c = 0
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
        # Try rational root theorem for integer coefficients
        c0 = int(coeffs[0].value) if isinstance(coeffs[0].value, int) else None
        cn = int(coeffs[degree].value) if isinstance(coeffs[degree].value, int) else None
        if c0 is not None and cn is not None and cn != 0:
            candidates = _rational_root_candidates(abs(c0), abs(cn))
            roots = []
            for cand in candidates:
                val = _eval_poly(coeffs, cand)
                if abs(val) < 1e-10:
                    roots.append(Num(cand))
                    # Try negative
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


def _rational_root_candidates(p: int, q: int) -> List[int]:
    """Generate candidate rational roots p/q for polynomial with leading coeff q and constant p."""
    candidates = set()
    for i in range(1, p + 1):
        if p % i == 0:
            candidates.add(i)
    for i in range(1, q + 1):
        if q % i == 0:
            candidates.add(i)
    return sorted(candidates)


def _collect_polynomial_coeffs(expr: Expr, var: str) -> Optional[Dict[int, Expr]]:
    """
    Collect polynomial coefficients for `var` in `expr`.
    Returns a dict mapping degree -> coefficient, or None if not a polynomial.
    """
    expr = simplify(expr)

    # Check if expr is constant (no var)
    if var not in collect_symbols(expr):
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
        # Handle x^n where n is a non-negative integer
        if isinstance(expr, Sym) and expr.name == var:
            # Check if exponent is a positive integer
            if isinstance(expr.exponent, Num):
                n = expr.exponent.value
                if isinstance(n, int) and n >= 0:
                    # This shouldn't happen since we're already matching Sym, but handle Pow on Sym
                    pass
            return {0: Num(0), 1: Num(1)}

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


# ──────────────────────────── Taylor Series ────────────────────────────

def taylor_series(expr: Expr, var: str, point: Union[int, float] = 0, order: int = 5) -> Expr:
    """
    Compute the Taylor series expansion of `expr` around `point` up to `order` terms.

    The Taylor series of f(x) around x=a is:
        f(x) = Σ [f^(n)(a) / n!] * (x - a)^n

    Returns a symbolic expression representing the polynomial approximation.
    """
    h = Sym(var)
    delta = BinOp('-', h, Num(point)) if point != 0 else h

    # Evaluate f(a) and successive derivatives at x=a
    result: Optional[Expr] = None
    derivative = expr
    factorial = 1

    for n in range(order + 1):
        # Compute f^(n)(a)
        if n == 0:
            f_n_a = expr
        else:
            derivative = differentiate(derivative, var)
            f_n_a = derivative

        # Substitute x = point to get f^(n)(a)
        try:
            val = f_n_a.substitute({var: Num(point)}).simplify()
        except (ValueError, ZeroDivisionError, OverflowError):
            val = Num(0)

        if n > 0:
            factorial *= n

        # term = (f^(n)(a) / n!) * (x - a)^n
        if isinstance(val, Num) and val.value == 0:
            continue

        coeff = simplify(BinOp('/', val, Num(factorial)))

        if n == 0:
            term = coeff
        elif point == 0:
            term = simplify(BinOp('*', coeff, Pow(h, Num(n))))
        else:
            term = simplify(BinOp('*', coeff, Pow(delta, Num(n))))

        if result is None:
            result = term
        else:
            result = BinOp('+', result, term)

    return simplify(result) if result is not None else Num(0)


# ──────────────────────────── Numerical Integration ────────────────────────────

def numerical_integrate(expr: Expr, var: str, a: float, b: float, n: int = 1000) -> float:
    """
    Numerically integrate `expr` from `a` to `b` using Simpson's rule.

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


# ──────────────────────────── Newton's Method ────────────────────────────

def newton_method(expr: Expr, var: str, x0: float = 0.0, tol: float = 1e-10, max_iter: int = 100) -> float:
    """
    Find a root of expr == 0 using Newton's method.

    Starting from x0, iterates: x_{n+1} = x_n - f(x_n) / f'(x_n)
    Raises ValueError if convergence fails.
    """
    derivative = expr.diff(var)

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


# ──────────────────────────── Factorization ────────────────────────────

def factor(expr: Expr, var: str) -> Expr:
    """
    Factor out common terms involving `var` from a sum expression.

    For example: 2*x + 4*x^2 → x * (2 + 4*x) or similar factored forms.
    Attempts to extract common polynomial factors.
    """
    expr = simplify(expr)

    # Only factor sums
    if not isinstance(expr, BinOp) or expr.op != '+':
        return expr

    # Collect additive terms
    terms = _collect_additive_terms(expr)

    if len(terms) < 2:
        return expr

    # Find common factors among all terms
    # Each term is (coefficient, factors_dict) where factors_dict maps base_expr -> exponent
    parsed_terms = []
    for term in terms:
        parsed_terms.append(_parse_multiplicative_factors(term))

    if len(parsed_terms) < 2:
        return expr

    # Find intersection of all factor sets (common factors)
    common_factors: Dict[Tuple, int] = {}

    # Start with factors from first term
    for base_key, exp in parsed_terms[0].items():
        common_factors[base_key] = exp

    # Intersect with factors from remaining terms
    for i in range(1, len(parsed_terms)):
        term_factors = parsed_terms[i]
        new_common = {}
        for base_key, exp in common_factors.items():
            if base_key in term_factors:
                # Take minimum exponent
                new_common[base_key] = min(exp, term_factors[base_key])
        common_factors = new_common

    if not common_factors:
        return expr  # No common factors found

    # Reconstruct: (common_factor) * (sum of reduced terms)
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
        # Start with the coefficient
        coeff = 1
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

    # Build the result: common_expr * (sum of reduced_terms)
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
        # Numeric factor
        key = ('num', expr.value)
        factors[key] = factors.get(key, 0) + 1
        return factors

    if isinstance(expr, Sym):
        key = ('sym', expr.name)
        factors[key] = factors.get(key, 0) + 1
        return factors

    if isinstance(expr, Pow):
        # For x^n, we get factor x^n
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


# ──────────────────────────── Pretty Printing ────────────────────────────

def pretty_print(expr: Expr) -> str:
    """
    Pretty-print an expression with minimal parentheses.

    Uses operator precedence to avoid unnecessary parentheses:
    - Addition/subtraction: lowest precedence (1)
    - Multiplication/division: medium precedence (2)
    - Unary negation: precedence (3)
    - Exponentiation: high precedence (4)
    - Atoms: no parentheses needed
    """
    return _pretty(expr, parent_prec=0, parent_side='none')


def _prec(expr: Expr) -> int:
    """Get the precedence level of an expression."""
    if isinstance(expr, (Num, Sym, Func)):
        return 100
    if isinstance(expr, UnaryOp):
        return 30
    if isinstance(expr, BinOp):
        if expr.op in ('+', '-'):
            return 10
        if expr.op in ('*', '/'):
            return 20
    if isinstance(expr, Pow):
        return 40
    return 0


def _pretty(expr: Expr, parent_prec: int, parent_side: str) -> str:
    """Pretty-print with context about parent operator for parenthesization."""
    if isinstance(expr, Num):
        v = expr.value
        if isinstance(v, float):
            # Clean up float display
            if v == int(v):
                return str(int(v))
            return str(v)
        return str(v)

    if isinstance(expr, Sym):
        return expr.name

    if isinstance(expr, UnaryOp) and expr.op == '-':
        inner = _pretty(expr.operand, 30, 'left')
        result = f"-{inner}"
        # Parenthesize if parent has higher precedence
        if parent_prec > 30:
            return f"({result})"
        return result

    if isinstance(expr, Func):
        arg_str = _pretty(expr.arg, 0, 'none')
        return f"{expr.name}({arg_str})"

    if isinstance(expr, Pow):
        base_str = _pretty(expr.base, 40, 'left')
        exp_str = _pretty(expr.exponent, 40, 'right')
        result = f"{base_str}^{exp_str}"
        if parent_prec > 40:
            return f"({result})"
        return result

    if isinstance(expr, BinOp):
        my_prec = _prec(expr)
        left_str = _pretty(expr.left, my_prec, 'left')
        right_str = _pretty(expr.right, my_prec, 'right')

        # For right side of subtraction or division, need parens if same precedence
        need_right_parens = False
        if expr.op == '-' and isinstance(expr.right, BinOp) and expr.right.op in ('+', '-'):
            need_right_parens = True
        if expr.op == '/' and isinstance(expr.right, BinOp) and expr.right.op in ('*', '/'):
            need_right_parens = True

        if need_right_parens:
            right_str = f"({right_str})"

        result = f"{left_str} {expr.op} {right_str}"

        # Parenthesize if parent has higher precedence, or if we're on the right
        # side of another operation with same precedence (for non-commutative ops)
        if parent_prec > my_prec:
            return f"({result})"
        if parent_prec == my_prec and parent_side == 'right' and my_prec in (10, 20):
            return f"({result})"

        return result

    return str(expr)


# ──────────────────────────── Enhanced Simplification (Trig Identities) ────────────────────────────

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
        # Check for sin²x + cos²x pattern
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
    # sin²x + cos²x = 1
    left_info = _extract_trig_squared(left)
    right_info = _extract_trig_squared(right)

    if left_info and right_info:
        l_name, l_arg, l_coeff = left_info
        r_name, r_arg, r_coeff = right_info

        # Check if arguments match
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


# ──────────────────────────── Parser ────────────────────────────

# Token types
_TOK_NUM = 'NUM'
_TOK_SYM = 'SYM'
_TOK_OP = 'OP'
_TOK_LPAREN = 'LPAREN'
_TOK_RPAREN = 'RPAREN'
_TOK_COMMA = 'COMMA'
_TOK_CARET = 'CARET'
_TOK_EOF = 'EOF'


class _Token:
    def __init__(self, typ: str, value: str):
        self.typ = typ
        self.value = value

    def __repr__(self):
        return f"Token({self.typ}, {self.value!r})"


def _tokenize(expr_str: str) -> List[_Token]:
    """Tokenize an expression string."""
    tokens = []
    i = 0
    while i < len(expr_str):
        ch = expr_str[i]
        if ch.isspace():
            i += 1
            continue
        if ch in '+-':
            tokens.append(_Token(_TOK_OP, ch))
            i += 1
        elif ch in '*/':
            tokens.append(_Token(_TOK_OP, ch))
            i += 1
        elif ch == '^':
            tokens.append(_Token(_TOK_CARET, '^'))
            i += 1
        elif ch == '(':
            tokens.append(_Token(_TOK_LPAREN, '('))
            i += 1
        elif ch == ')':
            tokens.append(_Token(_TOK_RPAREN, ')'))
            i += 1
        elif ch == ',':
            tokens.append(_Token(_TOK_COMMA, ','))
            i += 1
        elif ch.isdigit() or ch == '.':
            j = i
            has_dot = False
            while j < len(expr_str) and (expr_str[j].isdigit() or (expr_str[j] == '.' and not has_dot)):
                if expr_str[j] == '.':
                    has_dot = True
                j += 1
            tokens.append(_Token(_TOK_NUM, expr_str[i:j]))
            i = j
        elif ch.isalpha() or ch == '_':
            j = i
            while j < len(expr_str) and (expr_str[j].isalnum() or expr_str[j] == '_'):
                j += 1
            name = expr_str[i:j]
            # Check if it's a known function
            if name in Func.KNOWN_FUNCS:
                tokens.append(_Token(_TOK_SYM, name))  # will be parsed as function call if followed by (
            else:
                tokens.append(_Token(_TOK_SYM, name))
            i = j
        else:
            raise ValueError(f"Unexpected character: {ch!r} at position {i}")

    tokens.append(_Token(_TOK_EOF, ''))
    return tokens


class _Parser:
    """Recursive descent parser with proper operator precedence."""

    def __init__(self, tokens: List[_Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> _Token:
        return self.tokens[self.pos]

    def advance(self) -> _Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, typ: str) -> _Token:
        tok = self.advance()
        if tok.typ != typ:
            raise ValueError(f"Expected {typ}, got {tok.typ} ({tok.value!r})")
        return tok

    def parse(self) -> Expr:
        result = self.parse_expr()
        if self.peek().typ != _TOK_EOF:
            raise ValueError(f"Unexpected token after expression: {self.peek()}")
        return result

    def parse_expr(self) -> Expr:
        return self.parse_additive()

    def parse_additive(self) -> Expr:
        left = self.parse_multiplicative()
        while self.peek().typ == _TOK_OP and self.peek().value in ('+', '-'):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinOp(op, left, right)
        return left

    def parse_multiplicative(self) -> Expr:
        left = self.parse_unary()
        while self.peek().typ == _TOK_OP and self.peek().value in ('*', '/'):
            op = self.advance().value
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self) -> Expr:
        if self.peek().typ == _TOK_OP and self.peek().value == '-':
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('-', operand)
        if self.peek().typ == _TOK_OP and self.peek().value == '+':
            self.advance()
            return self.parse_unary()
        return self.parse_power()

    def parse_power(self) -> Expr:
        base = self.parse_atom()
        if self.peek().typ == _TOK_CARET:
            self.advance()
            exp = self.parse_unary()  # right-associative
            return Pow(base, exp)
        return base

    def parse_atom(self) -> Expr:
        tok = self.peek()

        if tok.typ == _TOK_NUM:
            self.advance()
            val = float(tok.value)
            if val == int(val) and '.' not in tok.value:
                val = int(val)
            return Num(val)

        if tok.typ == _TOK_SYM:
            name = tok.value
            self.advance()
            # Check if it's a function call
            if self.peek().typ == _TOK_LPAREN and name in Func.KNOWN_FUNCS:
                self.advance()  # consume '('
                arg = self.parse_expr()
                self.expect(_TOK_RPAREN)
                return Func(name, arg)
            return Sym(name)

        if tok.typ == _TOK_LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(_TOK_RPAREN)
            return expr

        raise ValueError(f"Unexpected token: {tok}")


def parse(expr_str: str) -> Expr:
    """Parse a mathematical expression string into an Expr AST."""
    tokens = _tokenize(expr_str)
    parser = _Parser(tokens)
    return parser.parse()


# ──────────────────────────── Convenience ────────────────────────────

# Pre-defined symbols for convenient construction
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


# Export all new functions for convenience
__all__ = [
    'Expr', 'Num', 'Sym', 'BinOp', 'UnaryOp', 'Func', 'Pow',
    'parse', 'simplify', 'differentiate', 'expand_expr',
    'substitute', 'evaluate', 'collect_symbols', 'to_latex', 'solve',
    'taylor_series', 'numerical_integrate', 'newton_method',
    'factor', 'pretty_print',
    'x', 'y', 'z', 't', 'n', 'pi', 'e',
    'sym', 'num', 'sin', 'cos', 'tan', 'exp', 'ln', 'sqrt', 'abs_expr',
]


# ──────────────────────────── CLI Interface ────────────────────────────

def main():
    """Simple REPL for the symbolic algebra system."""
    import sys

    print("=" * 60)
    print("  Symbolic Algebra System — Interactive REPL")
    print("=" * 60)
    print("Commands:")
    print("  <expr>            — Parse and simplify an expression")
    print("  diff <expr>       — Differentiate (w.r.t. x)")
    print("  expand <expr>     — Expand an expression")
    print("  factor <expr>     — Factor an expression (w.r.t. x)")
    print("  latex <expr>      — Convert to LaTeX")
    print("  eval <expr>       — Evaluate with x=1, y=2, z=3")
    print("  solve <expr>      — Solve expr=0 for x")
    print("  newton <expr>     — Find root via Newton's method (w.r.t. x)")
    print("  taylor <expr>     — Taylor series around x=0 (5 terms)")
    print("  integrate <expr>  — Numerically integrate from 0 to 1")
    print("  symbols <expr>    — List symbols in expression")
    print("  pretty <expr>     — Pretty-print expression")
    print("  quit              — Exit")
    print("=" * 60)

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue
        if line == 'quit':
            break

        try:
            if line.startswith('diff '):
                expr = parse(line[5:])
                result = expr.diff('x').simplify()
                print(f"  d/dx({expr.simplify()}) = {result}")
            elif line.startswith('expand '):
                expr = parse(line[7:])
                result = expr.expand().simplify()
                print(f"  Expanded: {result}")
            elif line.startswith('factor '):
                expr = parse(line[7:])
                result = expr.factor('x')
                print(f"  Factored: {result.pretty()}")
            elif line.startswith('latex '):
                expr = parse(line[6:])
                result = expr.simplify()
                print(f"  LaTeX: {result.to_latex()}")
            elif line.startswith('eval '):
                expr = parse(line[5:])
                result = expr.evaluate({'x': 1, 'y': 2, 'z': 3})
                print(f"  Result: {result}")
            elif line.startswith('solve '):
                expr = parse(line[6:])
                solutions = expr.solve('x')
                if solutions:
                    print(f"  Solutions: {', '.join(str(s) for s in solutions)}")
                else:
                    print("  No real solutions")
            elif line.startswith('newton '):
                expr = parse(line[7:])
                root = expr.newton_solve('x')
                print(f"  Root (Newton): x ≈ {root:.10f}")
            elif line.startswith('taylor '):
                expr = parse(line[7:])
                result = expr.taylor('x', point=0, order=5)
                print(f"  Taylor series: {result.pretty()}")
            elif line.startswith('integrate '):
                expr = parse(line[10:])
                result = expr.integrate('x', 0, 1)
                print(f"  ∫₀¹ f(x)dx ≈ {result:.10f}")
            elif line.startswith('symbols '):
                expr = parse(line[8:])
                syms = expr.symbols()
                print(f"  Symbols: {', '.join(sorted(syms))}")
            elif line.startswith('pretty '):
                expr = parse(line[7:])
                print(f"  {expr.pretty()}")
            else:
                expr = parse(line)
                result = expr.simplify()
                print(f"  Simplified: {result}")
        except Exception as exc:
            print(f"  Error: {exc}")


if __name__ == '__main__':
    main()