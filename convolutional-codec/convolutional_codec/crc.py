"""CRC helpers for frame-level integrity checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .utils import validate_bit_sequence


@dataclass(frozen=True, slots=True)
class CRC:
    """Binary polynomial CRC.

    ``polynomial`` includes the implicit top bit. For CRC-4-ITU, use ``0b10011``.
    """

    polynomial: int
    width: int
    init: int = 0
    xor_out: int = 0

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be positive")
        if self.polynomial.bit_length() != self.width + 1:
            raise ValueError("polynomial must have width + 1 bits including the leading 1")
        if self.init < 0 or self.init >= (1 << self.width):
            raise ValueError("init is out of range for CRC width")
        if self.xor_out < 0 or self.xor_out >= (1 << self.width):
            raise ValueError("xor_out is out of range for CRC width")

    def compute(self, bits: Iterable[int]) -> List[int]:
        payload = validate_bit_sequence(bits, name="CRC payload")
        register = self.init
        mask = (1 << self.width) - 1
        poly = self.polynomial & mask
        for bit in payload + [0] * self.width:
            top = (register >> (self.width - 1)) & 1
            register = ((register << 1) & mask) | bit
            if top:
                register ^= poly
        register ^= self.xor_out
        return [(register >> shift) & 1 for shift in range(self.width - 1, -1, -1)]

    def append(self, bits: Iterable[int]) -> List[int]:
        payload = validate_bit_sequence(bits, name="CRC payload")
        return payload + self.compute(payload)

    def verify(self, frame: Iterable[int]) -> bool:
        data = validate_bit_sequence(frame, name="CRC frame")
        if len(data) < self.width:
            return False
        payload = data[:-self.width]
        return data[-self.width :] == self.compute(payload)
