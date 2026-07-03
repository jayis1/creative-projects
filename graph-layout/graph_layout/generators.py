"""Graph generators: common named graphs and random generators."""

from __future__ import annotations

import random
from typing import Optional, List, Tuple

from .graph import Graph


def complete_bipartite(m: int, n: int) -> Graph:
    """Complete bipartite graph K_{m,n}."""
    g = Graph()
    for i in range(m):
        g.add_node(f"L{i}")
    for j in range(n):
        g.add_node(f"R{j}")
    for i in range(m):
        for j in range(n):
            g.add_edge(f"L{i}", f"R{j}")
    return g


def path_graph(n: int) -> Graph:
    """Path graph P_n with n nodes."""
    g = Graph()
    for i in range(n):
        g.add_node(str(i))
        if i > 0:
            g.add_edge(str(i - 1), str(i))
    return g


def star_graph(n: int, center: str = "0") -> Graph:
    """Star graph S_n: center connected to n leaves."""
    g = Graph()
    g.add_node(center)
    for i in range(1, n + 1):
        g.add_edge(center, str(i))
    return g


def cycle_graph(n: int) -> Graph:
    """Cycle graph C_n."""
    g = Graph()
    for i in range(n):
        g.add_edge(str(i), str((i + 1) % n))
    return g


def petersen_graph() -> Graph:
    """The Petersen graph (classic 10-node, 15-edge graph)."""
    g = Graph()
    # outer pentagon 0-4, inner pentagram 5-9, spokes
    for i in range(5):
        g.add_edge(str(i), str((i + 1) % 5))  # outer cycle
        g.add_edge(str(i), str(i + 5))        # spokes
    # inner pentagram: 5-7-9-6-8-5
    inner = [5, 7, 9, 6, 8]
    for i in range(5):
        g.add_edge(str(inner[i]), str(inner[(i + 1) % 5]))
    return g


def hypercube_graph(dim: int) -> Graph:
    """Q_d hypercube graph (2^d nodes)."""
    g = Graph()
    n = 1 << dim
    for i in range(n):
        g.add_node(format(i, f"0{dim}b"))
    for i in range(n):
        for d in range(dim):
            j = i ^ (1 << d)
            if j > i:
                g.add_edge(format(i, f"0{dim}b"),
                           format(j, f"0{dim}b"))
    return g


def erdos_renyi(n: int, p: float, seed: Optional[int] = None) -> Graph:
    """G(n, p) Erdős–Rényi random graph."""
    rng = random.Random(seed)
    g = Graph()
    for i in range(n):
        g.add_node(str(i))
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < p:
                g.add_edge(str(i), str(j))
    return g


def barabasi_albert(n: int, m: int, seed: Optional[int] = None) -> Graph:
    """Barabási–Albert preferential-attachment graph."""
    rng = random.Random(seed)
    g = Graph()
    if n <= 0:
        return g
    m = max(1, min(m, n - 1))
    # start with a small complete graph on m+1 nodes
    for i in range(m + 1):
        g.add_node(str(i))
    for i in range(m + 1):
        for j in range(i + 1, m + 1):
            g.add_edge(str(i), str(j))
    degrees = {str(i): m for i in range(m + 1)}
    for new_node in range(m + 1, n):
        nid = str(new_node)
        g.add_node(nid)
        # Bug fix: use weighted sampling from *available* (not-yet-targeted) nodes
        # to avoid potential infinite loops when the for-loop can't find a new target
        targets: List[str] = []
        available = [k for k in degrees if k not in targets]
        while len(targets) < m and available:
            total_deg = sum(degrees[k] for k in available)
            if total_deg <= 0:
                # fallback: uniform random from available
                targets.append(available.pop(rng.randint(0, len(available) - 1)))
                continue
            r = rng.random() * total_deg
            cum = 0
            chosen = None
            for existing in available:
                cum += degrees[existing]
                if cum >= r:
                    chosen = existing
                    break
            if chosen is None:
                chosen = available[-1]
            targets.append(chosen)
            available.remove(chosen)
        for t in targets:
            g.add_edge(nid, t)
            degrees[t] = degrees.get(t, 0) + 1
        degrees[nid] = m
    return g


def watts_strogatz(n: int, k: int, p: float, seed: Optional[int] = None) -> Graph:
    """Watts–Strogatz small-world graph."""
    rng = random.Random(seed)
    g = Graph()
    for i in range(n):
        g.add_node(str(i))
    # ring lattice
    for i in range(n):
        for j in range(1, k // 2 + 1):
            g.add_edge(str(i), str((i + j) % n))
    # rewire
    edges = list(g.edges)
    for e in edges:
        if rng.random() < p:
            new_target = str(rng.randint(0, n - 1))
            if new_target != e.source and not g.has_edge(e.source, new_target):
                g.remove_edge(e.source, e.target)
                g.add_edge(e.source, new_target)
    return g