"""
Command-line interface for the FM-Index.

Subcommands:
  build     - build an index from a text file and save it
  count     - count occurrences of a pattern
  locate    - print positions of all occurrences of a pattern
  search    - locate with context
  approx    - approximate search with mismatches
  wildcard  - search with single-char wildcards
  extract   - extract a substring by position
  kmers     - list all distinct k-mers with counts
  bench     - benchmark count over many random patterns
  multi     - count multiple patterns
  lcp       - print the LCP array
  longest-repeat - find the longest repeated substring
  info      - print index statistics
  stats     - print detailed text statistics (entropy, Gini, etc.)
  regex     - search with simple regex (supports '.')
  repeats   - find all repeated substrings
  mum       - find maximal unique matches vs a query
  visualize - render ASCII visualizations
  config    - print or generate a configuration file
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
from .wavelet_matrix import WaveletMatrix
from . import serialize
from . import text_stats
from . import searchers
from . import visualize as viz
from . import config as config_mod
from . import errors
from .logging_utils import setup_logging, get_logger


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def cmd_build(args: argparse.Namespace) -> int:
    logger = get_logger()
    # load config if provided
    cfg = None
    if args.config:
        cfg = config_mod.load_config(args.config)
        logger.info("Loaded config from %s", args.config)

    sample_rate = args.sample_rate
    backend = args.backend
    use_naive = args.naive_sa
    if cfg:
        sample_rate = cfg.sample_rate
        backend = cfg.backend
        use_naive = cfg.use_naive_sa

    with open(args.text_file, "r", encoding="utf-8") as f:
        text = f.read()
    # strip a trailing newline so it doesn't become part of the indexed text
    if args.strip_newline and text.endswith("\n"):
        text = text[:-1]
    logger.info("Building index for %d chars, backend=%s, sample_rate=%d",
                len(text), backend, sample_rate)
    t0 = time.perf_counter()
    idx = FMIndex(text, sample_rate=sample_rate, use_naive_sa=use_naive, backend=backend)
    dt = time.perf_counter() - t0

    # save using the appropriate format
    fmt = args.format
    if cfg:
        fmt = cfg.serialization.format
    if fmt == "binary":
        serialize.save_binary(idx, args.output)
    elif fmt == "json":
        serialize.save_json(idx, args.output)
    else:
        with open(args.output, "wb") as f:
            pickle.dump(_serialize_index(idx), f)

    mem_est = idx.estimate_memory_bytes()
    print(f"Built index for {len(text):,} chars in {dt:.3f}s")
    print(f"  alphabet size   : {idx.alphabet_size}")
    print(f"  sample rate     : {sample_rate}")
    print(f"  backend         : {backend}")
    print(f"  BWT length      : {idx.n:,}")
    print(f"  est. memory     : {mem_est:,} bytes ({mem_est / 1024:.1f} KB)")
    print(f"  saved to        : {args.output} ({fmt})")
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
    idx._logger = get_logger()
    idx._backend_name = "wavelet_tree"
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
    idx._sa_inverse = None
    return idx


def _load_index(path: str) -> FMIndex:
    """Load an index from a file, auto-detecting the format.

    Detection order:
      1. Pickle (legacy) — if the file starts with the pickle magic.
      2. Binary (FMDX) — if the file starts with b'FMDX' (after zlib decompress).
      3. JSON — if the file decompresses to a JSON object.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"index file not found: {path}")
    # try pickle first (legacy format)
    try:
        with open(path, "rb") as f:
            head = f.read(2)
        if head[:1] == b'\x80' or head[:2] == b'\x80\x04':
            with open(path, "rb") as f:
                data = pickle.load(f)
            return _deserialize_index(data)
    except (pickle.UnpicklingError, EOFError):
        pass
    # try binary format
    try:
        return serialize.load_binary(path)
    except (ValueError, errors.SerializationError):
        pass
    # try JSON format
    try:
        return serialize.load_json(path)
    except (ValueError, json.JSONDecodeError, KeyError):
        pass
    raise errors.SerializationError(
        f"could not detect index format for {path}"
    )


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
# wildcard
# ---------------------------------------------------------------------------
def cmd_wildcard(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    matches = idx.search_wildcard(args.pattern, wildcard=args.wildcard_char)
    for m in matches:
        print(m.position)
    print(f"# {len(matches)} match(es)")
    return 0


# ---------------------------------------------------------------------------
# multi
# ---------------------------------------------------------------------------
def cmd_multi(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    patterns = args.patterns
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            patterns = [line.rstrip("\n") for line in f if line.strip()]
    results = idx.count_multi(patterns)
    if args.json:
        print(json.dumps(results))
    else:
        for p, c in sorted(results.items()):
            print(f"{c:>6} {p}")
    return 0


# ---------------------------------------------------------------------------
# lcp
# ---------------------------------------------------------------------------
def cmd_lcp(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    lcp = idx.lcp_array()
    sa = idx.suffix_array
    if args.limit:
        rows = list(zip(sa[: args.limit], lcp[: args.limit]))
    else:
        rows = list(zip(sa, lcp))
    for s, l in rows:
        print(f"{l:>6} {s}")
    return 0


# ---------------------------------------------------------------------------
# longest-repeat
# ---------------------------------------------------------------------------
def cmd_longest_repeat(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    res = idx.longest_repeated_substring(min_len=args.min_len)
    if res is None:
        print("# no repeated substring found")
        return 1
    sub, length = res
    print(f"length: {length}")
    print(f"substring: {sub!r}")
    positions = idx.locate(sub)
    print(f"occurrences: {len(positions)}")
    for p in positions[:20]:
        print(f"  {p}")
    return 0


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------
def cmd_info(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    print(f"text length    : {idx._text_len:,}")
    print(f"alphabet size  : {idx.alphabet_size}")
    print(f"alphabet       : {idx.alphabet}")
    print(f"sample rate    : {idx.sample_rate}")
    print(f"backend        : {idx.backend}")
    print(f"BWT length     : {idx.n:,}")
    print(f"sampled SA rows: {len(idx._sa_sampled):,}")
    mem = idx.estimate_memory_bytes()
    print(f"est. memory    : {mem:,} bytes ({mem / 1024:.1f} KB)")
    return 0


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------
def cmd_stats(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    stats = text_stats.compute_statistics(idx)
    print(stats.summary())
    if args.json:
        import dataclasses
        d = dataclasses.asdict(stats)
        # most/least freq are list of tuples -> lists
        d["most_frequent"] = [[c, n] for c, n in stats.most_frequent]
        d["least_frequent"] = [[c, n] for c, n in stats.least_frequent]
        print("---JSON---")
        print(json.dumps(d, indent=2))
    return 0


# ---------------------------------------------------------------------------
# regex
# ---------------------------------------------------------------------------
def cmd_regex(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    matches = searchers.regex_search(idx, args.pattern)
    for m in matches:
        print(m.position)
    print(f"# {len(matches)} match(es)")
    return 0


# ---------------------------------------------------------------------------
# repeats
# ---------------------------------------------------------------------------
def cmd_repeats(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    repeats = searchers.find_all_repeats(idx, min_len=args.min_len, max_len=args.max_len)
    if args.limit:
        repeats = repeats[:args.limit]
    for sub, cnt in repeats:
        print(f"{cnt:>6}  len={len(sub):<4}  {sub!r}")
    print(f"# {len(repeats)} repeated substrings")
    return 0


# ---------------------------------------------------------------------------
# mum
# ---------------------------------------------------------------------------
def cmd_mum(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    mums = searchers.find_maximal_unique_matches(idx, args.query, min_len=args.min_len)
    for text_pos, query_pos, sub in mums:
        print(f"text={text_pos:>6}  query={query_pos:>6}  len={len(sub):<4}  {sub!r}")
    print(f"# {len(mums)} MUM(s)")
    return 0


# ---------------------------------------------------------------------------
# visualize
# ---------------------------------------------------------------------------
def cmd_visualize(args: argparse.Namespace) -> int:
    idx = _load_index(args.index)
    kind = args.kind
    if kind == "bwt":
        print(viz.visualize_bwt_matrix(idx, max_rows=args.rows))
    elif kind == "sa":
        print(viz.visualize_suffix_array(idx, max_entries=args.rows))
    elif kind == "lcp":
        print(viz.visualize_lcp_skyline(idx, width=args.width))
    elif kind == "matches":
        if not args.pattern:
            print("error: --pattern required for 'matches' visualization", file=sys.stderr)
            return 1
        print(viz.visualize_matches(idx, args.pattern, context=args.context))
    elif kind == "coverage":
        if not args.pattern:
            print("error: --pattern required for 'coverage' visualization", file=sys.stderr)
            return 1
        print(viz.visualize_coverage(idx, args.pattern, width=args.width))
    elif kind == "alphabet":
        print(viz.visualize_alphabet_distribution(idx, width=args.width))
    else:
        print(f"unknown visualization kind: {kind}", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
def cmd_config(args: argparse.Namespace) -> int:
    if args.generate:
        cfg = config_mod.FMIndexConfig()
        config_mod.save_config(cfg, args.generate)
        print(f"Default config written to {args.generate}")
        return 0
    if args.show:
        cfg = config_mod.load_config(args.show)
        print(json.dumps(cfg.to_dict(), indent=2))
        return 0
    print("Use --generate <file> or --show <file>")
    return 1


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
    p_build.add_argument("output", help="output index file")
    p_build.add_argument("-s", "--sample-rate", type=int, default=16, help="SA sample rate (default 16)")
    p_build.add_argument("--backend", choices=["wavelet_tree", "wavelet_matrix"], default="wavelet_tree", help="wavelet backend")
    p_build.add_argument("--naive-sa", action="store_true", help="use naive SA construction")
    p_build.add_argument("--format", choices=["binary", "json", "pickle"], default="binary", help="serialization format")
    p_build.add_argument("--config", help="path to YAML/JSON/TOML config file")
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

    # wildcard
    p_wild = sub.add_parser("wildcard", help="Search with single-char wildcards")
    p_wild.add_argument("index", help="index file")
    p_wild.add_argument("pattern", help="pattern (use ? for any char)")
    p_wild.add_argument("-w", "--wildcard-char", default="?", help="wildcard character")
    p_wild.set_defaults(func=cmd_wildcard)

    # multi
    p_multi = sub.add_parser("multi", help="Count multiple patterns at once")
    p_multi.add_argument("index", help="index file")
    p_multi.add_argument("patterns", nargs="*", help="patterns to count")
    p_multi.add_argument("-f", "--file", help="file with one pattern per line")
    p_multi.add_argument("--json", action="store_true")
    p_multi.set_defaults(func=cmd_multi)

    # lcp
    p_lcp = sub.add_parser("lcp", help="Print the LCP array")
    p_lcp.add_argument("index", help="index file")
    p_lcp.add_argument("--limit", type=int, default=0, help="limit rows")
    p_lcp.set_defaults(func=cmd_lcp)

    # longest-repeat
    p_lr = sub.add_parser("longest-repeat", help="Find the longest repeated substring")
    p_lr.add_argument("index", help="index file")
    p_lr.add_argument("--min-len", type=int, default=1, help="minimum length")
    p_lr.set_defaults(func=cmd_longest_repeat)

    # info
    p_info = sub.add_parser("info", help="Print index statistics")
    p_info.add_argument("index", help="index file")
    p_info.set_defaults(func=cmd_info)

    # stats
    p_stats = sub.add_parser("stats", help="Print detailed text statistics")
    p_stats.add_argument("index", help="index file")
    p_stats.add_argument("--json", action="store_true")
    p_stats.set_defaults(func=cmd_stats)

    # regex
    p_regex = sub.add_parser("regex", help="Search with simple regex (supports '.')")
    p_regex.add_argument("index", help="index file")
    p_regex.add_argument("pattern", help="pattern (use . for any char)")
    p_regex.set_defaults(func=cmd_regex)

    # repeats
    p_repeats = sub.add_parser("repeats", help="Find all repeated substrings")
    p_repeats.add_argument("index", help="index file")
    p_repeats.add_argument("--min-len", type=int, default=2, help="minimum repeat length")
    p_repeats.add_argument("--max-len", type=int, default=None, help="maximum repeat length")
    p_repeats.add_argument("--limit", type=int, default=0, help="limit output")
    p_repeats.set_defaults(func=cmd_repeats)

    # mum
    p_mum = sub.add_parser("mum", help="Find maximal unique matches vs a query")
    p_mum.add_argument("index", help="index file")
    p_mum.add_argument("query", help="query string")
    p_mum.add_argument("--min-len", type=int, default=3, help="minimum MUM length")
    p_mum.set_defaults(func=cmd_mum)

    # visualize
    p_viz = sub.add_parser("visualize", help="Render ASCII visualizations")
    p_viz.add_argument("index", help="index file")
    p_viz.add_argument("kind", choices=["bwt", "sa", "lcp", "matches", "coverage", "alphabet"], help="visualization kind")
    p_viz.add_argument("--pattern", help="pattern (for matches/coverage)")
    p_viz.add_argument("--rows", type=int, default=20, help="max rows to show")
    p_viz.add_argument("--width", type=int, default=60, help="bar width")
    p_viz.add_argument("--context", type=int, default=5, help="context chars (for matches)")
    p_viz.set_defaults(func=cmd_visualize)

    # config
    p_config = sub.add_parser("config", help="Generate or show a config file")
    p_config.add_argument("--generate", metavar="FILE", help="write a default config to FILE")
    p_config.add_argument("--show", metavar="FILE", help="print a config file as JSON")
    p_config.set_defaults(func=cmd_config)

    # global options
    parser.add_argument("--log-level", default="WARNING", help="logging level (default WARNING)")
    parser.add_argument("--log-file", default=None, help="log file path")

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # set up logging from global options
    log_level = getattr(args, "log_level", "WARNING")
    log_file = getattr(args, "log_file", None)
    setup_logging(level=log_level, log_file=log_file)
    try:
        return args.func(args)
    except errors.FMIndexError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())