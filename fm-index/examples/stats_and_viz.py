#!/usr/bin/env python3
"""Demonstrate text statistics, visualization, and analysis features."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex, text_stats, analysis, visualize

# A more interesting text
text = """the quick brown fox jumps over the lazy dog.
the dog was not amused. the fox ran away quickly.
brown is the color of the dog and the fox."""

idx = FMIndex(text)
print(f"Text length: {len(text)} chars")
print(f"Alphabet size: {idx.alphabet_size}")

# Text statistics
print("\n=== TEXT STATISTICS ===")
stats = text_stats.compute_statistics(idx)
print(stats.summary())

# Visualize BWT matrix (first 5 rows)
print("\n=== BWT MATRIX (first 5 rows) ===")
print(visualize.visualize_bwt_matrix(idx, max_rows=5))

# Visualize alphabet distribution
print("\n=== ALPHABET DISTRIBUTION ===")
print(visualize.visualize_alphabet_distribution(idx, width=40))

# Match visualization
print("\n=== MATCH VISUALIZATION ('the') ===")
print(visualize.visualize_matches(idx, "the", context=10))

# Coverage
print("\n=== COVERAGE ('the') ===")
print(visualize.visualize_coverage(idx, "the", width=50))

# LCP skyline
print("\n=== LCP SKYLINE ===")
print(visualize.visualize_lcp_skyline(idx, width=40))

# Match analysis
print("\n=== MATCH ANALYSIS ===")
positions = idx.locate("the")
cov = analysis.coverage_stats(positions, 3, len(text))
print(f"Coverage stats: {cov}")
clusters = analysis.cluster_matches(positions, gap=5)
print(f"Clusters: {len(clusters)}")
for c in clusters:
    print(f"  cluster at [{c.start}, {c.end}) — {c.size} match(es)")