#!/usr/bin/env python3
"""Demonstrate the wavelet matrix backend and configuration system."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex, config, serialize
from fmindex.rle import RLEString, rle_encode

text = "the quick brown fox jumps over the lazy dog" * 10

# Build with wavelet matrix backend
print("=== WAVELET MATRIX BACKEND ===")
idx_matrix = FMIndex(text, backend="wavelet_matrix", sample_rate=32)
print(f"Backend: {idx_matrix.backend}")
print(f"count('the') = {idx_matrix.count('the')}")
print(f"locate('fox')[:5] = {idx_matrix.locate('fox')[:5]}")

# Build with wavelet tree backend
print("\n=== WAVELET TREE BACKEND ===")
idx_tree = FMIndex(text, backend="wavelet_tree", sample_rate=32)
print(f"Backend: {idx_tree.backend}")
assert idx_tree.count("the") == idx_matrix.count("the")
assert idx_tree.locate("fox") == idx_matrix.locate("fox")
print("Both backends produce identical results ✓")

# RLE compression of BWT
print("\n=== RLE COMPRESSION ===")
bwt = idx_tree.bwt
runs = rle_encode(bwt)
rle = RLEString(bwt)
print(f"BWT length: {len(bwt)}")
print(f"RLE runs: {rle.num_runs}")
print(f"Compression ratio: {rle.compression_ratio():.2f}x")
print(f"BWT[:40] = {bwt[:40]!r}")

# Configuration
print("\n=== CONFIGURATION ===")
cfg = config.FMIndexConfig(
    sample_rate=64,
    backend="wavelet_matrix",
    serialization=config.SerializationConfig(format="binary"),
)
print(f"Config: {cfg.to_dict()}")
cfg.validate()
print("Config valid ✓")

# Save and load config
config.save_config(cfg, "/tmp/fmindex_config.json")
cfg2 = config.load_config("/tmp/fmindex_config.json")
assert cfg2.sample_rate == 64
assert cfg2.backend == "wavelet_matrix"
print("Config round-trip ✓")