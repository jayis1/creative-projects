# Topological Data Analysis (TDA) Toolkit

A from-scratch, pure-Python implementation of persistent homology and related topological data analysis primitives. No external dependencies — only the Python standard library.

## Features

### Complex Construction
- **Vietoris–Rips complex** from point clouds with configurable scale and dimension
- **Weighted Rips complex** with lower-star vertex weight filtration
- **Čech complex** with exact smallest-enclosing-ball (Welzl) criterion
- **Sublevel-set filtration** for 1D and 2D scalar grids (cubical complex triangulation)
- **Simplex tree** data structure for efficient filtered simplicial complex storage

### Persistent Homology
- **Boundary matrix reduction** (standard column algorithm) over GF(2)
- **Lookup-table optimization** for O(1) lowest-one access
- **Minimum persistence filter** to suppress zero-persistence noise
- **Persistence diagrams** with birth/death pairs, essential cycles, and barcode visualization

### Distance Metrics
- **Bottleneck distance** — binary search + Hopcroft-Karp bipartite matching
- **Wasserstein distance** (any order p ≥ 1) — Hungarian algorithm (Kuhn-Munkres)
- **Hausdorff distance** between persistence diagrams

### Vectorized Representations
- **Betti curves** — β_k(t) tracking the number of live features at each scale
- **Persistence landscapes** — stable vectorized representations with L^p norms
- **Persistence images** — Gaussian-weighted 2D image representation for ML

### Visualization & I/O
- **ASCII barcode** rendering
- **ASCII persistence diagram** scatter plot with diagonal
- **ASCII heatmap** for persistence images
- **JSON serialization** for persistence diagrams and images
- **CLI** with 8 subcommands (compute, distance, compare, landscape, betti, image, plot, info)

## How It Works

### Persistent Homology Pipeline

1. **Complex Construction**: Given a point cloud, build a filtered simplicial complex. For Vietoris–Rips, the filtration value of a simplex is its diameter (max pairwise distance among vertices). For weighted Rips, it's `max(max_weight, diameter/2)`. For sublevel sets, it's `max(cell_values)`.

2. **Boundary Matrix**: Construct the boundary matrix over GF(2), where each column represents a simplex and contains 1s at the positions of its codimension-1 faces. Columns are ordered by (filtration value, dimension, vertex tuple).

3. **Matrix Reduction**: Reduce the matrix from left to right using column addition (XOR). When the lowest nonzero entry of column j matches that of an earlier column i (tracked in a lookup table), add column i to j. This is the standard Edelsbrunner–Harer algorithm.

4. **Persistence Pairs**: Each reduced column with a nonzero lowest entry gives a (birth, death) pair. Columns that reduce to zero and whose index was never a birth row correspond to essential cycles (infinite persistence).

### Distance Metrics

- **Bottleneck distance**: The minimum over all perfect matchings (with diagonal augmentation) of the maximum L∞ distance. Computed via binary search over distance thresholds + Hopcroft-Karp maximum bipartite matching.
- **Wasserstein distance**: The p-th root of the minimum total p-th power cost matching. Computed via the O(n³) Hungarian (Kuhn-Munkres) algorithm.
- **Hausdorff distance**: The max of directed sup-inf distances between diagram points, with diagonal projection fallback.

### Persistence Landscapes

For each point (b, d) in a diagram, a "tent" function f(t) = max(0, min(t−b, d−t)) is defined. The k-th landscape function Λ_k(t) is the k-th largest tent value at t. These are stable vectorized representations suitable for statistical analysis and machine learning.

### Persistence Images

Transform a persistence diagram into a fixed-size 2D image by:
1. Converting (b, d) → (b, d−b) (persistence coordinates)
2. Placing weighted Gaussian kernels at each point
3. Integrating over a pixel grid

This produces a stable, rotation-invariant representation directly usable as input to ML pipelines.

## Installation

```bash
cd topological-data-analysis
pip install -e .
```

## Usage

### Python API

```python
from tda import (
    VietorisRipsComplex, compute_persistence,
    diagrams_from_persistence, barcode_string,
    plot_diagram_ascii,
)

# Point cloud: vertices of a pentagon
import math
points = [(math.cos(2*math.pi*i/5), math.sin(2*math.pi*i/5)) for i in range(5)]

# Build Vietoris-Rips complex up to dimension 2
vr = VietorisRipsComplex(points, max_scale=1.3, max_dimension=2)
tree = vr.build()

# Compute persistent homology
persistence = compute_persistence(tree, max_dimension=2, min_persistence=0.01)
diagrams = diagrams_from_persistence(persistence)
print(barcode_string(diagrams))
print(plot_diagram_ascii(diagrams))
```

### Weighted Rips complex

```python
from tda import WeightedRipsComplex, compute_persistence

points = [(0, 0), (1, 0), (2, 0), (3, 0)]
weights = [0.0, 0.3, 0.6, 0.9]  # vertex birth times

wr = WeightedRipsComplex(points, weights, max_scale=3.0, max_dimension=1)
tree = wr.build()
persistence = compute_persistence(tree, max_dimension=1)
```

### Sublevel-set filtration

