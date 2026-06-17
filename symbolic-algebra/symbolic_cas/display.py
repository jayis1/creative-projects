"""Display: pretty-printing and LaTeX output."""

from __future__ import annotations

from typing import Optional

from symbolic_cas.expr import Expr, Num, Sym, BinOp, UnaryOp, Func, Pow


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
            if v == int(v):
                return str(int(v))
            return str(v)
        return str(v)

    if isinstance(expr, Sym):
        return expr.name

    if isinstance(expr, UnaryOp) and expr.op == '-':
        inner = _pretty(expr.operand, 30, 'left')
        result = f"-{inner}"
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

        if parent_prec > my_prec:
            return f"({result})"
        if parent_prec == my_prec and parent_side == 'right' and my_prec in (10, 20):
            return f"({result})"

        return result

    return str(expr)