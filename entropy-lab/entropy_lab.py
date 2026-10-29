#!/usr/bin/env python3
"""Inspect symbol distributions and estimate source entropy."""
from __future__ import annotations
import argparse
import math
from collections import Counter
from pathlib import Path


def analyze(text: str) -> dict:
    """Return Shannon entropy and symbol frequencies in bits per symbol."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    counts = Counter(text)
    total = len(text)
    entropy = -sum((n / total) * math.log2(n / total) for n in counts.values()) if total else 0.0
    return {"length": total, "distinct": len(counts), "entropy": entropy,
            "frequencies": counts}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="UTF-8 input file (defaults to stdin)")
    parser.add_argument("--top", type=int, default=10, help="number of frequent symbols shown")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be non-negative")
    import sys
    try:
        text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    except (OSError, UnicodeError) as exc:
        parser.error(str(exc))
    result = analyze(text)
    print(f"Symbols: {result['length']}  distinct: {result['distinct']}")
    print(f"Shannon entropy: {result['entropy']:.6f} bits/symbol")
    for char, count in result["frequencies"].most_common(args.top):
        label = repr(char)
        print(f"{label:12} {count:6}  {count / result['length']:.4%}" if result['length'] else f"{label:12} {count:6}  0.0000%")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
