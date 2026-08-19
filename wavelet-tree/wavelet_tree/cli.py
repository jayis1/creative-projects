"""Command-line interface for the wavelet tree library."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .wavelet_tree import WaveletTree
from .wavelet_matrix import WaveletMatrix
from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix
from .queries import (
    range_quantile,
    range_count,
    range_next_value,
    range_prev_value,
    range_min,
    range_max,
    interval_symbols,
    range_intersection,
    prefix_search,
    count_distinct,
)
from .serialization import save, load
from .config import Config
from .logging_utils import setup_logging, get_logger


def _build_structure(sequence: str, struct_type: str, use_blocked: bool = True):
    """Build the requested wavelet tree structure."""
    seq = list(sequence)
    if struct_type == "tree":
        return WaveletTree(seq, use_blocked=use_blocked)
    elif struct_type == "matrix":
        return WaveletMatrix(seq, use_blocked=use_blocked)
    elif struct_type == "huffman-tree":
        return HuffmanWaveletTree(seq, use_blocked=use_blocked)
    elif struct_type == "huffman-matrix":
        return HuffmanWaveletMatrix(seq, use_blocked=use_blocked)
    else:
        raise ValueError(f"Unknown structure type: {struct_type}")


def _run_queries(wt, args) -> None:
    """Run all queries specified in args on the given wavelet tree."""
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

    if args.range_min:
        l, r = int(args.range_min[0]), int(args.range_min[1])
        result = range_min(wt, l, r)
        print(f"range_min({l}, {r}) = '{result}'")

    if args.range_max:
        l, r = int(args.range_max[0]), int(args.range_max[1])
        result = range_max(wt, l, r)
        print(f"range_max({l}, {r}) = '{result}'")

    if args.range_next:
        l, r, threshold = (
            int(args.range_next[0]),
            int(args.range_next[1]),
            args.range_next[2],
        )
        result = range_next_value(wt, l, r, threshold)
        print(f"range_next_value({l}, {r}, '{threshold}') = '{result}'")

    if args.range_prev:
        l, r, threshold = (
            int(args.range_prev[0]),
            int(args.range_prev[1]),
            args.range_prev[2],
        )
        result = range_prev_value(wt, l, r, threshold)
        print(f"range_prev_value({l}, {r}, '{threshold}') = '{result}'")

    if args.interval_symbols:
        l, r = (
            int(args.interval_symbols[0]),
            int(args.interval_symbols[1]),
        )
        result = interval_symbols(wt, l, r)
        print(f"interval_symbols({l}, {r}) = {result}")

    if args.count_distinct:
        l, r = (
            int(args.count_distinct[0]),
            int(args.count_distinct[1]),
        )
        result = count_distinct(wt, l, r)
        print(f"count_distinct({l}, {r}) = {result}")

    if args.prefix_search:
        result = prefix_search(wt, args.prefix_search)
        print(f"prefix_search('{args.prefix_search}') = {result}")

    if args.alphabet:
        print(f"Alphabet: {wt.alphabet}")


def cmd_build(args):
    """Build a wavelet tree from a sequence and run queries."""
    logger = get_logger()
    config = Config.from_file(args.config) if args.config else Config()

    # Override config with command-line flags
    if args.structure:
        config.structure = args.structure
    config.validate()

    logger.info(f"Building {config.structure} over sequence of length {len(args.sequence)}")
    wt = _build_structure(args.sequence, config.structure, config.use_blocked)

    if args.save:
        save(wt, args.save)
        logger.info(f"Saved to {args.save}")
        print(f"Saved to {args.save}")

    _run_queries(wt, args)

    if not any(
        [
            args.rank, args.select, args.access, args.quantile,
            args.range_count, args.range_next, args.range_prev,
            args.range_min, args.range_max, args.interval_symbols,
            args.count_distinct, args.prefix_search, args.alphabet,
            args.save,
        ]
    ):
        print(f"Built {type(wt).__name__} over sequence '{args.sequence}'")
        print(f"  Length: {len(wt)}")
        print(f"  Alphabet: {wt.alphabet}")


def cmd_load(args):
    """Load a wavelet tree from a file and run queries."""
    logger = get_logger()
    logger.info(f"Loading from {args.file}")
    wt = load(args.file)
    _run_queries(wt, args)


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
    print("            range_min, range_max, range_next_value, range_prev_value,")
    print("            interval_symbols, range_intersection, prefix_search,")
    print("            count_distinct")


def cmd_config(args):
    """Manage configuration files."""
    if args.action == "show":
        config = Config.from_file(args.file) if args.file else Config()
        print(json.dumps(config.to_dict(), indent=2))
    elif args.action == "create":
        config = Config()
        if args.structure:
            config.structure = args.structure
        if args.log_level:
            config.log_level = args.log_level
        config.validate()
        config.save(args.output)
        print(f"Config saved to {args.output}")


def _add_query_args(parser):
    """Add common query arguments to a subparser."""
    parser.add_argument("--rank", nargs=2, metavar=("SYMBOL", "N"), help="Compute rank(SYMBOL, N)")
    parser.add_argument("--select", nargs=2, metavar=("SYMBOL", "K"), help="Compute select(SYMBOL, K)")
    parser.add_argument("--access", metavar="I", help="Compute access(I)")
    parser.add_argument("--quantile", nargs=3, metavar=("L", "R", "K"), help="Range quantile [L,R) k-th smallest")
    parser.add_argument("--range-count", nargs=3, metavar=("SYMBOL", "L", "R"), help="Count SYMBOL in [L,R)")
    parser.add_argument("--range-min", nargs=2, metavar=("L", "R"), help="Minimum symbol in [L,R)")
    parser.add_argument("--range-max", nargs=2, metavar=("L", "R"), help="Maximum symbol in [L,R)")
    parser.add_argument("--range-next", nargs=3, metavar=("L", "R", "THRESHOLD"), help="Smallest symbol >= THRESHOLD in [L,R)")
    parser.add_argument("--range-prev", nargs=3, metavar=("L", "R", "THRESHOLD"), help="Largest symbol <= THRESHOLD in [L,R)")
    parser.add_argument("--interval-symbols", nargs=2, metavar=("L", "R"), help="Distinct symbols in [L,R)")
    parser.add_argument("--count-distinct", nargs=2, metavar=("L", "R"), help="Count distinct symbols in [L,R)")
    parser.add_argument("--prefix-search", metavar="PREFIX", help="Find all positions matching PREFIX")
    parser.add_argument("--alphabet", action="store_true", help="Print the alphabet")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="wavelet_tree",
        description="Wavelet tree succinct data structure library",
    )
    parser.add_argument("--version", action="version", version=f"wavelet_tree {__version__}")
    parser.add_argument("--log-level", default="WARNING", help="Logging level")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # build
    p_build = subparsers.add_parser("build", help="Build a wavelet tree from a sequence")
    p_build.add_argument("sequence", help="The input sequence (string)")
    p_build.add_argument(
        "--structure",
        choices=["tree", "matrix", "huffman-tree", "huffman-matrix"],
        default=None,
        help="Structure type (overrides config)",
    )
    p_build.add_argument("--config", metavar="FILE", help="Load configuration from file")
    p_build.add_argument("--save", metavar="FILE", help="Save to JSON file")
    _add_query_args(p_build)
    p_build.set_defaults(func=cmd_build)

    # load
    p_load = subparsers.add_parser("load", help="Load a wavelet tree from a JSON file")
    p_load.add_argument("file", help="JSON file path")
    _add_query_args(p_load)
    p_load.set_defaults(func=cmd_load)

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare structures on a sequence")
    p_compare.add_argument("sequence", help="The input sequence")
    p_compare.set_defaults(func=cmd_compare)

    # info
    p_info = subparsers.add_parser("info", help="Show library information")
    p_info.set_defaults(func=cmd_info)

    # config
    p_config = subparsers.add_parser("config", help="Manage configuration files")
    p_config.add_argument("action", choices=["show", "create"], help="Config action")
    p_config.add_argument("--file", metavar="FILE", help="Config file to show")
    p_config.add_argument("--output", metavar="FILE", help="Output path for create")
    p_config.add_argument("--structure", choices=["tree", "matrix", "huffman-tree", "huffman-matrix"], help="Structure type")
    p_config.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    p_config.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Set up logging
    log_level = getattr(args, "log_level", None) or "WARNING"
    setup_logging(level=log_level)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())