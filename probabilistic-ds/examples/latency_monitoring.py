"""Example: T-Digest for real-time latency monitoring.

Demonstrates using T-Digest to track API response time percentiles in
real-time, with minimal memory — no need to store every latency value.
"""
import sys
import os
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pds import TDigest

# Simulate API latency measurements (log-normal distribution)
random.seed(42)
td = TDigest(compression=200)

print("Simulating 100,000 API calls...")
for _ in range(100_000):
    # Most calls are fast (~50-200ms), but some are slow (tails)
    latency = random.lognormvariate(mu=4.5, sigma=0.5)  # ~90ms median
    td.add(latency)

# Report key percentiles
print(f"\n=== API Latency Report ===")
print(f"Total calls:    {td._total_count:,.0f}")
print(f"Centroids:      {td.num_centroids} (vs 100,000 raw values)")
print(f"Min latency:    {td.quantile(0):.1f}ms")
print(f"Max latency:    {td.quantile(1):.1f}ms")
print()

for label, q in [("p50 (median)", 0.50), ("p75", 0.75), ("p90", 0.90),
                  ("p95", 0.95), ("p99", 0.99), ("p99.9", 0.999)]:
    val = td.quantile(q)
    print(f"  {label:15s}: {val:7.1f}ms")

# CDF lookup
print(f"\nCDF (fraction of calls under 200ms): {td.cdf(200):.4f}")
print(f"CDF (fraction of calls under 500ms): {td.cdf(500):.4f}")

# Memory comparison
raw_size = 100_000 * 8  # 8 bytes per float64
td_size = td.num_centroids * 16  # 16 bytes per centroid (mean + count)
print(f"\nMemory: {td_size:,} bytes (T-Digest) vs {raw_size:,} bytes (raw)")
print(f"Compression: {raw_size / td_size:.0f}x")