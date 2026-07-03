# graph-layout

A from-scratch force-directed & hierarchical graph layout engine in pure Python (stdlib only). Nine layout algorithms, six quality metrics, and three renderers (SVG, ASCII, plain text) — no NumPy, no external dependencies.

## Features

### Layout Algorithms (9)

| Algorithm | Class | Description |
|-----------|-------|-------------|
| Fruchterman-Reingold | `FruchtermanReingold` | Classic force-directed: repulsive (all pairs) + attractive (edges) forces with temperature cooling |
| Kamada-Kawai | `KamadaKawai` | Stress minimization via Newton-Raphson on the node with the largest gradient |
| Stress Majorization | `StressMajorization` | Gansner-Koren-North iterative majorization (SMOF) |
| Sugiyama | `SugiyamaLayout` | Hierarchical layered layout: cycle removal → longest-path layering → median crossing reduction → coordinate assignment |
| Tree | `TreeLayout` | Recursive tidy tree positioning (top-down or left-right) |
| Radial | `RadialLayout` | BFS-rooted radial ring layout |
| Circular | `CircularLayout` | Evenly spaced on a circle |
| Grid | `GridLayout` | Regular grid arrangement |
| Random | `RandomLayout` | Uniform random (seedable) |

### Quality Metrics (6)

- **Edge length variance** — uniformity of edge lengths (lower = better)
- **Crossing count** — number of edge crossings (lower = better)
- **Angular resolution** — minimum angle between adjacent edges at any node (higher = better)
- **Aspect ratio** — width/height of the bounding box
- **Stress** — normalized deviation of realized distances from graph-theoretic distances (lower = better)
- **Node overlap** — count of pairs closer than a threshold

### Renderers (3)

- **SVGRenderer** — full SVG with directed-edge arrowheads, colored nodes, labels
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