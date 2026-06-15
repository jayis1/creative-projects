"""Command-line interface for the compression engine.

Provides compress, decompress, benchmark, analyze, compare, and config commands
with JSON output, verbose mode, pipeline support, and more.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .rle import RLECodec
from .delta import DeltaCodec
from .lzw import LZWCodec
from .arithmetic import ArithmeticCodec
from .pipeline import Pipeline, create_pipeline, CODEC_REGISTRY
from .analysis import analyze, shannon_entropy
from .benchmark import run_benchmark
from .config import load_config, save_config, resolve_pipeline, DEFAULT_CONFIG
from .logger import configure_logging, get_logger

CODECS = {
    "huffman": HuffmanCodec,
    "lz77": LZ77Codec,
    "bwt": BWTCodec,
    "deflate": DeflateCodec,
    "rle": RLECodec,
    "delta": DeltaCodec,
    "lzw": LZWCodec,
    "arithmetic": ArithmeticCodec,
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


def _get_codec(name: str, config: dict):
    """Get a codec instance by name, handling pipelines."""
    if "+" in name:
        return create_pipeline(name)
    if name in CODECS:
        codec_config = config.get("codecs", {}).get(name, {})
        return CODECS[name](**codec_config)
    raise ValueError(f"Unknown codec '{name}'. Available: {', '.join(CODECS.keys())} or pipeline (codec1+codec2)")


def cmd_compress(args: argparse.Namespace) -> None:
    """Compress a file."""
    logger = get_logger()
    config = load_config(args.config) if hasattr(args, "config") and args.config else DEFAULT_CONFIG

    # Resolve codec name
    codec_name = args.codec
    if hasattr(args, "pipeline") and args.pipeline:
        codec_name = args.pipeline
    elif codec_name in config.get("pipelines", {}):
        codec_name = resolve_pipeline(config, codec_name)

    try:
        codec = _get_codec(codec_name, config)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    logger.info("Compressing %d bytes with %s", len(data), codec_name)

    start = time.perf_counter()
    compressed = codec.compress(data)
    elapsed = time.perf_counter() - start

    # Write output
    if args.output == "-" or args.output is None:
        sys.stdout.buffer.write(compressed)
    else:
        with open(args.output, "wb") as f:
            f.write(compressed)

    if args.json:
        result = {
            "codec": codec_name,
            "original_size": len(data),
            "compressed_size": len(compressed),
            "ratio": len(compressed) / len(data) if len(data) > 0 else 0,
            "time_ms": round(elapsed * 1000, 2),
        }
        print(json.dumps(result, indent=2))
    elif args.verbose:
        print(f"Codec:       {codec_name}", file=sys.stderr)
        print(f"Original:    {_format_size(len(data))}", file=sys.stderr)
        print(f"Compressed:  {_format_size(len(compressed))}", file=sys.stderr)
        print(f"Ratio:       {_format_ratio(len(data), len(compressed))}", file=sys.stderr)
        print(f"Time:        {elapsed * 1000:.1f} ms", file=sys.stderr)


def cmd_decompress(args: argparse.Namespace) -> None:
    """Decompress a file."""
    config = load_config(args.config) if hasattr(args, "config") and args.config else DEFAULT_CONFIG

    codec_name = args.codec
    if hasattr(args, "pipeline") and args.pipeline:
        codec_name = args.pipeline
    elif codec_name in config.get("pipelines", {}):
        codec_name = resolve_pipeline(config, codec_name)

    try:
        codec = _get_codec(codec_name, config)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
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

    if args.json:
        result = {
            "codec": codec_name,
            "compressed_size": len(data),
            "decompressed_size": len(decompressed),
            "time_ms": round(elapsed * 1000, 2),
        }
        print(json.dumps(result, indent=2))
    elif args.verbose:
        print(f"Codec:        {codec_name}", file=sys.stderr)
        print(f"Compressed:   {_format_size(len(data))}", file=sys.stderr)
        print(f"Decompressed: {_format_size(len(decompressed))}", file=sys.stderr)
        print(f"Time:         {elapsed * 1000:.1f} ms", file=sys.stderr)


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Benchmark all codecs on the given input."""
    config = load_config(args.config) if hasattr(args, "config") and args.config else DEFAULT_CONFIG

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    report = run_benchmark(
        data,
        include_pipelines=not args.no_pipelines,
        repeat=args.repeat,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        analysis = analyze(data)
        print(f"Input size: {_format_size(len(data))}")
        print(f"Entropy:    {analysis['entropy_bits']:.2f} bits/symbol")
        print(f"Optimal:    {analysis['optimal_ratio']:.1%}")
        print()
        print(report.to_table())

        # Show recommendations
        best = report.best_ratio()
        if best:
            print(f"\nBest compression:  {best.codec_name} ({best.compression_ratio:.1%})")
        fastest = report.fastest_compress()
        if fastest:
            print(f"Fastest compress:  {fastest.codec_name} ({fastest.compression_time_ms:.1f} ms)")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze data compressibility."""
    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    result = analyze(data)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Size:            {_format_size(int(result['size_bytes']))}")
        print(f"Unique bytes:    {result['unique_bytes']}/256")
        print(f"Shannon entropy:  {result['entropy_bits']:.4f} bits/symbol")
        print(f"Optimal ratio:   {result['optimal_ratio']:.1%}")
        print(f"Compressibility:  {result['compressibility']:.1%}")
        print(f"Redundancy:      {result['redundancy']:.1%}")

        # Byte distribution hints
        entropy = result['entropy_bits']
        if entropy < 3.0:
            print(f"\n💡 High compressibility — data has skewed byte distribution")
        elif entropy < 6.0:
            print(f"\n💡 Moderate compressibility — some patterns present")
        else:
            print(f"\n💡 Low compressibility — data is near-random")


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare two or more codecs on the same input."""
    config = load_config(args.config) if hasattr(args, "config") and args.config else DEFAULT_CONFIG

    # Read input
    if args.input == "-" or args.input is None:
        data = sys.stdin.buffer.read()
    else:
        with open(args.input, "rb") as f:
            data = f.read()

    report = run_benchmark(
        data,
        codecs=args.codecs,
        include_pipelines=False,
        repeat=args.repeat,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Comparing codecs on {_format_size(len(data))} of data:\n")
        print(report.to_table())


def cmd_config(args: argparse.Namespace) -> None:
    """Show or manage configuration."""
    if args.show:
        config = DEFAULT_CONFIG
        if args.config_file:
            config = load_config(args.config_file)
        print(json.dumps(config, indent=2))
    elif args.save_default:
        config_path = args.save_default
        save_config(DEFAULT_CONFIG, config_path)
        print(f"Default configuration saved to {config_path}")


def main(argv: Optional[list] = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="compression-engine",
        description="Data compression engine with multiple algorithms, codec pipelines, and analysis tools",
    )
    parser.add_argument("--version", action="version", version="compression-engine 3.0.0")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set logging level")

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
    comp_parser.add_argument("--json", action="store_true", help="Output results as JSON")
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
    decomp_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    decomp_parser.set_defaults(func=cmd_decompress)

    # benchmark subcommand
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark all codecs")
    bench_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    bench_parser.add_argument("--no-pipelines", action="store_true", help="Skip pipeline benchmarks")
    bench_parser.add_argument("--repeat", type=int, default=1, help="Number of timing repetitions")
    bench_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    bench_parser.set_defaults(func=cmd_benchmark)

    # analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Analyze data compressibility")
    analyze_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    analyze_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    analyze_parser.set_defaults(func=cmd_analyze)

    # compare subcommand
    compare_parser = subparsers.add_parser("compare", help="Compare codecs on same input")
    compare_parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    compare_parser.add_argument("codecs", nargs="+",
                                 choices=list(CODECS.keys()),
                                 help="Codecs to compare")
    compare_parser.add_argument("--repeat", type=int, default=1, help="Number of timing repetitions")
    compare_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    compare_parser.set_defaults(func=cmd_compare)

    # config subcommand
    config_parser = subparsers.add_parser("config", help="Show or manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current configuration")
    config_parser.add_argument("--save-default", metavar="PATH",
                               help="Save default configuration to a file")
    config_parser.add_argument("--config-file", help="Config file to load")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args(argv)

    # Configure logging
    configure_logging(level=args.log_level if hasattr(args, "log_level") else "WARNING")

    # Handle pipeline override
    if hasattr(args, "pipeline") and args.pipeline:
        args.codec = args.pipeline

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)