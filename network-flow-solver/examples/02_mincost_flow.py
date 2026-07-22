#!/usr/bin/env python3
"""
Example 2: Min-Cost Flow and Flow Decomposition

Shows how to compute min-cost max-flow and decompose the result
into individual flow paths with their costs.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow import FlowNetwork, MinCostMaxFlow, flow_decomposition, ascii_flow_paths

# Build a transportation network
# Source (0) → two warehouses (1, 2) → two stores (3, 4) → Sink (5)
net = FlowNetwork(6)
net.add_edge(0, 1, 10, cost=0)    # source → warehouse A
net.add_edge(0, 2, 8, cost=0)     # source → warehouse B
net.add_edge(1, 3, 5, cost=3)     # warehouse A → store 1 (cheaper)
net.add_edge(1, 4, 7, cost=5)     # warehouse A → store 2
net.add_edge(2, 3, 6, cost=2)     # warehouse B → store 1 (cheapest)
net.add_edge(2, 4, 4, cost=7)     # warehouse B → store 2
net.add_edge(3, 5, 10, cost=0)    # store 1 → sink
net.add_edge(4, 5, 10, cost=0)    # store 2 → sink

# Compute min-cost max-flow
mcmf = MinCostMaxFlow()
flow, cost = mcmf.solve(net, 0, 5)
print(f"Min-Cost Max-Flow:")
print(f"  Total flow: {flow}")
print(f"  Total cost: {cost}")

# Decompose flow into paths
print(f"\nFlow Decomposition:")
paths = flow_decomposition(net, 0, 5)
print(ascii_flow_paths(paths))

# Show per-edge utilization
print(f"\nPer-edge flow:")
print(f"  {'Edge':>12} {'Flow':>6} {'Cap':>6} {'Cost':>6} {'Total':>6}")
print("  " + "-" * 42)
for u in range(net.n):
    for e in net.graph[u]:
        if e.cap > 0:
            print(f"  {u:>5} → {e.to:<5} {e.flow:>6.0f} {e.cap:>6.0f} "
                  f"{e.cost:>6.0f} {e.flow * e.cost:>6.0f}")