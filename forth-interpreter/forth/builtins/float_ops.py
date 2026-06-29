"""Floating-point words: F+, F-, F*, F/, FSQRT, FSIN, FCOS, FTAN, FLOG, FEXP, FLOOR, CEIL, ROUND."""

import math

from forth.core import ForthError


def register_float_ops(i) -> None:
    """Register floating-point words on *i*."""

    def _fadd(i, t, n):
        b = float(i.pop())
        a = float(i.pop())
        i.push(a + b)
    i.reg("F+", _fadd, doc="Float add")

    def _fsub(i, t, n):
        b = float(i.pop())
        a = float(i.pop())
        i.push(a - b)
    i.reg("F-", _fsub, doc="Float subtract")

    def _fmul(i, t, n):
        b = float(i.pop())
        a = float(i.pop())
        i.push(a * b)
    i.reg("F*", _fmul, doc="Float multiply")

    def _fdiv(i, t, n):
        b = float(i.pop())
        if b == 0.0:
            raise ForthError("float division by zero")
        a = float(i.pop())
        i.push(a / b)
    i.reg("F/", _fdiv, doc="Float divide")

    i.reg("FSQRT", lambda i, t, n: i.push(math.sqrt(float(i.pop()))), doc="Float sqrt")
    i.reg("FSIN", lambda i, t, n: i.push(math.sin(float(i.pop()))), doc="Float sin")
    i.reg("FCOS", lambda i, t, n: i.push(math.cos(float(i.pop()))), doc="Float cos")
    i.reg("FTAN", lambda i, t, n: i.push(math.tan(float(i.pop()))), doc="Float tan")
    i.reg("FLOG", lambda i, t, n: i.push(math.log(float(i.pop()))), doc="Float natural log")
    i.reg("FEXP", lambda i, t, n: i.push(math.exp(float(i.pop()))), doc="Float exp")
    i.reg("FLOOR", lambda i, t, n: i.push(math.floor(float(i.pop()))), doc="Floor")
    i.reg("CEIL", lambda i, t, n: i.push(math.ceil(float(i.pop()))), doc="Ceiling")
    i.reg("ROUND", lambda i, t, n: i.push(round(float(i.pop()))), doc="Round")

    # Additional float words
    i.reg("FABS", lambda i, t, n: i.push(abs(float(i.pop()))), doc="Float absolute value")
    i.reg("FNEGATE", lambda i, t, n: i.push(-float(i.pop())), doc="Float negate")
    i.reg("FATAN", lambda i, t, n: i.push(math.atan(float(i.pop()))), doc="Float arctan")
    i.reg("FASIN", lambda i, t, n: i.push(math.asin(float(i.pop()))), doc="Float arcsin")
    i.reg("FACOS", lambda i, t, n: i.push(math.acos(float(i.pop()))), doc="Float arccos")
    i.reg("FATAN2", lambda i, t, n: (b := float(i.pop()), a := float(i.pop()), i.push(math.atan2(a, b)))[-1], doc="Float atan2 ( y x -- atan2(y,x) )")
    i.reg("F**", lambda i, t, n: (b := float(i.pop()), a := float(i.pop()), i.push(a ** b))[-1], doc="Float power (base exp -- base^exp)")
    i.reg("PI", lambda i, t, n: i.push(math.pi), doc="Push pi")
    i.reg("E", lambda i, t, n: i.push(math.e), doc="Push Euler's number")