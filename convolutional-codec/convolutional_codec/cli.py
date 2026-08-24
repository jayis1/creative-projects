"""Command-line interface for the convolutional coding toolkit."""

from __future__ import annotations

import argparse
import json
import logging
import math
from typing import Any, Iterable, List, Sequence

from .analysis import analyze_codec, benchmark_awgn, benchmark_bsc, benchmark_burst, coerce_parameter_series
from .codec import ConvolutionalCodec, Trellis
from .config import ConfigError, load_config
from .crc import CRC
from .interleaver import BlockInterleaver
from .utils import bits_to_string, parse_bit_string

LOGGER = logging.getLogger("convolutional_codec")


def _parse_bits(text: str) -> List[int]:
    try:
        return parse_bit_string(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_generators(values: List[str]) -> tuple[int, ...]:
    try:
        return tuple(int(value, 8) for value in values)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("generators must be octal integers such as 7 5") from exc


def _parse_puncture_pattern(value: str | None) -> tuple[int, ...] | None:
    if value is None:
        return None
    if any(ch not in "01" for ch in value):
        raise argparse.ArgumentTypeError("puncture pattern must contain only 0 and 1")
    return tuple(int(ch) for ch in value)


def _parse_float_list(value: str) -> List[float]:
    chunks = value.split(",")
    if not chunks or any(chunk.strip() == "" for chunk in chunks):
        raise argparse.ArgumentTypeError("samples must be a comma-separated list of finite floats")
    try:
        values = [float(chunk) for chunk in chunks]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("samples must be a comma-separated list of finite floats") from exc
    if any(not math.isfinite(sample) for sample in values):
        raise argparse.ArgumentTypeError("samples must be finite")
    return values


def _parse_series(value: str) -> List[float]:
    values = _parse_float_list(value)
    if not values:
        raise argparse.ArgumentTypeError("parameter series may not be empty")
    return values


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"invalid log level: {level_name}")
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _build_crc(args: argparse.Namespace) -> CRC | None:
    if getattr(args, "crc_poly", None) is None:
        return None
    return CRC(polynomial=int(args.crc_poly, 0), width=args.crc_width)


def _build_interleaver(args: argparse.Namespace) -> BlockInterleaver | None:
    rows = getattr(args, "interleave_rows", None)
    cols = getattr(args, "interleave_cols", None)
    if rows is None or cols is None:
        return None
    return BlockInterleaver(rows, cols)


def _serialize(data: Any, *, pretty: bool) -> str:
    return json.dumps(data, indent=2 if pretty else None, sort_keys=pretty)


def _emit(data: Any, *, pretty: bool) -> None:
    print(_serialize(data, pretty=pretty))


def _build_codec_from_namespace(args: argparse.Namespace) -> tuple[ConvolutionalCodec, CRC | None, BlockInterleaver | None]:
    trellis = Trellis(args.constraint_length, _parse_generators(args.generators))
    codec = ConvolutionalCodec(trellis, puncture_pattern=_parse_puncture_pattern(args.puncture_pattern))
    return codec, _build_crc(args), _build_interleaver(args)


