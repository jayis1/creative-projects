"""
Benchmarking utilities for network flow algorithms.

Provides timing comparisons, random graph generation, and scaling analysis
to evaluate algorithm performance across different problem sizes.
"""

from __future__ import annotations

import random
import time
from typing import Callable

from .graph import FlowNetwork
from .maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel


def random_network(n: int, edge_prob: float = 0.3,
                   min_cap: int = 1, max_cap: int = 100,
                   seed: int | None = None) -> FlowNetwork:
    """Generate a random flow network with *n* nodes.

    Edges are added with probability *edge_prob*, capacities uniform in
    [min_cap, max_cap].  Source is node 0, sink is node n-1.
    """
    if n < 2:
        raise ValueError("Need at least 2 nodes")
    rng = random.Random(seed)
    net = FlowNetwork(n)
    for u in range(n):
        for v in range(n):
            if u != v and rng.random() < edge_prob:
                cap = rng.randint(min_cap, max_cap)
                net.add_edge(u, v, cap)
    # Ensure source has at least one outgoing edge
    if not any(e.cap > 0 for e in net.graph[0]):
        net.add_edge(0, 1 if 1 != 0 else min(2, n - 1), rng.randint(min_cap, max_cap))
    return net


def benchmark_solver(solver_class, sizes: list[int],
                     edge_prob: float = 0.3,
                     seed: int = 42) -> list[dict]:
    """Benchmark a solver across different network sizes.

    Returns a list of dicts with keys: n, edges, flow, time, iterations.
    """
    results = []
    for n in sizes:
        net = random_network(n, edge_prob=edge_prob, seed=seed)
        edge_count = net.edge_count()
        net2 = net.copy()
        t0 = time.perf_counter()
        flow = solver_class().solve(net2, 0, n - 1)
        elapsed = time.perf_counter() - t0
        results.append({
            "n": n,
            "edges": edge_count,
            "flow": flow,
            "time_ms": elapsed * 1000,
            "iterations": getattr(solver_class(), "iterations", "N/A"),
        })
    return results


def compare_solvers(sizes: list[int],
                    edge_prob: float = 0.3,
                    seed: int = 42) -> list[dict]:
    """Compare all max-flow solvers across different sizes.

    Returns rows with: n, edges, solver, flow, time_ms, iterations.
    """
    solvers = {
        "ford-fulkerson": FordFulkerson,
        "edmonds-karp": EdmondsKarp,
        "dinic": Dinic,
        "push-relabel": PushRelabel,
    }
    rows = []
    for n in sizes:
        base_net = random_network(n, edge_prob=edge_prob, seed=seed)
        edge_count = base_net.edge_count()
        for name, cls in solvers.items():
            net = base_net.copy()
            t0 = time.perf_counter()
            flow = cls().solve(net, 0, n - 1)
            elapsed = time.perf_counter() - t0
            rows.append({
                "n": n,
                "edges": edge_count,
                "solver": name,
                "flow": flow,
                "time_ms": elapsed * 1000,
                "iterations": getattr(cls(), "iterations", "N/A"),
            })
    return rows


def print_comparison_table(rows: list[dict]) -> None:
    """Pretty-print benchmark comparison results."""
    print(f"{'N':>6} {'Edges':>7} {'Solver':>16} {'Flow':>8} {'Time(ms)':>10} {'Iters':>8}")
    print("-" * 65)
    for r in rows:
        print(f"{r['n']:>6} {r['edges']:>7} {r['solver']:>16} {r['flow']:>8.0f} "
              f"{r['time_ms']:>10.3f} {str(r.get('iterations', 'N/A')):>8}")


def grid_network(rows: int, cols: int, cap: int = 10) -> FlowNetwork:
    """Create a grid-structured flow network.

    Nodes are arranged in a rows×cols grid, with edges going right and down.
    Source = top-left (0), sink = bottom-right (n-1).
    """
    n = rows * cols
    net = FlowNetwork(n)
    for r in range(rows):
        for c in range(cols):
            u = r * cols + c
            if c + 1 < cols:
                net.add_edge(u, u + 1, cap)
            if r + 1 < rows:
                net.add_edge(u, u + cols, cap)
    return net


def bipartite_network(L: int, R: int, edge_prob: float = 0.5,
                      seed: int | None = None) -> FlowNetwork:
    """Create a flow network for bipartite matching.

    Source → left (cap 1), left → right (cap 1, prob edge_prob), right → sink (cap 1).
    Max flow = maximum matching size.
    """
    rng = random.Random(seed)
    n = 1 + L + R + 1  # source, left, right, sink
    net = FlowNetwork(n)
    src, snk = 0, n - 1
    for i in range(L):
        net.add_edge(src, 1 + i, 1)
    for i in range(L):
        for j in range(R):
            if rng.random() < edge_prob:
                net.add_edge(1 + i, 1 + L + j, 1)
    for j in range(R):
        net.add_edge(1 + L + j, snk, 1)
    return net