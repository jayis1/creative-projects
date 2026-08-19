"""Example: FM-index pattern matching using wavelet trees.

Demonstrates building an FM-index from a text and searching for patterns
using backward search — the core algorithm behind compressed full-text indexes.
"""

from wavelet_tree import FMIndex

text = "abracadabra"
print(f"Text: '{text}'")
print(f"Length: {len(text)}")
print()

# Build FM-index
fm = FMIndex(text)
print(f"FM Index: {fm}")
print()

# Search for various patterns
patterns = ["a", "ab", "abra", "bra", "cad", "ra", "dab", "xyz", "abracadabra"]

print("=== Pattern Search ===")
print(f"{'Pattern':<15} {'Count':>6} {'Positions':>20}")
print("-" * 45)
for p in patterns:
    count = fm.count(p)
    positions = fm.locate(p)
    print(f"{p:<15} {count:>6} {str(positions):>20}")

print()

# Verify against brute force
print("=== Verification ===")
all_ok = True
for p in patterns:
    fm_count = fm.count(p)
    brute_count = sum(1 for i in range(len(text) - len(p) + 1) if text[i:i+len(p)] == p)
    fm_pos = fm.locate(p)
    brute_pos = [i for i in range(len(text) - len(p) + 1) if text[i:i+len(p)] == p]
    ok = fm_count == brute_count and fm_pos == brute_pos
    status = "OK" if ok else "MISMATCH"
    if not ok:
        all_ok = False
    print(f"  '{p}': FM={fm_count}/{fm_pos} brute={brute_count}/{brute_pos} [{status}]")

print()
print(f"All checks passed: {all_ok}")

# Test with different wavelet structures
print()
print("=== Structure Comparison ===")
text2 = "mississippi"
for struct in ["tree", "matrix", "huffman-tree", "huffman-matrix"]:
    fm = FMIndex(text2, structure=struct)
    count = fm.count("issi")
    positions = fm.locate("issi")
    print(f"  {struct:<20} count('issi')={count} positions={positions}")