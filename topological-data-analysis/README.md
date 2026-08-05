# Topological Data Analysis (TDA) Toolkit

A from-scratch, pure-Python implementation of persistent homology and related topological data analysis primitives. No external dependencies — only the Python standard library.

## Features

- **Vietoris–Rips complexes** from point clouds with configurable scale and dimension
- **Simplex tree** data structure for efficient filtered simplicial complex storage
- **Boundary matrix reduction** (standard algorithm) for computing persistent homology over GF(2)
- **Persistence diagrams** with birth/death pairs, essential cycles, and barcode visualization
- **Bottleneck distance** between persistence diagrams (binary search + Hopcroft-Karp matching)
- **Hausdorff distance** between persistence diagrams
- **Betti curves** — β_k(t) tracking the number of live features at each scale
- **Persistence landscapes** — stable vectorized representations of diagrams
- **Landscape norms** — L^p norms via trapezoidal integration
- **JSON serialization** for persistence diagrams
- **CLI** with compute, distance, landscape, betti, and info subcommands

## How It Works

### Persistent Homology Pipeline

1. **Complex Construction**: Given a point cloud, build a Vietoris–Rips filtered simplicial complex. The filtration value of a simplex is its diameter (max pairwise distance among vertices).

2. **Boundary Matrix**: Construct the boundary matrix over GF(2), where each column represents a simplex and contains 1s at the positions of its codimension-1 faces. Columns are ordered by (filtration value, dimension).

3. **Matrix Reduction**: Reduce the matrix from left to right using column addition (XOR). When the lowest nonzero entry of column j matches that of an earlier column i, add column i to j. This is the standard Edelsbrunner–Harer algorithm.

4. **Persistence Pairs**: Each reduced column with a nonzero lowest entry gives a (birth, death) pair. Columns that reduce to zero correspond to essential cycles (infinite persistence).

### Distance Metrics

- **Bottleneck distance**: The minimum over all perfect matchings (with diagonal augmentation) of the maximum L∞ distance. Computed via binary search over distance thresholds + Hopcroft-Karp maximum bipartite matching.
- **Hausdorff distance**: The max of directed sup-inf distances between diagram points, with diagonal projection fallback.

### Persistence Landscapes

For each point (b, d) in a diagram, a "tent" function f(t) = max(0, min(t−b, d−t)) is defined. The k-th landscape function Λ_k(t) is the k-th largest tent value at t. These are stable vectorized representations suitable for statistical analysis and machine learning.

## Installation

```bash
cd topological-data-analysis
pip install -e .
```

Or use directly without installation (ensure the `tda/` package is on your Python path).

## Usage

### Python API

```python
from tda import VietorisRipsComplex, compute_persistence, diagrams_from_persistence, barcode_string

# Point cloud: vertices of a triangle
points = [(0, 0), (1, 0), (0.5, 0.866)]

# Build Vietoris-Rips complex up to dimension 2
vr = VietorisRipsComplex(points, max_scale=2.0, max_dimension=2)
tree = vr.build()

# Compute persistent homology
persistence = compute_persistence(tree, max_dimension=2)
# {0: [(0.0, 1.0), (0.0, 1.0), (0.0, inf)], 1: [(1.0, 1.0)]}

# Convert to diagrams
diagrams = diagrams_from_persistence(persistence)
print(barcode_string(diagrams))
```

### Distance computation

```python
from tda import bottleneck_distance, hausdorff_distance
from tda.diagram import PersistenceDiagram

d1 = PersistenceDiagram(0)
d1.add(0.0, 1.0)
d1.add(0.0, float('inf'))

d2 = PersistenceDiagram(0)
d2.add(0.0, 1.1)
d2.add(0.0, float('inf'))

print(bottleneck_distance(d1, d2))  # 0.1
print(hausdorff_distance(d1, d2))   # 0.1
```

### Persistence landscapes

```python
from tda import persistence_landscape
from tda.curves import landscape_norm
from tda.diagram import PersistenceDiagram

diag = PersistenceDiagram(1)
diag.add(0.0, 1.0)
diag.add(0.5, 2.0)

landscapes = persistence_landscape(diag, resolution=100, max_functions=3)
for k, landscape in enumerate(landscapes, 1):
    print(f"Lambda_{k} L2 norm: {landscape_norm(landscape, p=2):.4f}")
```

### CLI

```bash
# Compute persistent homology from a point cloud
tda compute points.json --max-scale 2.0 --max-dimension 2 --format barcode

# Save diagrams to file
tda compute points.json --max-scale 2.0 -d 2 --output diagrams.json

# Compare two diagrams
tda distance diagrams1.json diagrams2.json --metric bottleneck -d 0

# Compute Betti curves
tda betti diagrams.json --resolution 100

# Compute persistence landscapes
tda landscape diagrams.json -d 0 -r 100 -k 3 --norm 2

# Show diagram info
tda info diagrams.json
```

### Input formats

**JSON point cloud**: `[[x1, y1], [x2, y2], ...]`

**CSV point cloud**: one point per line, comma-separated coordinates:
```
0.0,0.0
1.0,0.0
0.5,0.866
```

## Architecture

```
tda/
├── __init__.py    # Package exports
├── scomplex.py    # Simplex and SimplexTree data structures
├── complexes.py   # Vietoris-Rips complex builder
├── matrix.py      # Boundary matrix + column reduction
├── diagram.py     # PersistenceDiagram, PersistencePair, barcodes
├── distance.py    # Bottleneck and Hausdorff distances
├── curves.py      # Betti curves and persistence landscapes
├── io.py          # JSON serialization
└── cli.py         # Command-line interface
```

## License

MIT