"""Example: HyperLogLog + Count-Min Sketch for real-time stream analytics.

Demonstrates using HLL for unique visitor counting and CMS for page view
frequency tracking — both on the same event stream, using minimal memory.
"""
import sys
import os
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pds import HyperLogLog, CountMinSketch, TopK

# Simulate a stream of web events: (user_id, page)
random.seed(42)
events = [(f"user-{random.randint(0, 50000)}",
           f"/page-{random.randint(0, 100)}")
          for _ in range(1_000_000)]

# Create structures
hll = HyperLogLog(precision=14)   # ~16KB, ~0.8% error
cms = CountMinSketch(error=0.01, confidence=0.99)  # ~2KB
tk = TopK(k=100)  # track all 100 pages

print("Processing 1M events...")
for user, page in events:
    hll.add(user)
    cms.add(page)
    tk.add(page)

# Report
print(f"\n=== Stream Analytics Report ===")
print(f"Total events:     {len(events):,}")
print(f"Unique visitors:   ~{hll.estimate():,.0f} (exact: {len(set(e[0] for e in events)):,})")
print(f"HLL memory:        {hll.m:,} bytes ({hll.relative_error:.4f} error)")
print(f"\nTop 10 pages:")
for page, count in tk.topk(10):
    print(f"  {page}: ~{count:,} views (CMS estimate: {cms.query(page):,})")

# Verify CMS accuracy
exact_counts = {}
for _, page in events:
    exact_counts[page] = exact_counts.get(page, 0) + 1
errors = [abs(cms.query(p) - exact_counts[p]) for p in exact_counts]
print(f"\nCMS accuracy: avg error = {sum(errors)/len(errors):.1f}, "
      f"max error = {max(errors)}")