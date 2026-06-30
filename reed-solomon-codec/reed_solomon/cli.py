#!/usr/bin/env python3
"""Command-line interface for the Reed-Solomon codec.

Subcommands:
    encode       Encode a file with RS parity
    decode       Decode and correct a file
    demo         Run an interactive error-correction demo
    burst-demo   Demonstrate burst-error correction via interleaving
    info         Print code parameters
    bench        Benchmark encoding/decoding throughput
    config       Generate or validate a configuration file
    stream       Encode/decode stdin → stdout (pipeline mode)
    version      Print version information

Global options:
    --config FILE     Load codec configuration from a file (.json/.yaml/.toml)
    --log-level LVL   Set logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    --nsym N          Override parity symbol count (default: from config or 10)

Examples:
    rsc encode mydata.txt encoded.bin --nsym 16
    rsc decode encoded.bin recovered.txt --nsym 16
    rsc demo
    rsc burst-demo --nsym 10 --depth 5
    rsc config --generate config.json
    rsc bench --nsym 10 --size 1000
    echo "Hello" | rsc stream encode --nsym 10 | rsc stream decode --nsym 10
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Optional

from . import __version__
from .config import CodecConfig, _HAS_YAML, _HAS_TOML
from .codec import (
    RSCode,
    decode_message,
    decode_interleaved,
    encode_interleaved,
    encode_message,
    rs_decode,
    rs_encode,
)

logger = logging.getLogger("reed_solomon.cli")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_overrides(config: CodecConfig, args: argparse.Namespace) -> CodecConfig:
    """Apply CLI overrides on top of the loaded config."""
    if getattr(args, "nsym", None) is not None:
        config.nsym = args.nsym
    if getattr(args, "log_level", None) is not None:
        config.log_level = args.log_level
    return config


def _load_config_and_setup(args: argparse.Namespace) -> CodecConfig:
    """Load config (from --config or defaults), apply CLI overrides, set up logging."""
    config = CodecConfig()
    if getattr(args, "config", None):
        config = CodecConfig.load(args.config)
        config.validate()
    config = _apply_overrides(config, args)
    config.setup_logging()
    return config


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_encode(args: argparse.Namespace) -> int:
    """Encode a file with RS parity."""
    config = _load_config_and_setup(args)
    nsym = config.nsym
    with open(args.input, "rb") as f:
        data = f.read()

    if args.interleave:
        depth = args.interleave
        encoded = encode_interleaved(data, nsym, depth)
        logger.info("Interleaved encode: %d bytes -> %d bytes (nsym=%d, depth=%d)",
                    len(data), len(encoded), nsym, depth)
    else:
        encoded = encode_message(data, nsym)
        logger.info("Encode: %d bytes -> %d bytes (nsym=%d)", len(data), len(encoded), nsym)

    outfile = args.output or (args.input + ".rs")
    with open(outfile, "wb") as f:
        f.write(encoded)
    print(f"Encoded {len(data)} bytes -> {len(encoded)} bytes (nsym={nsym})")
    print(f"Parity: {nsym} bytes, max correctable errors: {nsym // 2}")
    print(f"Output: {outfile}")
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    """Decode and correct a file."""
    config = _load_config_and_setup(args)
    nsym = config.nsym
    with open(args.input, "rb") as f:
        data = f.read()

    try:
        if args.interleave:
            depth = args.interleave
            decoded = decode_interleaved(data, nsym, depth)
            logger.info("Interleaved decode: %d bytes -> %d bytes (nsym=%d, depth=%d)",
                        len(data), len(decoded), nsym, depth)
        else:
            decoded = decode_message(data, nsym)
            logger.info("Decode: %d bytes -> %d bytes (nsym=%d)", len(data), len(decoded), nsym)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        logger.error("Decode failed: %s", e)
        return 1

    if args.output:
        outfile = args.output
    elif args.input.endswith(".rs"):
        outfile = args.input[:-3]  # strip the .rs extension
    else:
        outfile = args.input + ".decoded"
    with open(outfile, "wb") as f:
        f.write(decoded)
    print(f"Decoded {len(data)} bytes -> {len(decoded)} bytes (nsym={nsym})")
    print(f"Output: {outfile}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Run an interactive demo showing error correction."""
    config = _load_config_and_setup(args)
    nsym = config.nsym
    rs = RSCode(nsym)
    message = b"The quick brown fox jumps over the lazy dog!"

    print("=" * 60)
    print("Reed-Solomon Codec Demo")
    print("=" * 60)
    print(f"Message: {message.decode()}")
    print(f"Message length: {len(message)} bytes")
    print(rs)
    print()

    codeword = bytearray(rs.encode_bytes(message))
    print(f"Codeword ({len(codeword)} bytes): {codeword.hex()}")

    # Simulate channel errors
    errors = min(nsym // 2, 5)
    error_positions = [5, 12, 20, 30, len(codeword) - 3][:errors]
    print(f"\nInjecting {len(error_positions)} errors at positions: {error_positions}")
    for pos in error_positions:
        old = codeword[pos]
        codeword[pos] ^= 0xAB
        print(f"  Position {pos}: {old:3d} (0x{old:02x}) -> {codeword[pos]:3d} (0x{codeword[pos]:02x})")

    print(f"\nCorrupted codeword: {bytes(codeword).hex()}")
    try:
        result = rs.decode_detailed(list(codeword))
        recovered = bytes(result.corrected[nsym:])
        print(f"Recovered message: {recovered.decode()}")
        print(f"Errors corrected:  {result.errors_corrected}")
        print(f"Error positions:   {result.error_positions}")
        if recovered == message:
            print("\n✓ SUCCESS: Message perfectly recovered!")
        else:
            print("\n✗ FAILURE: Recovered message does not match!")
            return 1
    except ValueError as e:
        print(f"\n✗ FAILED: {e}")
        return 1

    # Erasure demo
    print("\n" + "-" * 60)
    print("Erasure Correction Demo")
    print("-" * 60)
    codeword2 = bytearray(rs.encode_bytes(message))
    erasure_positions = [3, 8, 15, 25, len(codeword2) - 5][:nsym]
    print(f"Erasing {len(erasure_positions)} positions: {erasure_positions}")
    for pos in erasure_positions:
        codeword2[pos] = 0

    try:
        result = rs.decode_detailed(list(codeword2), erasures=erasure_positions)
        recovered = bytes(result.corrected[nsym:])
        print(f"Recovered message: {recovered.decode()}")
        print(f"Total corrections: {len(result.error_positions) + len(result.erasure_positions)}")
        if recovered == message:
            print("\n✓ SUCCESS: Erasures perfectly recovered!")
        else:
            print("\n✗ FAILURE: Recovered message does not match!")
            return 1
    except ValueError as e:
        print(f"\n✗ FAILED: {e}")
        return 1

    print("\n" + "=" * 60)
    print("Demo complete!")
    return 0


def cmd_burst_demo(args: argparse.Namespace) -> int:
    """Demonstrate burst-error correction via interleaving."""
    config = _load_config_and_setup(args)
    nsym = config.nsym
    depth = args.depth
    message = b"Interleaving spreads burst errors across multiple codewords!"

    print("=" * 60)
    print("Burst Error Correction Demo (Interleaved RS)")
    print("=" * 60)
    print(f"Message: {message.decode()}")
    print(f"Message length: {len(message)} bytes")
    print(f"nsym: {nsym}, interleaving depth: {depth}")
    print(f"Without interleaving: max burst = {nsym // 2} symbols")
    print(f"With interleaving:    max burst = {depth * (nsym // 2)} symbols")
    print()

    encoded = bytearray(encode_interleaved(message, nsym, depth))
    print(f"Encoded: {len(encoded)} bytes")

    burst_len = depth * (nsym // 2)
    burst_start = 10
    print(f"\nInjecting burst error of length {burst_len} at position {burst_start}")
    for i in range(burst_len):
        if burst_start + i < len(encoded):
            encoded[burst_start + i] ^= 0xFF

    try:
        recovered = decode_interleaved(bytes(encoded), nsym, depth, original_len=len(message))
        print(f"Recovered: {recovered.decode()}")
        if recovered == message:
            print(f"\n✓ SUCCESS: Burst of {burst_len} symbols corrected via interleaving!")
        else:
            print("\n✗ FAILURE: Recovered message does not match!")
            return 1
    except ValueError as e:
        print(f"\n✗ FAILED: {e}")
        return 1

    print("\n" + "=" * 60)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Print code parameters."""
    config = _load_config_and_setup(args)
    rs = RSCode(config.nsym)
    print(rs)
    print(f"\n  Interleaving depth:     {config.interleaving_depth}")
    print(f"  Version:                {__version__}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Benchmark encoding/decoding throughput."""
    config = _load_config_and_setup(args)
    nsym = config.nsym
    size = args.size
    rs = RSCode(nsym)

    # Generate random data
    import random
    random.seed(42)
    data = bytes(random.randint(0, 255) for _ in range(size))

    print("=" * 60)
    print("Reed-Solomon Benchmark")
    print("=" * 60)
    print(f"  nsym: {nsym}, data size: {size} bytes")
    print(f"  Codeword size: {size + nsym} bytes")
    print(f"  Max correctable errors: {nsym // 2}")
    print()

    # Encode benchmark
    iterations = args.iterations
    start = time.perf_counter()
    encoded: bytes = rs.encode_bytes(data)
    for _ in range(iterations - 1):
        rs.encode_bytes(data)
    enc_time = time.perf_counter() - start
    enc_throughput = (size * iterations) / enc_time / 1024 if enc_time > 0 else float("inf")
    print(f"  Encode: {iterations} iterations in {enc_time:.3f}s")
    print(f"    Throughput: {enc_throughput:.1f} KB/s")

    # Decode benchmark (no errors)
    start = time.perf_counter()
    for _ in range(iterations):
        rs.decode_bytes(encoded)
    dec_time = time.perf_counter() - start
    dec_throughput = ((size + nsym) * iterations) / dec_time / 1024 if dec_time > 0 else float("inf")
    print(f"  Decode (no errors): {iterations} iterations in {dec_time:.3f}s")
    print(f"    Throughput: {dec_throughput:.1f} KB/s")

    # Decode with errors
    num_errors = nsym // 2
    if num_errors > 0:
        corrupted = bytearray(encoded)
        for i in range(num_errors):
            corrupted[i * (len(corrupted) // num_errors + 1)] ^= 0xFF
        start = time.perf_counter()
        for _ in range(iterations):
            rs.decode_bytes(bytes(corrupted))
        dec_err_time = time.perf_counter() - start
        dec_err_throughput = ((size + nsym) * iterations) / dec_err_time / 1024 if dec_err_time > 0 else float("inf")
        print(f"  Decode ({num_errors} errors): {iterations} iterations in {dec_err_time:.3f}s")
        print(f"    Throughput: {dec_err_throughput:.1f} KB/s")

    print()
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Generate or validate a configuration file."""
    if args.generate:
        config = CodecConfig(
            nsym=args.nsym if args.nsym is not None else 10,
            interleaving_depth=args.depth if args.depth is not None else 4,
            log_level=args.log_level or "WARNING",
        )
        config.validate()
        config.save(args.generate)
        print(f"Configuration written to {args.generate}")
        print(config.to_json())
        return 0

    if args.validate:
        try:
            config = CodecConfig.load(args.validate)
            config.validate()
            print(f"✓ Configuration is valid: {args.validate}")
            print(config.to_json())
            return 0
        except Exception as e:
            print(f"✗ Configuration error: {e}", file=sys.stderr)
            return 1

    # No arguments — print current defaults
    config = CodecConfig()
    print("Default configuration:")
    print(config.to_json())
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    """Encode/decode stdin → stdout in pipeline mode."""
    config = _load_config_and_setup(args)
    nsym = config.nsym
    data = sys.stdin.buffer.read()

    if args.mode == "encode":
        result = encode_message(data, nsym)
        sys.stdout.buffer.write(result)
    elif args.mode == "decode":
        try:
            result = decode_message(data, nsym)
            sys.stdout.buffer.write(result)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
    else:
        print(f"Unknown stream mode: {args.mode}", file=sys.stderr)
        return 1
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Print version information."""
    print(f"reed-solomon-codec {__version__}")
    print(f"  YAML support: {'yes' if _HAS_YAML else 'no (install pyyaml)'}")
    print(f"  TOML support: {'yes' if _HAS_TOML else 'no (needs Python 3.11+ or tomli)'}")
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="rsc",
        description="Reed-Solomon encoder/decoder for GF(2^8)",
    )
    parser.add_argument("--config", help="Load configuration from file (.json/.yaml/.toml)")
    parser.add_argument("--log-level", default=None,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set logging level")
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # encode
    enc = subparsers.add_parser("encode", help="Encode a file with RS parity")
    enc.add_argument("input", help="Input file path")
    enc.add_argument("output", nargs="?", help="Output file path (default: input.rs)")
    enc.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    enc.add_argument("--interleave", type=int, default=None, metavar="DEPTH",
                     help="Interleaving depth for burst-error protection")
    enc.set_defaults(func=cmd_encode)

    # decode
    dec = subparsers.add_parser("decode", help="Decode and correct a file")
    dec.add_argument("input", help="Input file path")
    dec.add_argument("output", nargs="?", help="Output file path (default: input.decoded)")
    dec.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    dec.add_argument("--interleave", type=int, default=None, metavar="DEPTH",
                     help="Interleaving depth (must match encoding)")
    dec.set_defaults(func=cmd_decode)

    # demo
    demo = subparsers.add_parser("demo", help="Run an interactive demo")
    demo.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    demo.set_defaults(func=cmd_demo)

    # burst-demo
    bdemo = subparsers.add_parser("burst-demo", help="Demonstrate burst-error correction via interleaving")
    bdemo.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    bdemo.add_argument("--depth", type=int, default=5, help="Interleaving depth (default: 5)")
    bdemo.set_defaults(func=cmd_burst_demo)

    # info
    info = subparsers.add_parser("info", help="Print code parameters")
    info.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    info.set_defaults(func=cmd_info)

    # bench
    bench = subparsers.add_parser("bench", help="Benchmark encoding/decoding throughput")
    bench.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    bench.add_argument("--size", type=int, default=200, help="Data size in bytes (default: 200)")
    bench.add_argument("--iterations", type=int, default=100, help="Number of iterations (default: 100)")
    bench.set_defaults(func=cmd_bench)

    # config
    cfg = subparsers.add_parser("config", help="Generate or validate a configuration file")
    cfg.add_argument("--generate", metavar="FILE", help="Generate a default config file")
    cfg.add_argument("--validate", metavar="FILE", help="Validate an existing config file")
    cfg.add_argument("--nsym", type=int, default=None, help="nsym for generated config")
    cfg.add_argument("--depth", type=int, default=None, help="Interleaving depth for generated config")
    cfg.add_argument("--log-level", default=None, help="Log level for generated config")
    cfg.set_defaults(func=cmd_config)

    # stream
    stream = subparsers.add_parser("stream", help="Encode/decode stdin → stdout (pipeline mode)")
    stream.add_argument("mode", choices=["encode", "decode"], help="encode or decode")
    stream.add_argument("--nsym", type=int, default=None, help="Number of parity symbols (default: 10)")
    stream.set_defaults(func=cmd_stream)

    # version
    ver = subparsers.add_parser("version", help="Print version information")
    ver.set_defaults(func=cmd_version)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())