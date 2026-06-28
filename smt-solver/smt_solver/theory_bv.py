"""
Theory of Fixed-Size Bit-Vectors (QF_BV).

Supports basic bit-vector operations:
  - Bit-vector arithmetic: bvadd, bvsub, bvmul, bvudiv, bvurem, bvneg
  - Bit-wise: bvand, bvor, bvxor, bvnot, bvnand, bvnor, bvxnor
  - Shifts: bvshl, bvlshr, bvashr
  - Comparisons: bvult, bvule, bvugt, bvuge, bvslt, bv sle, bvsgt, bvsge
  - Concatenation: concat
  - Extraction: extract
  - Constants: bvN[digits]

Bit-vectors are represented as Python integers with a width parameter.
All operations are performed modulo 2^width.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional, Set


class BitVector:
    """A fixed-width bit-vector value."""

    __slots__ = ("value", "width")

    def __init__(self, value: int, width: int):
        self.width = width
        mask = (1 << width) - 1
        self.value = value & mask

    def __add__(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        return BitVector(self.value + other.value, self.width)

    def __sub__(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        return BitVector(self.value - other.value, self.width)

    def __mul__(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        return BitVector(self.value * other.value, self.width)

    def udiv(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        if other.value == 0:
            return BitVector((1 << self.width) - 1, self.width)  # all-ones
        return BitVector(self.value // other.value, self.width)

    def urem(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        if other.value == 0:
            return self
        return BitVector(self.value % other.value, self.width)

    def __neg__(self) -> "BitVector":
        return BitVector(-self.value, self.width)

    def __and__(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        return BitVector(self.value & other.value, self.width)

    def __or__(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        return BitVector(self.value | other.value, self.width)

    def __xor__(self, other: "BitVector") -> "BitVector":
        assert self.width == other.width
        return BitVector(self.value ^ other.value, self.width)

    def __invert__(self) -> "BitVector":
        return BitVector(~self.value, self.width)

    def shl(self, other: "BitVector") -> "BitVector":
        shift = other.value
        if shift >= self.width:
            return BitVector(0, self.width)
        return BitVector(self.value << shift, self.width)

    def lshr(self, other: "BitVector") -> "BitVector":
        shift = other.value
        if shift >= self.width:
            return BitVector(0, self.width)
        return BitVector(self.value >> shift, self.width)

    def ashr(self, other: "BitVector") -> "BitVector":
        shift = other.value
        if shift >= self.width:
            # Fill with sign bit
            if self.value >> (self.width - 1):
                return BitVector((1 << self.width) - 1, self.width)
            return BitVector(0, self.width)
        # Sign-extend the value
        if self.value >> (self.width - 1):
            # Negative: extend with 1s
            sign_bits = ((1 << shift) - 1) << (self.width - shift)
            return BitVector((self.value >> shift) | sign_bits, self.width)
        return BitVector(self.value >> shift, self.width)

    def ult(self, other: "BitVector") -> bool:
        return self.value < other.value

    def ule(self, other: "BitVector") -> bool:
        return self.value <= other.value

    def ugt(self, other: "BitVector") -> bool:
        return self.value > other.value

    def uge(self, other: "BitVector") -> bool:
        return self.value >= other.value

    def slt(self, other: "BitVector") -> bool:
        return self._signed() < other._signed()

    def sle(self, other: "BitVector") -> bool:
        return self._signed() <= other._signed()

    def sgt(self, other: "BitVector") -> bool:
        return self._signed() > other._signed()

    def sge(self, other: "BitVector") -> bool:
        return self._signed() >= other._signed()

    def _signed(self) -> int:
        if self.value >> (self.width - 1):
            return self.value - (1 << self.width)
        return self.value

    def concat(self, other: "BitVector") -> "BitVector":
        """Concatenate: self is the high part, other is the low part."""
        return BitVector((self.value << other.width) | other.value,
                         self.width + other.width)

    def extract(self, high: int, low: int) -> "BitVector":
        """Extract bits [high:low] (inclusive)."""
        mask = (1 << (high - low + 1)) - 1
        return BitVector((self.value >> low) & mask, high - low + 1)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BitVector):
            return False
        return self.value == other.value and self.width == other.width

    def __hash__(self) -> int:
        return hash((self.value, self.width))

    def __str__(self) -> str:
        return f"bv{self.width}[{self.value}]"

    def __repr__(self) -> str:
        return f"BitVector({self.value}, {self.width})"

    def to_bin(self) -> str:
        """Return binary string representation."""
        return format(self.value, f'0{self.width}b')


class BitVectorTheory:
    """Bit-vector theory solver for SMT.

    Evaluates bit-vector constraints against a model.
    """

    def __init__(self):
        self._constraints: List[Tuple[object, bool]] = []
        self._bv_vars: Set[str] = set()

    def assert_atom(self, atom: object, polarity: bool) -> bool:
        """Assert a bit-vector atom."""
        self._constraints.append((atom, polarity))
        return True

    def check(self, model: Dict[str, object]) -> Tuple[str, Optional[List[int]]]:
        """Check consistency of bit-vector constraints."""
        for i, (atom, polarity) in enumerate(self._constraints):
            result = self._eval_atom(atom, model)
            if result is None:
                continue
            if result != polarity:
                return "unsat", [i]
        return "sat", None

    def _eval_atom(self, atom: object, model: Dict[str, object]) -> Optional[bool]:
        """Evaluate a bit-vector atom under a model."""
        # Placeholder for full evaluation logic
        return None