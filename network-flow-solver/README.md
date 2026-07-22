# Network Flow Solver

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 85](https://img.shields.io/badge/tests-85%20passed-brightgreen.svg)](https://github.com/jayis1/creative-projects)
[![Pure Python](https://img.shields.io/badge/pure-Python-ff69b4.svg)](https://www.python.org/)

A from-scratch network flow algorithm toolkit implementing maximum flow,
minimum cut, minimum-cost flow, bipartite matching, assignment problems,
connectivity analysis, visualization, and graph I/O — all in pure Python
with zero external dependencies.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Configuration Files](#configuration-files)
  - [Graph I/O Formats](#graph-io-formats)
  - [Visualization](#visualization)
- [Algorithms](#algorithms)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Maximum Flow (6 algorithms)
- **Ford-Fulkerson** — DFS-based augmenting path method (integer capacities)
- **Edmonds-Karp** — BFS-based, O(V·E²) worst case, works with floats
- **Dinic's Algorithm** — level graphs + blocking flow, O(V²·E)
- **Push-Relabel** — FIFO queue with gap heuristic, O(V³)
- **Capacity Scaling** — scaling parameter Δ, O(E² log U) iterations
- **Boykov-Kolmogorov** — dual-tree algorithm, fast on low-connectivity graphs

### Minimum Cut
- **s-t Min Cut** — via max-flow duality (BFS in residual graph)
- **Stoer-Wagner** — global minimum cut for undirected weighted graphs
- **Gomory-Hu Tree** — all-pairs min-cut in n-1 max-flow calls, O(1) queries

### Minimum-Cost Flow
- **Min-Cost Max-Flow** — successive shortest paths with SPFA + Johnson's potentials
- **Min-Cost Fixed Flow** — cheapest way to send exactly *k* units
- **Cycle Canceling** — alternative min-cost flow via negative cycle detection
- Handles negative-cost edges via Bellman-Ford initial potentials

### Multi-Source / Multi-Sink
- **Super-source/sink construction** with individual supply/demand capacities

### Bipartite Matching
- **Hopcroft-Karp** — maximum cardinality matching, O(E·√V)
- **Kőnig's Theorem** — minimum vertex cover from maximum matching
- **Maximum Independent Set** — complement of minimum vertex cover

### Assignment Problem
- **Hungarian Algorithm (Kuhn-Munkres)** — minimum-cost assignment, O(n³)
- Supports rectangular cost matrices (auto-padded)
- Maximum weight assignment via cost negation

### Connectivity Analysis
- **Edge-Disjoint Paths** — max set of edge-disjoint s-t paths via unit max-flow
- **Vertex-Disjoint Paths** — max set of internally vertex-disjoint paths via node-splitting
- **Edge Connectivity** — global minimum cut over all s-t pairs
- **Gomory-Hu Cut Tree** — all-pairs min cut structure with O(1) queries

### Visualization
- **Graphviz DOT output** — color-coded by flow utilization, styled source/sink
- **ASCII table** — compact terminal-friendly edge listing
- **Flow decomposition** — decompose flow into s-t paths with amounts

### Graph I/O
- **JSON** — native format with full flow/cost serialization
- **DIMACS** — standard max-flow/min-cost challenge format
- **Edge list** — whitespace-delimited `u v capacity [cost]`
- **CSV/TSV adjacency matrix** — spreadsheet-compatible
- **GraphML** — interoperable with NetworkX, Gephi, yEd
- **LGF** — LEMON Graph Format
- **Format auto-detection** by file extension in CLI

### Benchmarking & Graph Generation
- **Random networks** — configurable size, edge probability, capacity range
- **Grid networks** — structured grid-structured flow topologies
- **Bipartite networks** — flow formulation for bipartite matching
- **Solver comparison** — benchmark all max-flow solvers side-by-side
- **JSON export** of benchmark results

### Configuration & Logging
- **Config files** — JSON or YAML (with PyYAML)
- **Structured logging** — configurable level, file output, custom format

---

## Installation

```bash
cd network-flow-solver
pip install -e .
```

With optional dependencies:
```bash
pip install -e ".[yaml,dev,viz]"
```

---

## Quick Start

```python
from networkflow import FlowNetwork, Dinic

# Classic CLRS network (max flow = 23)
net = FlowNetwork(6)
net.add_edge(0, 1, 16)
net.add_edge(0, 2, 13)
net.add_edge(1, 3, 12)
net.add_edge(2, 4, 14)
net.add_edge(3, 5, 20)
net.add_edge(4, 5, 4)

flow = Dinic().solve(net, 0, 5)
print(f"Max flow: {flow}")  # 23
```

---

## Usage

### Python API

#### Max Flow

```python
from networkflow import FlowNetwork, Dinic, PushRelabel, BoykovKolmogorov

net = FlowNetwork(6)
net.add_edge(0, 1, 16)
net.add_edge(0, 2, 13)
net.add_edge(1, 3, 12)
net.add_edge(2, 4, 14)
net.add_edge(3, 5, 20)
net.add_edge(4, 5, 4)

# Use any of 6 algorithms
flow = Dinic().solve(net, 0, 5)       # → 23
flow = PushRelabel().solve(net.copy(), 0, 5)  # → 23
flow = BoykovKolmogorov().solve(net.copy(), 0, 5)  # → 23

# Validate flow conservation
val = net.validate_flow(0, 5)  # raises ValueError if violated
```

#### Min Cut

```python
from networkflow import MinCut

net = FlowNetwork(6)
# ... add edges ...
mc = MinCut()
mc.compute(net, 0, 5)
print(f"Cut capacity: {mc.max_flow}")
print(f"Source side: {mc.source_side}")
print(f"Cut edges: {mc.cut_edges}")
```

#### Min-Cost Flow

```python
from networkflow import MinCostMaxFlow, MinCostFlow, CycleCanceling

net = FlowNetwork(4)
net.add_edge(0, 1, 3, cost=1)
net.add_edge(0, 2, 2, cost=2)
net.add_edge(1, 3, 2, cost=3)
net.add_edge(2, 3, 3, cost=1)

# Min-cost max-flow
mcmf = MinCostMaxFlow()
flow, cost = mcmf.solve(net, 0, 3)  # (4, 14)

# Min-cost fixed flow
mcf = MinCostFlow()
flow, cost = mcf.solve(net.copy(), 0, 3, target_flow=3)

# Cycle canceling (alternative method)
cc = CycleCanceling()
flow, cost = cc.solve(net.copy(), 0, 3)  # same result
```

#### Multi-Source / Multi-Sink

```python
from networkflow import MultiSourceSink

net = FlowNetwork(5)
net.add_edge(0, 2, 10)  # Factory A → DC
net.add_edge(1, 2, 5)   # Factory B → DC
net.add_edge(2, 3, 8)   # DC → Store 1
net.add_edge(2, 4, 7)   # DC → Store 2

ms = MultiSourceSink()
flow, _ = ms.solve(net, sources=[0, 1], sinks=[3, 4])
print(f"Max flow: {flow}")  # 15

# With supply limits
flow, _ = ms.solve(net, sources=[0, 1], sinks=[3, 4],
                   source_caps=[3, 2])
print(f"Capped flow: {flow}")  # 5
```

#### Bipartite Matching

```python
from networkflow import BipartiteMatcher

matcher = BipartiteMatcher(4, 4)
for u, v in [(0,0),(0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,3)]:
    matcher.add_edge(u, v)

size = matcher.match()  # 4
print(f"Matching: {matcher.get_matching()}")

# Kőnig's theorem
lc, rc = matcher.minimum_vertex_cover()
print(f"Min vertex cover: {lc}, {rc}")

# Max independent set
li, ri = matcher.maximum_independent_set()
print(f"Max independent set: {li}, {ri}")
```

#### Assignment Problem

```python
from networkflow import AssignmentSolver

solver = AssignmentSolver()
cost = solver.solve([[4,1,3],[2,0,5],[3,2,2]])
print(f"Min cost: {cost}")  # 5
print(f"Assignment: {solver.get_assignment()}")

# Maximum weight assignment
max_cost = AssignmentSolver.max_assignment([[1,2,3],[6,5,4],[1,1,1]])
print(f"Max cost: {max_cost}")  # 10
```

#### Connectivity

```python
from networkflow import edge_disjoint_paths, vertex_disjoint_paths, edge_connectivity, GomoryHuTree

net = FlowNetwork(4)
net.add_edge(0, 1, 1, bidirectional=True)
net.add_edge(0, 2, 1, bidirectional=True)
net.add_edge(1, 3, 1, bidirectional=True)
net.add_edge(2, 3, 1, bidirectional=True)

paths = edge_disjoint_paths(net, 0, 3)  # 2 paths
ec = edge_connectivity(net)  # 2

# Gomory-Hu tree for all-pairs min-cut
tree = GomoryHuTree(net)
print(f"Min cut (0,3): {tree.min_cut(0, 3)}")  # 2
```

#### Flow Decomposition

```python
from networkflow import Dinic, flow_decomposition, ascii_flow_paths

net = FlowNetwork(6)
# ... add edges and solve ...
Dinic().solve(net, 0, 5)
paths = flow_decomposition(net, 0, 5)
print(ascii_flow_paths(paths))
# Output:
#   Flow decomposition (3 paths):
#   Path 0: [0 → 1 → 3 → 5]  flow=12
#   Path 1: [0 → 2 → 4 → 5]  flow=4
#   Path 2: [0 → 2 → 4 → 3 → 5]  flow=7
#   Total flow: 23
```

### CLI

The CLI supports 14 subcommands with auto-format-detection for input files:

```bash
# Max flow (6 algorithms available)
networkflow maxflow network.json 0 5 --algorithm dinic
networkflow maxflow network.json 0 5 --algorithm boykov-kolmogorov --validate

# Min cut
networkflow mincut network.json 0 5

# Min-cost flow (two methods)
networkflow mincost network.json 0 5
networkflow mincost network.json 0 5 --target 10
networkflow mincost network.json 0 5 --method cycle-canceling

# Bipartite matching
networkflow matching bipartite.json --vertex-cover --independent-set

# Assignment
networkflow assignment matrix.json --maximize

# Global min cut (Stoer-Wagner)
networkflow global-cut graph.json

# Connectivity analysis
networkflow connectivity network.json edge-disjoint --source 0 --sink 3
networkflow connectivity network.json vertex-disjoint --source 0 --sink 3
networkflow connectivity network.json edge-connectivity
networkflow connectivity network.json gomory-hu --pair 0 3

# Multi-source/multi-sink
networkflow multi-flow network.json --sources 0,1 --sinks 3,4
networkflow multi-flow network.json --sources 0,1 --sinks 3,4 --source-caps 10,5

# Flow decomposition
networkflow decompose network.json 0 5 --algorithm dinic

# Visualization
networkflow visualize network.json --format dot --source 0 --sink 5 --flows
networkflow visualize network.json --format ascii --flows

# Format conversion
networkflow convert network.json output.graphml --output-format graphml
networkflow convert network.edges output.csv --output-format csv
networkflow convert network.json output.dot --output-format dot

# Benchmark all solvers
networkflow benchmark 10,50,100 --edge-prob 0.3 -o results.json

# Run from config file
networkflow config config.json

# Run built-in demos
networkflow demo

# Display network info
networkflow info network.json
```

### Configuration Files

Run solvers from a JSON or YAML config file:

```json
{
  "algorithm": "dinic",
  "source": 0,
  "sink": 5,
  "network_file": "network.json",
  "output_file": "result.json",
  "show_flows": true,
  "logging": {"level": "INFO", "file": "run.log"}
}
```

```bash
networkflow config config.json
```

### Graph I/O Formats

The CLI auto-detects format by file extension:

| Extension | Format | Description |
|-----------|--------|-------------|
| `.json` | JSON | Native format with full flow/cost |
| `.max`, `.dimacs`, `.txt` | DIMACS | Standard max-flow format |
| `.edges`, `.el` | Edge list | `u v cap [cost]` per line |
| `.csv` | CSV matrix | N×N adjacency matrix |
| `.tsv` | TSV matrix | Tab-separated adjacency matrix |
| `.graphml` | GraphML | XML-based, interoperable |
| `.lgf` | LGF | LEMON Graph Format |

Python API:

```python
from networkflow import read_edge_list, write_graphml, read_graphml

# Read edge list
net, src, snk = read_edge_list("network.edges", source=0, sink=5)

# Write GraphML
write_graphml(net, "network.graphml", source=0, sink=5)

# Read GraphML
net, src, snk = read_graphml("network.graphml")
```

### Visualization

#### DOT (Graphviz)

```python
from networkflow import to_dot

dot = to_dot(net, source=0, sink=5, show_flows=True, show_residuals=True)
# Save and render:
# dot -Tpng network.dot -o network.png
```

Edges are color-coded:
- **Black**: unused (flow = 0)
- **Blue**: partially used (0 < flow < capacity)
- **Red**: saturated (flow = capacity)
- **Dashed gray**: residual edges (when `show_residuals=True`)

#### ASCII Table

```python
from networkflow import ascii_graph

print(ascii_graph(net, source=0, sink=5, show_flows=True))
```

Output:
```
    From -> To        Cap      Flow   Util%  Note
  -------------------------------------------------------
       0 -> 1         16        12      75%  ← source
       0 -> 2         13        11      85%  ← source
       1 -> 3         12        12     100%
       ...
```

---

## Algorithms

| Algorithm | Problem | Complexity |
|-----------|---------|------------|
| Ford-Fulkerson | Max flow | O(E·max_flow) |
| Edmonds-Karp | Max flow | O(V·E²) |
| Dinic | Max flow | O(V²·E) |
| Push-Relabel (FIFO) | Max flow | O(V³) |
| Capacity Scaling | Max flow | O(E²·log U) |
| Boykov-Kolmogorov | Max flow | O(V²·E·\|C\|) worst, fast in practice |
| Min-cut (duality) | s-t min cut | = max flow |
| Stoer-Wagner | Global min cut | O(V³) |
| Gomory-Hu tree | All-pairs min cut | n-1 max-flow calls, O(n) query |
| SPFA (min-cost) | Min-cost flow | O(F·V·E) |
| Cycle Canceling | Min-cost flow | O(V·E²·C) |
| Hopcroft-Karp | Bipartite matching | O(E·√V) |
| Hungarian | Assignment | O(n³) |
| Node-splitting | Vertex-disjoint paths | = max flow on split graph |
| Super-source/sink | Multi-source/sink | = max flow on augmented graph |

---

## Architecture

The toolkit is built around the `FlowNetwork` class — a residual graph
representation using adjacency lists of `FlowEdge` objects. Each edge
maintains a back-reference (`rev`) to its reverse counterpart, enabling O(1)
residual updates during augmentation.

### Module Overview

```
networkflow/
├── graph.py           # Core: FlowNetwork, FlowEdge
├── maxflow.py         # 5 classic max-flow algorithms
├── advanced.py        # Boykov-Kolmogorov, Multi-Source/Sink, Cycle Canceling
├── mincost.py         # Min-cost flow (successive shortest paths)
├── matching.py        # Bipartite matching, assignment
├── mincut.py          # Min-cut, Stoer-Wagner
├── connectivity.py    # Disjoint paths, edge connectivity, Gomory-Hu
├── benchmark.py       # Generators, solver comparison
├── dimacs.py          # DIMACS I/O
├── io_formats.py      # Edge list, CSV, GraphML, LGF I/O
├── visualization.py   # DOT, ASCII, flow decomposition
├── config.py          # JSON/YAML configuration
├── logging_config.py  # Structured logging
└── cli.py             # 14-subcommand CLI
```

### Design Principles

1. **Pure stdlib** — no external dependencies required (PyYAML optional for YAML config)
2. **Solver protocol** — all max-flow solvers implement `solve(network, source, sink) → float`
3. **In-place mutation** — solvers update the network's edge flows directly; use `.copy()` to preserve
4. **Residual graph** — `FlowNetwork` is its own residual graph; reverse edges are auto-created
5. **Type-safe** — full type hints, input validation, `__slots__` on hot paths

### Data Flow

```
User Input → FlowNetwork (adjacency list of FlowEdge)
          → Solver (Dinic/PushRelabel/BK/etc.)
          → Edge flows updated in-place
          → Results: flow value, cut edges, paths, costs
          → Output: JSON/DOT/ASCII/CSV
```

---

## Examples

Six runnable examples in the `examples/` directory:

| Example | Description |
|---------|-------------|
| `01_max_flow.py` | Basic max flow with 4 algorithm comparison |
| `02_mincost_flow.py` | Min-cost flow and flow decomposition |
| `03_matching_assignment.py` | Bipartite matching and assignment |
| `04_multi_source_visualization.py` | Multi-source/sink and visualization |
| `05_io_formats.py` | Format conversion (edge list, CSV, GraphML, DOT) |
| `06_benchmarking.py` | Solver benchmarking and comparison |

```bash
cd network-flow-solver
python3 examples/01_max_flow.py
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=networkflow --cov-report=term-missing

# Run smoke test
python smoke_test_new.py
```

85 tests covering:
- All 6 max-flow algorithms (correctness, edge cases, cross-validation)
- Min-cost flow (successive shortest paths + cycle canceling)
- Bipartite matching and assignment
- Min-cut, Stoer-Wagner, Gomory-Hu tree
- Multi-source/multi-sink
- Connectivity (edge/vertex-disjoint paths)
- Visualization (DOT, ASCII, flow decomposition)
- I/O formats (edge list, CSV, GraphML roundtrips)
- Config and logging
- Regression tests for all Phase 3 bug fixes

---

## Known Issues (Resolved)

All bugs were found during Phase 3 bug hunt and have been fixed with regression tests.

1. **FlowNetwork.copy()/from_dict() didn't restore reverse edge flows**
   - *Symptom*: Copying a network after running max-flow produced a network where
     reverse edges had zero flow instead of the correct negative flow, making the
     residual graph inconsistent.
   - *Fix*: `from_dict()` now explicitly sets the reverse edge's flow to `-flow`
     after restoring the forward edge's flow.
   - *Test*: `TestBugCopyWithFlows.test_copy_preserves_flows`

2. **vertex_disjoint_paths produced paths with duplicate consecutive nodes**
   - *Symptom*: When converting from split-node representation back to original
     nodes, both `2*i` (in) and `2*i+1` (out) mapped to `i` via integer division,
     producing paths like `[0, 1, 1, 3]` instead of `[0, 1, 3]`.
   - *Fix*: Added deduplication when converting split nodes back — only append
     the original node if it differs from the last one.
   - *Test*: `TestBugVertexDisjointDuplicateNodes.test_no_duplicate_nodes`

3. **PushRelabel count array could be indexed out of bounds**
   - *Symptom*: The `count` array had size `2*n+1` (valid indices 0..2*n), but
     the relabel step could set height to `2*n+1`, causing a potential
     `IndexError` when accessing `count[height[u]]`.
   - *Fix*: Increased array size to `2*n+2` and added bounds checks before
     indexing `count`.
   - *Tests*: `TestBugPushRelabelHeightOOB` (2 tests)

4. **StoerWagner docstring had incorrect example output**
   - *Symptom*: The class docstring claimed `sw.solve(graph)` returns `2.0`
     for a triangle graph with edge weights 2, 3, 4, but the correct min cut
     is `5.0` (cutting vertex 0 from {1,2} costs 2+3=5).
   - *Fix*: Updated docstring to show correct result `5.0` with explanation.
   - *Test*: `TestBugStoerWagnerDocstring.test_docstring_example`

5. **Boykov-Kolmogorov adoption could create parent cycles**
   - *Symptom*: The adoption phase could set parent pointers that form a cycle
     (e.g., parent[1] = (4, 0), parent[4] = (1, 2)), causing `_build_path` to
     loop infinitely when tracing from a node to the source.
   - *Fix*: Added `_connected_to_root()` check in adoption to verify candidate
     parents can reach the root without cycling.
   - *Test*: `TestBoykovKolmogorov.test_matches_dinic_random`

---

## Changelog

### v3.0.0 — Comprehensive Improvement

**New Algorithms:**
- Boykov-Kolmogorov max-flow (dual-tree, vision-oriented)
- Cycle Canceling min-cost flow (alternative to successive shortest paths)
- Multi-source/multi-sink max-flow with supply/demand capacities

**New I/O Formats:**
- Edge list (.edges) with comments and cost support
- CSV/TSV adjacency matrix
- GraphML (interoperable with NetworkX, Gephi, yEd)
- LGF (LEMON Graph Format)
- Auto-detection by file extension in CLI

**New Visualization:**
- Graphviz DOT output with color-coded flow utilization
- ASCII edge table with utilization percentages
- Flow decomposition into s-t paths with amounts

**New Infrastructure:**
- JSON/YAML configuration file support
- Structured logging module with configurable levels
- 4 new CLI subcommands: visualize, multi-flow, decompose, convert, config
- GitHub Actions CI (Python 3.10–3.13)
- CONTRIBUTING.md with development guidelines
- 6 runnable examples in examples/
- 32 new tests (total: 85)

**Improvements:**
- Version bumped to 3.0.0
- Enhanced pyproject.toml with classifiers, keywords, optional deps
- Improved CLI with verbose flag and help text
- Better error messages throughout

### v2.0.0 — Phase 2 Enhancement

- Added CapacityScaling algorithm
- Added edge/vertex-disjoint paths
- Added edge connectivity and Gomory-Hu tree
- Added benchmark utilities and DIMACS I/O
- Added 10-subcommand CLI
- Added 13 new tests

### v1.0.0 — Initial Release

- 5 max-flow algorithms, min-cut, min-cost flow, matching, assignment
- 53 tests

---

## Roadmap

- [ ] **MPM algorithm** — O(V³) max-flow via blocking flow with prefetch
- [ ] **Orlin's algorithm** — O(V·E) max-flow (strongly polynomial)
- [ ] **Network Simplex** — min-cost flow via simplex on the flow polytope
- [ ] **Cost scaling** — O(V²·E·log(V·C)) min-cost flow
- [ ] **Bipartite matching with weights** — min-cost bipartite matching
- [ ] **Matroid intersection** — via augmenting paths
- [ ] **Interactive web visualization** — D3.js-based graph renderer
- [ ] **NumPy backend** — optional array-based dense graph for performance
- [ ] **Multithreaded benchmarking** — parallel solver comparison
- [ ] **Python type stubs** — `.pyi` files for IDE support
- [ ] **Property-based testing** — Hypothesis for invariant checking

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, code style,
testing requirements, and pull request process.

---

## License

MIT — see [LICENSE](LICENSE)