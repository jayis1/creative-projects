"""Example: Bloom filter for URL deduplication.

Demonstrates using a Bloom filter to track which URLs have been visited
in a web crawler, avoiding redundant fetches with minimal memory.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pds import BloomFilter

# Simulate a web crawler's URL set
urls_visited = [
    "https://example.com/page/1",
    "https://example.com/page/2",
    "https://example.com/page/3",
    "https://example.com/about",
    "https://example.com/contact",
]

# Create a Bloom filter sized for 1M URLs at 0.1% FPR
bf = BloomFilter(capacity=1_000_000, error_rate=0.001)
print(f"Bloom filter: {bf.num_bits:,} bits ({bf.num_bits // 8:,} bytes), "
      f"{bf.num_hashes} hash functions")

# Add visited URLs
for url in urls_visited:
    bf.add(url)
print(f"Added {len(urls_visited)} URLs")

# Check membership
test_urls = urls_visited + [
    "https://example.com/page/4",  # not visited
    "https://example.com/blog",     # not visited
]
print("\nMembership test:")
for url in test_urls:
    status = "VISITED" if url in bf else "new"
    print(f"  {url}: {status}")

# Show memory comparison
import sys
exact_set_size = sys.getsizeof(set(urls_visited)) + sum(
    sys.getsizeof(u) for u in urls_visited)
print(f"\nMemory comparison:")
print(f"  Bloom filter: {bf.num_bits // 8:,} bytes (fixed, scales to 1M URLs)")
print(f"  Exact set:    {exact_set_size:,} bytes (scales linearly)")