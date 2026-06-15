#!/usr/bin/env python3
"""Example: Pipeline compression — chaining codecs together.

Pipelines apply multiple codecs in sequence for better compression.
For example, RLE + Huffman is excellent for data with many repeated bytes.
"""

from compression_engine import create_pipeline

# Data with long runs (good for RLE pre-processing)
data = b"\x00" * 500 + b"\xFF" * 300 + b"hello world! " * 100

print(f"Original size: {len(data)} bytes")
print(f"{'Pipeline':<20} {'Compressed':>12} {'Ratio':>8}")
print("-" * 44)

pipelines = [
    "rle+huffman",
    "rle+lz77",
    "rle+deflate",
    "rle+lzw",
    "delta+huffman",
    "delta+deflate",
    "bwt+huffman",
    "bwt+deflate",
]

for spec in pipelines:
    pipe = create_pipeline(spec)
    compressed = pipe.compress(data)
    decompressed = pipe.decompress(compressed)
    assert decompressed == data, f"Pipeline {spec} roundtrip failed!"
    ratio = len(compressed) / len(data)
    print(f"{spec:<20} {len(compressed):>10} B {ratio:>7.1%}")

# You can also create pipelines programmatically
from compression_engine import Pipeline

custom_pipe = Pipeline(["rle", "lzw", "huffman"])
compressed = custom_pipe.compress(data)
decompressed = custom_pipe.decompress(compressed)
assert decompressed == data, "Custom pipeline roundtrip failed!"
ratio = len(compressed) / len(data)
print(f"{'rle+lzw+huffman':<20} {len(compressed):>10} B {ratio:>7.1%}")