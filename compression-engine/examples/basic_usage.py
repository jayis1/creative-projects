#!/usr/bin/env python3
"""Example: Basic compression and decompression.

Demonstrates using each codec individually to compress and
decompress data, then comparing compression ratios.
"""

from compression_engine import (
    HuffmanCodec, LZ77Codec, BWTCodec, DeflateCodec,
    RLECodec, DeltaCodec, LZWCodec, ArithmeticCodec,
)

# Sample data: a paragraph of English text
data = b"""
The compression engine implements multiple algorithms from scratch,
including Huffman coding, LZ77, BWT, DEFLATE, RLE, Delta encoding,
LZW, and Arithmetic coding. Each codec can be used independently
or chained together in a pipeline for better compression ratios.
""".strip() * 20

print(f"Original size: {len(data)} bytes")
print(f"{'Codec':<15} {'Compressed':>12} {'Ratio':>8} {'Saving':>8}")
print("-" * 47)

codecs = [
    ("Huffman", HuffmanCodec()),
    ("LZ77", LZ77Codec()),
    ("BWT", BWTCodec()),
    ("DEFLATE", DeflateCodec()),
    ("RLE", RLECodec()),
    ("Delta", DeltaCodec()),
    ("LZW", LZWCodec()),
    ("Arithmetic", ArithmeticCodec()),
]

for name, codec in codecs:
    compressed = codec.compress(data)
    decompressed = codec.decompress(compressed)
    assert decompressed == data, f"{name} roundtrip failed!"
    ratio = len(compressed) / len(data)
    saving = (1 - ratio) * 100
    print(f"{name:<15} {len(compressed):>10} B {ratio:>7.1%} {saving:>7.1f}%")