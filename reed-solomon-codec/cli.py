#!/usr/bin/env python3
"""Command-line interface for the Reed-Solomon codec.

Usage:
    python3 cli.py encode <input_file> [output_file] [--nsym N]
    python3 cli.py decode <input_file> [output_file] [--nsym N]
    python3 cli.py demo
    python3 cli.py burst-demo [--nsym N] [--depth D]
    python3 cli.py info [--nsym N]

Examples:
    python3 cli.py encode mydata.txt encoded.bin --nsym 16
    python3 cli.py decode encoded.bin recovered.txt --nsym 16
    python3 cli.py demo
    python3 cli.py burst-demo --nsym 10 --depth 5
"""
from __future__ import annotations

import argparse
import sys

from rs_codec import (
    encode_message,
    decode_message,
    RSCode,
    encode_interleaved,
    decode_interleaved,
)


def cmd_encode(args: argparse.Namespace) -> int:
    """Encode a file with RS parity."""
    with open(args.input, "rb") as f:
        data = f.read()
    encoded = encode_message(data, args.nsym)
    outfile = args.output or (args.input + ".rs")
    with open(outfile, "wb") as f:
        f.write(encoded)
    print(f"Encoded {len(data)} bytes -> {len(encoded)} bytes (nsym={args.nsym})")
    print(f"Parity: {args.nsym} bytes, max correctable errors: {args.nsym // 2}")
    print(f"Output: {outfile}")
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    """Decode and correct a file."""
    with open(args.input, "rb") as f:
        data = f.read()
    try:
        decoded = decode_message(data, args.nsym)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    outfile = args.output or args.input.replace(".rs", "")
    if outfile == args.input:
        outfile = args.input + ".decoded"
    with open(outfile, "wb") as f:
        f.write(decoded)
    print(f"Decoded {len(data)} bytes -> {len(decoded)} bytes (nsym={args.nsym})")
    print(f"Output: {outfile}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Run an interactive demo showing error correction."""
    nsym = args.nsym
    rs = RSCode(nsym)
    message = b"The quick brown fox jumps over the lazy dog!"

    print("=" * 60)
    print("Reed-Solomon Codec Demo")
    print("=" * 60)
    print(f"Message: {message.decode()}")
    print(f"Message length: {len(message)} bytes")
    print(rs)
    print()

    # Encode
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

    # Decode
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
    nsym = args.nsym
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

    # Encode with interleaving
    encoded = bytearray(encode_interleaved(message, nsym, depth))
    print(f"Encoded: {len(encoded)} bytes")

    # Inject a burst error of length depth * (nsym//2) - should be correctable
    burst_len = depth * (nsym // 2)
    burst_start = 10
    print(f"\nInjecting burst error of length {burst_len} at position {burst_start}")
    for i in range(burst_len):
        if burst_start + i < len(encoded):
            encoded[burst_start + i] ^= 0xFF

    # Decode
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
    """Print codec information."""
    rs = RSCode(args.nsym)
    print(rs)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reed-Solomon encoder/decoder for GF(2^8)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # encode
    enc = subparsers.add_parser("encode", help="Encode a file with RS parity")
    enc.add_argument("input", help="Input file path")
    enc.add_argument("output", nargs="?", help="Output file path (default: input.rs)")
    enc.add_argument("--nsym", type=int, default=10, help="Number of parity symbols (default: 10)")
    enc.set_defaults(func=cmd_encode)

    # decode
    dec = subparsers.add_parser("decode", help="Decode and correct a file")
    dec.add_argument("input", help="Input file path")
    dec.add_argument("output", nargs="?", help="Output file path (default: input.decoded)")
    dec.add_argument("--nsym", type=int, default=10, help="Number of parity symbols (default: 10)")
    dec.set_defaults(func=cmd_decode)

    # demo
    demo = subparsers.add_parser("demo", help="Run an interactive demo")
    demo.add_argument("--nsym", type=int, default=10, help="Number of parity symbols (default: 10)")
    demo.set_defaults(func=cmd_demo)

    # burst demo
    bdemo = subparsers.add_parser("burst-demo", help="Demonstrate burst-error correction via interleaving")
    bdemo.add_argument("--nsym", type=int, default=10, help="Number of parity symbols (default: 10)")
    bdemo.add_argument("--depth", type=int, default=5, help="Interleaving depth (default: 5)")
    bdemo.set_defaults(func=cmd_burst_demo)

    # info
    info = subparsers.add_parser("info", help="Print code parameters")
    info.add_argument("--nsym", type=int, default=10, help="Number of parity symbols (default: 10)")
    info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())