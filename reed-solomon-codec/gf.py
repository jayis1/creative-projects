"""Galois Field GF(2^8) arithmetic for Reed-Solomon codes.

The field uses the irreducible polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D),
which is the standard polynomial used in QR codes, CDs, and most RS implementations.
The generator (primitive element) is 2.

All polynomial functions use the LOWEST-DEGREE-FIRST convention:
  poly[0] = constant term, poly[1] = x^1 coefficient, ..., poly[n] = x^n coefficient.
"""
from __future__ import annotations

from typing import List

# Irreducible polynomial for GF(2^8): x^8 + x^4 + x^3 + x^2 + 1
# Used in QR codes and many RS implementations
PRIMARY_POLY = 0x11D


class GF256:
    """GF(2^8) finite field with precomputed log/exp tables.

    Supports addition (XOR), multiplication, division, and powers
    using the primitive element (generator) g = 2.
    """

    _exp: List[int] = [0] * 512  # doubled for wraparound in multiply
    _log: List[int] = [0] * 256

    def __init__(self) -> None:
        raise TypeError("GF256 is a static class; do not instantiate.")

    @classmethod
    def _init_tables(cls) -> None:
        """Precompute exp and log tables for the field."""
        x = 1
        for i in range(255):
            cls._exp[i] = x
            cls._log[x] = i
            # Multiply by generator (2): shift left, reduce if needed
            x <<= 1
            if x & 0x100:
                x ^= PRIMARY_POLY
        # Extend exp table for wraparound (exp[i+255] == exp[i])
        for i in range(255, 512):
            cls._exp[i] = cls._exp[i - 255]

    @classmethod
    def add(cls, a: int, b: int) -> int:
        """Add two field elements (XOR in GF(2^8))."""
        return a ^ b

    @classmethod
    def sub(cls, a: int, b: int) -> int:
        """Subtract two field elements (same as add in GF(2^8))."""
        return a ^ b

    @classmethod
    def mul(cls, a: int, b: int) -> int:
        """Multiply two field elements."""
        if a == 0 or b == 0:
            return 0
        return cls._exp[cls._log[a] + cls._log[b]]

    @classmethod
    def div(cls, a: int, b: int) -> int:
        """Divide field element a by field element b. Raises ZeroDivisionError if b is 0."""
        if b == 0:
            raise ZeroDivisionError("division by zero in GF(256)")
        if a == 0:
            return 0
        return cls._exp[(cls._log[a] - cls._log[b]) % 255]

    @classmethod
    def pow(cls, a: int, e: int) -> int:
        """Raise field element a to power e."""
        if a == 0:
            return 0 if e != 0 else 1
        if e == 0:
            return 1
        return cls._exp[(cls._log[a] * e) % 255]

    @classmethod
    def inv(cls, a: int) -> int:
        """Multiplicative inverse of a in GF(2^8)."""
        if a == 0:
            raise ZeroDivisionError("no inverse for 0 in GF(256)")
        return cls._exp[255 - cls._log[a]]

    @classmethod
    def log(cls, a: int) -> int:
        """Discrete logarithm base generator (2). Raises ValueError if a is 0."""
        if a == 0:
            raise ValueError("log(0) is undefined")
        return cls._log[a]


# Initialize tables on import
GF256._init_tables()


# --- Polynomial operations over GF(2^8) ---
# Convention: polynomials are lists with LOWEST degree first.
#   poly[0] = constant term, poly[i] = coefficient of x^i


def gf_poly_add(p: List[int], q: List[int]) -> List[int]:
    """Add two polynomials (lowest-degree-first)."""
    r = [0] * max(len(p), len(q))
    for i, c in enumerate(p):
        r[i] ^= c
    for i, c in enumerate(q):
        r[i] ^= c
    return r


def gf_poly_mul(p: List[int], q: List[int]) -> List[int]:
    """Multiply two polynomials (lowest-degree-first)."""
    r = [0] * (len(p) + len(q) - 1)
    for j in range(len(q)):
        for i in range(len(p)):
            r[i + j] ^= GF256.mul(p[i], q[j])
    return r


def gf_poly_eval(poly: List[int], x: int) -> int:
    """Evaluate polynomial at x using Horner's method (lowest-degree-first).

    Computes poly[0] + poly[1]*x + poly[2]*x^2 + ... + poly[n]*x^n.
    """
    y = 0
    for i in range(len(poly) - 1, -1, -1):
        y = GF256.mul(y, x) ^ poly[i]
    return y


def gf_poly_div(dividend: List[int], divisor: List[int]) -> tuple:
    """Polynomial division (lowest-degree-first).

    Returns (quotient, remainder) as lowest-degree-first coefficient lists.
    dividend = quotient * divisor + remainder, deg(remainder) < deg(divisor).
    """
    # Reverse to highest-degree-first for the division algorithm
    rev_div = list(reversed(dividend))
    rev_divisor = list(reversed(divisor))

    msg_out = list(rev_div)
    for i in range(len(rev_div) - len(rev_divisor) + 1):
        coef = msg_out[i]
        if coef != 0:
            for j in range(1, len(rev_divisor)):
                msg_out[i + j] ^= GF256.mul(rev_divisor[j], coef)
    separator = -(len(rev_divisor) - 1)
    quotient = list(reversed(msg_out[:separator]))
    remainder = list(reversed(msg_out[separator:]))
    return quotient, remainder


def gf_poly_scale(poly: List[int], x: int) -> List[int]:
    """Scale polynomial by scalar x (lowest-degree-first)."""
    return [GF256.mul(c, x) for c in poly]