# Network Flow Solver

A from-scratch network flow algorithm toolkit implementing maximum flow,
minimum cut, minimum-cost flow, bipartite matching, and assignment problem
solvers — all in pure Python with no external dependencies.

## Features

### Maximum Flow
- **Ford-Fulkerson** — DFS-based augmenting path method (integer capacities)
- **Edmonds-Karp** — BFS-based, O(V·E²) worst case, works with floats
- **Dinic's Algorithm** — level graphs + blocking flow, O(V²·E)
- **Push-Relabel** — FIFO queue with gap heuristic, O(V³)

### Minimum Cut
- **s-t Min Cut** — via max-flow duality (BFS in residual graph)
- **Stoer-Wagner** — global minimum cut for undirected weighted graphs

### Minimum-Cost Flow
- **Min-Cost Max-Flow** — successive shortest paths with SPFA + Johnson's potentials
- **Min-Cost Fixed Flow** — cheapest way to send exactly *k* units
- Handles negative-cost edges via Bellman-Ford initial potentials

### Bipartite Matching
- **Hopcroft-Karp** — maximum cardinality matching, O(E·√V)
- **Kőnig's Theorem** — minimum vertex cover from maximum matching
- **Maximum Independent Set** — complement of minimum vertex cover

### Assignment Problem
- **Hungarian Algorithm (Kuhn-Munkres)** — minimum-cost assignment, O(n³)
- Supports rectangular cost matrices (auto-padded)
- Maximum weight assignment via cost negation

## How It Works

The toolkit is built around the `FlowNetwork` class — a residual graph
representation using adjacency lists of `FlowEdge` objects.  Each edge
maintains a back-reference (`rev`) to its reverse counterpart, enabling O(1)
residual updates during augmentation.

**Max-flow algorithms** find augmenting paths (or push excess flow) through
the residual graph until no more flow can be pushed.  Dinic's algorithm builds
level graphs via BFS and finds blocking flows via DFS, achieving O(V²·E).
Push-Relabel maintains a height function and pushes flow downhill, using the
gap heuristic to skip disconnected levels.

**Min-cost flow** uses the successive shortest paths paradigm: repeatedly
find the shortest (by reduced cost) augmenting path and push flow along it.
Initial node potentials (computed via Bellman-Ford) handle negative-cost
edges.  The SPFA (Shortest Path Faster Algorithm) provides practical
performance improvements over plain Bellman-Ford.

**Bipartite matching** uses Hopcroft-Karp: BFS builds layers of alternating
paths from free vertices, then DFS finds augmenting paths along those layers.
This achieves O(E·√V) versus O(VE) for plain augmenting-path matching.

**Assignment** uses the O(n³) Hungarian algorithm with dual variables
(potentials).  Each iteration relaxes potentials to expose new zero-cost
edges until a perfect matching is found.

## Installation

```bash
cd network-flow-solver
pip install -e .
```

## Usage

### Python API

```python
from networkflow import FlowNetwork, Dinic, MinCut, MinCostMaxFlow

# Max flow — classic CLRS network
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
print(f"Max flow: {flow}")  # 23

# Min cut
net2 = net.copy()
mc = MinCut()
mc.compute(net2, 0, 5)
print(f"Cut edges: {mc.cut_edges}")

# Min-cost max-flow
net3 = FlowNetwork(4)
net3.add_edge(0, 1, 3, cost=1)
net3.add_edge(0, 2, 2, cost=2)
net3.add_edge(1, 3, 2, cost=3)
net3.add_edge(2, 3, 3, cost=1)
mcmf = MinCostMaxFlow()
f, c = mcmf.solve(net3, 0, 3)
print(f"Flow: {f}, Cost: {c}")
```

```python
from networkflow import BipartiteMatcher, AssignmentSolver

# Bipartite matching
matcher = BipartiteMatcher(4, 4)
for u, v in [(0,0),(0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,3)]:
    matcher.add_edge(u, v)
size = matcher.match()
print(f"Matching size: {size}")  # 4
print(f"Matching: {matcher.get_matching()}")

# Assignment
solver = AssignmentSolver()
cost = solver.solve([[4,1,3],[2,0,5],[3,2,2]])
print(f"Min cost: {cost}")  # 5
```

### CLI

```bash
# Max flow
networkflow maxflow network.json 0 5 --algorithm dinic

# Min cut
networkflow mincut network.json 0 5

# Min-cost flow
networkflow mincost network.json 0 5 --target 10

# Bipartite matching
networkflow matching bipartite.json --vertex-cover

# Assignment
networkflow assignment matrix.json

# Run demos
networkflow demo
```

### Network JSON Format

```json
{
  "n": 6,
  "edges": [
    {"from": 0, "to": 1, "cap": 16},
    {"from": 0, "to": 2, "cap": 13},
    {"from": 1, "to": 3, "cap": 12, "cost": 1}
  ]
}
```

### Bipartite Matching JSON Format

```json
{
  "left": 4,
  "right": 4,
  "edges": [[0, 0], [0, 1], [1, 2], [2, 3]]
}
```

### Assignment JSON Format

```json
{
  "matrix": [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
}
```

## Project Structure

```
network-flow-solver/
├── networkflow/
│   ├── __init__.py      # Package exports
│   ├── graph.py         # FlowNetwork, FlowEdge data structures
│   ├── maxflow.py       # FordFulkerson, EdmondsKarp, Dinic, PushRelabel
│   ├── mincost.py       # MinCostMaxFlow, MinCostFlow
│   ├── matching.py      # BipartiteMatcher (Hopcroft-Karp), AssignmentSolver (Hungarian)
│   ├── mincut.py        # MinCut, StoerWagner
│   └── cli.py           # argparse CLI with 8 subcommands
├── tests/
│   └── test_all.py      # Comprehensive test suite
├── pyproject.toml
└── README.md
```

## Algorithms Reference

| Algorithm | Problem | Complexity |
|-----------|---------|------------|
| Ford-Fulkerson | Max flow | O(E·max_flow) |
| Edmonds-Karp | Max flow | O(V·E²) |
| Dinic | Max flow | O(V²·E) |
| Push-Relabel (FIFO) | Max flow | O(V³) |
| Min-cut (duality) | s-t min cut | = max flow |
| Stoer-Wagner | Global min cut | O(V³) |
| Hopcroft-Karp | Bipartite matching | O(E·√V) |
| Hungarian | Assignment | O(n³) |
| SPFA (min-cost) | Min-cost flow | O(F·V·E) |

## License

MIT