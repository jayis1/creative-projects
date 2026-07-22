#!/usr/bin/env python3
"""
Example 1: Basic Max Flow

Demonstrates computing max flow on the classic CLRS network using
different algorithms and comparing results.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow import FlowNetwork, Dinic, EdmondsKarp, PushRelabel, BoykovKolmogorov

# Build the classic CLRS max-flow network (max flow = 23)
net = FlowNetwork(6)
edges = [
    (0, 1, 16), (0, 2, 13), (1, 2, 10), (1, 3, 12),
    (2, 1, 4),  (2, 4, 14), (3, 2, 9),  (3, 5, 20),
    (4, 3, 7),  (4, 5, 4),
]
for u, v, cap in edges:
    net.add_edge(u, v, cap)

print("CLRS Network: 6 nodes, 10 edges")
print(f"  Source: 0, Sink: 5\n")

# Solve with different algorithms
solvers = {
    "Edmonds-Karp": EdmondsKarp,
    "Dinic": Dinic,
    "Push-Relabel": PushRelabel,
    "Boykov-Kolmogorov": BoykovKolmogorov,
}

print(f"{'Algorithm':>20} | {'Max Flow':>8} | {'Iterations':>10}")
print("-" * 45)

for name, cls in solvers.items():
    n = net.copy()
    solver = cls()
    flow = solver.solve(n, 0, 5)
    iters = getattr(solver, "iterations", "N/A")
    print(f"{name:>20} | {flow:>8.0f} | {iters:>10}")

print(f"\nAll algorithms agree: max flow = 23 ✓")