"""Galois Field GF(2^8) arithmetic for Reed-Solomon codes.

The field uses the irreducible polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D),
which is the standard polynomial used in QR codes, CDs, and most RS implementations.
The generator (primitive element) is 2.

All polynomial functions use the LOWEST-DEGREE-FIRST convention:
  poly[0] = constant term, poly[1] = x^1 coefficient, ..., poly[n] = x^n coefficient.
"""
from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)

# Irreducible polynomial for GF(2^8): x^8 + x^4 + x^3 + x^2 + 1
# Used in QR codes and many RS implementations
PRIMARY_POLY = 0x11D


class GF256:
    """GF(2^8) finite field with precomputed log/exp tables.

    Supports addition (XOR), multiplication, division, and powers
    using the primitive element (generator) g = 2.

    All operations are O(1) after table initialisation at import time.
    """

    _exp: List[int] = [0] * 512  # doubled for wraparound in multiply
    _log: List[int] = [0] * 256
    _initialised: bool = False

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
        cls._initialised = True
        logger.debug("GF(2^8) log/exp tables initialised (primary poly=0x%03X)", PRIMARY_POLY)

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
        """Divide field element a by field element b.

        Raises:
            ZeroDivisionError: If b is 0.
        """
        if b == 0:
            raise ZeroDivisionError("division by zero in GF(256)")
        if a == 0:
            return 0
        return cls._exp[(cls._log[a] - cls._log[b]) % 255]

    @classmethod
    def pow(cls, a: int, e: int) -> int:
        """Raise field element a to power e.

        Args:
            a: Field element (0-255).
            e: Non-negative integer exponent.

        Raises:
            ValueError: If e is negative.
            TypeError: If e is not an integer.
        """
        if not isinstance(e, int):
            raise TypeError(f"exponent must be an integer, got {type(e).__name__}")
        if e < 0:
            raise ValueError(f"negative exponent {e} not supported in GF(256) pow")
        if a == 0:
            return 0 if e != 0 else 1
        if e == 0:
            return 1
        return cls._exp[(cls._log[a] * e) % 255]

    @classmethod
    def inv(cls, a: int) -> int:
        """Multiplicative inverse of a in GF(2^8).

        Raises:
            ZeroDivisionError: If a is 0.
        """
        if a == 0:
            raise ZeroDivisionError("no inverse for 0 in GF(256)")
        return cls._exp[255 - cls._log[a]]

    @classmethod
    def log(cls, a: int) -> int:
        """Discrete logarithm base generator (2).

        Raises:
            ValueError: If a is 0.
        """
        if a == 0:
            raise ValueError("log(0) is undefined")
        return cls._log[a]


# Initialise tables on import
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
    """Multiply two polynomials (lowest-degree-first).

    The product of anything with an empty/zero polynomial is ``[0]``.
    """
    if not p or not q:
        return [0]
    r = [0] * (len(p) + len(q) - 1)
    for j in range(len(q)):
        for i in range(len(p)):
            r[i + j] ^= GF256.mul(p[i], q[j])
    return r


def gf_poly_eval(poly: List[int], x: int) -> int:
    """Evaluate polynomial at *x* using Horner's method (lowest-degree-first).

    Computes ``poly[0] + poly[1]*x + poly[2]*x^2 + ... + poly[n]*x^n``.
    """
    y = 0
    for i in range(len(poly) - 1, -1, -1):
        y = GF256.mul(y, x) ^ poly[i]
    return y


def gf_poly_div(dividend: List[int], divisor: List[int]) -> tuple:
    """Polynomial division (lowest-degree-first).

    Returns ``(quotient, remainder)`` as lowest-degree-first coefficient lists.
    ``dividend = quotient * divisor + remainder``, ``deg(remainder) < deg(divisor)``.
    """
    if not divisor or all(c == 0 for c in divisor):
        raise ZeroDivisionError("polynomial division by zero")

    # Work with copies in highest-degree-first for the standard long-division algorithm
    rev_div = list(reversed(dividend))
    rev_divisor = list(reversed(divisor))

    # Trim leading zeros from divisor
    while len(rev_divisor) > 1 and rev_divisor[0] == 0:
        rev_divisor.pop(0)

    divisor_lead_inv = GF256.inv(rev_divisor[0])

    quotient_rev: List[int] = []
    remainder = list(rev_div)

    for i in range(len(rev_div) - len(rev_divisor) + 1):
        if remainder[i] == 0:
            quotient_rev.append(0)
            continue
        # Scale factor: make remainder[i] cancel with divisor[0]
        scale = GF256.mul(remainder[i], divisor_lead_inv)
        quotient_rev.append(scale)
        for j in range(len(rev_divisor)):
            remainder[i + j] ^= GF256.mul(rev_divisor[j], scale)

    quotient = list(reversed(quotient_rev))
    rem_start = len(quotient_rev)
    rem_rev = remainder[rem_start:]
    remainder_low = list(reversed(rem_rev))

    # Trim trailing zeros from quotient (high-degree zero coefficients)
    while len(quotient) > 1 and quotient[-1] == 0:
        quotient.pop()

    return quotient, remainder_low


def gf_poly_scale(poly: List[int], x: int) -> List[int]:
    """Scale polynomial by scalar *x* (lowest-degree-first)."""
    return [GF256.mul(c, x) for c in poly]