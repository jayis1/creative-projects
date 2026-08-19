"""Example: Comparing all four wavelet tree variants."""

from wavelet_tree import (
    WaveletTree,
    WaveletMatrix,
    HuffmanWaveletTree,
    HuffmanWaveletMatrix,
)

seq = "the quick brown fox jumps over the lazy dog"
print(f"Sequence: '{seq}'")
print(f"Length: {len(seq)}")
print(f"Alphabet: {sorted(set(seq))}")
print()

structures = {
    "WaveletTree": WaveletTree(seq),
    "WaveletMatrix": WaveletMatrix(seq),
    "HuffmanWaveletTree": HuffmanWaveletTree(seq),
    "HuffmanWaveletMatrix": HuffmanWaveletMatrix(seq),
}

# Verify all structures agree on access
print("=== Access verification ===")
all_ok = True
for name, wt in structures.items():
    for i in range(len(seq)):
        if wt.access(i) != seq[i]:
            print(f"  MISMATCH: {name}.access({i}) = '{wt.access(i)}' != '{seq[i]}'")
            all_ok = False
    print(f"  {name}: OK")
print()

# Verify all structures agree on rank
print("=== Rank verification ===")
for c in sorted(set(seq)):
    if c == " ":
        continue
    results = {}
    for name, wt in structures.items():
        results[name] = wt.rank(c, len(seq))
    expected = seq.count(c)
    all_match = all(r == expected for r in results.values())
    status = "OK" if all_match else "MISMATCH"
    print(f"  rank('{c}', {len(seq)}): {results} expected={expected} [{status}]")

print()

# Show Huffman codes
print("=== Huffman Codes ===")
hwt = structures["HuffmanWaveletTree"]
for sym, code in sorted(hwt.codes.items(), key=lambda x: len(x[1])):
    print(f"  '{sym}': {code} (freq={seq.count(sym)})")

print()

# Verify select
print("=== Select verification ===")
for c in sorted(set(seq)):
    count = structures["WaveletTree"].rank(c, len(seq))
    if count == 0:
        continue
    for k in range(min(count, 3)):
        results = {}
        for name, wt in structures.items():
            results[name] = wt.select(c, k)
        expected_pos = [i for i, ch in enumerate(seq) if ch == c][k]
        all_match = all(r == expected_pos for r in results.values())
        status = "OK" if all_match else "MISMATCH"
        print(f"  select('{c}', {k}): {results} expected={expected_pos} [{status}]")