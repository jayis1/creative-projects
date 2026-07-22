#!/usr/bin/env python3
"""
Example 4: Multi-Source/Multi-Sink and Visualization

Shows multi-source/multi-sink max flow and network visualization
(DOT and ASCII output).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow import FlowNetwork, MultiSourceSink, to_dot, ascii_graph

# Build a supply chain network
# Factories (0, 1) → Distribution center (2) → Stores (3, 4)
net = FlowNetwork(5)
net.add_edge(0, 2, 10)  # Factory A → DC (capacity 10)
net.add_edge(1, 2, 5)   # Factory B → DC (capacity 5)
net.add_edge(2, 3, 8)   # DC → Store 1 (capacity 8)
net.add_edge(2, 4, 7)   # DC → Store 2 (capacity 7)

# Multi-source/sink max flow
ms = MultiSourceSink()
flow, _ = ms.solve(net, sources=[0, 1], sinks=[3, 4])
print(f"Multi-source/sink max flow: {flow}")
print(f"  Sources: [0, 1] (factories)")
print(f"  Sinks: [3, 4] (stores)")

# With capacity limits on sources
flow_capped, _ = ms.solve(net, sources=[0, 1], sinks=[3, 4],
                           source_caps=[3, 2])
print(f"\nWith source caps [3, 2]: {flow_capped}")

# === Visualization ===
print("\n=== ASCII Visualization ===")
print(ascii_graph(net, source=0, sink=4, show_flows=False))

print("\n=== DOT Output (first 10 lines) ===")
dot = to_dot(net, source=0, sink=4)
for line in dot.split("\n")[:10]:
    print(line)
print("  ... (use `dot -Tpng` to render full graph)")