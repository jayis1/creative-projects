"""Interleaver implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Iterable, List, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class BlockInterleaver(Generic[T]):
    """Rectangular block interleaver for bit or sample streams."""

    rows: int
    columns: int

    def __post_init__(self) -> None:
        if self.rows <= 0 or self.columns <= 0:
            raise ValueError("rows and columns must be positive")

    @property
    def block_size(self) -> int:
        return self.rows * self.columns

    def interleave(self, values: Sequence[T] | Iterable[T]) -> List[T]:
        payload = list(values)
        if len(payload) % self.block_size != 0:
            raise ValueError("input length must be a multiple of rows * columns")
        output: List[T] = []
        for offset in range(0, len(payload), self.block_size):
            block = payload[offset : offset + self.block_size]
            for col in range(self.columns):
                for row in range(self.rows):
                    output.append(block[row * self.columns + col])
        return output

    def deinterleave(self, values: Sequence[T] | Iterable[T]) -> List[T]:
        payload = list(values)
        if len(payload) % self.block_size != 0:
            raise ValueError("input length must be a multiple of rows * columns")
        output: List[T] = []
        for offset in range(0, len(payload), self.block_size):
            block = payload[offset : offset + self.block_size]
            restored: List[T | None] = [None] * self.block_size
            index = 0
            for col in range(self.columns):
                for row in range(self.rows):
                    restored[row * self.columns + col] = block[index]
                    index += 1
            output.extend(item for item in restored if item is not None)
        return output
