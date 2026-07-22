#!/usr/bin/env python3
"""Quick smoke test for new features."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from networkflow import (
    FlowNetwork, Dinic, BoykovKolmogorov, MultiSourceSink,
    CycleCanceling, MinCostMaxFlow,
    to_dot, ascii_graph, flow_decomposition, ascii_flow_paths,
    SolverConfig, load_config, save_config,
    setup_logging, get_logger,
    read_edge_list, write_edge_list, read_adjacency_matrix, write_adjacency_matrix,
    write_graphml, read_graphml,
)
import tempfile, json, os

def clrs():
    net = FlowNetwork(6)
    for u, v, c in [(0,1,16),(0,2,13),(1,2,10),(1,3,12),(2,1,4),(2,4,14),(3,2,9),(3,5,20),(4,3,7),(4,5,4)]:
        net.add_edge(u, v, c)
    return net

# Test BoykovKolmogorov
net = clrs()
bk = BoykovKolmogorov()
flow = bk.solve(net, 0, 5)
print(f"BoykovKolmogorov max flow: {flow} (expected 23)")
assert flow == 23, f"BK failed: {flow}"

# Test on simple path
net2 = FlowNetwork(3)
net2.add_edge(0, 1, 5)
net2.add_edge(1, 2, 3)
bk2 = BoykovKolmogorov()
f2 = bk2.solve(net2, 0, 2)
print(f"BK simple path: {f2} (expected 3)")
assert f2 == 3

# Test MultiSourceSink
mnet = FlowNetwork(5)
mnet.add_edge(0, 2, 10)
mnet.add_edge(1, 2, 5)
mnet.add_edge(2, 3, 8)
mnet.add_edge(2, 4, 7)
ms = MultiSourceSink()
mflow, _ = ms.solve(mnet, sources=[0, 1], sinks=[3, 4])
print(f"Multi-source/sink max flow: {mflow} (expected 15)")
assert mflow == 15, f"Multi flow failed: {mflow}"

# Test CycleCanceling
cnet = FlowNetwork(4)
cnet.add_edge(0, 1, 3, cost=1)
cnet.add_edge(0, 2, 2, cost=2)
cnet.add_edge(1, 3, 2, cost=3)
cnet.add_edge(2, 3, 3, cost=1)
cc = CycleCanceling()
cf, cc_cost = cc.solve(cnet, 0, 3)
print(f"CycleCanceling: flow={cf}, cost={cc_cost} (expected flow=4, cost=14)")
assert cf == 4
assert cc_cost == 14, f"CC cost wrong: {cc_cost}"

# Compare with MinCostMaxFlow
cnet2 = FlowNetwork(4)
cnet2.add_edge(0, 1, 3, cost=1)
cnet2.add_edge(0, 2, 2, cost=2)
cnet2.add_edge(1, 3, 2, cost=3)
cnet2.add_edge(2, 3, 3, cost=1)
mcmf = MinCostMaxFlow()
mf, mc = mcmf.solve(cnet2, 0, 3)
print(f"MinCostMaxFlow: flow={mf}, cost={mc}")
assert mf == cf and mc == cc_cost

# Test flow decomposition
net = clrs()
Dinic().solve(net, 0, 5)
paths = flow_decomposition(net, 0, 5)
print(f"Flow decomposition: {len(paths)} paths")
total = sum(a for _, a in paths)
print(f"  Total: {total} (expected 23)")
assert total == 23

# Test visualization
dot = to_dot(clrs(), source=0, sink=5)
print(f"DOT output: {len(dot)} chars, starts with: {dot[:30]}")
assert dot.startswith("digraph")

ascii_out = ascii_graph(clrs(), source=0, sink=5, show_flows=False)
print(f"ASCII output: {len(ascii_out)} chars")

# Test config
cfg = SolverConfig(algorithm="dinic", source=0, sink=5, network_file="test.json")
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    save_config(cfg, f.name)
    cfg2 = load_config(f.name)
    assert cfg2.algorithm == "dinic"
    assert cfg2.source == 0
    print(f"Config roundtrip OK")
    os.unlink(f.name)

# Test logging
logger = setup_logging("DEBUG")
logger.debug("Debug message works")
logger.info("Info message works")

# Test I/O formats
net = clrs()
with tempfile.NamedTemporaryFile(mode='w', suffix='.edges', delete=False) as f:
    write_edge_list(net, f.name)
    net_el, src, snk = read_edge_list(f.name, source=0, sink=5)
    assert net_el.edge_count() == net.edge_count()
    print(f"Edge list roundtrip OK: {net_el.edge_count()} edges")
    os.unlink(f.name)

with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
    write_adjacency_matrix(net, f.name)
    net_csv, _, _ = read_adjacency_matrix(f.name, source=0, sink=5)
    assert net_csv.edge_count() == net.edge_count()
    print(f"CSV adjacency matrix roundtrip OK")
    os.unlink(f.name)

with tempfile.NamedTemporaryFile(mode='w', suffix='.graphml', delete=False) as f:
    write_graphml(net, f.name, source=0, sink=5)
    net_gml, gsrc, gsnk = read_graphml(f.name)
    assert net_gml.edge_count() == net.edge_count()
    assert gsrc == 0
    assert gsnk == 5
    print(f"GraphML roundtrip OK: {net_gml.edge_count()} edges, source={gsrc}, sink={gsnk}")
    os.unlink(f.name)

print("\n✅ All new feature smoke tests passed!")