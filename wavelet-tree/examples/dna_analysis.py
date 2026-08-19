"""Example: Range queries on a DNA sequence."""

from wavelet_tree import WaveletTree
from wavelet_tree.queries import (
    range_quantile,
    range_count,
    interval_symbols,
    range_min,
    range_max,
    range_next_value,
    range_prev_value,
    count_distinct,
    prefix_search,
)

# A DNA sequence
dna = "ATCGATCGATCGGCTAGCTAGCTAGCATCGATCG"
print(f"DNA sequence: {dna}")
print(f"Length: {len(dna)}")
print()

wt = WaveletTree(dna)

# Count each nucleotide in the full sequence
print("=== Nucleotide counts ===")
for base in "ACGT":
    print(f"  {base}: {wt.rank(base, len(dna))}")

print()

# Range analysis: first half vs second half
mid = len(dna) // 2
print(f"=== First half [0, {mid}) vs Second half [{mid}, {len(dna)}) ===")
first = interval_symbols(wt, 0, mid)
second = interval_symbols(wt, mid, len(dna))
print(f"  First half:  {first}")
print(f"  Second half: {second}")

print()

# Find the k-th smallest in a range
print("=== Range quantile ===")
for k in [0, 5, 10, 15]:
    if k < len(dna):
        result = range_quantile(wt, 0, len(dna), k)
        print(f"  {k}-th smallest in full sequence: '{result}'")

print()

# Find GC content in a sliding window
print("=== GC content in windows of 10 ===")
window = 10
for i in range(0, len(dna) - window + 1, 5):
    gc = range_count(wt, "G", i, i + window) + range_count(wt, "C", i + window, i + window)
    gc = range_count(wt, "G", i, i + window) + range_count(wt, "C", i, i + window)
    total = window
    print(f"  [{i}, {i+window}): GC={gc}/{total} ({100*gc/total:.0f}%)")

print()

# Find distinct symbols in a range
print("=== Distinct symbols ===")
for r in [(0, 10), (10, 20), (0, len(dna))]:
    d = count_distinct(wt, r[0], r[1])
    print(f"  count_distinct({r[0]}, {r[1]}) = {d}")

print()

# Prefix search
print("=== Prefix search ===")
# Find all positions where "ATCG" appears
positions = prefix_search(wt, "ATCG")
print(f"  'ATCG' found at positions: {positions}")