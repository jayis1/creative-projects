"""Example: Benchmarking and statistics for wavelet tree structures.

Shows space usage, structural metrics, and performance benchmarks
for all four wavelet tree variants.
"""

from wavelet_tree import WaveletTree, WaveletMatrix, HuffmanWaveletTree, HuffmanWaveletMatrix
from wavelet_tree.stats import space_stats, tree_stats, benchmark, benchmark_report

seq = "the quick brown fox jumps over the lazy dog"
print(f"Sequence: '{seq}'")
print(f"Length: {len(seq)}")
print(f"Alphabet size: {len(set(seq))}")
print()

# Build all structures
structures = {
    "WaveletTree": WaveletTree(seq),
    "WaveletMatrix": WaveletMatrix(seq),
    "HuffmanWaveletTree": HuffmanWaveletTree(seq),
    "HuffmanWaveletMatrix": HuffmanWaveletMatrix(seq),
}

# Space statistics
print("=== Space Statistics ===")
print(f"{'Structure':<25} {'Bits':>8} {'Bytes':>6} {'Bits/Sym':>10} {'H0':>8}")
print("-" * 65)
for name, wt in structures.items():
    ss = space_stats(wt)
    print(f"{name:<25} {ss.total_bits:>8} {ss.total_bytes:>6} "
          f"{ss.bits_per_symbol:>10.2f} {ss.h0:>8.4f}")

print()

# Structural statistics
print("=== Structural Statistics ===")
for name, wt in structures.items():
    ts = tree_stats(wt)
    print(ts)
    print()

# Benchmark
print("=== Performance Benchmark ===")
results = benchmark(seq, num_rank_queries=500, num_access_queries=500, num_select_queries=500)
print(benchmark_report(results))