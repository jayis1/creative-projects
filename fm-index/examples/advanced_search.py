#!/usr/bin/env python3
"""Demonstrate advanced search: regex, repeats, MUMs, and minimal unique substrings."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex, searchers

text = "abracadabra abracadabra"
print(f"Text: {text!r}")
idx = FMIndex(text)

# Regex search
print("\n=== REGEX SEARCH (.) ===")
for pat in [".bra", "a.a.a", "ab.a"]:
    matches = searchers.regex_search(idx, pat)
    positions = sorted(m.position for m in matches)
    print(f"  {pat!r:8} -> {positions}")

# Find all repeats
print("\n=== REPEATED SUBSTRINGS (min_len=3) ===")
repeats = searchers.find_all_repeats(idx, min_len=3, max_len=10)
for sub, cnt in repeats[:10]:
    print(f"  {cnt}x  {sub!r}")

# Top k-mers
print("\n=== TOP 3-MERS ===")
for kmer, count in searchers.top_k_frequent_kmers(idx, 3, 5):
    print(f"  {count:>3}  {kmer!r}")

# Minimal unique substrings
print("\n=== MINIMAL UNIQUE SUBSTRINGS (first 5) ===")
mus = searchers.find_minimal_unique_substrings(idx, min_len=1, max_len=10)
for pos, (sub, length) in list(mus.items())[:5]:
    print(f"  pos={pos:>3}  {sub!r} (len={length})")

# MUMs
print("\n=== MAXIMAL UNIQUE MATCHES ===")
query = "cadabra"
mums = searchers.find_maximal_unique_matches(idx, query, min_len=3)
for text_pos, query_pos, sub in mums:
    print(f"  text={text_pos:>3}  query={query_pos:>3}  {sub!r}")