#!/usr/bin/env python3
"""Comprehensive CLI for the probabilistic-ds toolkit.

Subcommands:
    demo        — Run interactive demos (from demo.py)
    bench       — Run benchmarks and print a comparison table
    save        — Serialize a structure to a file
    load        — Load and query a serialized structure
    test        — Run the test suite
"""
import argparse
import json
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, CuckooFilter, CountMinSketch,
    HyperLogLog, TopK, TDigest, SkipList, ScalableBloomFilter,
    ConservativeCountMinSketch, serialize, deserialize, run_all_benchmarks,
)


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
            if isinstance(struct, (BloomFilter, CountingBloomFilter, CuckooFilter)):
                print(f"  '{item}' in filter: {item in struct}")
            elif isinstance(struct, CountMinSketch):
                print(f"  '{item}' count ≈ {struct.query(item)}")
            elif isinstance(struct, TopK):
                print(f"  '{item}' count = {struct.query(item)}")
    if args.topk:
        if isinstance(struct, TopK):
            for item, count in struct.topk(args.topk):
                print(f"  {item}: {count}")
    if args.estimate:
        if isinstance(struct, HyperLogLog):
            print(f"  Estimated cardinality: {struct.estimate():.0f}")
    if args.quantile:
        if isinstance(struct, TDigest):
            for q in args.quantile:
                print(f"  q={q}: {struct.quantile(q):.4f}")


def _build_structure(args):
    t = args.type
    if t == "bloom":
        return BloomFilter(args.capacity, args.error)
    if t == "counting-bloom":
        return CountingBloomFilter(args.capacity, args.error)
    if t == "cuckoo":
        return CuckooFilter(args.capacity)
    if t == "cms":
        return CountMinSketch(error=args.error, confidence=args.confidence)
    if t == "conservative-cms":
        return ConservativeCountMinSketch(error=args.error, confidence=args.confidence)
    if t == "hll":
        return HyperLogLog(precision=args.precision)
    if t == "topk":
        return TopK(k=args.k)
    if t == "tdigest":
        return TDigest(compression=args.compression)
    raise ValueError(f"Unknown type: {t}")


def main():
    parser = argparse.ArgumentParser(
        description="Probabilistic Data Structures Toolkit CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bench", help="Run benchmarks")
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("save", help="Build a structure from stdin and save to file")
    p.add_argument("output", help="Output file path")
    p.add_argument("--type", required=True,
                   choices=["bloom", "counting-bloom", "cuckoo", "cms",
                            "conservative-cms", "hll", "topk", "tdigest"])
    p.add_argument("--capacity", type=int, default=10000)
    p.add_argument("--error", type=float, default=0.01)
    p.add_argument("--confidence", type=float, default=0.99)
    p.add_argument("--precision", type=int, default=14)
    p.add_argument("--k", type=int, default=100)
    p.add_argument("--compression", type=float, default=200)
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("load", help="Load and query a serialized structure")
    p.add_argument("input", help="Input file path")
    p.add_argument("--query", nargs="*", help="Items to query")
    p.add_argument("--topk", type=int, nargs="?", const=10, help="Show top-K")
    p.add_argument("--estimate", action="store_true", help="Show cardinality estimate")
    p.add_argument("--quantile", type=float, nargs="*", help="Quantiles to estimate")
    p.set_defaults(func=cmd_load)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()