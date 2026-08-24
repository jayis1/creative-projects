"""Convolutional encoder and Viterbi decoder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


def _validate_bit_sequence(bits: Iterable[int]) -> List[int]:
    validated = list(bits)
    for bit in validated:
        if bit not in (0, 1):
            raise ValueError(f"expected binary symbols, got {bit!r}")
    return validated


def _parity(value: int) -> int:
    return value.bit_count() & 1


@dataclass(frozen=True, slots=True)
class Trellis:
    """Convolutional-code trellis specification.

    Parameters are given in octal, matching common coding-theory notation.
    For example, ``constraint_length=3`` and generators ``(0o7, 0o5)`` define
    the standard rate-1/2 code with free distance 5.
    """

    constraint_length: int
    generators: Tuple[int, ...]

    def __post_init__(self) -> None:
        if self.constraint_length < 2:
            raise ValueError("constraint_length must be >= 2")
        if not self.generators:
            raise ValueError("at least one generator is required")
        max_mask = (1 << self.constraint_length) - 1
        validated: List[int] = []
        for generator in self.generators:
            if generator <= 0:
                raise ValueError("generators must be positive")
            if generator > max_mask:
                raise ValueError(
                    f"generator {oct(generator)} exceeds constraint length {self.constraint_length}"
                )
            validated.append(generator)
        object.__setattr__(self, "generators", tuple(validated))

    @property
    def rate_denominator(self) -> int:
        return len(self.generators)

    @property
    def memory(self) -> int:
        return self.constraint_length - 1

    @property
    def state_count(self) -> int:
        return 1 << self.memory

    def branch_output(self, state: int, input_bit: int) -> Tuple[int, ...]:
        register = (input_bit << self.memory) | state
        return tuple(_parity(register & generator) for generator in self.generators)

    def next_state(self, state: int, input_bit: int) -> int:
        return ((input_bit << (self.memory - 1)) | (state >> 1)) if self.memory else 0


@dataclass(slots=True)
class DecodingResult:
    bits: List[int]
    path_metric: int
    corrected_codeword: List[int]


class ConvolutionalCodec:
    """Convolutional encoder/decoder using hard-decision Viterbi decoding."""

    def __init__(self, trellis: Trellis) -> None:
        self.trellis = trellis

    def encode(self, bits: Iterable[int], *, terminate: bool = True) -> List[int]:
        payload = _validate_bit_sequence(bits)
        work = payload + ([0] * self.trellis.memory if terminate else [])
        state = 0
        encoded: List[int] = []
        for bit in work:
            encoded.extend(self.trellis.branch_output(state, bit))
            state = self.trellis.next_state(state, bit)
        return encoded

    def decode(self, received: Sequence[int], *, assume_terminated: bool = True) -> DecodingResult:
        codeword = _validate_bit_sequence(received)
        n = self.trellis.rate_denominator
        if len(codeword) % n != 0:
            raise ValueError(
                f"received codeword length {len(codeword)} is not divisible by rate denominator {n}"
            )

        step_count = len(codeword) // n
        inf = 10 ** 12
        path_metrics = [inf] * self.trellis.state_count
        path_metrics[0] = 0
        predecessors: List[List[Tuple[int, int]]] = []

        for step in range(step_count):
            symbol = tuple(codeword[step * n : (step + 1) * n])
            new_metrics = [inf] * self.trellis.state_count
            decisions: List[Tuple[int, int]] = [(-1, -1)] * self.trellis.state_count
            for state, metric in enumerate(path_metrics):
                if metric >= inf:
                    continue
                for input_bit in (0, 1):
                    next_state = self.trellis.next_state(state, input_bit)
                    expected = self.trellis.branch_output(state, input_bit)
                    branch_metric = sum(a ^ b for a, b in zip(symbol, expected))
                    candidate = metric + branch_metric
                    if candidate < new_metrics[next_state]:
                        new_metrics[next_state] = candidate
                        decisions[next_state] = (state, input_bit)
            predecessors.append(decisions)
            path_metrics = new_metrics

        final_state = 0 if assume_terminated else min(
            range(self.trellis.state_count), key=lambda s: path_metrics[s]
        )
        decoded: List[int] = []
        corrected: List[int] = []
        for step in range(step_count - 1, -1, -1):
            prev_state, input_bit = predecessors[step][final_state]
            if prev_state < 0:
                raise ValueError("trellis traceback failed; received sequence may be invalid")
            decoded.append(input_bit)
            corrected.extend(reversed(self.trellis.branch_output(prev_state, input_bit)))
            final_state = prev_state

        decoded.reverse()
        corrected.reverse()
        if assume_terminated and self.trellis.memory:
            decoded = decoded[: -self.trellis.memory]
        return DecodingResult(decoded, path_metrics[0], corrected)

    def simulate_bsc(
        self,
        bits: Iterable[int],
        crossover_probability: float,
        *,
        terminate: bool = True,
        seed: int | None = None,
    ) -> dict:
        from .channels import BinarySymmetricChannel

        payload = _validate_bit_sequence(bits)
        encoded = self.encode(payload, terminate=terminate)
        channel = BinarySymmetricChannel(crossover_probability, seed=seed)
        received = channel.transmit(encoded)
        decoded = self.decode(received, assume_terminated=terminate)
        bit_errors = sum(a ^ b for a, b in zip(payload, decoded.bits))
        return {
            "input_bits": payload,
            "encoded_bits": encoded,
            "received_bits": received,
            "decoded_bits": decoded.bits,
            "bit_errors": bit_errors,
            "path_metric": decoded.path_metric,
        }
