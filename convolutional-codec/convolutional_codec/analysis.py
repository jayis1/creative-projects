"""Analysis and benchmarking helpers."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .codec import ConvolutionalCodec
from .crc import CRC
from .interleaver import BlockInterleaver
from .utils import BitList, validate_bit_sequence


@dataclass(frozen=True, slots=True)
class BenchmarkPoint:
    parameter: float
    trials: int
    total_bits: int
    bit_errors: int
    frame_errors: int
    crc_failures: int

    @property
    def ber(self) -> float:
        return 0.0 if self.total_bits == 0 else self.bit_errors / self.total_bits

    @property
    def fer(self) -> float:
        return 0.0 if self.trials == 0 else self.frame_errors / self.trials

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "trials": self.trials,
            "total_bits": self.total_bits,
            "bit_errors": self.bit_errors,
            "frame_errors": self.frame_errors,
            "crc_failures": self.crc_failures,
            "ber": self.ber,
            "fer": self.fer,
        }


def _random_bits(length: int, rng: random.Random) -> BitList:
    return [rng.randint(0, 1) for _ in range(length)]


def _resolve_payload(source_bits: Sequence[int] | None, payload_length: int, rng: random.Random) -> BitList:
    if source_bits is not None:
        return list(source_bits)
    if payload_length <= 0:
        raise ValueError("payload_length must be positive when no explicit payload bits are supplied")
    return _random_bits(payload_length, rng)


def _aggregate_trial(result: dict, expected_bits: Sequence[int]) -> tuple[int, int, int]:
    decoded = result["decoded_bits"]
    bit_errors = sum(a ^ b for a, b in zip(expected_bits, decoded)) + abs(len(expected_bits) - len(decoded))
    frame_error = int(bit_errors > 0)
    crc_failure = int(result.get("crc_ok") is False)
    return bit_errors, frame_error, crc_failure


def benchmark_bsc(
    codec: ConvolutionalCodec,
    probabilities: Iterable[float],
    *,
    trials: int,
    bits: Sequence[int] | None = None,
    payload_length: int = 64,
    terminate: bool = True,
    seed: int | None = None,
    crc: CRC | None = None,
    interleaver: BlockInterleaver[int] | None = None,
) -> List[dict]:
    rng = random.Random(seed)
    series: List[dict] = []
    for probability in probabilities:
        point = BenchmarkPoint(parameter=float(probability), trials=trials, total_bits=0, bit_errors=0, frame_errors=0, crc_failures=0)
        bit_errors = frame_errors = crc_failures = total_bits = 0
        for _ in range(trials):
            payload = _resolve_payload(bits, payload_length, rng)
            trial_seed = rng.randint(0, 2**31 - 1)
            result = codec.simulate_bsc(payload, probability, terminate=terminate, seed=trial_seed, crc=crc, interleaver=interleaver)
            b_err, f_err, c_err = _aggregate_trial(result, payload)
            bit_errors += b_err
            frame_errors += f_err
            crc_failures += c_err
            total_bits += len(payload)
        point = BenchmarkPoint(float(probability), trials, total_bits, bit_errors, frame_errors, crc_failures)
        series.append(point.to_dict())
    return series


def benchmark_awgn(
    codec: ConvolutionalCodec,
    snr_values: Iterable[float],
    *,
    trials: int,
    bits: Sequence[int] | None = None,
    payload_length: int = 64,
    terminate: bool = True,
    seed: int | None = None,
    crc: CRC | None = None,
    interleaver: BlockInterleaver[float] | None = None,
) -> List[dict]:
    rng = random.Random(seed)
    series: List[dict] = []
    for snr_db in snr_values:
        bit_errors = frame_errors = crc_failures = total_bits = 0
        for _ in range(trials):
            payload = _resolve_payload(bits, payload_length, rng)
            trial_seed = rng.randint(0, 2**31 - 1)
            result = codec.simulate_awgn(payload, float(snr_db), terminate=terminate, seed=trial_seed, crc=crc, interleaver=interleaver)
            b_err, f_err, c_err = _aggregate_trial(result, payload)
            bit_errors += b_err
            frame_errors += f_err
            crc_failures += c_err
            total_bits += len(payload)
        series.append(BenchmarkPoint(float(snr_db), trials, total_bits, bit_errors, frame_errors, crc_failures).to_dict())
    return series


def benchmark_burst(
    codec: ConvolutionalCodec,
    bad_error_probabilities: Iterable[float],
    *,
    p_good_to_bad: float,
    p_bad_to_good: float,
    good_error_probability: float = 0.001,
    trials: int,
    bits: Sequence[int] | None = None,
    payload_length: int = 64,
    terminate: bool = True,
    seed: int | None = None,
    crc: CRC | None = None,
    interleaver: BlockInterleaver[int] | None = None,
) -> List[dict]:
    rng = random.Random(seed)
    series: List[dict] = []
    for bad_error_probability in bad_error_probabilities:
        bit_errors = frame_errors = crc_failures = total_bits = 0
        for _ in range(trials):
            payload = _resolve_payload(bits, payload_length, rng)
            trial_seed = rng.randint(0, 2**31 - 1)
            result = codec.simulate_burst(
                payload,
                p_good_to_bad=p_good_to_bad,
                p_bad_to_good=p_bad_to_good,
                good_error_probability=good_error_probability,
                bad_error_probability=float(bad_error_probability),
                terminate=terminate,
                seed=trial_seed,
                crc=crc,
                interleaver=interleaver,
            )
            b_err, f_err, c_err = _aggregate_trial(result, payload)
            bit_errors += b_err
            frame_errors += f_err
            crc_failures += c_err
            total_bits += len(payload)
        point = BenchmarkPoint(float(bad_error_probability), trials, total_bits, bit_errors, frame_errors, crc_failures)
        series.append(point.to_dict())
    return series


def estimate_free_distance(codec: ConvolutionalCodec, *, max_input_bits: int = 8) -> dict:
    if max_input_bits <= 0:
        raise ValueError("max_input_bits must be positive")
    best_weight: int | None = None
    best_inputs: List[str] = []
    examined = 0
    for length in range(1, max_input_bits + 1):
        for payload in itertools.product((0, 1), repeat=length):
            if not any(payload):
                continue
            examined += 1
            encoded = codec.encode(payload, terminate=True)
            weight = sum(encoded)
            if best_weight is None or weight < best_weight:
                best_weight = weight
                best_inputs = ["".join(map(str, payload))]
            elif weight == best_weight and len(best_inputs) < 8:
                best_inputs.append("".join(map(str, payload)))
    return {
        "max_input_bits": max_input_bits,
        "examined_paths": examined,
        "estimated_free_distance": best_weight,
        "example_inputs": best_inputs,
    }


def analyze_codec(codec: ConvolutionalCodec, *, max_input_bits: int = 8) -> dict:
    puncture_pattern = None if codec.puncture_pattern is None else "".join(str(bit) for bit in codec.puncture_pattern)
    return {
        "constraint_length": codec.trellis.constraint_length,
        "generators_octal": [oct(generator) for generator in codec.trellis.generators],
        "state_count": codec.trellis.state_count,
        "memory": codec.trellis.memory,
        "nominal_rate": codec.nominal_rate,
        "effective_rate": codec.effective_rate,
        "puncture_pattern": puncture_pattern,
        "distance_estimate": estimate_free_distance(codec, max_input_bits=max_input_bits),
    }


def coerce_parameter_series(values: Sequence[float] | Sequence[int] | float | int) -> List[float]:
    if isinstance(values, (int, float)):
        return [float(values)]
    return [float(value) for value in values]


def normalize_bits(bits: Iterable[int] | None) -> BitList | None:
    if bits is None:
        return None
    return validate_bit_sequence(bits)
