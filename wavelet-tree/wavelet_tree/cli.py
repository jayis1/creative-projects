"""Command-line interface for the wavelet tree library."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .wavelet_tree import WaveletTree
from .wavelet_matrix import WaveletMatrix
from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix
from .queries import range_quantile, range_count, range_next_value, interval_symbols
from .serialization import save, load


def _build_structure(sequence: str, struct_type: str):
    """Build the requested wavelet tree structure."""
    seq = list(sequence)
    if struct_type == "tree":
        return WaveletTree(seq)
    elif struct_type == "matrix":
        return WaveletMatrix(seq)
    elif struct_type == "huffman-tree":
        return HuffmanWaveletTree(seq)
    elif struct_type == "huffman-matrix":
        return HuffmanWaveletMatrix(seq)
    else:
        raise ValueError(f"Unknown structure type: {struct_type}")


def cmd_build(args):
    """Build a wavelet tree from a sequence and run queries."""
    wt = _build_structure(args.sequence, args.structure)

    if args.save:
        save(wt, args.save)
        print(f"Saved to {args.save}")

    if args.rank:
        c, i = args.rank[0], int(args.rank[1])
        result = wt.rank(c, i)
        print(f"rank('{c}', {i}) = {result}")

    if args.select:
        c, k = args.select[0], int(args.select[1])
        result = wt.select(c, k)
        print(f"select('{c}', {k}) = {result}")

    if args.access:
        i = int(args.access)
        result = wt.access(i)
        print(f"access({i}) = '{result}'")

    if args.quantile:
        l, r, k = int(args.quantile[0]), int(args.quantile[1]), int(args.quantile[2])
        result = range_quantile(wt, l, r, k)
        print(f"range_quantile({l}, {r}, {k}) = '{result}'")

    if args.range_count:
        c, l, r = (
            args.range_count[0],
            int(args.range_count[1]),
            int(args.range_count[2]),
        )
        result = range_count(wt, c, l, r)
        print(f"range_count('{c}', {l}, {r}) = {result}")

    if args.range_next:
        l, r, threshold = (
            int(args.range_next[0]),
            int(args.range_next[1]),
            args.range_next[2],
        )
        result = range_next_value(wt, l, r, threshold)
        print(f"range_next_value({l}, {r}, '{threshold}') = '{result}'")

    if args.interval_symbols:
        l, r = (
            int(args.interval_symbols[0]),
            int(args.interval_symbols[1]),
        )
        result = interval_symbols(wt, l, r)
        print(f"interval_symbols({l}, {r}) = {result}")

    if args.alphabet:
        print(f"Alphabet: {wt.alphabet}")

    if not any(
        [
            args.rank,
            args.select,
            args.access,
            args.quantile,
            args.range_count,
            args.range_next,
            args.interval_symbols,
            args.alphabet,
            args.save,
        ]
    ):
        print(f"Built {type(wt).__name__} over sequence '{args.sequence}'")
        print(f"  Length: {len(wt)}")
        print(f"  Alphabet: {wt.alphabet}")


def cmd_load(args):
    """Load a wavelet tree from a file and run queries."""
    wt = load(args.file)

    if args.rank:
        c, i = args.rank[0], int(args.rank[1])
        result = wt.rank(c, i)
        print(f"rank('{c}', {i}) = {result}")

    if args.select:
        c, k = args.select[0], int(args.select[1])
        result = wt.select(c, k)
        print(f"select('{c}', {k}) = {result}")

    if args.access:
        i = int(args.access)
        result = wt.access(i)
        print(f"access({i}) = '{result}'")

    if args.quantile:
        l, r, k = int(args.quantile[0]), int(args.quantile[1]), int(args.quantile[2])
        result = range_quantile(wt, l, r, k)
        print(f"range_quantile({l}, {r}, {k}) = '{result}'")

    if args.range_count:
        c, l, r = (
            args.range_count[0],
            int(args.range_count[1]),
            int(args.range_count[2]),
        )
        result = range_count(wt, c, l, r)
        print(f"range_count('{c}', {l}, {r}) = {result}")

    if args.interval_symbols:
        l, r = (
            int(args.interval_symbols[0]),
            int(args.interval_symbols[1]),
        )
        result = interval_symbols(wt, l, r)
        print(f"interval_symbols({l}, {r}) = {result}")


def cmd_compare(args):
    """Compare different wavelet tree structures on a sequence."""
    seq = list(args.sequence)
    structures = {
        "WaveletTree": WaveletTree(seq),
        "WaveletMatrix": WaveletMatrix(seq),
        "HuffmanWaveletTree": HuffmanWaveletTree(seq),
        "HuffmanWaveletMatrix": HuffmanWaveletMatrix(seq),
    }

    print(f"Sequence: '{args.sequence}' (length={len(seq)})")
    print(f"Alphabet: {sorted(set(seq))}")
    print()
    print(f"{'Structure':<25} {'Access(0)':<12} {'Rank(a,n)':<12} {'Select(a,0)':<14}")
    print("-" * 65)

    for name, wt in structures.items():
        try:
            a0 = wt.access(0)
        except Exception:
            a0 = "ERR"
        try:
            rn = wt.rank(seq[0], len(seq))
        except Exception:
            rn = "ERR"
        try:
            s0 = wt.select(seq[0], 0)
        except Exception:
            s0 = "ERR"
        print(f"{name:<25} {str(a0):<12} {str(rn):<12} {str(s0):<14}")


def cmd_info(args):
    """Show information about the library."""
    print(f"wavelet_tree v{__version__}")
    print("A succinct data structure library for sequence analysis.")
    print()
    print("Available structures:")
    print("  - WaveletTree (balanced binary)")
    print("  - WaveletMatrix (level-ordered)")
    print("  - HuffmanWaveletTree (Huffman-shaped)")
    print("  - HuffmanWaveletMatrix (Huffman + matrix)")
    print()
    print("Operations: access, rank, select, range_quantile, range_count,")
    print("            range_next_value, interval_symbols")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="wavelet_tree",
        description="Wavelet tree succinct data structure library",
    )
    parser.add_argument("--version", action="version", version=f"wavelet_tree {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # build
    p_build = subparsers.add_parser("build", help="Build a wavelet tree from a sequence")
    p_build.add_argument("sequence", help="The input sequence (string)")
    p_build.add_argument(
        "--structure",
        choices=["tree", "matrix", "huffman-tree", "huffman-matrix"],
        default="tree",
        help="Structure type (default: tree)",
    )
    p_build.add_argument("--rank", nargs=2, metavar=("SYMBOL", "N"), help="Compute rank(SYMBOL, N)")
    p_build.add_argument("--select", nargs=2, metavar=("SYMBOL", "K"), help="Compute select(SYMBOL, K)")
    p_build.add_argument("--access", metavar="I", help="Compute access(I)")
    p_build.add_argument("--quantile", nargs=3, metavar=("L", "R", "K"), help="Range quantile [L,R) k-th smallest")
    p_build.add_argument("--range-count", nargs=3, metavar=("SYMBOL", "L", "R"), help="Count SYMBOL in [L,R)")
    p_build.add_argument("--range-next", nargs=3, metavar=("L", "R", "THRESHOLD"), help="Smallest symbol >= THRESHOLD in [L,R)")
    p_build.add_argument("--interval-symbols", nargs=2, metavar=("L", "R"), help="Distinct symbols in [L,R)")
    p_build.add_argument("--alphabet", action="store_true", help="Print the alphabet")
    p_build.add_argument("--save", metavar="FILE", help="Save to JSON file")
    p_build.set_defaults(func=cmd_build)

    # load
    p_load = subparsers.add_parser("load", help="Load a wavelet tree from a JSON file")
    p_load.add_argument("file", help="JSON file path")
    p_load.add_argument("--rank", nargs=2, metavar=("SYMBOL", "N"), help="Compute rank(SYMBOL, N)")
    p_load.add_argument("--select", nargs=2, metavar=("SYMBOL", "K"), help="Compute select(SYMBOL, K)")
    p_load.add_argument("--access", metavar="I", help="Compute access(I)")
    p_load.add_argument("--quantile", nargs=3, metavar=("L", "R", "K"), help="Range quantile [L,R) k-th smallest")
    p_load.add_argument("--range-count", nargs=3, metavar=("SYMBOL", "L", "R"), help="Count SYMBOL in [L,R)")
    p_load.add_argument("--interval-symbols", nargs=2, metavar=("L", "R"), help="Distinct symbols in [L,R)")
    p_load.set_defaults(func=cmd_load)

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare structures on a sequence")
    p_compare.add_argument("sequence", help="The input sequence")
    p_compare.set_defaults(func=cmd_compare)

    # info
    p_info = subparsers.add_parser("info", help="Show library information")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())