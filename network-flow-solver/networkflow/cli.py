"""
Command-line interface for the network-flow-solver toolkit.

Subcommands:
  maxflow      — compute max flow with a choice of algorithm
  mincut       — compute minimum s-t cut
  mincost      — compute min-cost max-flow
  matching     — maximum bipartite matching
  assignment   — minimum-cost assignment (Hungarian algorithm)
  global-cut   — Stoer-Wagner global minimum cut
  connectivity — edge/vertex connectivity, disjoint paths, Gomory-Hu tree
  benchmark    — compare all max-flow solvers on random graphs
  visualize    — generate DOT/ASCII visualization of a network
  multi-flow   — multi-source/multi-sink max flow
  decompose    — decompose flow into paths
  convert      — convert between graph file formats
  config       — run from a config file
  info         — display network info
  demo         — run built-in demos

Networks are loaded from JSON files with the format:
  {"n": <int>, "edges": [{"from": i, "to": j, "cap": c, "cost": k}, ...]}

For matching/assignment, JSON format:
  matching: {"left": L, "right": R, "edges": [[u, v], ...]}
  assignment: {"matrix": [[c00, c01, ...], ...]}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .graph import FlowNetwork
from .maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel, CapacityScaling
from .mincost import MinCostMaxFlow, MinCostFlow
from .matching import BipartiteMatcher, AssignmentSolver
from .mincut import MinCut, StoerWagner
from .connectivity import edge_disjoint_paths, vertex_disjoint_paths, edge_connectivity, GomoryHuTree
from .benchmark import compare_solvers, print_comparison_table, random_network, grid_network, bipartite_network
from .advanced import BoykovKolmogorov, MultiSourceSink, CycleCanceling
from .visualization import to_dot, ascii_graph, flow_decomposition, ascii_flow_paths
from .io_formats import (
    read_edge_list, write_edge_list,
    read_adjacency_matrix, write_adjacency_matrix,
    read_graphml, write_graphml,
    read_lgf,
)
from .config import load_config
from .logging_config import setup_logging


SOLVERS = {
    "ford-fulkerson": FordFulkerson,
    "edmonds-karp": EdmondsKarp,
    "dinic": Dinic,
    "push-relabel": PushRelabel,
    "capacity-scaling": CapacityScaling,
    "boykov-kolmogorov": BoykovKolmogorov,
}


def load_network(path: str) -> FlowNetwork:
    """Load a FlowNetwork from a JSON file or other supported format."""
    # Auto-detect format by extension
    lower = path.lower()
    if lower.endswith(".dimacs") or lower.endswith(".max") or lower.endswith(".txt"):
        from .dimacs import read_dimacs
        net, _, _ = read_dimacs(path)
        return net
    elif lower.endswith(".edges") or lower.endswith(".el"):
        net, _, _ = read_edge_list(path)
        return net
    elif lower.endswith(".csv") or lower.endswith(".tsv"):
        delim = "\t" if lower.endswith(".tsv") else ","
        net, _, _ = read_adjacency_matrix(path, delimiter=delim)
        return net
    elif lower.endswith(".graphml"):
        net, _, _ = read_graphml(path)
        return net
    elif lower.endswith(".lgf"):
        net, _, _ = read_lgf(path)
        return net
    else:
        with open(path) as f:
            data = json.load(f)
        return FlowNetwork.from_dict(data)


def save_network(net: FlowNetwork, path: str) -> None:
    """Save a FlowNetwork to a JSON file."""
    with open(path, "w") as f:
        json.dump(net.to_dict(), f, indent=2)


def cmd_maxflow(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    solver = SOLVERS[args.algorithm]()
    flow = solver.solve(net, args.source, args.sink)
    print(f"Algorithm: {args.algorithm}")
    print(f"Max flow: {flow}")
    print(f"Iterations: {getattr(solver, 'iterations', 'N/A')}")
    if args.output:
        save_network(net, args.output)
        print(f"Network saved to {args.output}")
    if args.show_flows:
        for u in range(net.n):
            for e in net.graph[u]:
                if e.cap > 0:
                    print(f"  {u} -> {e.to}: {e.flow}/{e.cap}")
    if args.validate:
        val = net.validate_flow(args.source, args.sink)
        print(f"Flow validation: OK (value={val})")
    return 0


def cmd_mincut(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    solver = SOLVERS.get(args.algorithm, Dinic)()
    mc = MinCut(solver=solver)
    val = mc.compute(net, args.source, args.sink)
    print(f"Min cut capacity: {val}")
    print(f"Source side: {mc.source_side}")
    print(f"Sink side: {mc.sink_side}")
    print(f"Cut edges:")
    for u, v, c in mc.cut_edges:
        print(f"  {u} -> {v} (cap={c})")
    return 0


def cmd_mincost(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    if args.method == "cycle-canceling":
        solver = CycleCanceling()
        flow, cost = solver.solve(net, args.source, args.sink)
        print(f"Method: cycle-canceling")
        print(f"Max flow: {flow}")
    elif args.target is not None:
        solver = MinCostFlow()
        flow, cost = solver.solve(net, args.source, args.sink, args.target)
        print(f"Flow sent: {flow} / {args.target}")
    else:
        solver = MinCostMaxFlow()
        flow, cost = solver.solve(net, args.source, args.sink)
        print(f"Max flow: {flow}")
    print(f"Total cost: {cost}")
    if args.output:
        save_network(net, args.output)
    return 0


def cmd_matching(args: argparse.Namespace) -> int:
    with open(args.input) as f:
        data = json.load(f)
    matcher = BipartiteMatcher(data["left"], data["right"])
    for u, v in data["edges"]:
        matcher.add_edge(u, v)
    size = matcher.match()
    matching = matcher.get_matching()
    print(f"Max matching size: {size}")
    print(f"Matching: {matching}")
    if args.vertex_cover:
        lc, rc = matcher.minimum_vertex_cover()
        print(f"Min vertex cover (left): {lc}")
        print(f"Min vertex cover (right): {rc}")
    if args.independent_set:
        li, ri = matcher.maximum_independent_set()
        print(f"Max independent set (left): {li}")
        print(f"Max independent set (right): {ri}")
    return 0


def cmd_assignment(args: argparse.Namespace) -> int:
    with open(args.input) as f:
        data = json.load(f)
    matrix = data["matrix"]
    solver = AssignmentSolver()
    cost = solver.solve(matrix)
    print(f"Min assignment cost: {cost}")
    print(f"Assignment: {solver.get_assignment()}")
    if args.maximize:
        max_cost = AssignmentSolver.max_assignment(matrix)
        print(f"Max assignment cost: {max_cost}")
    return 0


def cmd_global_cut(args: argparse.Namespace) -> int:
    with open(args.input) as f:
        data = json.load(f)
    # Build adjacency dict
    node_ids: list[int] = data.get("nodes", [])
    if not node_ids and data["edges"]:
        node_ids = list(range(max(e["from"] for e in data["edges"]) + 1))
    graph: dict[int, list[tuple[int, float]]] = {}
    for node in node_ids:
        graph[node] = []
    for e in data["edges"]:
        u, v, w = e["from"], e["to"], e.get("weight", 1)
        graph.setdefault(u, []).append((v, w))
        graph.setdefault(v, []).append((u, w))
    sw = StoerWagner()
    val = sw.solve(graph)
    print(f"Global min cut: {val}")
    part = sw.get_partition()
    if part:
        print(f"Partition: {sorted(part[0])} | {sorted(part[1])}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    print(f"Nodes: {net.node_count()}")
    print(f"Edges: {net.edge_count()}")
    for u in range(net.n):
        for e in net.graph[u]:
            if e.cap > 0:
                print(f"  {u} -> {e.to}: cap={e.cap}, cost={e.cost}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    print("=== Max Flow Demo (Dinic) ===")
    net = FlowNetwork(6)
    net.add_edge(0, 1, 16)
    net.add_edge(0, 2, 13)
    net.add_edge(1, 2, 10)
    net.add_edge(1, 3, 12)
    net.add_edge(2, 1, 4)
    net.add_edge(2, 4, 14)
    net.add_edge(3, 2, 9)
    net.add_edge(3, 5, 20)
    net.add_edge(4, 3, 7)
    net.add_edge(4, 5, 4)
    flow = Dinic().solve(net, 0, 5)
    print(f"Max flow (0->5): {flow}")  # Classic CLRS example: 23
    assert flow == 23, f"Expected 23, got {flow}"
    print("Passed!\n")

    print("=== Min Cut Demo ===")
    net2 = FlowNetwork(6)
    for u, v, c in [(0,1,16),(0,2,13),(1,2,10),(1,3,12),(2,1,4),(2,4,14),(3,2,9),(3,5,20),(4,3,7),(4,5,4)]:
        net2.add_edge(u, v, c)
    mc = MinCut()
    mc.compute(net2, 0, 5)
    print(f"Min cut capacity: {mc.max_flow}")
    print(f"Cut edges: {mc.cut_edges}\n")

    print("=== Min-Cost Max-Flow Demo ===")
    net3 = FlowNetwork(4)
    net3.add_edge(0, 1, 3, cost=1)
    net3.add_edge(0, 2, 2, cost=2)
    net3.add_edge(1, 3, 2, cost=3)
    net3.add_edge(2, 3, 3, cost=1)
    mcmf = MinCostMaxFlow()
    f, c = mcmf.solve(net3, 0, 3)
    print(f"Flow: {f}, Cost: {c}\n")

    print("=== Bipartite Matching Demo ===")
    matcher = BipartiteMatcher(4, 4)
    for u, v in [(0,0),(0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,3)]:
        matcher.add_edge(u, v)
    size = matcher.match()
    print(f"Matching size: {size}")
    print(f"Matching: {matcher.get_matching()}\n")

    print("=== Assignment Demo ===")
    solver = AssignmentSolver()
    cost_matrix = [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
    cost = solver.solve(cost_matrix)
    print(f"Min cost: {cost}")
    print(f"Assignment: {solver.get_assignment()}")

    print("\n=== Flow Decomposition Demo ===")
    paths = flow_decomposition(net, 0, 5)
    print(ascii_flow_paths(paths))

    print("\n=== Multi-Source/Sink Demo ===")
    mnet = FlowNetwork(5)
    mnet.add_edge(0, 2, 10)
    mnet.add_edge(1, 2, 5)
    mnet.add_edge(2, 3, 8)
    mnet.add_edge(2, 4, 7)
    ms = MultiSourceSink()
    mflow, _ = ms.solve(mnet, sources=[0, 1], sinks=[3, 4])
    print(f"Multi-source/sink max flow: {mflow}")

    print("\n=== Visualization (ASCII) ===")
    print(ascii_graph(net, source=0, sink=5, show_flows=True))

    print("\nAll demos passed!")
    return 0


def cmd_connectivity(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    if args.mode == "edge-disjoint":
        paths = edge_disjoint_paths(net, args.source, args.sink)
        print(f"Max edge-disjoint paths: {len(paths)}")
        for i, p in enumerate(paths):
            print(f"  Path {i}: {p}")
    elif args.mode == "vertex-disjoint":
        paths = vertex_disjoint_paths(net, args.source, args.sink)
        print(f"Max vertex-disjoint paths: {len(paths)}")
        for i, p in enumerate(paths):
            print(f"  Path {i}: {p}")
    elif args.mode == "edge-connectivity":
        ec = edge_connectivity(net)
        print(f"Global edge connectivity: {ec}")
    elif args.mode == "gomory-hu":
        tree = GomoryHuTree(net)
        if args.pair:
            u, v = args.pair
            print(f"Min cut ({u}, {v}): {tree.min_cut(u, v)}")
        else:
            print("Gomory-Hu tree edges (node, parent, capacity):")
            for i in range(1, tree.n):
                print(f"  {i} -- {tree._parent[i]} (cap={tree._capacity[i]})")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    sizes = [int(s) for s in args.sizes.split(",")]
    rows = compare_solvers(sizes, edge_prob=args.edge_prob, seed=args.seed)
    print_comparison_table(rows)
    if args.output:
        with open(args.output, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"Results saved to {args.output}")
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    if args.format == "dot":
        print(to_dot(net, source=args.source, sink=args.sink,
                      show_flows=args.flows, show_residuals=args.residuals))
    elif args.format == "ascii":
        print(ascii_graph(net, source=args.source, sink=args.sink,
                           show_flows=args.flows))
    return 0


def cmd_multi_flow(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    sources = [int(s) for s in args.sources.split(",")]
    sinks = [int(s) for s in args.sinks.split(",")]
    source_caps = [float(c) for c in args.source_caps.split(",")] if args.source_caps else None
    sink_caps = [float(c) for c in args.sink_caps.split(",")] if args.sink_caps else None
    ms = MultiSourceSink()
    flow, _ = ms.solve(net, sources=sources, sinks=sinks,
                       source_caps=source_caps, sink_caps=sink_caps)
    print(f"Multi-source/sink max flow: {flow}")
    return 0


def cmd_decompose(args: argparse.Namespace) -> int:
    net = load_network(args.input)
    # First run max flow
    solver = SOLVERS.get(args.algorithm, Dinic)()
    flow = solver.solve(net, args.source, args.sink)
    print(f"Max flow: {flow}")
    paths = flow_decomposition(net, args.source, args.sink)
    print(ascii_flow_paths(paths))
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """Convert between graph file formats."""
    net = load_network(args.input)
    if args.output_format == "json":
        save_network(net, args.output)
    elif args.output_format == "dimacs":
        from .dimacs import write_dimacs
        write_dimacs(net, 0, net.n - 1, args.output)
    elif args.output_format == "edges":
        write_edge_list(net, args.output)
    elif args.output_format == "csv":
        write_adjacency_matrix(net, args.output)
    elif args.output_format == "graphml":
        write_graphml(net, args.output)
    elif args.output_format == "dot":
        Path(args.output).write_text(to_dot(net))
    else:
        print(f"Unknown output format: {args.output_format}", file=sys.stderr)
        return 1
    print(f"Converted to {args.output_format}: {args.output}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Run from a configuration file."""
    cfg = load_config(args.config_file)
    setup_logging(level=cfg.log_level, log_file=cfg.log_file)

    if cfg.network_file:
        net = load_network(cfg.network_file)
        sink = cfg.sink if cfg.sink >= 0 else net.n - 1

        if cfg.target_flow is not None:
            solver = MinCostFlow()
            flow, cost = solver.solve(net, cfg.source, sink, cfg.target_flow)
            print(f"Flow sent: {flow} / {cfg.target_flow}")
            print(f"Total cost: {cost}")
        else:
            solver = SOLVERS.get(cfg.algorithm, Dinic)()
            flow = solver.solve(net, cfg.source, sink)
            print(f"Algorithm: {cfg.algorithm}")
            print(f"Max flow: {flow}")

        if cfg.output_file:
            save_network(net, cfg.output_file)
            print(f"Saved to {cfg.output_file}")

        if cfg.show_flows:
            for u in range(net.n):
                for e in net.graph[u]:
                    if e.cap > 0:
                        print(f"  {u} -> {e.to}: {e.flow}/{e.cap}")
    else:
        print("No network_file specified in config", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="networkflow",
        description="Network flow solver toolkit: max-flow, min-cut, min-cost flow, "
                    "matching, assignment, visualization, and more.",
        epilog="Use 'networkflow <command> --help' for command-specific options.",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                         help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # maxflow
    p_mf = sub.add_parser("maxflow", help="Compute max flow")
    p_mf.add_argument("input", help="Network file (JSON/DIMACS/edge-list/GraphML)")
    p_mf.add_argument("source", type=int)
    p_mf.add_argument("sink", type=int)
    p_mf.add_argument("-a", "--algorithm", choices=list(SOLVERS), default="dinic")
    p_mf.add_argument("-o", "--output", help="Save updated network to JSON")
    p_mf.add_argument("-f", "--show-flows", action="store_true", help="Print per-edge flows")
    p_mf.add_argument("--validate", action="store_true", help="Validate flow conservation")
    p_mf.set_defaults(func=cmd_maxflow)

    # mincut
    p_mc = sub.add_parser("mincut", help="Compute minimum s-t cut")
    p_mc.add_argument("input", help="Network file")
    p_mc.add_argument("source", type=int)
    p_mc.add_argument("sink", type=int)
    p_mc.add_argument("-a", "--algorithm", choices=list(SOLVERS), default="dinic")
    p_mc.set_defaults(func=cmd_mincut)

    # mincost
    p_cost = sub.add_parser("mincost", help="Min-cost max-flow (or target flow)")
    p_cost.add_argument("input", help="Network file")
    p_cost.add_argument("source", type=int)
    p_cost.add_argument("sink", type=int)
    p_cost.add_argument("--target", type=float, help="Target flow (default: max flow)")
    p_cost.add_argument("--method", choices=["successive-shortest-path", "cycle-canceling"],
                         default="successive-shortest-path")
    p_cost.add_argument("-o", "--output", help="Save updated network to JSON")
    p_cost.set_defaults(func=cmd_mincost)

    # matching
    p_match = sub.add_parser("matching", help="Maximum bipartite matching")
    p_match.add_argument("input", help="JSON file: {left, right, edges}")
    p_match.add_argument("--vertex-cover", action="store_true")
    p_match.add_argument("--independent-set", action="store_true")
    p_match.set_defaults(func=cmd_matching)

    # assignment
    p_asgn = sub.add_parser("assignment", help="Minimum-cost assignment")
    p_asgn.add_argument("input", help="JSON file: {matrix: [[...], ...]}")
    p_asgn.add_argument("--maximize", action="store_true", help="Also show max assignment")
    p_asgn.set_defaults(func=cmd_assignment)

    # global-cut
    p_gc = sub.add_parser("global-cut", help="Global min cut (Stoer-Wagner)")
    p_gc.add_argument("input", help="JSON file: {nodes, edges}")
    p_gc.set_defaults(func=cmd_global_cut)

    # info
    p_info = sub.add_parser("info", help="Display network info")
    p_info.add_argument("input", help="Network file")
    p_info.set_defaults(func=cmd_info)

    # connectivity
    p_conn = sub.add_parser("connectivity", help="Edge/vertex connectivity, disjoint paths, Gomory-Hu tree")
    p_conn.add_argument("input", help="Network file")
    p_conn.add_argument("mode", choices=["edge-disjoint", "vertex-disjoint", "edge-connectivity", "gomory-hu"])
    p_conn.add_argument("--source", type=int, default=0)
    p_conn.add_argument("--sink", type=int, default=-1)
    p_conn.add_argument("--pair", type=int, nargs=2, help="Pair for Gomory-Hu min cut query")
    p_conn.set_defaults(func=cmd_connectivity)

    # benchmark
    p_bench = sub.add_parser("benchmark", help="Compare max-flow solvers on random graphs")
    p_bench.add_argument("sizes", help="Comma-separated node counts, e.g. 10,50,100")
    p_bench.add_argument("--edge-prob", type=float, default=0.3)
    p_bench.add_argument("--seed", type=int, default=42)
    p_bench.add_argument("-o", "--output", help="Save results as JSON")
    p_bench.set_defaults(func=cmd_benchmark)

    # visualize
    p_vis = sub.add_parser("visualize", help="Generate visualization of a network")
    p_vis.add_argument("input", help="Network file")
    p_vis.add_argument("--format", choices=["dot", "ascii"], default="ascii")
    p_vis.add_argument("--source", type=int, default=None)
    p_vis.add_argument("--sink", type=int, default=None)
    p_vis.add_argument("--flows", action="store_true", help="Show flow values")
    p_vis.add_argument("--residuals", action="store_true", help="Show residual edges (DOT only)")
    p_vis.set_defaults(func=cmd_visualize)

    # multi-flow
    p_msf = sub.add_parser("multi-flow", help="Multi-source/multi-sink max flow")
    p_msf.add_argument("input", help="Network file")
    p_msf.add_argument("--sources", required=True, help="Comma-separated source nodes")
    p_msf.add_argument("--sinks", required=True, help="Comma-separated sink nodes")
    p_msf.add_argument("--source-caps", help="Comma-separated source capacities")
    p_msf.add_argument("--sink-caps", help="Comma-separated sink capacities")
    p_msf.set_defaults(func=cmd_multi_flow)

    # decompose
    p_dec = sub.add_parser("decompose", help="Decompose flow into s-t paths")
    p_dec.add_argument("input", help="Network file")
    p_dec.add_argument("source", type=int)
    p_dec.add_argument("sink", type=int)
    p_dec.add_argument("-a", "--algorithm", choices=list(SOLVERS), default="dinic")
    p_dec.set_defaults(func=cmd_decompose)

    # convert
    p_conv = sub.add_parser("convert", help="Convert between graph file formats")
    p_conv.add_argument("input", help="Input network file")
    p_conv.add_argument("output", help="Output file path")
    p_conv.add_argument("--output-format",
                         choices=["json", "dimacs", "edges", "csv", "graphml", "dot"],
                         default="json")
    p_conv.set_defaults(func=cmd_convert)

    # config
    p_cfg = sub.add_parser("config", help="Run from a configuration file")
    p_cfg.add_argument("config_file", help="JSON or YAML config file")
    p_cfg.set_defaults(func=cmd_config)

    # demo
    p_demo = sub.add_parser("demo", help="Run built-in demos")
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    if getattr(args, "verbose", False):
        setup_logging("DEBUG")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())