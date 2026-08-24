"""Simple communication channel models."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from random import Random
from typing import Iterable, List


@dataclass(slots=True)
class BinarySymmetricChannel:
    """Flip bits independently with probability ``crossover_probability``."""

    crossover_probability: float
    seed: int | None = None
    _rng: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.crossover_probability <= 1.0:
            raise ValueError("crossover_probability must be in [0, 1]")
        self._rng = random.Random(self.seed)

    def transmit(self, bits: Iterable[int]) -> List[int]:
        output: List[int] = []
        for bit in bits:
            if bit not in (0, 1):
                raise ValueError(f"channel accepts only binary symbols, got {bit!r}")
            flip = self._rng.random() < self.crossover_probability
            output.append(bit ^ int(flip))
        return output
