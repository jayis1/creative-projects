"""Bitwise words: AND, OR, XOR, INVERT, LSHIFT, RSHIFT, NOT."""

from forth.core import ForthError


def register_bitwise(i) -> None:
    """Register bitwise words on *i*."""

    i.reg("AND", lambda i, t, n: i.push(i.pop_int() & i.pop_int()), doc="Bitwise AND")
    i.reg("OR", lambda i, t, n: i.push(i.pop_int() | i.pop_int()), doc="Bitwise OR")
    i.reg("XOR", lambda i, t, n: i.push(i.pop_int() ^ i.pop_int()), doc="Bitwise XOR")
    i.reg("INVERT", lambda i, t, n: i.push(~i.pop_int()), doc="Bitwise NOT")

    def _lshift(i, t, n):
        b = i.pop_int()
        a = i.pop_int()
        i.push(a << b)
    i.reg("LSHIFT", _lshift, doc="Left shift")

    def _rshift(i, t, n):
        b = i.pop_int()
        a = i.pop_int()
        i.push(a >> b)
    i.reg("RSHIFT", _rshift, doc="Right shift")

    i.reg("NOT", lambda i, t, n: i.push(-1 if i.pop() == 0 else 0), doc="Logical NOT")