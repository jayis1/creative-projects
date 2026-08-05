# Topological Data Analysis (TDA) Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pure stdlib](https://img.shields.io/badge/dependencies-pure%20stdlib-green.svg)]()
[![Tests: 153](https://img.shields.io/badge/tests-153%20passing-brightgreen.svg)]()
[![Version: 3.0](https://img.shields.io/badge/version-3.0.0-blue.svg)]()

A from-scratch, pure-Python implementation of **persistent homology** and
related topological data analysis primitives. No external dependencies —
only the Python standard library. Optional PyYAML support for config
files.

> **v3.0** — Now with alpha complexes, sparse Rips complexes, clearing
> reduction, persistence kernels (PSS/PWG/Fisher), batch processing,
> statistical summaries, configuration files, and 12 CLI subcommands.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Complex Construction](#complex-construction)
  - [Distance Metrics](#distance-metrics)
  - [Vectorized Representations](#vectorized-representations)
  - [Statistics & Feature Extraction](#statistics--feature-extraction)
  - [Persistence Kernels](#persistence-kernels)
  - [Batch Processing](#batch-processing)
  - [Configuration Files](#configuration-files)
  - [CLI](#cli)
- [Architecture](#architecture)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

### Complex Construction
- **Vietoris–Rips complex** from point clouds with configurable scale and dimension
- **Weighted Rips complex** with lower-star vertex weight filtration
- **Čech complex** with exact smallest-enclosing-ball (Welzl) criterion
- **Alpha complex** — filtered by smallest-enclosing-ball radius (tighter than Rips)
- **Sparse Rips complex** — k-nearest-neighbour truncation for efficient approximation
- **Sublevel-set filtration** for 1D and 2D scalar grids (cubical complex triangulation)
- **Simplex tree** data structure for efficient filtered simplicial complex storage

### Persistent Homology
- **Boundary matrix reduction** (standard column algorithm) over GF(2)
- **Clearing optimisation** — skips already-cleared columns for faster reduction
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

### Statistics & Feature Extraction
- **Per-dimension statistics** — feature counts, mean/median/std persistence, entropy
- **Persistent entropy** — normalised Shannon entropy of the persistence distribution
- **Amplitudes** — p-th total persistence for any p ≥ 1
- **Feature vectorization** — fixed-length vectors for ML pipelines

### Persistence Kernels
- **Persistence Scale-Space (PSS) kernel** — Reininghaus et al. (2015)
- **Persistence Weighted Gaussian (PWG) kernel** — Kusano & Hiraoka (2016)
- **Persistence Fisher kernel** — Le & Yamada (2018)
- **Kernel matrix** computation for sets of diagrams

### Batch & Streaming
- **BatchProcessor** — process multiple point clouds with statistics/vectors
- **stream_persistence** — lazy generator for memory-efficient processing

### Visualization & I/O
- **ASCII barcode** rendering
- **ASCII persistence diagram** scatter plot with diagonal
- **ASCII heatmap** for persistence images
- **JSON serialization** for persistence diagrams and images
- **Configuration files** (YAML/JSON) for reproducible workflows
- **CLI** with 12 subcommands

## Installation

```bash
cd topological-data-analysis
pip install -e .
```

With optional YAML config support:
```bash
pip install -e ".[yaml]"
```

For development (includes test dependencies):
```bash
pip install -e ".[dev]"
```

## Quick Start

```python
import math
import tda

# Point cloud: vertices of a pentagon
points = [(math.cos(2*math.pi*i/5), math.sin(2*math.pi*i/5)) for i in range(5)]

# Build Vietoris-Rips complex and compute persistent homology
vr = tda.VietorisRipsComplex(points, max_scale=1.3, max_dimension=2)
tree = vr.build()
persistence = tda.compute_persistence(tree, max_dimension=2, min_persistence=0.01)
diagrams = tda.diagrams_from_persistence(persistence)

# Visualize
print(tda.barcode_string(diagrams))
print(tda.plot_diagram_ascii(diagrams))

# Statistics
print(tda.statistics_table(diagrams))
```

## Usage

### Python API

#### Vietoris–Rips Complex

```python
from tda import VietorisRipsComplex, compute_persistence

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

#### Weighted Rips Complex

```python
from tda import WeightedRipsComplex, compute_persistence

points = [(0, 0), (1, 0), (2, 0), (3, 0)]
weights = [0.0, 0.3, 0.6, 0.9]  # vertex birth times

wr = WeightedRipsComplex(points, weights, max_scale=3.0, max_dimension=1)
tree = wr.build()
persistence = compute_persistence(tree, max_dimension=1)
```

#### Alpha Complex

```python
from tda import AlphaComplex, compute_persistence

points = [(0, 0), (1, 0), (0.5, 0.866)]
ac = AlphaComplex(points, alpha=0.6, max_dimension=2)
tree = ac.build()
persistence = compute_persistence(tree, max_dimension=2)
```

#### Sparse Rips Complex (k-NN Truncation)

```python
from tda import SparseRipsComplex, compute_persistence

points = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
sr = SparseRipsComplex(points, k=2, max_scale=5.0, max_dimension=1)
tree = sr.build()  # Much fewer simplices than full Rips
```

#### Sublevel-set Filtration

```python
from tda import SublevelFiltration, compute_persistence

# 2D scalar field (e.g., an image)
grid = [[0, 2, 1], [3, 5, 4], [1, 2, 0]]

sf = SublevelFiltration(grid, max_dimension=2)
tree = sf.build()
persistence = compute_persistence(tree, max_dimension=2)
```

#### Clearing Reduction

```python
from tda import VietorisRipsComplex, compute_persistence_clearing

vr = VietorisRipsComplex(points, max_scale=2.0, max_dimension=2)
tree = vr.build()

# Same results as compute_persistence, with clearing optimisation
persistence = compute_persistence_clearing(tree, max_dimension=2, min_persistence=0.01)
```

### Distance Metrics

```python
from tda import bottleneck_distance, wasserstein_distance
from tda.diagram import PersistenceDiagram

d1 = PersistenceDiagram(0)
d1.add(0.0, 1.0)
d1.add(0.0, float('inf'))

d2 = PersistenceDiagram(0)
d2.add(0.0, 1.5)
d2.add(0.0, float('inf'))

print(bottleneck_distance(d1, d2))         # 0.5
print(wasserstein_distance(d1, d2, p=2.0)) # ~0.56
```

### Vectorized Representations

```python
from tda import persistence_image, image_to_ascii, persistence_landscape, landscape_norm
from tda.diagram import PersistenceDiagram

# Persistence image
diag = PersistenceDiagram(1)
diag.add(0.0, 2.0)
diag.add(1.0, 3.0)

img, birth_range, pers_range = persistence_image(diag, resolution=30, sigma=0.5)
print(image_to_ascii(img, width=40))

# Persistence landscape
landscapes = persistence_landscape(diag, resolution=100, max_functions=3)
for k, landscape in enumerate(landscapes, 1):
    norm = landscape_norm(landscape, p=2)
    print(f"Λ_{k}: L^2 norm = {norm:.4f}")
```

### Statistics & Feature Extraction

```python
from tda import diagram_statistics, statistics_table, persistent_entropy, amplitudes, vectorize

# Per-dimension statistics
stats = diagram_statistics(diag)
print(f"Features: {stats['num_features']}")
print(f"Mean persistence: {stats['mean_persistence']:.4f}")
print(f"Entropy: {stats['entropy']:.4f}")

# Normalised persistent entropy
entropy = persistent_entropy(diag)
print(f"Normalised entropy: {entropy:.4f}")

# Amplitude (total p-persistence)
amp = amplitudes(diag, p=2.0)
print(f"L2 amplitude: {amp:.4f}")

# Fixed-length feature vector for ML
vec = vectorize(diag, max_features=10)
print(f"Feature vector: {vec}")  # length = 3 * max_features
```

### Persistence Kernels

```python
from tda import pss_kernel, pwg_kernel, fisher_kernel, kernel_matrix

d1 = PersistenceDiagram(0)
d1.add(0.0, 1.0)
d1.add(0.0, 2.0)

d2 = PersistenceDiagram(0)
d2.add(0.0, 1.5)
d2.add(0.0, 2.5)

# Three kernel functions for ML
print(f"PSS kernel:    {pss_kernel(d1, d2, sigma=1.0):.6f}")
print(f"PWG kernel:     {pwg_kernel(d1, d2, sigma=1.0):.6f}")
print(f"Fisher kernel:  {fisher_kernel(d1, d2, sigma=1.0, beta=1.0):.6f}")

# Kernel matrix for a set of diagrams
K = kernel_matrix([d1, d2], pwg_kernel, sigma=1.0)
# K is a 2x2 symmetric positive semi-definite matrix
```

### Batch Processing

```python
from tda import BatchProcessor, stream_persistence

clouds = [
    [(0, 0), (1, 0), (0.5, 0.866)],
    [(0, 0), (2, 0), (4, 0)],
]

# Process all at once
bp = BatchProcessor(clouds, max_scale=2.0, max_dimension=1, min_persistence=0.01)
stats = bp.run_with_stats()
vectors = bp.run_with_vectors(max_features=10)

# Or stream lazily (memory-efficient for large collections)
for i, diagrams in enumerate(stream_persistence(clouds, max_scale=2.0)):
    print(f"Cloud {i}: {sorted(diagrams.keys())}")
```

### Configuration Files

```python
from tda import load_config, save_config, validate_config

# Load a config (JSON or YAML)
cfg = load_config("tda_config.yaml")
validate_config(cfg)

# Access merged configuration
print(cfg["complex"]["type"])      # "rips"
print(cfg["complex"]["max_scale"]) # 2.0
```

### CLI

The `tda` command provides 12 subcommands:

```bash
# Compute persistent homology from a point cloud
tda compute points.json --max-scale 2.0 --max-dimension 2 --format barcode
tda compute points.json --max-scale 2.0 -d 2 --min-persistence 0.01 --format plot

# Use different complex types
tda compute points.json --complex weighted --weights weights.json --max-scale 3.0
tda compute points.json --complex cech --max-scale 2.0 -d 2
tda compute points.json --complex alpha --max-scale 2.0 -d 2
tda compute grid.json --complex sublevel --grid grid.json -d 2

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

# Show statistics table
tda stats diagrams.json

# Batch process multiple point clouds
tda batch clouds.json --max-scale 2.0 -d 1 --output-format stats
tda batch clouds.json --max-scale 2.0 -d 1 --output-format vectors --max-features 10

# Compute persistence kernel matrix
tda kernel d1.json d2.json d3.json --kernel pss --sigma 1.0
tda kernel d1.json d2.json --kernel pwg --sigma 0.5
tda kernel d1.json d2.json --kernel fisher --sigma 1.0 --beta 1.0

# Generate or validate configuration
tda config generate -o my_config.json
tda config validate -f my_config.json
```

#### Verbose Logging

```bash
tda --verbose compute points.json --max-scale 2.0
# Or via environment variable:
TDA_LOG_LEVEL=DEBUG tda compute points.json --max-scale 2.0
```

### Input Formats

**JSON point cloud**: `[[x1, y1], [x2, y2], ...]`

**CSV point cloud**: one point per line, comma-separated coordinates:
```
0.0,0.0
1.0,0.0
0.5,0.866
```

**JSON weights**: `[0.0, 0.3, 0.6, 0.9]`

**JSON batch input**: `[[[x,y], ...], [[x,y], ...], ...]` (list of point clouds)

## Architecture

```
tda/
├── __init__.py          # Package exports (53 symbols)
├── scomplex.py          # Simplex and SimplexTree data structures
├── complexes.py         # Vietoris-Rips complex builder
├── complexes_extra.py   # Weighted Rips, Cech, Sublevel filtration
├── alpha_complex.py     # Alpha complex (smallest-enclosing-ball filtration)
├── optimized.py         # Clearing reduction + Sparse Rips (k-NN)
├── matrix.py            # Boundary matrix + column reduction
├── diagram.py           # PersistenceDiagram, PersistencePair, barcodes
├── distance.py          # Bottleneck and Hausdorff distances
├── wasserstein.py       # Wasserstein distance (Hungarian algorithm)
├── curves.py            # Betti curves and persistence landscapes
├── images.py            # Persistence images (Gaussian-weighted)
├── statistics.py        # Summary stats, entropy, amplitudes, vectorization
├── kernels.py           # PSS, PWG, Fisher persistence kernels
├── batch.py             # BatchProcessor and stream_persistence
├── plot.py              # ASCII persistence diagram plotting
├── io.py                # JSON serialization
├── config.py            # YAML/JSON config loading and validation
├── exceptions.py        # Exception hierarchy
├── logging_config.py    # Logging utilities
└── cli.py               # Command-line interface (12 subcommands)

tests/
├── test_tda.py           # 86 original tests
└── test_new_features.py  # 67 new tests (v3.0)

examples/
├── 01_basic_shapes.py    # Circle, triangle, clusters
├── 02_distances.py       # Bottleneck, Wasserstein, Hausdorff
├── 03_kernels.py         # PSS, PWG, Fisher kernels
├── 04_batch_features.py  # Batch processing and ML features
├── 05_config.py          # Configuration files
└── 06_efficient_complexes.py  # Alpha, sparse Rips, clearing

.github/workflows/
└── ci.yml                # GitHub Actions CI (Python 3.10-3.13)
```

### Layer Diagram

```
┌───────────────────────────────────────────────┐
│  CLI (cli.py) — 12 subcommands                 │
├───────────────────────────────────────────────┤
│  Config / Logging / Exceptions                  │
├───────────────────────────────────────────────┤
│  Batch / Kernels / Statistics                   │
├───────────────────────────────────────────────┤
│  Distance / Wasserstein / Curves / Images       │
├───────────────────────────────────────────────┤
│  Diagram / Matrix (persistence computation)     │
├───────────────────────────────────────────────┤
│  Complexes (Rips, Cech, Alpha, Sublevel, Sparse)│
├───────────────────────────────────────────────┤
│  Simplex / SimplexTree (data structures)        │
└───────────────────────────────────────────────┘
```

### How It Works

#### Persistent Homology Pipeline

1. **Complex Construction**: Given a point cloud, build a filtered simplicial complex. For Vietoris–Rips, the filtration value of a simplex is its diameter (max pairwise distance among vertices). For weighted Rips, it's `max(max_weight, diameter/2)`. For alpha, it's the smallest-enclosing-ball radius. For sublevel sets, it's `max(cell_values)`.

2. **Boundary Matrix**: Construct the boundary matrix over GF(2), where each column represents a simplex and contains 1s at the positions of its codimension-1 faces. Columns are ordered by (filtration value, dimension, vertex tuple).

3. **Matrix Reduction**: Reduce the matrix from left to right using column addition (XOR). When the lowest nonzero entry of column j matches that of an earlier column i (tracked in a lookup table), add column i to j. The clearing optimisation skips columns that are already zero.

4. **Persistence Pairs**: Each reduced column with a nonzero lowest entry gives a (birth, death) pair. Columns that reduce to zero and whose index was never a birth row correspond to essential cycles (infinite persistence).

#### Distance Metrics

- **Bottleneck distance**: The minimum over all perfect matchings (with diagonal augmentation) of the maximum L∞ distance. Computed via binary search over distance thresholds + Hopcroft-Karp maximum bipartite matching.
- **Wasserstein distance**: The p-th root of the minimum total p-th power cost matching. Computed via the O(n³) Hungarian (Kuhn-Munkres) algorithm.
- **Hausdorff distance**: The max of directed sup-inf distances between diagram points, with diagonal projection fallback.

#### Persistence Landscapes

For each point (b, d) in a diagram, a "tent" function f(t) = max(0, min(t−b, d−t)) is defined. The k-th landscape function Λ_k(t) is the k-th largest tent value at t. These are stable vectorized representations suitable for statistical analysis and machine learning.

#### Persistence Images

Transform a persistence diagram into a fixed-size 2D image by:
1. Converting (b, d) → (b, d−b) (persistence coordinates)
2. Placing weighted Gaussian kernels at each point
3. Integrating over a pixel grid

#### Persistence Kernels

Three positive-definite kernel functions on the space of persistence diagrams:
- **PSS** (Reininghaus 2015): Places Gaussians at each point and its mirror below the diagonal.
- **PWG** (Kusano 2016): Weighted Gaussian kernel with arctan persistence weighting.
- **Fisher** (Le & Yamada 2018): Based on the Fisher information metric between Gaussian-smoothed densities.

## Examples

Run the example scripts:

```bash
cd topological-data-analysis
pip install -e .

# Basic shapes (circle, triangle, clusters)
python examples/01_basic_shapes.py

# Distance metrics
python examples/02_distances.py

# Persistence kernels
python examples/03_kernels.py

# Batch processing and ML features
python examples/04_batch_features.py

# Configuration files
python examples/05_config.py

# Efficient complexes (alpha, sparse Rips, clearing)
python examples/06_efficient_complexes.py
```

### ASCII Demo

```
$ tda compute points.json --max-scale 2.0 -d 2 --format plot

H0 (8 features):
  ███████████████████████████████████████████████████████████  (0.000 → 0.765)
  ███████████████████████████████████████████████████████████  (0.000 → 0.765)
  ...
  ████████████████████████████████████████████████████████████→∞  (0.000 → ∞)
H1 (1 features):
                                                              →∞  (0.765 → ∞)

$ tda stats diagrams.json

dim  features  essential  finite  max_pers  mean_pers  median_pers  std_pers  total_pers  entropy
---  --------  ---------  ------  --------  ---------  -----------  --------  ----------  -------
0    8         1          7       0.7654    0.7654     0.7654       0.0000    5.3576      1.9459
1    1         1          0       0.0000    nan        nan          0.0000    0.0000      0.0000
```

## Known Issues (Resolved)

1. **`Simplex.boundary()` on 0-simplices yielded an invalid empty `Simplex(())`** — Fixed: 0-simplices now correctly yield no boundary faces.

2. **`Simplex.all_subsimplices()` yielded `Simplex(())` (empty simplex) for 0-simplices** — Fixed: the range now starts at k=1, excluding the empty combination.

3. **`SimplexTree` ID assignment was broken** — the `insert()` method called `setdefault()` without incrementing the counter, causing all simplices to receive ID 0. Fixed: IDs are now assigned via `_assign_id()` which properly increments `_next_id` for every newly created node.

4. **Dead duplicate-check code in `Simplex.__init__`** — the check `len(self._vertices) != len(set(self._vertices))` was unreachable because `set(vertices)` already removes duplicates before `sorted()`. Removed the dead code.

5. **`VietorisRipsComplex` ignored custom `metric` parameter** — the `distance_matrix` property always called `pairwise_distances()` which uses Euclidean distance, ignoring the user-supplied metric. Fixed: the property now calls `_compute_distance_matrix()` which uses `self.metric`.

6. **Wasserstein distance with p=∞ returned incorrect results** — the Hungarian algorithm minimizes the *sum* of costs, but for p=∞ the correct objective is to minimize the *maximum* cost. Fixed: p=∞ now delegates to `bottleneck_distance()` (binary search + Hopcroft-Karp), which correctly solves the minimax problem.

7. **Bottleneck and Wasserstein distances used a fixed diagonal point for augmentation** — this gave incorrect distances when one diagram was empty or when diagrams had different sizes. Fixed: both now use per-point diagonal projections `((b+d)/2, (b+d)/2)` — the closest point on the diagonal in L∞ norm — ensuring each off-diagonal point can match its own projection at the correct cost `(d-b)/2`.

## Changelog

### v3.0.0 (2026-08-05) — Comprehensive Improvement

**New Features:**
- Alpha complex (filtered by smallest-enclosing-ball radius)
- Sparse Rips complex (k-nearest-neighbour truncation)
- Clearing reduction optimisation for persistence computation
- Persistence statistics module (entropy, amplitudes, feature vectorization)
- Three persistence kernels: PSS, PWG, Fisher
- Kernel matrix computation for sets of diagrams
- BatchProcessor for multi-cloud processing
- stream_persistence generator for memory-efficient processing
- Configuration file support (YAML/JSON) with validation
- Exception hierarchy (TDAError and subclasses)
- Logging utilities with TDA_LOG_LEVEL environment variable

**CLI Enhancements:**
- 4 new subcommands: `stats`, `batch`, `kernel`, `config`
- `--complex alpha` and `--complex sublevel` support
- `--verbose` global flag for debug logging
- Improved error handling with TDA-specific exceptions

**Architecture:**
- 7 new modules (alpha_complex, optimized, statistics, kernels, batch, config, exceptions/logging)
- 67 new tests (153 total, all passing)
- 6 example scripts
- GitHub Actions CI (Python 3.10–3.13)
- CONTRIBUTING.md and LICENSE
- Optional dependencies (pyyaml, pytest) in pyproject.toml

### v2.0.0 — Enhanced

- Weighted Rips complexes
- Čech complexes (with Welzl miniball)
- Sublevel-set filtrations for 1D/2D grids
- Wasserstein distance (Hungarian algorithm)
- Persistence images (Gaussian-weighted vectorization for ML)
- ASCII diagram plots and heatmaps
- `compare` CLI subcommand
- `min_persistence` filter
- 7 bugs fixed, 86 tests

### v1.0.0 — Initial Release

- Vietoris–Rips complex
- Simplex tree
- Boundary matrix reduction
- Persistence diagrams
- Bottleneck and Hausdorff distances
- Betti curves and persistence landscapes
- JSON serialization
- CLI with 8 subcommands

## Roadmap

- [ ] Delaunay triangulation for efficient alpha complexes
- [ ] Zigzag persistence
- [ ] Multipersistence (2-parameter persistence)
- [ ] GPU-accelerated boundary matrix reduction
- [ ] SVG/Matplotlib plot export (optional dependency)
- [ ] Integration with scikit-learn transformers
- [ ] Morse theory-based persistence
- [ ] Witness complex
- [ ] Cover complexes (Mapper algorithm)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, code
style, testing requirements, and pull request process.

## Notes on Dimension Caps

When computing persistent homology with `max_dimension=k`, features in dimension k+1 and higher are not tracked. This means k-dimensional features that would normally be "filled" by (k+1)-simplices may appear as essential (infinite persistence). This is expected behavior for truncated filtrations. To avoid spurious essential features, either:
- Use a higher `max_dimension` to include filling simplices
- Use the `min_persistence` filter to suppress noise
- Interpret essential features in the highest computed dimension with caution

## License

MIT