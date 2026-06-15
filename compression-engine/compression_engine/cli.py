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
from .rle import RLECodec
from .delta import DeltaCodec
from .pipeline import Pipeline, create_pipeline, CODEC_REGISTRY
from .analysis import analyze, shannon_entropy


CODECS = {
    "huffman": HuffmanCodec,
    "lz77": LZ77Codec,
    "bwt": BWTCodec,
    "deflate": DeflateCodec,
    "rle": RLECodec,
    "delta": DeltaCodec,
}


def _format_size(n: int) -> str:
    """Format a byte size with appropriate unit."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    elif n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    else:
        return f"{n / (1024 * 1024 * 1024):.2f} GB"


def _format_ratio(original: int, compressed: int) -> str:
    """Format compression ratio."""
    if original == 0:
        return "N/A"
    ratio = compressed / original * 100
    return f"{ratio:.1f}%"


def cmd_compress(args: argparse.Namespace) -> None:
    """Compress a file."""
    codec_name = args.codec

    # Check if it's a pipeline specification (contains '+')
    if "+" in codec_name:
        pipeline = create_pipeline(codec_name)
        codec = pipeline
    elif codec_name in CODECS:
        codec = CODECS[codec_name]()
    else:
        print(f"Error: unknown codec '{codec_name}'. Available: {', '.join(CODECS.keys())} or pipeline (codec1+codec2)", file=sys.stderr)
        sys.exit(1)

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

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

    if "+" in codec_name:
        codec = create_pipeline(codec_name)
    elif codec_name in CODECS:
        codec = CODECS[codec_name]()
    else:
        print(f"Error: unknown codec '{codec_name}'", file=sys.stderr)
        sys.exit(1)

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

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

    # Also test pipelines
    pipelines = ["rle+huffman", "rle+lz77", "rle+deflate", "delta+huffman", "delta+deflate"]

    all_codecs = list(CODECS.items()) + [(p, None) for p in pipelines]

    print(f"Input size: {_format_size(len(data))}")
    analysis = analyze(data)
    print(f"Entropy:    {analysis['entropy_bits']:.2f} bits/symbol")
    print(f"Optimal:    {analysis['optimal_ratio']:.1%}")
    print()
    print(f"{'Codec':<20} {'Compressed':<12} {'Ratio':<10} {'Comp ms':<10} {'Decomp ms':<10} {'OK?':<5}")
    print("-" * 70)

    for name, codec_cls in all_codecs:
        if codec_cls is not None:
            codec = codec_cls()
        else:
            codec = create_pipeline(name)

        try:
            start = time.perf_counter()
            compressed = codec.compress(data)
            comp_time = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            decompressed = codec.decompress(compressed)
            decomp_time = (time.perf_counter() - start) * 1000

            ok = decompressed == data
            print(f"{name:<20} {_format_size(len(compressed)):<12} {_format_ratio(len(data), len(compressed)):<10} "
                  f"{comp_time:<10.1f} {decomp_time:<10.1f} {'✓' if ok else '✗':<5}")
        except Exception as e:
            print(f"{name:<20} ERROR: {e}")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze data compressibility."""
    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    result = analyze(data)
    print(f"Size:            {_format_size(int(result['size_bytes']))}")
    print(f"Unique bytes:    {result['unique_bytes']}/256")
    print(f"Shannon entropy: {result['entropy_bits']:.4f} bits/symbol")
    print(f"Optimal ratio:   {result['optimal_ratio']:.1%}")
    print(f"Compressibility:  {result['compressibility']:.1%}")
    print(f"Redundancy:      {result['redundancy']:.1%}")


def main(argv: Optional[list] = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="compression-engine",
        description="Data compression engine with multiple algorithms and codec pipelines",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # compress subcommand
    comp_parser = subparsers.add_parser("compress", help="Compress a file")
    comp_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    comp_parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    comp_parser.add_argument("-c", "--codec", default="deflate",
                             choices=list(CODECS.keys()),
                             help="Codec to use (default: deflate)")
    comp_parser.add_argument("-p", "--pipeline", help="Pipeline spec (e.g., rle+huffman)")
    comp_parser.add_argument("-v", "--verbose", action="store_true", help="Show statistics")
    comp_parser.set_defaults(func=cmd_compress)

    # decompress subcommand
    decomp_parser = subparsers.add_parser("decompress", help="Decompress a file")
    decomp_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    decomp_parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    decomp_parser.add_argument("-c", "--codec", default="deflate",
                               choices=list(CODECS.keys()),
                               help="Codec to use (default: deflate)")
    decomp_parser.add_argument("-p", "--pipeline", help="Pipeline spec (e.g., rle+huffman)")
    decomp_parser.add_argument("-v", "--verbose", action="store_true", help="Show statistics")
    decomp_parser.set_defaults(func=cmd_decompress)

    # benchmark subcommand
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark all codecs")
    bench_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    bench_parser.set_defaults(func=cmd_benchmark)

    # analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Analyze data compressibility")
    analyze_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args(argv)

    # Handle pipeline override
    if hasattr(args, 'pipeline') and args.pipeline:
        args.codec = args.pipeline

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)