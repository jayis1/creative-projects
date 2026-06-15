#!/usr/bin/env python3
"""Example: File compression using the CLI.

Shows how to use the command-line interface for common tasks.
"""

import os
import subprocess
import tempfile

# Create a test file
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
    f.write("Hello, compression engine! " * 1000)
    input_path = f.name

compressed_path = input_path + ".compressed"
decompressed_path = input_path + ".decompressed"

try:
    # Compress
    print("=== Compressing with DEFLATE ===")
    result = subprocess.run(
        ["python3", "-m", "compression_engine", "compress",
         input_path, "-o", compressed_path, "-c", "deflate", "-v"],
        capture_output=True, text=True,
    )
    print(result.stderr)

    # Decompress
    print("=== Decompressing ===")
    result = subprocess.run(
        ["python3", "-m", "compression_engine", "decompress",
         compressed_path, "-o", decompressed_path, "-c", "deflate", "-v"],
        capture_output=True, text=True,
    )
    print(result.stderr)

    # Verify
    with open(input_path, "rb") as f:
        original = f.read()
    with open(decompressed_path, "rb") as f:
        restored = f.read()
    print(f"\nRoundtrip OK: {original == restored}")

    # Analyze
    print("\n=== Analyzing ===")
    result = subprocess.run(
        ["python3", "-m", "compression_engine", "analyze", input_path],
        capture_output=True, text=True,
    )
    print(result.stdout)

    # Benchmark
    print("\n=== Benchmarking ===")
    result = subprocess.run(
        ["python3", "-m", "compression_engine", "benchmark", input_path],
        capture_output=True, text=True,
    )
    print(result.stdout)

finally:
    # Clean up
    for path in [input_path, compressed_path, decompressed_path]:
        if os.path.exists(path):
            os.unlink(path)