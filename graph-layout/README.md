# graph-layout

A from-scratch force-directed & hierarchical graph layout engine in pure Python (stdlib only). Nine layout algorithms, six quality metrics, twelve graph generators, layout transforms, and four renderers (SVG, animated SVG, ASCII, plain text) — no NumPy, no external dependencies.

## Features

### Layout Algorithms (9)

| Algorithm | Class | Description |
|-----------|-------|-------------|
| Fruchterman-Reingold | `FruchtermanReingold` | Classic force-directed: repulsive (all pairs) + attractive (edges) forces with temperature cooling. Supports **frame capture** for animated SVG. |
| Kamada-Kawai | `KamadaKawai` | Stress minimization via Newton-Raphson on the node with the largest gradient |
| Stress Majorization | `StressMajorization` | Gansner-Koren-North iterative majorization (SMOF) |
| Sugiyama | `SugiyamaLayout` | Hierarchical layered layout: cycle removal → longest-path layering → median crossing reduction → coordinate assignment |
| Tree | `TreeLayout` | Recursive tidy tree positioning (top-down or left-right) |
| Radial | `RadialLayout` | BFS-rooted radial ring layout |
| Circular | `CircularLayout` | Evenly spaced on a circle |
| Grid | `GridLayout` | Regular grid arrangement |
| Random | `RandomLayout` | Uniform random (seedable) |

### Graph Generators (12)

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

### Quality Metrics (6)

- **Edge length variance** — uniformity of edge lengths (lower = better)
- **Crossing count** — number of edge crossings (lower = better)
- **Angular resolution** — minimum angle between adjacent edges at any node (higher = better)
- **Aspect ratio** — width/height of the bounding box
- **Stress** — normalized deviation of realized distances from graph-theoretic distances (lower = better)
- **Node overlap** — count of pairs closer than a threshold

### Layout Transforms (6)

- `scale_to_fit(graph, w, h, margin)` — scale and center to fit a bounding box
- `normalize(graph)` — scale to unit square [0,1]²
- `translate(graph, dx, dy)` — shift all positions
- `rotate(graph, angle, cx, cy)` — rotate around a point
- `center_on_origin(graph)` — center centroid at origin
- `bounding_box(graph)` — get (min_x, min_y, max_x, max_y)

### Renderers (4)

- **SVGRenderer** — full SVG with directed-edge arrowheads, colored nodes, labels
- **AnimatedSVGRenderer** — SMIL-based animated SVG from captured layout frames
- **ASCIIRenderer** — Bresenham-line ASCII art for terminal preview
- **TextRenderer** — plain-text node/edge listing with positions

### I/O Formats (3)

- **DOT** (Graphviz subset) — load/save with `pos` attributes
- **JSON** — full round-trip with positions and attributes
- **Edge list** — plain `src tgt weight` text

## Installation

```bash
cd graph-layout
pip install -e .
```

Or just use the package directly — pure stdlib, no dependencies.

## Usage

### Python API

```python
from graph_layout import (
    Graph, FruchtermanReingold, SVGRenderer, ASCIIRenderer, LayoutMetrics,
)

g = Graph()
edges = [("A","B"), ("A","C"), ("B","D"), ("C","E"), ("D","E")]
for s, t in edges:
    g.add_edge(s, t)

# Compute a layout
FruchtermanReingold(seed=42, iterations=300).layout(g)

# Render
print(ASCIIRenderer(60, 20).render(g))
SVGRenderer().save(g, "output.svg")

# Quality metrics
print(LayoutMetrics.all_metrics(g))
```

### CLI

```bash
# Compute a layout and save as SVG
python -m graph_layout.cli layout input.edges -o output.svg -a fr

# Print quality metrics for a positioned graph
python -m graph_layout.cli metrics graph.json

# ASCII preview
python -m graph_layout.cli ascii input.dot -a kamada

# Compare all algorithms by metrics
python -m graph_layout.cli compare input.edges

# Generate a named graph
python -m graph_layout.cli generate petersen -o petersen.json
python -m graph_layout.cli generate erdos-renyi 30 20 42 -o er.json
python -m graph_layout.cli generate barabasi-albert 50 3 42 -o ba.json
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

## How It Works

### Fruchterman-Reingold

Each iteration computes two forces for every node:
- **Repulsive** (all pairs): `F_rep = k² / dist`, pushing nodes apart
- **Attractive** (edges): `F_attr = dist² / k`, pulling connected nodes together

where `k = √(area / n)` is the optimal distance. Displacements are capped by a temperature that cools linearly or exponentially.

### Kamada-Kawai

Defines a stress function `E = Σ k_{ij} (|p_i - p_j| - L_{ij})²` where `L_{ij}` is the target distance (graph-theoretic distance × scale) and `k_{ij}` is a spring strength inversely proportional to distance². Minimized by repeatedly applying Newton-Raphson steps to the single node with the largest gradient magnitude.

### Stress Majorization

Same stress target as Kamada-Kawai but solved iteratively: each step solves a weighted least-squares problem `L·z = b(z)` where `L` is the graph Laplacian weighted by `k_{ij}` and `b` depends on current positions. Guaranteed to monotonically decrease stress.

### Sugiyama

Four-phase hierarchical layout:
1. **Cycle removal** — DFS post-order to ignore back edges
2. **Layer assignment** — longest-path topological layering
3. **Crossing reduction** — median heuristic sweeps (top-down + bottom-up)
4. **Coordinate assignment** — even spacing within layers, centered overall

## License

MIT