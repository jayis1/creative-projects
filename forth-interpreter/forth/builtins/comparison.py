"""Comparison words: =, <>, <, >, <=, >=, 0=, 0<>, 0<, 0>."""


def register_comparison(i) -> None:
    """Register comparison words on *i*."""

    i.reg("=", lambda i, t, n: i.push(-1 if i.pop() == i.pop() else 0), doc="Equal")
    i.reg("<>", lambda i, t, n: i.push(-1 if i.pop() != i.pop() else 0), doc="Not equal")

    def _lt(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(-1 if a < b else 0)
    i.reg("<", _lt, doc="Less than")

    def _gt(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(-1 if a > b else 0)
    i.reg(">", _gt, doc="Greater than")

    def _le(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(-1 if a <= b else 0)
    i.reg("<=", _le, doc="Less or equal")

    def _ge(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(-1 if a >= b else 0)
    i.reg(">=", _ge, doc="Greater or equal")

    i.reg("0=", lambda i, t, n: i.push(-1 if i.pop() == 0 else 0), doc="Top == 0?")
    i.reg("0<>", lambda i, t, n: i.push(-1 if i.pop() != 0 else 0), doc="Top != 0?")
    i.reg("0<", lambda i, t, n: i.push(-1 if i.pop() < 0 else 0), doc="Top < 0?")
    i.reg("0>", lambda i, t, n: i.push(-1 if i.pop() > 0 else 0), doc="Top > 0?")