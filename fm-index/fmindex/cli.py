"""
Command-line interface for the FM-Index.

Subcommands:
  build   - build an index from a text file and save it
  count   - count occurrences of a pattern
  locate  - print positions of all occurrences of a pattern
  search  - locate with context
  approx  - approximate search with mismatches
  extract - extract a substring by position
  kmers   - list all distinct k-mers with counts
  bench   - benchmark count over many random patterns
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import random
import sys
import time
from typing import List

from .index import FMIndex, FMIndexMatch
from .bwt import bwt_encode, bwt_decode
from .wavelet import WaveletTree


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def cmd_build(args: argparse.Namespace) -> int:
    with open(args.text_file, "r", encoding="utf-8") as f:
        text = f.read()
    # strip a trailing newline so it doesn't become part of the indexed text
    if args.strip_newline and text.endswith("\n"):
        text = text[:-1]
    t0 = time.perf_counter()
    idx = FMIndex(text, sample_rate=args.sample_rate)
    dt = time.perf_counter() - t0
    with open(args.output, "wb") as f:
        pickle.dump(_serialize_index(idx), f)
    print(f"Built index for {len(text):,} chars in {dt:.3f}s")
    print(f"  alphabet size : {idx.alphabet_size}")
    print(f"  sample rate   : {args.sample_rate}")
    print(f"  BWT length    : {idx.n:,}")
    print(f"  saved to       : {args.output}")
    return 0


# ---------------------------------------------------------------------------
# load helper
# ---------------------------------------------------------------------------
def _serialize_index(idx: FMIndex) -> dict:
    return {
        "raw_text": idx._raw_text,
        "sample_rate": idx.sample_rate,
        "sa": idx._sa,
        "bwt": idx._bwt,
    }


def _deserialize_index(data: dict) -> FMIndex:
    idx = FMIndex.__new__(FMIndex)
    idx._raw_text = data["raw_text"]
    idx.sample_rate = data["sample_rate"]
    idx.n = len(idx._raw_text)
    idx._sa = data["sa"]
    idx._bwt = data["bwt"]
    idx._text_len = idx.n - 1
    idx._wt = WaveletTree([ord(c) for c in idx._bwt])
    # rebuild C array
    counts = {}
    for c in idx._raw_text:
        code = ord(c)
        counts[code] = counts.get(code, 0) + 1
    sorted_codes = sorted(counts.keys())
    idx._alphabet = [chr(c) for c in sorted_codes]
    idx._c = {}
    cumulative = 0
    for code in sorted_codes:
        idx._c[code] = cumulative
        cumulative += counts[code]
    idx.alphabet_size = len(sorted_codes)
    idx._sa_sampled = {}
    for i in range(idx.n):
        if idx._sa[i] % idx.sample_rate == 0:
            idx._sa_sampled[i] = idx._sa[i]
    return idx


def _load_index(path: str) -> FMIndex:
    with open(path, "rb") as f:
        data = pickle.load(f)
    return _deserialize_index(data)


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------
def cmd_count(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    t0 = time.perf_counter()
    c = idx.count(args.pattern)
    dt = time.perf_counter() - t0
    print(f"{c}")
    if args.verbose:
        print(f"# {dt*1e6:.1f} µs", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# locate
# ---------------------------------------------------------------------------
def cmd_locate(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    t0 = time.perf_counter()
    positions = idx.locate(args.pattern)
    dt = time.perf_counter() - t0
    if args.json:
        print(json.dumps({"pattern": args.pattern, "count": len(positions), "positions": positions}))
    else:
        print(f"# {len(positions)} match(es)")
        for p in positions:
            print(p)
    if args.verbose:
        print(f"# {dt*1e6:.1f} µs", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# search (locate with context)
# ---------------------------------------------------------------------------
def cmd_search(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    positions = idx.locate(args.pattern)
    text = idx.text
    plen = len(args.pattern)
    for p in positions:
        ctx_start = max(0, p - args.context)
        ctx_end = min(len(text), p + plen + args.context)
        snippet = text[ctx_start:ctx_end]
        marker = " " * (p - ctx_start) + "^" * plen
        print(f"{p:>8}: {snippet}")
        print(f"          {marker}")
    print(f"# {len(positions)} match(es)")
    return 0


# ---------------------------------------------------------------------------
# approx
# ---------------------------------------------------------------------------
def cmd_approx(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    matches = idx.search_approx(args.pattern, max_mismatches=args.mismatches)
    for m in matches:
        print(f"{m.position:>8}  mismatches={m.mismatches}")
    print(f"# {len(matches)} match(es)")
    return 0


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------
def cmd_extract(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    s = idx.extract(args.pos, args.length)
    print(s)
    return 0


# ---------------------------------------------------------------------------
# kmers
# ---------------------------------------------------------------------------
def cmd_kmers(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    kmers = list(idx.iter_kmers(args.k))
    kmers.sort(key=lambda x: (-x[1], x[0]))
    if args.limit:
        kmers = kmers[: args.limit]
    if args.json:
        print(json.dumps([{"kmer": k, "count": c} for k, c in kmers]))
    else:
        for kmer, count in kmers:
            print(f"{count:>6} {kmer}")
    print(f"# {len(kmers)} distinct {args.k}-mers")
    return 0


# ---------------------------------------------------------------------------
# bench
# ---------------------------------------------------------------------------
def cmd_bench(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    text = idx.text
    n = len(text)
    rng = random.Random(args.seed)
    total = 0
    times: List[float] = []
    for _ in range(args.queries):
        k = rng.randint(args.min_k, args.max_k)
        if n - k <= 0:
            continue
        start = rng.randint(0, n - k)
        pat = text[start : start + k]
        t0 = time.perf_counter()
        c = idx.count(pat)
        dt = time.perf_counter() - t0
        times.append(dt)
        total += c
    if times:
        times.sort()
        avg = sum(times) / len(times)
        p50 = times[len(times) // 2]
        p99 = times[int(len(times) * 0.99)]
        print(f"queries: {len(times)}")
        print(f"avg:    {avg*1e6:.1f} µs")
        print(f"p50:    {p50*1e6:.1f} µs")
        print(f"p99:    {p99*1e6:.1f} µs")
        print(f"total matches: {total}")
    else:
        print("no queries (text too short)")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fmindex",
        description="FM-Index compressed full-text index",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Build an index from a text file")
    p_build.add_argument("text_file", help="input text file")
    p_build.add_argument("output", help="output index file (.pkl)")
    p_build.add_argument("-s", "--sample-rate", type=int, default=16, help="SA sample rate (default 16)")
    p_build.add_argument("--strip-newline", action="store_true", default=True, help="strip trailing newline (default)")
    p_build.set_defaults(func=cmd_build)

    # count
    p_count = sub.add_parser("count", help="Count occurrences of a pattern")
    p_count.add_argument("index", help="index file")
    p_count.add_argument("pattern", help="pattern to count")
    p_count.add_argument("-v", "--verbose", action="store_true")
    p_count.set_defaults(func=cmd_count)

    # locate
    p_loc = sub.add_parser("locate", help="Print positions of all occurrences")
    p_loc.add_argument("index", help="index file")
    p_loc.add_argument("pattern", help="pattern to locate")
    p_loc.add_argument("--json", action="store_true")
    p_loc.add_argument("-v", "--verbose", action="store_true")
    p_loc.set_defaults(func=cmd_locate)

    # search
    p_search = sub.add_parser("search", help="Locate with context")
    p_search.add_argument("index", help="index file")
    p_search.add_argument("pattern", help="pattern")
    p_search.add_argument("-c", "--context", type=int, default=10, help="context chars")
    p_search.set_defaults(func=cmd_search)

    # approx
    p_approx = sub.add_parser("approx", help="Approximate search with mismatches")
    p_approx.add_argument("index", help="index file")
    p_approx.add_argument("pattern", help="pattern")
    p_approx.add_argument("-m", "--mismatches", type=int, default=1, help="max mismatches")
    p_approx.set_defaults(func=cmd_approx)

    # extract
    p_ext = sub.add_parser("extract", help="Extract a substring")
    p_ext.add_argument("index", help="index file")
    p_ext.add_argument("pos", type=int, help="start position")
    p_ext.add_argument("length", type=int, help="length")
    p_ext.set_defaults(func=cmd_extract)

    # kmers
    p_kmers = sub.add_parser("kmers", help="List distinct k-mers with counts")
    p_kmers.add_argument("index", help="index file")
    p_kmers.add_argument("k", type=int, help="k-mer length")
    p_kmers.add_argument("--limit", type=int, default=0, help="limit output")
    p_kmers.add_argument("--json", action="store_true")
    p_kmers.set_defaults(func=cmd_kmers)

    # bench
    p_bench = sub.add_parser("bench", help="Benchmark count over random patterns")
    p_bench.add_argument("index", help="index file")
    p_bench.add_argument("-q", "--queries", type=int, default=1000, help="number of queries")
    p_bench.add_argument("--min-k", type=int, default=4, help="min pattern length")
    p_bench.add_argument("--max-k", type=int, default=16, help="max pattern length")
    p_bench.add_argument("--seed", type=int, default=42, help="RNG seed")
    p_bench.set_defaults(func=cmd_bench)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())