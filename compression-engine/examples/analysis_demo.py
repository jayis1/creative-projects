#!/usr/bin/env python3
"""Example: Compression analysis and benchmarking.

Analyze data characteristics and benchmark different codecs.
"""

from compression_engine import (
    shannon_entropy, analyze, DeflateCodec, HuffmanCodec, LZWCodec,
)
from compression_engine.benchmark import run_benchmark

# Create different types of test data
datasets = {
    "English text": b"The quick brown fox jumps over the lazy dog. " * 200,
    "Repetitive": b"\x00" * 3000 + b"\xFF" * 2000,
    "Near-random": bytes((i * 7 + 13) % 256 for i in range(5000)),
    "Sorted integers": b"".join(i.to_bytes(4, "little") for i in range(1250)),
}

for name, data in datasets.items():
    print(f"\n{'='*60}")
    print(f"Dataset: {name} ({len(data)} bytes)")
    print(f"{'='*60}")

    # Analysis
    result = analyze(data)
    print(f"  Unique bytes:    {result['unique_bytes']}/256")
    print(f"  Shannon entropy: {result['entropy_bits']:.2f} bits/symbol")
    print(f"  Compressibility: {result['compressibility']:.1%}")
    print(f"  Optimal ratio:   {result['optimal_ratio']:.1%}")

    # Benchmark
    report = run_benchmark(data, include_pipelines=False)
    print()
    print(report.to_table())