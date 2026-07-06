#!/usr/bin/env python3
"""Basic usage example: build an index, search, extract, and serialize."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex, serialize

text = "mississippi"
print(f"Building FM-Index for: {text!r}")
idx = FMIndex(text, sample_rate=2)

print(f"\nIndex: {idx}")
print(f"Alphabet: {idx.alphabet}")
print(f"BWT: {idx.bwt!r}")

# Count
print(f"\ncount('iss') = {idx.count('iss')}")
print(f"count('ss')  = {idx.count('ss')}")
print(f"count('xyz') = {idx.count('xyz')}")

# Locate
print(f"\nlocate('iss') = {idx.locate('iss')}")
print(f"locate('s')  = {idx.locate('s')}")

# Extract
print(f"\nextract(0, 4) = {idx.extract(0, 4)!r}")
print(f"extract(1, 3) = {idx.extract(1, 3)!r}")

# Contains
print(f"\n'iss' in idx  = {'iss' in idx}")
print(f"'xyz' in idx  = {'xyz' in idx}")

# Serialize
serialize.save_binary(idx, "/tmp/mississippi.bin")
idx2 = serialize.load_binary("/tmp/mississippi.bin")
assert idx2.count("iss") == 2
print(f"\nSerialized and reloaded — count('iss') = {idx2.count('iss')}")

# First/last occurrence
print(f"\nfirst('iss') = {idx.first_occurrence('iss')}")
print(f"last('iss')  = {idx.last_occurrence('iss')}")