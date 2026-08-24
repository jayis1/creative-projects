"""Shared validation and formatting helpers."""

from __future__ import annotations

from typing import Iterable, List, Sequence


BitList = List[int]


def validate_bit_sequence(bits: Iterable[int], *, name: str = "bits") -> BitList:
    """Return a validated list of binary digits."""
    validated = list(bits)
    for bit in validated:
        if bit not in (0, 1):
            raise ValueError(f"{name} must contain only 0 and 1, got {bit!r}")
    return validated


def parity(value: int) -> int:
    return value.bit_count() & 1


def bits_to_string(bits: Sequence[int]) -> str:
    return "".join(str(bit) for bit in validate_bit_sequence(bits))


def parse_bit_string(text: str) -> BitList:
    stripped = "".join(ch for ch in text if not ch.isspace())
    if not stripped:
        return []
    if any(ch not in "01" for ch in stripped):
        raise ValueError("bit strings must contain only 0 and 1")
    return [int(ch) for ch in stripped]
