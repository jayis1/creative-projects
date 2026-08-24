"""Convolutional encoder/decoder primitives."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterable, List, Sequence, Tuple

from .channels import AWGNChannel, BinarySymmetricChannel, GilbertElliottChannel
from .crc import CRC
from .interleaver import BlockInterleaver
from .utils import BitList, parity, validate_bit_sequence


MetricList = Sequence[float]


@dataclass(frozen=True, slots=True)
class Trellis:
    """Convolutional-code trellis specification."""

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
        return tuple(parity(register & generator) for generator in self.generators)

    def next_state(self, state: int, input_bit: int) -> int:
        return ((input_bit << (self.memory - 1)) | (state >> 1)) if self.memory else 0


@dataclass(slots=True)
class DecodingResult:
    bits: BitList
    path_metric: float
    corrected_codeword: BitList
    final_state: int


class ConvolutionalCodec:
    """Convolutional encoder/decoder with hard and soft Viterbi decoding."""

    def __init__(self, trellis: Trellis, *, puncture_pattern: Sequence[int] | None = None) -> None:
        self.trellis = trellis
        self.puncture_pattern = self._normalize_puncture_pattern(puncture_pattern)

    def _normalize_puncture_pattern(self, pattern: Sequence[int] | None) -> Tuple[int, ...] | None:
        if pattern is None:
            return None
        normalized = tuple(pattern)
        if not normalized:
            raise ValueError("puncture_pattern cannot be empty")
        if len(normalized) % self.trellis.rate_denominator != 0:
            raise ValueError("puncture_pattern length must be divisible by the number of generators")
        if any(bit not in (0, 1) for bit in normalized):
            raise ValueError("puncture_pattern must contain only 0 and 1")
        if all(bit == 0 for bit in normalized):
            raise ValueError("puncture_pattern cannot delete every symbol")
        return normalized

    @property
    def nominal_rate(self) -> str:
        return f"1/{self.trellis.rate_denominator}"

    @property
    def effective_rate(self) -> float:
        if self.puncture_pattern is None:
            return 1.0 / self.trellis.rate_denominator
        kept = sum(self.puncture_pattern)
        return len(self.puncture_pattern) / (self.trellis.rate_denominator * kept)

    def encode(self, bits: Iterable[int], *, terminate: bool = True) -> BitList:
        payload = validate_bit_sequence(bits)
        work = payload + ([0] * self.trellis.memory if terminate else [])
        state = 0
        encoded: BitList = []
        for bit in work:
            encoded.extend(self.trellis.branch_output(state, bit))
            state = self.trellis.next_state(state, bit)
        return self.apply_puncturing(encoded)

    def apply_puncturing(self, encoded_bits: Sequence[int]) -> BitList:
        payload = validate_bit_sequence(encoded_bits)
        if self.puncture_pattern is None:
            return payload
        output: BitList = []
        pattern_width = len(self.puncture_pattern)
        for offset in range(0, len(payload), pattern_width):
            block = payload[offset : offset + pattern_width]
            for bit, keep in zip(block, self.puncture_pattern):
                if keep:
                    output.append(bit)
        return output

    def depuncture(self, received: Sequence[float | int], *, erased_value: float = 0.0) -> List[float]:
        if self.puncture_pattern is None:
            return [float(x) for x in received]
        output: List[float] = []
        source_index = 0
        pattern_width = len(self.puncture_pattern)
        while source_index < len(received):
            block_start = len(output)
            for keep in self.puncture_pattern:
                if keep:
                    if source_index >= len(received):
                        break
                    output.append(float(received[source_index]))
                    source_index += 1
                else:
                    output.append(erased_value)
            block_length = len(output) - block_start
            remainder = block_length % self.trellis.rate_denominator
            if remainder:
                del output[-remainder:]
            if block_length < pattern_width:
                break
        if source_index != len(received):
            raise ValueError("received punctured sequence could not be aligned with puncture pattern")
        return output

    def decode(self, received: Sequence[int], *, assume_terminated: bool = True) -> DecodingResult:
        samples = self.depuncture(received, erased_value=0.5)
        return self._viterbi_decode(samples, metric_type="hard", assume_terminated=assume_terminated)

    def decode_soft(self, received: Sequence[float], *, assume_terminated: bool = True) -> DecodingResult:
        samples = self.depuncture(received, erased_value=0.0)
        return self._viterbi_decode(samples, metric_type="soft", assume_terminated=assume_terminated)

    def _viterbi_decode(
        self,
        received: MetricList,
        *,
        metric_type: str,
        assume_terminated: bool,
    ) -> DecodingResult:
        n = self.trellis.rate_denominator
        if len(received) % n != 0:
            raise ValueError(
                f"received codeword length {len(received)} is not divisible by rate denominator {n}"
            )
        step_count = len(received) // n
        if step_count == 0:
            return DecodingResult([], 0.0, [], 0)

        path_metrics = [inf] * self.trellis.state_count
        path_metrics[0] = 0.0
        predecessors: List[List[Tuple[int, int]]] = []

        for step in range(step_count):
            symbol = received[step * n : (step + 1) * n]
            new_metrics = [inf] * self.trellis.state_count
            decisions: List[Tuple[int, int]] = [(-1, -1)] * self.trellis.state_count
            for state, metric in enumerate(path_metrics):
                if metric == inf:
                    continue
                for input_bit in (0, 1):
                    next_state = self.trellis.next_state(state, input_bit)
                    expected = self.trellis.branch_output(state, input_bit)
                    branch_metric = self._branch_metric(symbol, expected, metric_type=metric_type)
                    candidate = metric + branch_metric
                    if candidate < new_metrics[next_state]:
                        new_metrics[next_state] = candidate
                        decisions[next_state] = (state, input_bit)
            predecessors.append(decisions)
            path_metrics = new_metrics

        terminal_state = 0 if assume_terminated else min(
            range(self.trellis.state_count), key=lambda state: path_metrics[state]
        )
        terminal_metric = path_metrics[terminal_state]
        traceback_state = terminal_state
        decoded: BitList = []
        corrected: BitList = []
        for step in range(step_count - 1, -1, -1):
            prev_state, input_bit = predecessors[step][traceback_state]
            if prev_state < 0:
                raise ValueError("trellis traceback failed; received sequence may be invalid")
            decoded.append(input_bit)
            corrected.extend(reversed(self.trellis.branch_output(prev_state, input_bit)))
            traceback_state = prev_state

        decoded.reverse()
        corrected.reverse()
        if assume_terminated and self.trellis.memory:
            decoded = decoded[: -self.trellis.memory]
        return DecodingResult(decoded, terminal_metric, corrected, terminal_state)

    def _branch_metric(
        self,
        received_symbol: Sequence[float],
        expected_symbol: Sequence[int],
        *,
        metric_type: str,
    ) -> float:
        if metric_type == "hard":
            if any(sample not in (0.0, 0.5, 1.0) for sample in received_symbol):
                raise ValueError("hard-decision decoding expects binary samples or 0.5 erasures")
            return sum(abs(float(sample) - expected) for sample, expected in zip(received_symbol, expected_symbol))
        if metric_type == "soft":
            expected_bpsk = [1.0 if bit == 0 else -1.0 for bit in expected_symbol]
            return sum((sample - target) ** 2 for sample, target in zip(received_symbol, expected_bpsk))
        raise ValueError(f"unknown metric_type {metric_type!r}")

    def encode_frame(self, bits: Iterable[int], *, crc: CRC | None = None, terminate: bool = True) -> BitList:
        payload = validate_bit_sequence(bits)
        if crc is not None:
            payload = crc.append(payload)
        return self.encode(payload, terminate=terminate)

    def decode_frame(
        self,
        received: Sequence[int] | Sequence[float],
        *,
        crc: CRC | None = None,
        terminate: bool = True,
        soft: bool = False,
    ) -> dict:
        result = self.decode_soft(received, assume_terminated=terminate) if soft else self.decode(received, assume_terminated=terminate)
        frame_bits = result.bits
        crc_ok = None
        payload = frame_bits
        if crc is not None:
            crc_ok = crc.verify(frame_bits)
            payload = frame_bits[:-crc.width] if len(frame_bits) >= crc.width else []
        return {
            "payload_bits": payload,
            "frame_bits": frame_bits,
            "crc_ok": crc_ok,
            "path_metric": result.path_metric,
            "final_state": result.final_state,
        }

    def simulate_bsc(
        self,
        bits: Iterable[int],
        crossover_probability: float,
        *,
        terminate: bool = True,
        seed: int | None = None,
        crc: CRC | None = None,
        interleaver: BlockInterleaver[int] | None = None,
    ) -> dict:
        payload = validate_bit_sequence(bits)
        encoded = self.encode_frame(payload, crc=crc, terminate=terminate)
        tx_bits = interleaver.interleave(encoded) if interleaver else encoded
        channel = BinarySymmetricChannel(crossover_probability, seed=seed)
        rx_bits = channel.transmit(tx_bits)
        deinterleaved = interleaver.deinterleave(rx_bits) if interleaver else rx_bits
        decoded = self.decode_frame(deinterleaved, crc=crc, terminate=terminate)
        payload_bits = decoded["payload_bits"]
        bit_errors = sum(a ^ b for a, b in zip(payload, payload_bits)) + abs(len(payload) - len(payload_bits))
        return {
            "channel": "bsc",
            "input_bits": payload,
            "encoded_bits": encoded,
            "transmitted_bits": tx_bits,
            "received_bits": rx_bits,
            "decoded_bits": payload_bits,
            "frame_bits": decoded["frame_bits"],
            "crc_ok": decoded["crc_ok"],
            "bit_errors": bit_errors,
            "path_metric": decoded["path_metric"],
        }

    def simulate_burst(
        self,
        bits: Iterable[int],
        *,
        p_good_to_bad: float,
        p_bad_to_good: float,
        good_error_probability: float = 0.001,
        bad_error_probability: float = 0.2,
        terminate: bool = True,
        seed: int | None = None,
        crc: CRC | None = None,
        interleaver: BlockInterleaver[int] | None = None,
    ) -> dict:
        payload = validate_bit_sequence(bits)
        encoded = self.encode_frame(payload, crc=crc, terminate=terminate)
        tx_bits = interleaver.interleave(encoded) if interleaver else encoded
        channel = GilbertElliottChannel(
            p_good_to_bad=p_good_to_bad,
            p_bad_to_good=p_bad_to_good,
            good_error_probability=good_error_probability,
            bad_error_probability=bad_error_probability,
            seed=seed,
        )
        rx_bits = channel.transmit(tx_bits)
        deinterleaved = interleaver.deinterleave(rx_bits) if interleaver else rx_bits
        decoded = self.decode_frame(deinterleaved, crc=crc, terminate=terminate)
        payload_bits = decoded["payload_bits"]
        bit_errors = sum(a ^ b for a, b in zip(payload, payload_bits)) + abs(len(payload) - len(payload_bits))
        return {
            "channel": "gilbert-elliott",
            "input_bits": payload,
            "encoded_bits": encoded,
            "transmitted_bits": tx_bits,
            "received_bits": rx_bits,
            "decoded_bits": payload_bits,
            "frame_bits": decoded["frame_bits"],
            "crc_ok": decoded["crc_ok"],
            "bit_errors": bit_errors,
            "path_metric": decoded["path_metric"],
        }

    def simulate_awgn(
        self,
        bits: Iterable[int],
        snr_db: float,
        *,
        terminate: bool = True,
        seed: int | None = None,
        crc: CRC | None = None,
        interleaver: BlockInterleaver[float] | None = None,
    ) -> dict:
        payload = validate_bit_sequence(bits)
        encoded = self.encode_frame(payload, crc=crc, terminate=terminate)
        tx_bits = interleaver.interleave(encoded) if interleaver else encoded
        channel = AWGNChannel(snr_db, seed=seed)
        samples = channel.transmit(tx_bits)
        deinterleaved_samples = interleaver.deinterleave(samples) if interleaver is not None else samples
        decoded = self.decode_frame(deinterleaved_samples, crc=crc, terminate=terminate, soft=True)
        payload_bits = decoded["payload_bits"]
        bit_errors = sum(a ^ b for a, b in zip(payload, payload_bits)) + abs(len(payload) - len(payload_bits))
        return {
            "channel": "awgn",
            "input_bits": payload,
            "encoded_bits": encoded,
            "transmitted_bits": tx_bits,
            "received_samples": samples,
            "decoded_bits": payload_bits,
            "frame_bits": decoded["frame_bits"],
            "crc_ok": decoded["crc_ok"],
            "bit_errors": bit_errors,
            "path_metric": decoded["path_metric"],
        }
