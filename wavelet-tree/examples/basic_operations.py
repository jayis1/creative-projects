"""Example: Basic wavelet tree operations on a string."""

from wavelet_tree import WaveletTree, WaveletMatrix
from wavelet_tree.queries import (
    range_quantile,
    range_count,
    interval_symbols,
    range_min,
    range_max,
    count_distinct,
)

seq = "abracadabra"
print(f"Sequence: {seq}")
print(f"Length: {len(seq)}")
print()

# Build both structures
wt = WaveletTree(seq)
wm = WaveletMatrix(seq)

print("=== Access ===")
for i in range(len(seq)):
    assert wt.access(i) == seq[i], f"WT access mismatch at {i}"
    assert wm.access(i) == seq[i], f"WM access mismatch at {i}"
    print(f"  access({i}) = '{wt.access(i)}'")

print()
print("=== Rank ===")
for c in wt.alphabet:
    r = wt.rank(c, len(seq))
    expected = seq.count(c)
    assert r == expected, f"WT rank mismatch for '{c}': {r} != {expected}"
    print(f"  rank('{c}', {len(seq)}) = {r}")

print()
print("=== Select ===")
for c in wt.alphabet:
    count = wt.rank(c, len(seq))
    for k in range(count):
        pos = wt.select(c, k)
    if count > 0:
        print(f"  select('{c}', 0) = {wt.select(c, 0)}")

print()
print("=== Range Queries ===")
print(f"  range_count('a', 0, 5) = {range_count(wt, 'a', 0, 5)}")
print(f"  range_quantile(0, 11, 0) = '{range_quantile(wt, 0, 11, 0)}'")
print(f"  range_quantile(0, 11, 10) = '{range_quantile(wt, 0, 11, 10)}'")
print(f"  range_min(0, 11) = '{range_min(wt, 0, 11)}'")
print(f"  range_max(0, 11) = '{range_max(wt, 0, 11)}'")
print(f"  interval_symbols(0, 11) = {interval_symbols(wt, 0, 11)}")
print(f"  count_distinct(0, 11) = {count_distinct(wt, 0, 11)}")

print()
print("All checks passed!")