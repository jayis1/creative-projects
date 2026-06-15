"""Command-line interface for the compression engine."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec


CODECS = {
    "huffman": HuffmanCodec,
    "lz77": LZ77Codec,
    "bwt": BWTCodec,
    "deflate": DeflateCodec,
}


def _format_size(n: int) -> str:
    """Format a byte size with appropriate unit."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    else:
        return f"{n / (1024 * 1024):.1f} MB"


def _format_ratio(original: int, compressed: int) -> str:
    """Format compression ratio."""
    if original == 0:
        return "N/A"
    ratio = compressed / original * 100
    return f"{ratio:.1f}%"


def cmd_compress(args: argparse.Namespace) -> None:
    """Compress a file."""
    codec_name = args.codec
    if codec_name not in CODECS:
        print(f"Error: unknown codec '{codec_name}'. Available: {', '.join(CODECS)}", file=sys.stderr)
        sys.exit(1)

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    codec = CODECS[codec_name]()
    start = time.perf_counter()
    compressed = codec.compress(data)
    elapsed = time.perf_counter() - start

    # Write output
    if args.output == "-" or args.output is None:
        sys.stdout.buffer.write(compressed)
    else:
        with open(args.output, "wb") as f:
            f.write(compressed)

    if args.verbose:
        print(f"Codec:       {codec_name}", file=sys.stderr)
        print(f"Original:    {_format_size(len(data))}", file=sys.stderr)
        print(f"Compressed:  {_format_size(len(compressed))}", file=sys.stderr)
        print(f"Ratio:       {_format_ratio(len(data), len(compressed))}", file=sys.stderr)
        print(f"Time:        {elapsed * 1000:.1f} ms", file=sys.stderr)


def cmd_decompress(args: argparse.Namespace) -> None:
    """Decompress a file."""
    codec_name = args.codec
    if codec_name not in CODECS:
        print(f"Error: unknown codec '{codec_name}'. Available: {', '.join(CODECS)}", file=sys.stderr)
        sys.exit(1)

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    codec = CODECS[codec_name]()
    start = time.perf_counter()
    decompressed = codec.decompress(data)
    elapsed = time.perf_counter() - start

    # Write output
    if args.output == "-" or args.output is None:
        sys.stdout.buffer.write(decompressed)
    else:
        with open(args.output, "wb") as f:
            f.write(decompressed)

    if args.verbose:
        print(f"Codec:        {codec_name}", file=sys.stderr)
        print(f"Compressed:   {_format_size(len(data))}", file=sys.stderr)
        print(f"Decompressed: {_format_size(len(decompressed))}", file=sys.stderr)
        print(f"Time:         {elapsed * 1000:.1f} ms", file=sys.stderr)


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Benchmark all codecs on the given input."""
    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    print(f"Input size: {_format_size(len(data))}")
    print(f"{'Codec':<12} {'Compressed':<12} {'Ratio':<10} {'Comp ms':<10} {'Decomp ms':<10} {'OK?':<5}")
    print("-" * 60)

    for name, codec_cls in CODECS.items():
        codec = codec_cls()
        try:
            start = time.perf_counter()
            compressed = codec.compress(data)
            comp_time = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            decompressed = codec.decompress(compressed)
            decomp_time = (time.perf_counter() - start) * 1000

            ok = decompressed == data
            print(f"{name:<12} {_format_size(len(compressed)):<12} {_format_ratio(len(data), len(compressed)):<10} "
                  f"{comp_time:<10.1f} {decomp_time:<10.1f} {'✓' if ok else '✗':<5}")
        except Exception as e:
            print(f"{name:<12} ERROR: {e}")


def main(argv: Optional[list] = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="compression-engine",
        description="Data compression engine with multiple algorithms",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # compress subcommand
    comp_parser = subparsers.add_parser("compress", help="Compress a file")
    comp_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    comp_parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    comp_parser.add_argument("-c", "--codec", default="deflate",
                             choices=list(CODECS.keys()), help="Codec to use")
    comp_parser.add_argument("-v", "--verbose", action="store_true", help="Show statistics")
    comp_parser.set_defaults(func=cmd_compress)

    # decompress subcommand
    decomp_parser = subparsers.add_parser("decompress", help="Decompress a file")
    decomp_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    decomp_parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    decomp_parser.add_argument("-c", "--codec", default="deflate",
                               choices=list(CODECS.keys()), help="Codec to use")
    decomp_parser.add_argument("-v", "--verbose", action="store_true", help="Show statistics")
    decomp_parser.set_defaults(func=cmd_decompress)

    # benchmark subcommand
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark all codecs")
    bench_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    bench_parser.set_defaults(func=cmd_benchmark)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)