def _namespace_from_config(config: dict[str, Any]) -> argparse.Namespace:
    codec_section = config.get("codec", {})
    crc_section = config.get("crc", {})
    interleaver_section = config.get("interleaver", {})
    command = config.get("command")
    if not isinstance(codec_section, dict) or not isinstance(crc_section, dict) or not isinstance(interleaver_section, dict):
        raise ConfigError("codec, crc, and interleaver sections must be objects when present")
    if not isinstance(command, dict) or "name" not in command:
        raise ConfigError("config command section must be an object with a name field")
    merged = {
        "constraint_length": codec_section.get("constraint_length", 3),
        "generators": codec_section.get("generators", ["7", "5"]),
        "puncture_pattern": codec_section.get("puncture_pattern"),
        "crc_poly": crc_section.get("polynomial"),
        "crc_width": crc_section.get("width", 4),
        "interleave_rows": interleaver_section.get("rows"),
        "interleave_cols": interleaver_section.get("columns"),
        "command": command["name"],
        "payload_length": 64,
        "pretty": config.get("pretty", True),
        "log_level": config.get("log_level", "INFO"),
    }
    merged.update({key: value for key, value in command.items() if key != "name"})
    return argparse.Namespace(**merged)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convolutional encoder/decoder and simulation toolkit")
    parser.add_argument("--constraint-length", type=int, default=3)
    parser.add_argument("--generators", nargs="+", default=["7", "5"], help="octal generators")
    parser.add_argument("--puncture-pattern", type=str, help="e.g. 1101 for a rate-2/3 puncturing pattern")
    parser.add_argument("--crc-poly", type=str, help="CRC polynomial such as 0b10011")
    parser.add_argument("--crc-width", type=int, default=4)
    parser.add_argument("--interleave-rows", type=int)
    parser.add_argument("--interleave-cols", type=int)
    parser.add_argument("--log-level", default="WARNING", help="DEBUG, INFO, WARNING, ERROR")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="encode a bit string")
    encode.add_argument("bits", type=_parse_bits)
    encode.add_argument("--unterminated", action="store_true")
    encode.add_argument("--frame", action="store_true", help="apply CRC framing if CRC options are set")
    encode.add_argument("--pretty", action="store_true")

    decode = subparsers.add_parser("decode", help="decode a hard-decision bit string")
    decode.add_argument("bits", type=_parse_bits)
    decode.add_argument("--unterminated", action="store_true")
    decode.add_argument("--frame", action="store_true")
    decode.add_argument("--pretty", action="store_true")

    soft = subparsers.add_parser("decode-soft", help="decode comma-separated BPSK samples")
    soft.add_argument("samples", type=_parse_float_list)
    soft.add_argument("--unterminated", action="store_true")
    soft.add_argument("--frame", action="store_true")
    soft.add_argument("--pretty", action="store_true")

    simulate = subparsers.add_parser("simulate-bsc", help="simulate over a binary symmetric channel")
    simulate.add_argument("bits", type=_parse_bits)
    simulate.add_argument("--p", type=float, required=True, help="crossover probability")
    simulate.add_argument("--seed", type=int)
    simulate.add_argument("--unterminated", action="store_true")
    simulate.add_argument("--frame", action="store_true")
    simulate.add_argument("--pretty", action="store_true")

    awgn = subparsers.add_parser("simulate-awgn", help="simulate over an AWGN channel")
    awgn.add_argument("bits", type=_parse_bits)
    awgn.add_argument("--snr-db", type=float, required=True)
    awgn.add_argument("--seed", type=int)
    awgn.add_argument("--unterminated", action="store_true")
    awgn.add_argument("--frame", action="store_true")
    awgn.add_argument("--pretty", action="store_true")

    burst = subparsers.add_parser("simulate-burst", help="simulate over a Gilbert-Elliott burst channel")
    burst.add_argument("bits", type=_parse_bits)
    burst.add_argument("--p-good-to-bad", type=float, required=True)
    burst.add_argument("--p-bad-to-good", type=float, required=True)
    burst.add_argument("--good-error-prob", type=float, default=0.001)
    burst.add_argument("--bad-error-prob", type=float, default=0.2)
    burst.add_argument("--seed", type=int)
    burst.add_argument("--unterminated", action="store_true")
    burst.add_argument("--frame", action="store_true")
    burst.add_argument("--pretty", action="store_true")

    analyze = subparsers.add_parser("analyze", help="analyze trellis properties and estimate free distance")
    analyze.add_argument("--max-input-bits", type=int, default=8)
    analyze.add_argument("--pretty", action="store_true")

    bench_bsc = subparsers.add_parser("benchmark-bsc", help="estimate BER/FER across BSC probabilities")
    bench_bsc.add_argument("--bits", type=_parse_bits)
    bench_bsc.add_argument("--payload-length", type=int, default=64)
    bench_bsc.add_argument("--probabilities", type=_parse_series, required=True)
    bench_bsc.add_argument("--trials", type=int, default=50)
    bench_bsc.add_argument("--seed", type=int)
    bench_bsc.add_argument("--unterminated", action="store_true")
    bench_bsc.add_argument("--frame", action="store_true")
    bench_bsc.add_argument("--pretty", action="store_true")

    bench_awgn = subparsers.add_parser("benchmark-awgn", help="estimate BER/FER across AWGN SNR points")
    bench_awgn.add_argument("--bits", type=_parse_bits)
    bench_awgn.add_argument("--payload-length", type=int, default=64)
    bench_awgn.add_argument("--snr-db", type=_parse_series, required=True)
    bench_awgn.add_argument("--trials", type=int, default=50)
    bench_awgn.add_argument("--seed", type=int)
    bench_awgn.add_argument("--unterminated", action="store_true")
    bench_awgn.add_argument("--frame", action="store_true")
    bench_awgn.add_argument("--pretty", action="store_true")

    bench_burst = subparsers.add_parser("benchmark-burst", help="estimate BER/FER across burst-channel severities")
    bench_burst.add_argument("--bits", type=_parse_bits)
    bench_burst.add_argument("--payload-length", type=int, default=64)
    bench_burst.add_argument("--bad-error-prob", type=_parse_series, required=True)
    bench_burst.add_argument("--p-good-to-bad", type=float, required=True)
    bench_burst.add_argument("--p-bad-to-good", type=float, required=True)
    bench_burst.add_argument("--good-error-prob", type=float, default=0.001)
    bench_burst.add_argument("--trials", type=int, default=50)
    bench_burst.add_argument("--seed", type=int)
    bench_burst.add_argument("--unterminated", action="store_true")
    bench_burst.add_argument("--frame", action="store_true")
    bench_burst.add_argument("--pretty", action="store_true")

    run_config = subparsers.add_parser("run-config", help="run a command from a JSON or TOML config file")
    run_config.add_argument("path")

    return parser


