"""Channel models and modulation helpers."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from random import Random
from typing import Iterable, List

from .utils import BitList, validate_bit_sequence


def bpsk_modulate(bits: Iterable[int]) -> List[float]:
    return [1.0 if bit == 0 else -1.0 for bit in validate_bit_sequence(bits)]


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
        for bit in validate_bit_sequence(bits):
            output.append(bit ^ int(self._rng.random() < self.crossover_probability))
        return output


@dataclass(slots=True)
class GilbertElliottChannel:
    """Two-state burst-error channel.

    The channel alternates between a good and bad state. Each state has its own
    crossover probability and independent transition probability.
    """

    p_good_to_bad: float
    p_bad_to_good: float
    good_error_probability: float = 0.001
    bad_error_probability: float = 0.2
    seed: int | None = None
    start_in_bad_state: bool = False
    _rng: Random = field(init=False, repr=False)
    _bad_state: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for name in ("p_good_to_bad", "p_bad_to_good", "good_error_probability", "bad_error_probability"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.bad_error_probability < self.good_error_probability:
            raise ValueError("bad_error_probability must be >= good_error_probability")
        self._rng = random.Random(self.seed)
        self._bad_state = self.start_in_bad_state

    def reset(self) -> None:
        self._bad_state = self.start_in_bad_state

    def transmit(self, bits: Iterable[int]) -> BitList:
        output: BitList = []
        for bit in validate_bit_sequence(bits):
            error_probability = self.bad_error_probability if self._bad_state else self.good_error_probability
            output.append(bit ^ int(self._rng.random() < error_probability))
            transition_probability = self.p_bad_to_good if self._bad_state else self.p_good_to_bad
            if self._rng.random() < transition_probability:
                self._bad_state = not self._bad_state
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
