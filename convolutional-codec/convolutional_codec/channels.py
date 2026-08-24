"""Communication channel models and modulation helpers."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from random import Random
from typing import Iterable, List


BitList = List[int]


def _validate_bits(bits: Iterable[int]) -> BitList:
    output = list(bits)
    if any(bit not in (0, 1) for bit in output):
        raise ValueError("expected binary symbols containing only 0 and 1")
    return output


def bpsk_modulate(bits: Iterable[int]) -> List[float]:
    return [1.0 if bit == 0 else -1.0 for bit in _validate_bits(bits)]


def hard_decide(samples: Iterable[float]) -> BitList:
    return [0 if sample >= 0.0 else 1 for sample in samples]


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

    def transmit(self, bits: Iterable[int]) -> BitList:
        output: BitList = []
        for bit in _validate_bits(bits):
            flip = self._rng.random() < self.crossover_probability
            output.append(bit ^ int(flip))
        return output


@dataclass(slots=True)
class AWGNChannel:
    """BPSK + additive white Gaussian noise channel."""

    snr_db: float
    seed: int | None = None
    _rng: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.snr_db):
            raise ValueError("snr_db must be finite")
        self._rng = random.Random(self.seed)

    @property
    def sigma(self) -> float:
        eb_n0 = 10 ** (self.snr_db / 10.0)
        return math.sqrt(1.0 / (2.0 * eb_n0))

    def transmit(self, bits: Iterable[int]) -> List[float]:
        sigma = self.sigma
        return [sample + self._rng.gauss(0.0, sigma) for sample in bpsk_modulate(bits)]