```python
from tda import SublevelFiltration, compute_persistence

# 2D scalar field (e.g., an image)
grid = [[0, 2, 1], [3, 5, 4], [1, 2, 0]]

sf = SublevelFiltration(grid, max_dimension=2)
tree = sf.build()
persistence = compute_persistence(tree, max_dimension=2)
```

### Distance computation

```python
from tda import bottleneck_distance, wasserstein_distance
from tda.diagram import PersistenceDiagram

d1 = PersistenceDiagram(0)
d1.add(0.0, 1.0)
d1.add(0.0, float('inf'))

d2 = PersistenceDiagram(0)
d2.add(0.0, 1.5)
d2.add(0.0, float('inf'))

print(bottleneck_distance(d1, d2))   # 0.5
print(wasserstein_distance(d1, d2, p=2.0))  # 0.5
```

### Persistence images

```python
from tda import persistence_image, image_to_ascii
from tda.diagram import PersistenceDiagram

diag = PersistenceDiagram(1)
diag.add(0.0, 2.0)
diag.add(1.0, 3.0)

img, birth_range, pers_range = persistence_image(diag, resolution=30, sigma=0.5)
print(image_to_ascii(img, width=40))
```

### CLI

```bash
# Compute persistent homology from a point cloud
tda compute points.json --max-scale 2.0 --max-dimension 2 --format barcode
tda compute points.json --max-scale 2.0 -d 2 --min-persistence 0.01 --format plot

# Use weighted Rips complex
tda compute points.json --complex weighted --weights weights.json --max-scale 3.0

# Save diagrams to file
tda compute points.json --max-scale 2.0 -d 2 --output diagrams.json

# Compare two diagrams with all metrics
tda compare diagrams1.json diagrams2.json

# Compute specific distance
tda distance diagrams1.json diagrams2.json --metric wasserstein --p 2 -d 0

# Compute Betti curves
tda betti diagrams.json --resolution 100

# Compute persistence landscapes
tda landscape diagrams.json -d 0 -r 100 -k 3 --norm 2

# Compute persistence images
tda image diagrams.json -d 1 -r 30 --sigma 0.5

# ASCII scatter plot
tda plot diagrams.json --dims 0,1

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

**JSON weights**: `[0.0, 0.3, 0.6, 0.9]`

## Architecture

```
tda/
├── __init__.py         # Package exports
├── scomplex.py         # Simplex and SimplexTree data structures
├── complexes.py        # Vietoris-Rips complex builder
├── complexes_extra.py  # Weighted Rips, Cech, Sublevel filtration
├── matrix.py           # Boundary matrix + column reduction
├── diagram.py          # PersistenceDiagram, PersistencePair, barcodes
├── distance.py         # Bottleneck and Hausdorff distances
├── wasserstein.py      # Wasserstein distance (Hungarian algorithm)
├── curves.py           # Betti curves and persistence landscapes
├── images.py           # Persistence images
├── plot.py             # ASCII persistence diagram plotting
├── io.py               # JSON serialization
└── cli.py              # Command-line interface (8 subcommands)
```

## Notes on Dimension Caps

When computing persistent homology with `max_dimension=k`, features in dimension k+1 and higher are not tracked. This means k-dimensional features that would normally be "filled" by (k+1)-simplices may appear as essential (infinite persistence). This is expected behavior for truncated filtrations. To avoid spurious essential features, either:
- Use a higher `max_dimension` to include filling simplices
- Use the `min_persistence` filter to suppress noise
- Interpret essential features in the highest computed dimension with caution

## Known Issues (Resolved)

1. **`Simplex.boundary()` on 0-simplices yielded an invalid empty `Simplex(())`** — Fixed: 0-simplices now correctly yield no boundary faces.

2. **`Simplex.all_subsimplices()` yielded `Simplex(())` (empty simplex) for 0-simplices** — Fixed: the range now starts at k=1, excluding the empty combination.

3. **`SimplexTree` ID assignment was broken** — the `insert()` method called `setdefault()` without incrementing the counter, causing all simplices to receive ID 0. Fixed: IDs are now assigned via `_assign_id()` which properly increments `_next_id` for every newly created node.

4. **Dead duplicate-check code in `Simplex.__init__`** — the check `len(self._vertices) != len(set(self._vertices))` was unreachable because `set(vertices)` already removes duplicates before `sorted()`. Removed the dead code.

5. **`VietorisRipsComplex` ignored custom `metric` parameter** — the `distance_matrix` property always called `pairwise_distances()` which uses Euclidean distance, ignoring the user-supplied metric. Fixed: the property now calls `_compute_distance_matrix()` which uses `self.metric`.

6. **Wasserstein distance with p=∞ returned incorrect results** — the Hungarian algorithm minimizes the *sum* of costs, but for p=∞ the correct objective is to minimize the *maximum* cost. Fixed: p=∞ now delegates to `bottleneck_distance()` (binary search + Hopcroft-Karp), which correctly solves the minimax problem.

7. **Bottleneck and Wasserstein distances used a fixed diagonal point for augmentation** — this gave incorrect distances when one diagram was empty or when diagrams had different sizes. Fixed: both now use per-point diagonal projections `((b+d)/2, (b+d)/2)` — the closest point on the diagonal in L∞ norm — ensuring each off-diagonal point can match its own projection at the correct cost `(d-b)/2`.

## License

MIT