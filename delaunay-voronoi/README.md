# delaunay-voronoi

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 125](https://img.shields.io/badge/tests-125%20passing-brightgreen.svg)](#tests)
[![No Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success.svg)](#dependencies)

> A pure-Python computational geometry toolkit — **no external dependencies required**.

Implements Delaunay triangulation, Voronoi diagrams, convex hulls, Lloyd's
relaxation, Ruppert's mesh refinement, spatial queries, mesh quality
metrics, multiple export formats (SVG, PPM, PNG, OBJ, STL), and more — all
with robust exact-arithmetic geometric predicates.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Mesh Quality Metrics](#mesh-quality-metrics)
- [Export Formats](#export-formats)
- [Configuration](#configuration)
- [Performance](#performance)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Algorithms
| Algorithm | Description | Complexity |
|-----------|-------------|------------|
| **Bowyer-Watson Delaunay** | Incremental triangulation with robust in-circle tests | O(n²) |
| **Voronoi Diagram** | Dual graph construction with Liang-Barsky clipping | O(n) from Delaunay |
| **Convex Hull** | Andrew's monotone-chain algorithm | O(n log n) |
| **Lloyd's Relaxation** | Centroidal Voronoi tessellation for even distributions | O(n·iter) |
| **Ruppert's Refinement** | Quality meshing with minimum-angle guarantee | O(n·iter) |
| **Ear-Clip Triangulation** | Triangulate simple polygons | O(n²) |

### Spatial Queries
- **Nearest-neighbour** lookup via walking traversal or spatial hash grid
- **k-nearest neighbours** by graph distance (BFS on triangulation)
- **Point location** — visibility-walk to find the containing triangle
- **Range/radius search** — find all points within a given distance

### Robust Predicates
`orient2d` and `incircle` use `fractions.Fraction` for exact arithmetic.
The float path handles the common case; an exact fallback prevents
misclassification of cocircular/collinear points.

### Rendering & Export
- **SVG** — vector output with layered Delaunay/Voronoi/hull/points
- **Animated SVG** — CSS-keyframe cross-fade between Lloyd relaxation frames
- **PPM** — flat-shaded Voronoi raster (binary P6)
- **PNG** — flat-shaded Voronoi PNG (pure stdlib via `zlib`, no Pillow needed)
- **OBJ** — Wavefront mesh export for 3D modelling tools (Blender, MeshLab)
- **STL** — ASCII STL mesh export for 3D printing pipelines
- **JSON** — save/load triangulations and Voronoi diagrams

### Mesh Quality Metrics
Comprehensive analysis including:
- Min/max/mean/median/std angle distributions
- Area and edge-length statistics
- Radius ratio (2·r_in/r_out) and edge-ratio quality measures
- Binned histograms for angle and area distributions
- Overall quality grade (A–D)

### Polygon Utilities
- **Area** (shoelace formula), **centroid** (area-weighted)
- **Point-in-polygon** (ray casting)
- **Sutherland-Hodgman clipping** (polygon ∩ convex polygon)
- **Ear clipping triangulation**
- **Boundary extraction** (edges and ordered loops)

---

## Installation

### From source (recommended)

```bash
cd delaunay-voronoi
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the `delaunay-voronoi` CLI command and the importable
`delaunay_voronoi` Python package.

### Without installation

Just add the project root to `sys.path` and import directly — **no
external dependencies are required** (uses only `math`, `fractions`,
`dataclasses`, `random`, `json`, `argparse`, `zlib`, `struct`,
`logging`, `tomllib`/`tomli`).

### Optional dependencies

```bash
pip install -e ".[dev]"     # pytest + pyyaml for development
pip install -e ".[yaml]"    # pyyaml for YAML config support
```

---

## Quick Start

### CLI — one-liner

```bash
# Generate a Delaunay/Voronoi SVG diagram with 50 points and 5 Lloyd iterations
delaunay-voronoi diagram -n 50 --lloyd 5 -o diagram.svg
```

### Python — 10 lines

```python
from delaunay_voronoi import (
    DelaunayTriangulation, VoronoiDiagram, convex_hull,
    lloyd_relaxation, render_svg,
)
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed

box = (Point(0, 0), Point(800, 600))
pts = generate_poisson_seed(50, box, seed=42)
pts = lloyd_relaxation(pts, iterations=10, clip_box=box, seed=42)

dt = DelaunayTriangulation.from_points(pts)
vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
hull = convex_hull(pts)

svg = render_svg(width=800, height=600,
    delaunay_edges=dt.edges(), voronoi_edges=vd.edges,
    points=pts, hull=hull)
open("diagram.svg", "w").write(svg)
```

---

## CLI Reference

The CLI has **15 subcommands** (expanded from the original 7):

```bash
# ─── Rendering ──────────────────────────────────────────────
delaunay-voronoi diagram   -n 50 --lloyd 5 -o diagram.svg
delaunay-voronoi animate   -n 30 --lloyd 10 --frame-ms 500 -o anim.svg
delaunay-voronoi compare   -n 20 --lloyd 10 -o compare.svg   # before/after
delaunay-voronoi ppm       -n 15 -w 200 --height 150 -o voronoi.ppm
delaunay-voronoi png       -n 15 -w 200 --height 150 -o voronoi.png

# ─── Mesh Refinement ────────────────────────────────────────
delaunay-voronoi refine    -n 20 --min-angle 30 --max-area 500 -o mesh.svg

# ─── Analysis ───────────────────────────────────────────────
delaunay-voronoi info      -n 30          # quick stats
delaunay-voronoi mesh-stats -n 30         # detailed quality report
delaunay-voronoi mesh-stats -n 30 --json -o report.json
delaunay-voronoi nearest   -n 25 --x 200 --y 150 --knn 5
delaunay-voronoi boundary  -n 30 -v       # boundary edges & loops

# ─── Export ─────────────────────────────────────────────────
delaunay-voronoi json      -n 20 -o mesh.json
delaunay-voronoi from-json mesh.json -o rendered.svg
delaunay-voronoi obj       -n 20 -o mesh.obj
delaunay-voronoi stl       -n 20 -o mesh.stl

# ─── Config ─────────────────────────────────────────────────
delaunay-voronoi config    -o config.json  # generate default config
delaunay-voronoi --config config.json diagram -o diagram.svg
delaunay-voronoi --log-level DEBUG diagram -n 10 -o debug.svg
```

### Global Options

| Flag | Description |
|------|-------------|
| `--config PATH` | Load defaults from a JSON/TOML/YAML config file |
| `--log-level LEVEL` | Set logging verbosity (DEBUG, INFO, WARNING, ERROR) |

---

## Python API

### Core

```python
from delaunay_voronoi import (
    DelaunayTriangulation, VoronoiDiagram, VoronoiCell,
    convex_hull, lloyd_relaxation, generate_poisson_seed,
    ruppert_refine,
    nearest_neighbor, k_nearest_neighbors, locate_point,
    polygon_area, polygon_centroid, point_in_polygon,
    sutherland_hodgman_clip, ear_clip_triangulate,
    render_svg, render_ppm,
    render_animated_svg, render_lloyd_animation,
    save_json, load_json,
    triangulation_to_dict, triangulation_from_dict,
)
from delaunay_voronoi.geometry import Point, Triangle, Edge, Circle, orient2d, incircle
```

### Mesh Quality

```python
from delaunay_voronoi import compute_mesh_report

dt = DelaunayTriangulation.from_points(pts)
report = compute_mesh_report(dt, hull_vertices=len(hull))

print(report.to_text())           # human-readable report
print(report.to_json())           # JSON for pipelines
print(report.min_radius_ratio)    # quality ∈ [0, 1]
print(report.angle_stats.min_deg) # minimum angle in degrees
```

### Export

```python
from delaunay_voronoi import (
    save_obj, export_ascii_stl, save_png,
    extract_boundary_edges, extract_boundary_loops,
)

# 3D mesh formats
save_obj(dt, "mesh.obj")           # Wavefront OBJ
with open("mesh.stl", "w") as f:
    f.write(export_ascii_stl(dt))  # ASCII STL

# Raster image (pure stdlib — no Pillow!)
save_png(800, 600, pts, "voronoi.png")

# Boundary analysis
edges = extract_boundary_edges(dt)
loops = extract_boundary_loops(dt)
```

### Spatial Hash Grid

```python
from delaunay_voronoi import SpatialHashGrid, deduplicate_points

# Fast nearest-neighbour and range queries
grid = SpatialHashGrid.from_points(pts, cell_size=50)
nearest = grid.nearest(query_point)
nearby = grid.points_in_radius(query_point, radius=10.0)

# Remove near-duplicate points
clean = deduplicate_points(pts, tolerance=0.01)
```

### Configuration

```python
from delaunay_voronoi import Config, load_config, save_config

# Load from file
config = load_config("config.json")  # or .toml or .yaml

# Modify and save
config.render.width = 1024
config.algorithm.num_points = 100
save_config(config, "my_config.toml")
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLI (cli.py)                       │
│         15 subcommands · config · logging               │
├─────────────────────────────────────────────────────────┤
│  Config (config.py)    Logging (logging_utils.py)       │
├─────────────────────────────────────────────────────────┤
│                    Core Algorithms                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │Delaunay  │  │ Voronoi  │  │ ConvexHull│  │ Lloyd   │ │
│  │(Bowyer-  │  │ (Dual)   │  │(Monotone │  │(Relax)  │ │
│  │ Watson)  │  │          │  │ Chain)   │  │         │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│  ┌──────────┐  ┌──────────────────────────────────────┐ │
│  │ Ruppert  │  │   Spatial (NN, k-NN, point-in-tri)   │ │
│  │(Refine)  │  │   SpatialHash (grid-accelerated NN)  │ │
│  └──────────┘  └──────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│              Geometry Primitives (geometry.py)           │
│     Point · Edge · Triangle · Circle · Predicates        │
│       orient2d · incircle (exact via Fraction)           │
├─────────────────────────────────────────────────────────┤
│  Rendering        Export           Analysis              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐       │
│  │ SVG      │    │ OBJ      │    │ Mesh Report  │       │
│  │ PPM      │    │ STL      │    │ (metrics.py) │       │
│  │ PNG      │    │ PNG      │    │ Boundary     │       │
│  │ Animated │    │ JSON     │    │ Extraction   │       │
│  └──────────┘    └──────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────┘
```

### How It Works

#### Delaunay Triangulation (Bowyer-Watson)

1. Create a **super-triangle** large enough to contain all input points.
2. For each point to insert:
   - Find all triangles whose **circumcircle** contains the point
     (using the exact `incircle` predicate).
   - Compute the **boundary** of the "bad triangle" cavity (edges
     appearing exactly once).
   - Remove bad triangles and form new triangles from each boundary
     edge to the new point.
3. Remove all triangles touching the super-triangle vertices.

#### Voronoi Diagram (Dual Construction)

- Each **Voronoi vertex** = circumcenter of a Delaunay triangle.
- Each **Voronoi edge** connects circumcenters of two triangles sharing
  a Delaunay edge.
- **Boundary rays** (from triangles with one neighbour) are clipped to
  the bounding box using Liang-Barsky line clipping.

#### Ruppert's Refinement

Repeatedly finds the triangle with the smallest minimum angle (or
largest area) and inserts its circumcenter as a new site, improving
mesh quality until all triangles meet the angle bound or a stall/limit
is reached. Circumcenters are clamped to the bounding box to prevent
divergence.

#### Robust Predicates

The `orient2d` and `incircle` predicates use `fractions.Fraction` for
exact arithmetic. The float path handles the common case quickly; when
the determinant is suspiciously close to zero (relative to coordinate
magnitude), the exact fallback prevents misclassification.

#### Spatial Hash Grid

The `SpatialHashGrid` partitions 2-D space into uniform cells and maps
each cell to the list of points it contains. This turns nearest-neighbour
and range queries from O(n) brute-force scans into O(k) lookups where
*k* is the number of points in nearby cells — typically **10–50× faster**
for large point sets.

---

## Mesh Quality Metrics

The `mesh-stats` command produces a detailed report:

```
============================================================
  MESH QUALITY REPORT
============================================================

  Points:          25
  Triangles:       42
  Edges:           66
  Hull vertices:   6

------------------------------------------------------------
  ANGLE STATISTICS (degrees)
------------------------------------------------------------
  Minimum:          0.70°
  Maximum:        177.95°
  Mean:            60.00°
  Median:          52.25°
  Std dev:         38.38°
  Angles < 20°:    11

  Angle histogram:
      [0.0, 6.7) :    3 ███
    [13.3, 20.0) :    5 █████
    [20.0, 26.7) :   10 ██████████
    ...

------------------------------------------------------------
  QUALITY MEASURES
------------------------------------------------------------
  Min radius ratio:    0.0123  (1.0 = equilateral)
  Min aspect ratio:    0.0456  (1.0 = equilateral)

  Overall grade:        D (poor — needs refinement)
============================================================
```

---

## Export Formats

| Format | Command | Use Case |
|--------|---------|----------|
| **SVG** | `diagram` | Vector diagrams for web/browser |
| **PPM** | `ppm` | Minimal raster (no encoding deps) |
| **PNG** | `png` | Standard raster image (via stdlib `zlib`) |
| **OBJ** | `obj` | 3D mesh for Blender/MeshLab |
| **STL** | `stl` | 3D printing pipelines |
| **JSON** | `json` / `from-json` | Save & reload triangulations |

---

## Configuration

The toolkit supports JSON, TOML, and YAML configuration files:

```bash
# Generate a default config
delaunay-voronoi config -o config.json

# Use it
delaunay-voronoi --config config.json diagram -o out.svg
```

**JSON** example (`config.json`):
```json
{
  "render": { "width": 1024, "height": 768, "background": "#000000" },
  "algorithm": { "num_points": 100, "lloyd_iterations": 10 },
  "log_level": "DEBUG"
}
```

**TOML** example (`config.toml`):
```toml
[render]
width = 1024
height = 768

[algorithm]
num_points = 100
lloyd_iterations = 10
```

See `examples/config.json` and `examples/config.toml` for full examples.

---

## Performance

The spatial hash grid (`SpatialHashGrid`) provides significant speedups
over brute-force for nearest-neighbour queries:

```
Points: 500, Queries: 1000
Brute force: 0.0903s
Spatial hash: 0.0080s
Speedup: 11.3x
```

The `render_ppm` and `render_png` functions both use the spatial hash
for flat-shaded Voronoi rendering, making them practical for larger
images.

Run the benchmark yourself:
```bash
python3 examples/spatial_hash_benchmark.py
```

---

## Examples

The `examples/` directory contains runnable demos:

| Script | Description |
|--------|-------------|
| `generate_diagram.py` | Generate a Delaunay/Voronoi SVG diagram |
| `mesh_quality_report.py` | Print before/after refinement quality reports |
| `export_formats.py` | Export to OBJ, STL, and PNG |
| `spatial_hash_benchmark.py` | Benchmark grid vs brute-force nearest-neighbour |
| `config.json` | Example JSON configuration |
| `config.toml` | Example TOML configuration |

Run them:
```bash
python3 examples/generate_diagram.py
python3 examples/mesh_quality_report.py
python3 examples/export_formats.py
python3 examples/spatial_hash_benchmark.py
```

---

## Tests

The project includes a comprehensive test suite with **125 tests** across
6 test files:

```
tests/
├── test_bug_hunt.py     # 55 tests — original bug-hunt suite
├── test_cli.py          # 20 tests — all CLI subcommands
├── test_exporters.py    # 13 tests — OBJ, STL, PNG, boundary
├── test_spatial_hash.py # 14 tests — spatial hash grid
├── test_metrics.py      # 10 tests — mesh quality metrics
├── test_config.py       #  9 tests — config I/O (JSON, TOML, YAML)
└── test_logging.py      #  4 tests — logging utilities
```

Run the tests:
```bash
python3 -m pytest tests/ -v
```

CI runs on Python 3.10, 3.11, 3.12, and 3.13 via GitHub Actions.

---

## Known Issues (Resolved)

The following bugs were found during the Phase 3 bug hunt and have been
fixed:

1. **`Triangle.circumcircle()` returned a bare tuple instead of `Circle`**
   for degenerate (collinear) triangles. Fixed to always return a `Circle`
   object. *(geometry.py)*

2. **`render_ppm()` crashed on empty point sets.** The empty-points branch
   used `bytes()` on an iterable of tuples (invalid) and a bytes-format `%`
   operator (invalid in Python 3). Fixed to use `f-string` header and
   `bytes(background) * (width * height)` for flat-fill. *(render.py)*

3. **Ruppert's refinement threshold formula was wrong.** The original code
   used `0.5 * sin(2θ)` as the threshold but `_min_angle_sin_ratio` returns
   `sin(min_angle)`, so the comparison was incorrect — the algorithm never
   terminated for reasonable angle targets. Fixed to use
   `sin(min_angle_rad)` directly. *(refine.py)*

4. **Ruppert's refinement could insert circumcenters far outside the input
   domain.** Skinny hull triangles have circumcenters very far from the
   input points, creating even larger triangles and preventing convergence.
   Fixed by clamping inserted circumcenters to the input bounding box.
   *(refine.py)*

5. **Ruppert's stall detection was too aggressive (5 iterations).** The
   stall counter broke out of refinement before making meaningful progress
   on large meshes. Increased to 20. *(refine.py)*

6. **CLI `info` subcommand had an undefined variable `r`.** The min-angle
   computation referenced `r` instead of `min(ratios)`. Fixed. *(cli.py)*

---

## Changelog

### v3.0.0 — Comprehensive Improvement

**New Modules**
- `metrics.py` — mesh quality metrics & reporting (angles, areas, edges,
  radius ratio, aspect ratio, histograms, text/JSON reports, quality grade)
- `spatial_hash.py` — `SpatialHashGrid` for O(k) nearest-neighbour and
  range queries (10–50× faster than brute force)
- `exporters.py` — OBJ, ASCII STL, PNG (via stdlib `zlib`), boundary edge
  and loop extraction
- `config.py` — `Config` dataclass with JSON/TOML/YAML support and a
  minimal built-in YAML parser (no pyyaml required)
- `logging_utils.py` — structured logging with env-var and config support

**New CLI Subcommands** (7 → 15)
- `png` — PNG raster export (stdlib zlib, no Pillow)
- `mesh-stats` — detailed quality report (text or JSON)
- `from-json` — render SVG from a saved JSON triangulation
- `obj` — Wavefront OBJ mesh export
- `stl` — ASCII STL mesh export
- `boundary` — boundary edge/loop extraction
- `compare` — side-by-side before/after Lloyd SVG
- `config` — generate default config files

**Performance**
- `render_ppm` and `render_png` now use `SpatialHashGrid` instead of
  brute-force O(W·H·n) — major speedup for large images/point sets

**Architecture**
- Fixed `pyproject.toml` build backend (`setuptools.build_meta`)
- Added `[project.optional-dependencies]` for dev/yaml extras
- Added `[tool.pytest.ini_options]` configuration
- Full type hints across all new modules
- Comprehensive docstrings

**Testing**
- 55 → 125 tests (70 new tests across 5 new test files)
- Tests for spatial hash, metrics, exporters, config, CLI, logging
- All 125 tests pass

**Tooling**
- GitHub Actions CI workflow (Python 3.10–3.13)
- `CONTRIBUTING.md` with development workflow
- `LICENSE` (MIT)
- Example config files (JSON + TOML)
- 3 new example scripts

### v2.0.0 — Enhance Phase
- Added Ruppert's refinement, spatial queries, polygon utilities,
  animated SVG, JSON serialization, 7-subcommand CLI

### v1.0.0 — Initial Release
- Bowyer-Watson Delaunay, Voronoi dual, convex hull, Lloyd relaxation,
  SVG/PPM rendering, robust predicates

---

## Roadmap

- [ ] **Constrained Delaunay** — support PSLG input with required segments
- [ ] **3-D Delaunay** — tetrahedralization for volumetric meshing
- [ ] **KD-tree** — alternative spatial index for non-uniform point sets
- [ ] **Jump-and-walk** point location — O(√n) expected for large meshes
- [ ] **Parallel Lloyd relaxation** — multi-threaded cell centroid computation
- [ ] **Interactive viewer** — web-based SVG viewer with pan/zoom
- [ ] **PLY export** — Polygon File Format for richer mesh attributes
- [ ] **Mesh smoothing** — Laplacian and optimisation-based smoothers
- [ ] **Delaunay hierarchy** — O(log n) point location for very large meshes
- [ ] **Weighted Voronoi** — power diagrams for anisotropic tessellation

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and pull request guidelines.

Contributions are welcome! The project maintains a **stdlib-only** core —
no required external dependencies. Please ensure all tests pass before
opening a PR:

```bash
python3 -m pytest tests/ -v
```

---

## License

[MIT](LICENSE) — © 2026 creative-projects