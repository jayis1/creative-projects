#!/usr/bin/env python3
"""Comprehensive CLI for the probabilistic-ds toolkit.

Subcommands:
    demo        — Run interactive demos (from demo.py)
    bench       — Run benchmarks and print a comparison table
    save        — Serialize a structure to a file
    load        — Load and query a serialized structure
    config      — Build a structure from a config file (JSON/YAML/TOML)
    structures  — List all supported structures
    test        — Run the test suite
"""
import argparse
import json
import os
import sys
import random
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, BlockedBloomFilter, CuckooFilter,
    CountMinSketch, HyperLogLog, KMV, MinHash, ReservoirSampler,
    TopK, TDigest, SkipList, ScalableBloomFilter,
    ConservativeCountMinSketch, serialize, deserialize, run_all_benchmarks,
    load_config, build_from_config, build_from_file, list_structures,
    get_param_spec,
)
from pds.logging_utils import set_level as _set_log_level


def cmd_bench(args):
    """Run all benchmarks."""
    print("Running benchmarks (this may take a moment)...\n")
    results = run_all_benchmarks(seed=args.seed)
    for r in results:
        print(f"  {r['structure']}:")
        for k, v in r.items():
            if k != "structure":
                if isinstance(v, float):
                    print(f"    {k}: {v:.2f}")
                elif isinstance(v, dict):
                    print(f"    {k}:")
                    for qk, qv in v.items():
                        print(f"      {qk}: {qv:.2f}%")
                else:
                    print(f"    {k}: {v}")
        print()


def cmd_save(args):
    """Create a structure, populate it from stdin (one item per line), and save."""
    struct = _build_structure(args)
    for line in sys.stdin:
        item = line.strip()
        if item:
            struct.add(item)
    data = serialize(struct)
    with open(args.output, "w") as f:
        f.write(data)
    print(f"Saved {type(struct).__name__} to {args.output} ({len(data)} bytes)")


def cmd_load(args):
    """Load a serialized structure and query items."""
    with open(args.input, "r") as f:
        struct = deserialize(f.read())
    print(f"Loaded {type(struct).__name__}")
    if args.query:
        for item in args.query:
            if isinstance(struct, (BloomFilter, CountingBloomFilter,
                                   BlockedBloomFilter, CuckooFilter)):
                print(f"  '{item}' in filter: {item in struct}")
            elif isinstance(struct, CountMinSketch):
                print(f"  '{item}' count ≈ {struct.query(item)}")
            elif isinstance(struct, TopK):
                print(f"  '{item}' count = {struct.query(item)}")
            elif isinstance(struct, (KMV, HyperLogLog)):
                print(f"  (cardinality structures don't support per-item query)")
    if args.topk:
        if isinstance(struct, TopK):
            for item, count in struct.topk(args.topk):
                print(f"  {item}: {count}")
    if args.estimate:
        if isinstance(struct, HyperLogLog):
            print(f"  Estimated cardinality: {struct.estimate():.0f}")
        elif isinstance(struct, KMV):
            print(f"  Estimated cardinality: {struct.estimate():.0f}")
    if args.quantile:
        if isinstance(struct, TDigest):
            for q in args.quantile:
                print(f"  q={q}: {struct.quantile(q):.4f}")
    if args.cdf:
        if isinstance(struct, TDigest):
            for v in args.cdf:
                print(f"  cdf({v}): {struct.cdf(v):.4f}")
    if args.jaccard:
        if isinstance(struct, MinHash):
            # Load second MinHash from file
            with open(args.jaccard, "r") as f:
                other = deserialize(f.read())
            print(f"  Jaccard similarity: {struct.jaccard(other):.4f}")
    if args.sample:
        if isinstance(struct, ReservoirSampler):
            items = struct.sample()[:args.sample]
            for item in items:
                print(f"  {item}")


