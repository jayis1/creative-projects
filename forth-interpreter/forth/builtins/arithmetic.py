"""Arithmetic words: +, -, *, /, MOD, /MOD, NEGATE, ABS, MIN, MAX, **, etc."""

from forth.core import ForthError


def register_arithmetic(i) -> None:
    """Register arithmetic words on *i*."""

    def _add(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(a + b)
    i.reg("+", _add, doc="Addition")

    def _sub(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(a - b)
    i.reg("-", _sub, doc="Subtraction")

    def _mul(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(a * b)
    i.reg("*", _mul, doc="Multiplication")

    def _div(i, t, n):
        b = i.pop_int()
        if b == 0:
            raise ForthError("division by zero")
        a = i.pop_int()
        q = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            q = -q
        i.push(q)
    i.reg("/", _div, doc="Integer division (truncate toward zero)")

    def _mod(i, t, n):
        b = i.pop_int()
        if b == 0:
            raise ForthError("modulo by zero")
        a = i.pop_int()
        r = abs(a) % abs(b)
        if a < 0:
            r = -r
        i.push(r)
    i.reg("MOD", _mod, doc="Modulo (sign follows dividend)")

    def _divmod(i, t, n):
        b = i.pop_int()
        if b == 0:
            raise ForthError("division by zero")
        a = i.pop_int()
        q = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            q = -q
        r = abs(a) % abs(b)
        if a < 0:
            r = -r
        i.push(r)
        i.push(q)
    i.reg("/MOD", _divmod, doc="Division with remainder")

    i.reg("NEGATE", lambda i, t, n: i.push(-i.pop()), doc="Negate")
    i.reg("ABS", lambda i, t, n: i.push(abs(i.pop())), doc="Absolute value")

    def _min(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(min(a, b))
    i.reg("MIN", _min, doc="Minimum")

    def _max(i, t, n):
        b = i.pop()
        a = i.pop()
        i.push(max(a, b))
    i.reg("MAX", _max, doc="Maximum")

    def _pow(i, t, n):
        b = i.pop_int()
        a = i.pop_int()
        i.push(a ** b)
    i.reg("**", _pow, doc="Power")

    # ── convenience arithmetic ──
    i.reg("1+", lambda i, t, n: i.push(i.pop() + 1), doc="Add 1")
    i.reg("1-", lambda i, t, n: i.push(i.pop() - 1), doc="Subtract 1")
    i.reg("2+", lambda i, t, n: i.push(i.pop() + 2), doc="Add 2")
    i.reg("2-", lambda i, t, n: i.push(i.pop() - 2), doc="Subtract 2")
    i.reg("2*", lambda i, t, n: i.push(i.pop_int() * 2), doc="Multiply by 2")
    i.reg("2/", lambda i, t, n: i.push(i.pop_int() >> 1), doc="Divide by 2 (shift right)")
    i.reg("S>D", lambda i, t, n: None, doc="Sign-extend to double (no-op for Python ints)")