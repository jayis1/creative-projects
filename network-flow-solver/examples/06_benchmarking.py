#!/usr/bin/env python3
"""
Example 6: Benchmarking and Solver Comparison

Compares all max-flow solvers on random networks of increasing size.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow import compare_solvers, print_comparison_table

print("=== Max-Flow Solver Benchmark ===\n")
print("Comparing Ford-Fulkerson, Edmonds-Karp, Dinic, Push-Relabel")
print("on random networks with edge probability 0.3\n")

# Run benchmark
sizes = [10, 25, 50, 100]
rows = compare_solvers(sizes, edge_prob=0.3, seed=42)
print_comparison_table(rows)

print("\n=== Grid Network Benchmark ===\n")
from networkflow import grid_network, Dinic, PushRelabel, BoykovKolmogorov
import time

print(f"{'Grid':>10} {'Nodes':>7} {'Edges':>7} {'Dinic(ms)':>10} "
      f"{'PR(ms)':>10} {'BK(ms)':>10}")
print("-" * 60)

for rows_g, cols_g in [(5, 5), (10, 10), (15, 15), (20, 20)]:
    net = grid_network(rows_g, cols_g, cap=10)
    n = net.n
    edges = net.edge_count()

    # Dinic
    net_d = net.copy()
    t0 = time.perf_counter()
    Dinic().solve(net_d, 0, n - 1)
    t_d = (time.perf_counter() - t0) * 1000

    # Push-Relabel
    net_p = net.copy()
    t0 = time.perf_counter()
    PushRelabel().solve(net_p, 0, n - 1)
    t_p = (time.perf_counter() - t0) * 1000

    # Boykov-Kolmogorov
    net_b = net.copy()
    t0 = time.perf_counter()
    BoykovKolmogorov().solve(net_b, 0, n - 1)
    t_b = (time.perf_counter() - t0) * 1000

    print(f"{rows_g}x{cols_g:>3} {n:>7} {edges:>7} {t_d:>10.2f} "
          f"{t_p:>10.2f} {t_b:>10.2f}")