"""Command-line interface for the convolutional coding toolkit."""

from __future__ import annotations

import argparse
import json
from typing import List

from .codec import ConvolutionalCodec, Trellis


def _parse_bits(text: str) -> List[int]:
    stripped = "".join(ch for ch in text if not ch.isspace())
    if not stripped:
        return []
    if any(ch not in "01" for ch in stripped):
        raise argparse.ArgumentTypeError("bit strings must contain only 0 and 1")
    return [int(ch) for ch in stripped]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convolutional encoder/decoder")
    parser.add_argument("--constraint-length", type=int, default=3)
    parser.add_argument("--generators", nargs="+", default=["7", "5"], help="octal generators")

    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="encode a bit string")
    encode.add_argument("bits", type=_parse_bits)
    encode.add_argument("--unterminated", action="store_true")

    decode = subparsers.add_parser("decode", help="decode a bit string")
    decode.add_argument("bits", type=_parse_bits)
    decode.add_argument("--unterminated", action="store_true")

    simulate = subparsers.add_parser("simulate-bsc", help="simulate over a binary symmetric channel")
    simulate.add_argument("bits", type=_parse_bits)
    simulate.add_argument("--p", type=float, required=True, help="crossover probability")
    simulate.add_argument("--seed", type=int)
    simulate.add_argument("--unterminated", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    trellis = Trellis(args.constraint_length, tuple(int(g, 8) for g in args.generators))
    codec = ConvolutionalCodec(trellis)

    if args.command == "encode":
        encoded = codec.encode(args.bits, terminate=not args.unterminated)
        print("".join(map(str, encoded)))
        return 0
    if args.command == "decode":
        result = codec.decode(args.bits, assume_terminated=not args.unterminated)
        print(json.dumps({"bits": result.bits, "path_metric": result.path_metric}))
        return 0
    if args.command == "simulate-bsc":
        result = codec.simulate_bsc(
            args.bits,
            args.p,
            terminate=not args.unterminated,
            seed=args.seed,
        )
        print(json.dumps(result))
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
