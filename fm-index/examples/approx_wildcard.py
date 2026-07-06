#!/usr/bin/env python3
"""Demonstrate approximate (Hamming-distance) and wildcard search."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex

text = "the quick brown fox jumps over the lazy dog"
print(f"Text: {text!r}")
idx = FMIndex(text)

# Exact search
print("\n--- Exact search ---")
for pat in ["the", "fox", "quick", "xyz"]:
    print(f"  count({pat!r:10}) = {idx.count(pat)}")

# Approximate search with 1 mismatch
print("\n--- Approximate search (1 mismatch) ---")
matches = idx.search_approx("the", max_mismatches=1)
for m in matches:
    print(f"  pos={m.position:>3}  mismatches={m.mismatches}  text[{m.position}:{m.position+len(m.pattern)}]={text[m.position:m.position+len(m.pattern)]!r}")

# Approximate with 2 mismatches
print("\n--- Approximate search (2 mismatches) ---")
matches = idx.search_approx("fox", max_mismatches=2)
for m in matches:
    print(f"  pos={m.position:>3}  mismatches={m.mismatches}")

# Wildcard search
print("\n--- Wildcard search (? = any char) ---")
for pat in ["?he", "f?x", "??e", "dog"]:
    matches = idx.search_wildcard(pat)
    positions = [m.position for m in matches]
    print(f"  {pat!r:6} -> positions {positions}")