def cmd_config(args):
    """Build a structure from a config file."""
    try:
        struct = build_from_file(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Built {type(struct).__name__} from {args.config}")
    if args.populate:
        for line in sys.stdin:
            item = line.strip()
            if item:
                struct.add(item)
        print(f"  Populated with {len(struct)} items")
    if args.output:
        data = serialize(struct)
        with open(args.output, "w") as f:
            f.write(data)
        print(f"  Saved to {args.output} ({len(data)} bytes)")
    if args.print:
        print(f"  {struct!r}")


def cmd_structures(args):
    """List all supported structures and their parameters."""
    print("Supported structures:\n")
    for name in list_structures():
        params = get_param_spec(name)
        print(f"  {name}: {', '.join(params) if params else '(no params)'}")


def _build_structure(args):
    t = args.type
    if t == "bloom":
        return BloomFilter(args.capacity, args.error)
    if t == "blocked-bloom":
        return BlockedBloomFilter(args.capacity, args.error)
    if t == "counting-bloom":
        return CountingBloomFilter(args.capacity, args.error)
    if t == "cuckoo":
        return CuckooFilter(args.capacity)
    if t == "cms":
        return CountMinSketch(error=args.error, confidence=args.confidence)
    if t == "conservative-cms":
        return ConservativeCountMinSketch(
            error=args.error, confidence=args.confidence)
    if t == "hll":
        return HyperLogLog(precision=args.precision)
    if t == "kmv":
        return KMV(k=args.k)
    if t == "minhash":
        return MinHash(num_perm=args.num_perm)
    if t == "reservoir":
        return ReservoirSampler(k=args.k)
    if t == "topk":
        return TopK(k=args.k)
    if t == "tdigest":
        return TDigest(compression=args.compression)
    raise ValueError(f"Unknown type: {t}")


def main():
    parser = argparse.ArgumentParser(
        description="Probabilistic Data Structures Toolkit CLI v3.0"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bench", help="Run benchmarks")
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("save", help="Build a structure from stdin and save to file")
    p.add_argument("output", help="Output file path")
    p.add_argument("--type", required=True,
                   choices=["bloom", "blocked-bloom", "counting-bloom", "cuckoo",
                            "cms", "conservative-cms", "hll", "kmv", "minhash",
                            "reservoir", "topk", "tdigest"])
    p.add_argument("--capacity", type=int, default=10000)
    p.add_argument("--error", type=float, default=0.01)
    p.add_argument("--confidence", type=float, default=0.99)
    p.add_argument("--precision", type=int, default=14)
    p.add_argument("--k", type=int, default=100)
    p.add_argument("--num-perm", type=int, default=128)
    p.add_argument("--compression", type=float, default=200)
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("load", help="Load and query a serialized structure")
    p.add_argument("input", help="Input file path")
    p.add_argument("--query", nargs="*", help="Items to query")
    p.add_argument("--topk", type=int, nargs="?", const=10, help="Show top-K")
    p.add_argument("--estimate", action="store_true",
                   help="Show cardinality estimate (HLL/KMV)")
    p.add_argument("--quantile", type=float, nargs="*",
                   help="Quantiles to estimate (TDigest)")
    p.add_argument("--cdf", type=float, nargs="*",
                   help="CDF values to estimate (TDigest)")
    p.add_argument("--jaccard", type=str,
                   help="Compute Jaccard with a second MinHash file")
    p.add_argument("--sample", type=int, nargs="?", const=10,
                   help="Show reservoir sample")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("config", help="Build a structure from a config file")
    p.add_argument("config", help="Config file path (JSON/YAML/TOML)")
    p.add_argument("--populate", action="store_true",
                   help="Populate from stdin (one item per line)")
    p.add_argument("--output", type=str, help="Save serialized structure")
    p.add_argument("--print", action="store_true", help="Print repr of structure")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("structures", help="List supported structures")
    p.set_defaults(func=cmd_structures)

    # Global options
    parser.add_argument("--log-level", default="WARNING",
                        help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args, _ = parser.parse_known_args()
    if hasattr(args, "log_level"):
        _set_log_level(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()