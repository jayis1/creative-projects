#!/usr/bin/env python3
"""
Example 5: Graph I/O and Format Conversion

Demonstrates reading and writing networks in multiple formats:
JSON, DIMACS, edge list, CSV adjacency matrix, and GraphML.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow import FlowNetwork, write_edge_list, read_edge_list, write_adjacency_matrix, read_adjacency_matrix, write_graphml, read_graphml, to_dot

# Build a network
net = FlowNetwork(5)
net.add_edge(0, 1, 10, cost=2)
net.add_edge(0, 2, 5, cost=5)
net.add_edge(1, 3, 8, cost=1)
net.add_edge(2, 3, 7, cost=3)
net.add_edge(3, 4, 15, cost=0)

print(f"Original network: {net.n} nodes, {net.edge_count()} edges\n")

# Save in different formats
tmpdir = tempfile.mkdtemp()

# 1. Edge list
el_path = os.path.join(tmpdir, "network.edges")
write_edge_list(net, el_path)
print(f"Edge list written to: {el_path}")
with open(el_path) as f:
    print(f"  Contents:\n{''.join('    ' + line for line in f)}")

# Read back
net_el, src, snk = read_edge_list(el_path, source=0, sink=4)
print(f"  Read back: {net_el.n} nodes, {net_el.edge_count()} edges\n")

# 2. CSV adjacency matrix
csv_path = os.path.join(tmpdir, "network.csv")
write_adjacency_matrix(net, csv_path)
print(f"CSV adjacency matrix written to: {csv_path}")
with open(csv_path) as f:
    print(f"  Contents:")
    for line in f:
        print(f"    {line.rstrip()}")

# 3. GraphML
gml_path = os.path.join(tmpdir, "network.graphml")
write_graphml(net, gml_path, source=0, sink=4)
print(f"\nGraphML written to: {gml_path} ({os.path.getsize(gml_path)} bytes)")
net_gml, gsrc, gsnk = read_graphml(gml_path)
print(f"  Read back: {net_gml.n} nodes, {net_gml.edge_count()} edges, source={gsrc}, sink={gsnk}")

# 4. DOT
dot_path = os.path.join(tmpdir, "network.dot")
with open(dot_path, "w") as f:
    f.write(to_dot(net, source=0, sink=4))
print(f"\nDOT written to: {dot_path}")
print("  Render with: dot -Tpng " + dot_path + " -o network.png")

# Cleanup
import shutil
shutil.rmtree(tmpdir)
print("\n✓ All format conversions successful!")