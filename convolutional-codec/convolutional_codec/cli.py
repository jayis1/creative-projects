"""Command-line interface for the convolutional coding toolkit."""

from __future__ import annotations

import argparse
import json
from typing import List

from .codec import BlockInterleaver, ConvolutionalCodec, Trellis
from .crc import CRC


def _parse_bits(text: str) -> List[int]:
    stripped = "".join(ch for ch in text if not ch.isspace())
    if not stripped:
        return []
    if any(ch not in "01" for ch in stripped):
        raise argparse.ArgumentTypeError("bit strings must contain only 0 and 1")
    return [int(ch) for ch in stripped]


def _parse_generators(values: List[str]) -> tuple[int, ...]:
    return tuple(int(value, 8) for value in values)


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
    return values


def _build_crc(args: argparse.Namespace) -> CRC | None:
    if args.crc_poly is None:
        return None
    return CRC(polynomial=int(args.crc_poly, 0), width=args.crc_width)


def _build_interleaver(args: argparse.Namespace) -> BlockInterleaver | None:
    if args.interleave_rows is None or args.interleave_cols is None:
        return None
    return BlockInterleaver(args.interleave_rows, args.interleave_cols)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convolutional encoder/decoder")
    parser.add_argument("--constraint-length", type=int, default=3)
    parser.add_argument("--generators", nargs="+", default=["7", "5"], help="octal generators")
    parser.add_argument("--puncture-pattern", type=str, help="e.g. 1101 for a rate-2/3 puncturing pattern")
    parser.add_argument("--crc-poly", type=str, help="CRC polynomial such as 0b10011")
    parser.add_argument("--crc-width", type=int, default=4)
    parser.add_argument("--interleave-rows", type=int)
    parser.add_argument("--interleave-cols", type=int)

    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="encode a bit string")
    encode.add_argument("bits", type=_parse_bits)
    encode.add_argument("--unterminated", action="store_true")
    encode.add_argument("--frame", action="store_true", help="apply CRC framing if CRC options are set")

    decode = subparsers.add_parser("decode", help="decode a hard-decision bit string")
    decode.add_argument("bits", type=_parse_bits)
    decode.add_argument("--unterminated", action="store_true")
    decode.add_argument("--frame", action="store_true")

    soft = subparsers.add_parser("decode-soft", help="decode comma-separated BPSK samples")
    soft.add_argument("samples", type=_parse_float_list)
    soft.add_argument("--unterminated", action="store_true")
    soft.add_argument("--frame", action="store_true")

    simulate = subparsers.add_parser("simulate-bsc", help="simulate over a binary symmetric channel")
    simulate.add_argument("bits", type=_parse_bits)
    simulate.add_argument("--p", type=float, required=True, help="crossover probability")
    simulate.add_argument("--seed", type=int)
    simulate.add_argument("--unterminated", action="store_true")
    simulate.add_argument("--frame", action="store_true")

    awgn = subparsers.add_parser("simulate-awgn", help="simulate over an AWGN channel")
    awgn.add_argument("bits", type=_parse_bits)
    awgn.add_argument("--snr-db", type=float, required=True)
    awgn.add_argument("--seed", type=int)
    awgn.add_argument("--unterminated", action="store_true")
    awgn.add_argument("--frame", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    trellis = Trellis(args.constraint_length, _parse_generators(args.generators))
    codec = ConvolutionalCodec(trellis, puncture_pattern=_parse_puncture_pattern(args.puncture_pattern))
    crc = _build_crc(args) if getattr(args, "frame", False) else None
    interleaver = _build_interleaver(args)

    if args.command == "encode":
        encoded = codec.encode_frame(args.bits, crc=crc, terminate=not args.unterminated) if args.frame else codec.encode(args.bits, terminate=not args.unterminated)
        print("".join(map(str, encoded)))
        return 0
    if args.command == "decode":
        if args.frame:
            print(json.dumps(codec.decode_frame(args.bits, crc=crc, terminate=not args.unterminated)))
        else:
            result = codec.decode(args.bits, assume_terminated=not args.unterminated)
            print(json.dumps({"bits": result.bits, "path_metric": result.path_metric}))
        return 0
    if args.command == "decode-soft":
        if args.frame:
            print(json.dumps(codec.decode_frame(args.samples, crc=crc, terminate=not args.unterminated, soft=True)))
        else:
            result = codec.decode_soft(args.samples, assume_terminated=not args.unterminated)
            print(json.dumps({"bits": result.bits, "path_metric": result.path_metric}))
        return 0
    if args.command == "simulate-bsc":
        result = codec.simulate_bsc(
            args.bits,
            args.p,
            terminate=not args.unterminated,
            seed=args.seed,
            crc=crc,
            interleaver=interleaver,
        )
        print(json.dumps(result))
        return 0
    if args.command == "simulate-awgn":
        result = codec.simulate_awgn(
            args.bits,
            args.snr_db,
            terminate=not args.unterminated,
            seed=args.seed,
            crc=crc,
            interleaver=interleaver,
        )
        print(json.dumps(result))
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
