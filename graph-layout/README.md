# 🕸️ graph-layout

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 90 passed](https://img.shields.io/badge/tests-90%20passed-brightgreen.svg)](tests/)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-success.svg)](#installation)

> A from-scratch force-directed & hierarchical graph layout engine in pure Python (stdlib only).
> 11 layout algorithms · 6 quality metrics · 6 renderers · 12 graph generators · graph algorithms · config files · CLI

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Configuration Files](#configuration-files)
  - [Graph Algorithms](#graph-algorithms)
  - [Animated SVG](#animated-svg)
- [Architecture](#architecture)
- [Layout Algorithms](#layout-algorithms-11)
- [Graph Algorithms](#graph-algorithms-module)
- [Renderers](#renderers-6)
- [Quality Metrics](#quality-metrics-6)
- [Graph Generators](#graph-generators-12)
- [I/O Formats](#io-formats-3)
- [Layout Transforms](#layout-transforms-6)
- [ASCII Art Demo](#ascii-art-demo)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

- **11 layout algorithms** — force-directed, stress-minimization, hierarchical, tree, radial, grid, circular, random, DRGraph, PivotMDS
- **6 renderers** — SVG, animated SVG, HTML, ASCII art, plain text, adjacency-matrix heatmap
- **Graph algorithms** — BFS, DFS, Dijkstra, degree/closeness/betweenness centrality, MST (Prim's), cycle detection, topological sort, community detection (label propagation)
- **6 quality metrics** — edge length variance, crossing count, angular resolution, aspect ratio, stress, node overlap
- **12 graph generators** — Petersen, hypercube, Erdős–Rényi, Barabási–Albert, Watts–Strogatz, and more
- **Configuration files** — JSON/TOML pipeline configs for reproducible layouts
- **CLI** — 6 subcommands (`layout`, `metrics`, `ascii`, `compare`, `generate`, `analyze`, `pipeline`)
- **Zero external dependencies** — pure Python stdlib
- **90 tests** — comprehensive test suite with pytest

---

## Installation

```bash
cd graph-layout
pip install -e .
```

Or use directly without installation (pure stdlib, no dependencies):

```bash
python3 -m graph_layout.cli --help
```

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/graph-layout
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

---

## Quick Start

```python
from graph_layout import (
    Graph, FruchtermanReingold, SVGRenderer, ASCIIRenderer, LayoutMetrics,
)

# Build a graph
g = Graph()
for s, t in [("A","B"), ("A","C"), ("B","D"), ("C","E"), ("D","E")]:
    g.add_edge(s, t)

# Compute a force-directed layout
FruchtermanReingold(seed=42, iterations=300).layout(g)

# Render to SVG
SVGRenderer().save(g, "output.svg")

# Or preview in terminal
print(ASCIIRenderer(60, 20).render(g))

# Check layout quality
for k, v in LayoutMetrics.all_metrics(g).items():
    print(f"  {k}: {v:.4f}")
```

---

## Usage

### Python API

#### Basic Layout

```python
from graph_layout import Graph, KamadaKawai, SVGRenderer

g = Graph()
g.add_edge("A", "B", weight=2.0)
g.add_edge("B", "C")
g.add_edge("A", "C")

KamadaKawai(seed=42).layout(g)
SVGRenderer(width=800, height=600).save(g, "kamada.svg")
```

#### Compare All Algorithms

```python
from graph_layout import (
    petersen_graph, FruchtermanReingold, KamadaKawai, StressMajorization,
    SugiyamaLayout, CircularLayout, DRGraphLayout, PivotMDSLayout,
    LayoutMetrics,
)

g = petersen_graph()
for cls in [FruchtermanReingold, KamadaKawai, StressMajorization,
            CircularLayout, DRGraphLayout, PivotMDSLayout]:
    g2 = g.copy()
    cls(seed=42, iterations=100).layout(g2)
    m = LayoutMetrics.all_metrics(g2)
    print(f"{cls.__name__:30s} crossings={int(m['crossing_count']):3d} "
          f"stress={m['stress']:.2f}")
```

#### HTML Rendering with Metrics

```python
from graph_layout import (
    barabasi_albert, DRGraphLayout, HTMLRenderer,
)

g = barabasi_albert(50, 3, seed=42)
DRGraphLayout(width=1000, height=800, iterations=200).layout(g)

html = HTMLRenderer(width=1000, height=800, title="BA Network",
                    show_metrics=True, theme="dark")
html.save(g, "ba_network.html")
```

#### Matrix Visualization

```python
from graph_layout import petersen_graph, MatrixRenderer

g = petersen_graph()
MatrixRenderer(cell_size=24, color="#e74c3c").save(g, "petersen_matrix.svg")
```

### CLI

```bash
# Generate a named graph
graph-layout generate petersen -o petersen.json
graph-layout generate barabasi-albert 100 3 42 -o ba.json
graph-layout generate erdos-renyi 30 20 42 -o er.json

# Compute a layout and save as SVG
graph-layout layout petersen.json -o petersen.svg -a fr

# Use new layout algorithms
graph-layout layout ba.json -o ba.svg -a drgraph
graph-layout layout er.json -o er.svg -a pivot-mds

# Render as HTML (with metrics table)
graph-layout layout petersen.json -o petersen.html -a fr --output-format html

# Print quality metrics
graph-layout metrics petersen.json

# ASCII preview
graph-layout ascii petersen.json -a kamada

# Compare all 11 algorithms by metrics
graph-layout compare petersen.json

# Run graph algorithms
graph-layout analyze petersen.json --analysis betweenness
graph-layout analyze petersen.json --analysis mst
graph-layout analyze petersen.json --analysis community --seed 42
graph-layout analyze petersen.json --analysis bfs --start 0
graph-layout analyze petersen.json --analysis cycle

# Run a full pipeline from a config file
graph-layout pipeline examples/pipeline_config.json
```

### Configuration Files

Define a complete layout pipeline in JSON (or TOML on Python 3.11+):

```json
{
    "graph": {"generator": "barabasi-albert", "params": [100, 3, 42]},
    "layout": {
        "algorithm": "drgraph",
        "width": 1200,
        "height": 800,
        "seed": 42
    },
    "render": {
        "format": "html",
        "output": "ba_network.html"
    },
    "metrics": true
}
```

Then run:

```bash
graph-layout pipeline examples/pipeline_config_ba.json
```

See [`examples/`](examples/) for more config file examples.

### Graph Algorithms

The `graph_layout.algorithms` module provides graph-theoretic computations:

```python
from graph_layout import (
    barabasi_albert, dijkstra, degree_centrality, closeness_centrality,
    betweenness_centrality, minimum_spanning_tree, has_cycle,
    topological_sort, label_propagation, bfs, dfs,
)

g = barabasi_albert(50, 3, seed=42)

# Traversal
print(bfs(g, "0"))       # → ['0', '1', '3', '2', ...]
print(dfs(g, "0"))

# Shortest paths
dist = dijkstra(g, "0")
print(dist["10"])        # → distance from node 0 to node 10

# Centrality
deg = degree_centrality(g)
top = sorted(deg.items(), key=lambda x: -x[1])[:5]
print(top)               # → top 5 most connected nodes

# Minimum spanning tree
mst = minimum_spanning_tree(g)
print(f"MST: {len(mst)} edges, weight={sum(w for _,_,w in mst)}")

# Community detection
communities = label_propagation(g, seed=42)
print(f"{len(set(communities.values()))} communities detected")
```

### Animated SVG

```python
from graph_layout import FruchtermanReingold, petersen_graph, AnimatedSVGRenderer

g = petersen_graph()
algo = FruchtermanReingold(seed=42, iterations=200,
                            capture_frames=True, frame_interval=10)
algo.layout(g)
AnimatedSVGRenderer().save(algo.frames, g, "animation.svg")
```

---

## Architecture

```
graph-layout/
├── graph_layout/
│   ├── __init__.py          # Package exports (v3.0.0)
│   ├── graph.py             # Core data structures: Graph, Node, Edge
│   ├── layouts.py           # 9 core layout algorithms
│   ├── advanced_layouts.py  # DRGraph + PivotMDS (v3.0.0)
│   ├── metrics.py           # 6 quality metrics
│   ├── render.py            # SVG, ASCII, Text, AnimatedSVG renderers
│   ├── html_renderer.py     # HTML renderer with metrics (v3.0.0)
│   ├── matrix_renderer.py   # Adjacency-matrix heatmap (v3.0.0)
│   ├── generators.py        # 12 graph generators
│   ├── transform.py         # 6 layout transforms
│   ├── algorithms.py        # Graph algorithms (v3.0.0)
│   ├── config.py            # JSON/TOML config support (v3.0.0)
│   ├── logging_utils.py     # Structured logging (v3.0.0)
│   ├── io_utils.py          # DOT/JSON/edge-list I/O
│   └── cli.py               # CLI with 7 subcommands
├── tests/
│   ├── test_graph_layout.py  # Original 22 tests
│   ├── test_algorithms.py    # Graph algorithm tests (v3.0.0)
│   ├── test_advanced_layouts.py  # New layout tests (v3.0.0)
│   ├── test_new_renderers.py # HTML/Matrix/config tests (v3.0.0)
│   └── test_cli_new.py       # CLI tests for new commands (v3.0.0)
├── examples/
│   ├── demo.py               # Basic demo
│   ├── enhanced_demo.py      # Enhanced demo
│   ├── advanced_demo.py      # v3.0.0 features demo
│   ├── pipeline_config.json  # Config: Petersen + FR → SVG
│   ├── pipeline_config_ba.json  # Config: BA network + DRGraph → HTML
│   └── pipeline_config_ws.json  # Config: small-world + PivotMDS → SVG
├── .github/workflows/ci.yml  # GitHub Actions CI
├── pyproject.toml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Design Principles

1. **Zero dependencies** — Everything uses only the Python standard library (`math`, `random`, `json`, `re`, `collections`, `heapq`, `argparse`, `logging`).
2. **Mutable graphs** — Layout algorithms assign `x`/`y` directly to `Node` objects in-place.
3. **Composable** — Layouts, metrics, renderers, and transforms are independent and can be chained.
4. **Deterministic** — All algorithms accept a `seed` parameter for reproducible results.

---

## Layout Algorithms (11)

| # | Algorithm | Class | Description |
|---|-----------|-------|-------------|
| 1 | Fruchterman-Reingold | `FruchtermanReingold` | Classic force-directed: repulsive + attractive forces with temperature cooling. Supports **frame capture** for animated SVG. |
| 2 | Kamada-Kawai | `KamadaKawai` | Stress minimization via Newton-Raphson on the node with the largest gradient |
| 3 | Stress Majorization | `StressMajorization` | Gansner-Koren-North iterative majorization (SMOF) |
| 4 | DRGraph | `DRGraphLayout` | Deterministic force-directed with spiral initialization (no seed needed) — **v3.0.0** |
| 5 | PivotMDS | `PivotMDSLayout` | Multi-dimensional scaling using pivot nodes (O(p·n) time) — **v3.0.0** |
| 6 | Sugiyama | `SugiyamaLayout` | Hierarchical layered layout: cycle removal → longest-path layering → median crossing reduction → coordinate assignment |
| 7 | Tree | `TreeLayout` | Recursive tidy tree positioning (top-down or left-right) |
| 8 | Radial | `RadialLayout` | BFS-rooted radial ring layout |
| 9 | Circular | `CircularLayout` | Evenly spaced on a circle |
| 10 | Grid | `GridLayout` | Regular grid arrangement |
| 11 | Random | `RandomLayout` | Uniform random (seedable) |

---

## Graph Algorithms Module

| Algorithm | Function | Description |
|-----------|----------|-------------|
| BFS traversal | `bfs(graph, start)` | Breadth-first search from a node |
| DFS traversal | `dfs(graph, start)` | Depth-first search (iterative) |
| Dijkstra | `dijkstra(graph, source)` | Shortest path distances using edge weights |
| All-pairs shortest paths | `all_pairs_shortest_paths(graph)` | Dijkstra from every node |
| Degree centrality | `degree_centrality(graph)` | `degree(n) / (n-1)` |
| Closeness centrality | `closeness_centrality(graph)` | Reciprocal of sum of shortest distances |
| Betweenness centrality | `betweenness_centrality(graph)` | Brandes' algorithm (O(VE)) |
| Minimum Spanning Tree | `minimum_spanning_tree(graph)` | Prim's algorithm |
| Cycle detection | `has_cycle(graph)` | Undirected cycle detection via BFS |
| Topological sort | `topological_sort(graph)` | Kahn's algorithm (raises on cycles) |
| Community detection | `label_propagation(graph)` | Raghavan et al. label propagation |

---

## Renderers (6)

| Renderer | Class | Output |
|----------|-------|--------|
| SVG | `SVGRenderer` | Full SVG with arrowheads, colored nodes, labels |
| Animated SVG | `AnimatedSVGRenderer` | SMIL-based animated SVG from captured layout frames |
| HTML | `HTMLRenderer` | Self-contained HTML page with embedded SVG + metrics table — **v3.0.0** |
| Matrix | `MatrixRenderer` | Adjacency-matrix heatmap SVG — **v3.0.0** |
| ASCII | `ASCIIRenderer` | Bresenham-line ASCII art for terminal preview |
| Text | `TextRenderer` | Plain-text node/edge listing with positions |

---

## Quality Metrics (6)

- **Edge length variance** — uniformity of edge lengths (lower = better)
- **Crossing count** — number of edge crossings (lower = better)
- **Angular resolution** — minimum angle between adjacent edges at any node (higher = better)
- **Aspect ratio** — width/height of the bounding box
- **Stress** — normalized deviation of realized distances from graph-theoretic distances (lower = better)
- **Node overlap** — count of pairs closer than a threshold

---

## Graph Generators (12)

| Generator | Function | Parameters |
|-----------|----------|------------|
| Complete bipartite | `complete_bipartite(m, n)` | K_{m,n} |
| Path | `path_graph(n)` | P_n |
| Star | `star_graph(n)` | center + n leaves |
| Cycle | `cycle_graph(n)` | C_n |
| Petersen | `petersen_graph()` | classic 10-node |
| Hypercube | `hypercube_graph(dim)` | Q_d |
| Erdős–Rényi | `erdos_renyi(n, p, seed)` | G(n, p) |
| Barabási–Albert | `barabasi_albert(n, m, seed)` | preferential attachment |
| Watts–Strogatz | `watts_strogatz(n, k, p, seed)` | small-world |
| Grid | `Graph.grid_graph(rows, cols)` | rows×cols lattice |
| Tree | `Graph.tree_graph(branching, depth)` | balanced tree |
| Complete | `Graph.complete_graph(n)` | K_n |

---

## I/O Formats (3)

- **DOT** (Graphviz subset) — load/save with `pos` attributes
- **JSON** — full round-trip with positions and attributes
- **Edge list** — plain `src tgt weight` text

---

## Layout Transforms (6)

- `scale_to_fit(graph, w, h, margin)` — scale and center to fit a bounding box
- `normalize(graph)` — scale to unit square [0,1]²
- `translate(graph, dx, dy)` — shift all positions
- `rotate(graph, angle, cx, cy)` — rotate around a point
- `center_on_origin(graph)` — center centroid at origin
- `bounding_box(graph)` — get (min_x, min_y, max_x, max_y)

---

## ASCII Art Demo

```
$ graph-layout generate petersen -o petersen.edges
$ graph-layout ascii petersen.edges -a fr

  6++++++++++++++++1+----------9
  |                 |--      -- --
  |                 |  --  --     -
 |                   |   ++        --
 |                   | --  --        -
 |                   -+      --       --
 |                 -- |        --       --
|                --    | --------+2       -
|              7+------+-         |        --
|             |         |        |           -
|            |          |        |            --
|            |            |      |    ----------+4
8--         |            -0------+----       ---
 | -----   |          ---       |          --
  |     ---+-      ---          |       ---
   |      |  ---++-            |     ---
   |     |    --  -----        |   --
    |   |  ---         -----  | ---
     | |---                 --3-
      5-
```

---

## Known Issues (Resolved)

The following bugs were found during the bug hunt phase and have been fixed:

1. **Partial-position crash in metrics** (`metrics.py`): `crossing_count`, `angular_resolution`, `node_overlap`, `edge_length_variance`, and `stress` only checked `node.x is None` but not `node.y`, causing a `TypeError`. Fixed by checking both coordinates.
2. **RadialLayout didn't handle disconnected graphs** (`layouts.py`): BFS from a single root left other components unpositioned. Fixed by iterating over all component roots.
3. **TreeLayout didn't BFS disconnected components** (`layouts.py`): Unvisited nodes were added as isolated roots without exploring edges. Fixed by BFS-ing each component.
4. **Sugiyama DFS hit Python recursion limit** (`layouts.py`): Recursive DFS exceeded the limit on 200+ node chains. Fixed by converting to iterative DFS.
5. **remove_edge crashed on nonexistent edges** (`graph.py`): Raised `KeyError`. Fixed by guarding adjacency access.
6. **ASCIIRenderer Bresenham char selection** (`render.py`): Used changing `x0/y0` deltas. Fixed by capturing initial `dx/dy`.
7. **Barabási–Albert potential infinite loop** (`generators.py`): Target selection could spin. Fixed by sampling from a shrinking available-nodes list.
8. **Inconsistent constructor signatures** (`layouts.py`): 4 layout classes lacked `seed` parameter. Added for API consistency.
9. **Dead code in `add_edge`** (`graph.py`): Unused `key` variable. Removed.
10. **Dead variable in `save_dot`** (`io_utils.py`): Unused `w` variable. Removed.

---

## Changelog

### v3.0.0 (2026-07-03) — Comprehensive Improvement

- **+2 layout algorithms**: DRGraph (deterministic force-directed) and PivotMDS (multi-dimensional scaling)
- **+2 renderers**: HTMLRenderer (self-contained HTML page with metrics) and MatrixRenderer (adjacency-matrix heatmap)
- **+Graph algorithms module**: BFS, DFS, Dijkstra, degree/closeness/betweenness centrality, MST (Prim's), cycle detection, topological sort (Kahn's), community detection (label propagation)
- **+Configuration file support**: JSON and TOML pipeline configs
- **+Structured logging**: `setup_logging()` and `get_logger()`
- **+CLI `analyze` subcommand**: Run graph algorithms from the command line
- **+CLI `pipeline` subcommand**: Run full pipelines from config files
- **+68 new tests** (22 → 90 total)
- **+GitHub Actions CI**: Tests run on Python 3.8, 3.11, 3.12
- **+LICENSE, CONTRIBUTING.md**
- **+Example config files** and advanced demo script
- **+Dramatically improved README** with table of contents, badges, architecture diagram, ASCII art demo

### v2.0.0 — Bug Hunt

- Fixed 10 bugs across metrics, layouts, generators, renderers, and I/O
- Added 22 tests

### v1.0.0 — Initial Release

- 9 layout algorithms, 6 metrics, 12 generators, 4 renderers, 3 I/O formats, CLI

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding new layout algorithms, renderers, graph algorithms, and running tests.

---

## Roadmap

- [ ] Barnes-Hut O(n·log n) force-directed acceleration
- [ ] GraphML I/O format support
- [ ] Interactive HTML viewer with zoom/pan (JavaScript)
- [ ] More community detection algorithms (Louvain, Girvan-Newman)
- [ ] Edge bundling for dense graphs
- [ ] 3D layout support
- [ ] Graph compression / simplification

---

## License

[MIT](LICENSE)