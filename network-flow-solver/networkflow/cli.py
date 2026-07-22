"""
Command-line interface for the network-flow-solver toolkit.

Subcommands:
  maxflow      — compute max flow with a choice of algorithm
  mincut       — compute minimum s-t cut
  mincost      — compute min-cost max-flow
  matching     — maximum bipartite matching
  assignment   — minimum-cost assignment (Hungarian algorithm)
  global-cut   — Stoer-Wagner global minimum cut
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
from typing import Any

from .graph import FlowNetwork
from .maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel
from .mincost import MinCostMaxFlow, MinCostFlow
from .matching import BipartiteMatcher, AssignmentSolver
from .mincut import MinCut, StoerWagner


SOLVERS = {
    "ford-fulkerson": FordFulkerson,
    "edmonds-karp": EdmondsKarp,
    "dinic": Dinic,
    "push-relabel": PushRelabel,
}


def load_network(path: str) -> FlowNetwork:
    with open(path) as f:
        data = json.load(f)
    return FlowNetwork.from_dict(data)


def save_network(net: FlowNetwork, path: str) -> None:
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
    if args.target is not None:
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
    print("\nAll demos passed!")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="networkflow",
        description="Network flow solver toolkit: max-flow, min-cut, min-cost flow, matching, assignment",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_mf = sub.add_parser("maxflow", help="Compute max flow")
    p_mf.add_argument("input", help="JSON network file")
    p_mf.add_argument("source", type=int)
    p_mf.add_argument("sink", type=int)
    p_mf.add_argument("-a", "--algorithm", choices=list(SOLVERS), default="dinic")
    p_mf.add_argument("-o", "--output", help="Save updated network to JSON")
    p_mf.add_argument("-f", "--show-flows", action="store_true", help="Print per-edge flows")
    p_mf.set_defaults(func=cmd_maxflow)

    p_mc = sub.add_parser("mincut", help="Compute minimum s-t cut")
    p_mc.add_argument("input", help="JSON network file")
    p_mc.add_argument("source", type=int)
    p_mc.add_argument("sink", type=int)
    p_mc.add_argument("-a", "--algorithm", choices=list(SOLVERS), default="dinic")
    p_mc.set_defaults(func=cmd_mincut)

    p_cost = sub.add_parser("mincost", help="Min-cost max-flow (or target flow)")
    p_cost.add_argument("input", help="JSON network file")
    p_cost.add_argument("source", type=int)
    p_cost.add_argument("sink", type=int)
    p_cost.add_argument("--target", type=float, help="Target flow (default: max flow)")
    p_cost.add_argument("-o", "--output", help="Save updated network to JSON")
    p_cost.set_defaults(func=cmd_mincost)

    p_match = sub.add_parser("matching", help="Maximum bipartite matching")
    p_match.add_argument("input", help="JSON file: {left, right, edges}")
    p_match.add_argument("--vertex-cover", action="store_true")
    p_match.add_argument("--independent-set", action="store_true")
    p_match.set_defaults(func=cmd_matching)

    p_asgn = sub.add_parser("assignment", help="Minimum-cost assignment")
    p_asgn.add_argument("input", help="JSON file: {matrix: [[...], ...]}")
    p_asgn.set_defaults(func=cmd_assignment)

    p_gc = sub.add_parser("global-cut", help="Global min cut (Stoer-Wagner)")
    p_gc.add_argument("input", help="JSON file: {nodes, edges}")
    p_gc.set_defaults(func=cmd_global_cut)

    p_info = sub.add_parser("info", help="Display network info")
    p_info.add_argument("input", help="JSON network file")
    p_info.set_defaults(func=cmd_info)

    p_demo = sub.add_parser("demo", help="Run built-in demos")
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())