def _resolve_bits_argument(value: Any) -> List[int] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return parse_bit_string(value)
    if isinstance(value, Sequence):
        return [int(bit) for bit in value]
    raise ConfigError("bits must be a bit string or sequence of 0/1 values")


def _handle_command(args: argparse.Namespace) -> int:
    codec, crc, interleaver = _build_codec_from_namespace(args)
    pretty = bool(getattr(args, "pretty", False))

    if args.command == "encode":
        encoded = codec.encode_frame(args.bits, crc=crc, terminate=not args.unterminated) if args.frame else codec.encode(args.bits, terminate=not args.unterminated)
        print(bits_to_string(encoded))
        return 0
    if args.command == "decode":
        result = codec.decode_frame(args.bits, crc=crc, terminate=not args.unterminated) if args.frame else codec.decode(args.bits, assume_terminated=not args.unterminated)
        payload = result if args.frame else {"bits": result.bits, "path_metric": result.path_metric, "final_state": result.final_state}
        _emit(payload, pretty=pretty)
        return 0
    if args.command == "decode-soft":
        result = codec.decode_frame(args.samples, crc=crc, terminate=not args.unterminated, soft=True) if args.frame else codec.decode_soft(args.samples, assume_terminated=not args.unterminated)
        payload = result if args.frame else {"bits": result.bits, "path_metric": result.path_metric, "final_state": result.final_state}
        _emit(payload, pretty=pretty)
        return 0
    if args.command == "simulate-bsc":
        LOGGER.info("Running BSC simulation with p=%s", args.p)
        _emit(codec.simulate_bsc(args.bits, args.p, terminate=not args.unterminated, seed=args.seed, crc=crc, interleaver=interleaver), pretty=pretty)
        return 0
    if args.command == "simulate-awgn":
        LOGGER.info("Running AWGN simulation with Eb/N0=%s dB", args.snr_db)
        _emit(codec.simulate_awgn(args.bits, args.snr_db, terminate=not args.unterminated, seed=args.seed, crc=crc, interleaver=interleaver), pretty=pretty)
        return 0
    if args.command == "simulate-burst":
        LOGGER.info("Running burst simulation with bad-state error probability=%s", args.bad_error_prob)
        _emit(
            codec.simulate_burst(
                args.bits,
                p_good_to_bad=args.p_good_to_bad,
                p_bad_to_good=args.p_bad_to_good,
                good_error_probability=args.good_error_prob,
                bad_error_probability=args.bad_error_prob,
                terminate=not args.unterminated,
                seed=args.seed,
                crc=crc,
                interleaver=interleaver,
            ),
            pretty=pretty,
        )
        return 0
    if args.command == "analyze":
        _emit(analyze_codec(codec, max_input_bits=args.max_input_bits), pretty=pretty)
        return 0
    if args.command == "benchmark-bsc":
        bits = getattr(args, "bits", None)
        _emit(
            {
                "channel": "bsc",
                "series": benchmark_bsc(
                    codec,
                    coerce_parameter_series(args.probabilities),
                    trials=args.trials,
                    bits=bits,
                    payload_length=args.payload_length,
                    terminate=not args.unterminated,
                    seed=args.seed,
                    crc=crc if args.frame else None,
                    interleaver=interleaver,
                ),
            },
            pretty=pretty,
        )
        return 0
    if args.command == "benchmark-awgn":
        bits = getattr(args, "bits", None)
        _emit(
            {
                "channel": "awgn",
                "series": benchmark_awgn(
                    codec,
                    coerce_parameter_series(args.snr_db),
                    trials=args.trials,
                    bits=bits,
                    payload_length=args.payload_length,
                    terminate=not args.unterminated,
                    seed=args.seed,
                    crc=crc if args.frame else None,
                    interleaver=interleaver,
                ),
            },
            pretty=pretty,
        )
        return 0
    if args.command == "benchmark-burst":
        bits = getattr(args, "bits", None)
        _emit(
            {
                "channel": "gilbert-elliott",
                "series": benchmark_burst(
                    codec,
                    coerce_parameter_series(args.bad_error_prob),
                    p_good_to_bad=args.p_good_to_bad,
                    p_bad_to_good=args.p_bad_to_good,
                    good_error_probability=args.good_error_prob,
                    trials=args.trials,
                    bits=bits,
                    payload_length=args.payload_length,
                    terminate=not args.unterminated,
                    seed=args.seed,
                    crc=crc if args.frame else None,
                    interleaver=interleaver,
                ),
            },
            pretty=pretty,
        )
        return 0
    raise ConfigError(f"unsupported command: {args.command}")


def _run_config_command(path: str) -> int:
    config = load_config(path)
    args = _namespace_from_config(config)
    _configure_logging(args.log_level)
    bits = _resolve_bits_argument(getattr(args, "bits", None))
    if bits is not None:
        args.bits = bits
    if hasattr(args, "probabilities"):
        args.probabilities = coerce_parameter_series(args.probabilities)
    if hasattr(args, "snr_db") and isinstance(args.snr_db, (str, int, float, list, tuple)):
        args.snr_db = coerce_parameter_series(args.snr_db)
    if hasattr(args, "bad_error_prob"):
        args.bad_error_prob = coerce_parameter_series(args.bad_error_prob)
    setattr(args, "frame", bool(getattr(args, "frame", False)))
    setattr(args, "unterminated", bool(getattr(args, "unterminated", False)))
    return _handle_command(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run-config":
            return _run_config_command(args.path)
        _configure_logging(args.log_level)
        return _handle_command(args)
    except (ConfigError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
