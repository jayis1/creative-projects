# delaunay-voronoi

A pure-Python computational geometry toolkit implementing Delaunay triangulation, Voronoi diagrams, convex hulls, and Lloyd's relaxation — with robust exact-arithmetic geometric predicates and SVG/PPM rendering.

**No external dependencies.** Uses only the Python standard library (`math`, `fractions`, `dataclasses`, `random`).

## Features

- **Bowyer-Watson Delaunay triangulation** — incremental insertion with robust in-circle tests
- **Voronoi diagrams** — dual graph construction with boundary edge clipping
- **Convex hull** — Andrew's monotone-chain algorithm (O(n log n))
- **Lloyd's relaxation** — centroidal Voronoi tessellation for even point distributions
- **Robust predicates** — `orient2d` and `incircle` use `fractions.Fraction` for exact degeneracy handling
- **Rendering** — SVG (vector) and PPM (raster) output

## Installation

```bash
cd delaunay-voronoi
python3 -m venv .venv
source .venv/bin/activate
```

No pip install needed — the package is imported in place.

## Usage

### Command-line

```bash
# Generate a diagram with 30 random points and 5 Lloyd relaxation iterations
python3 -m delaunay_voronoi.cli -n 30 --lloyd 5 -o diagram.svg

# Options:
#   -n N          number of random sites (default 30)
#   -w WIDTH      image width in pixels (default 800)
#   --height H    image height in pixels (default 600)
#   --seed S      random seed (default 42)
#   --lloyd I     Lloyd relaxation iterations (default 0)
#   -o FILE       output SVG path (default diagram.svg)
#   --no-voronoi  hide Voronoi edges
#   --no-delaunay hide Delaunay edges
```

### Python API

```python
from delaunay_voronoi import (
    DelaunayTriangulation, VoronoiDiagram, convex_hull,
    lloyd_relaxation, render_svg,
)
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed

# Generate random sites
box = (Point(0, 0), Point(800, 600))
pts = generate_poisson_seed(50, box, seed=42)

# Relax for even spacing
pts = lloyd_relaxation(pts, iterations=10, clip_box=box, seed=42)

# Build Delaunay and Voronoi
dt = DelaunayTriangulation.from_points(pts)
vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
hull = convex_hull(pts)

# Render to SVG
svg = render_svg(
    width=800, height=600,
    delaunay_edges=dt.edges(),
    voronoi_edges=vd.edges,
    points=pts,
    hull=hull,
)
open("diagram.svg", "w").write(svg)
```

## How It Works

### Delaunay Triangulation (Bowyer-Watson)

1. Create a **super-triangle** large enough to contain all input points.
2. For each point to insert:
   - Find all triangles whose **circumcircle** contains the point (using the exact `incircle` predicate).
   - Compute the **boundary** of the "bad triangle" cavity (edges appearing exactly once).
   - Remove bad triangles and form new triangles from each boundary edge to the new point.
3. Remove all triangles touching the super-triangle vertices.

### Voronoi Diagram (Dual Construction)

- Each **Voronoi vertex** = circumcenter of a Delaunay triangle.
- Each **Voronoi edge** connects circumcenters of two triangles sharing a Delaunay edge.
- **Boundary rays** (from triangles with one neighbour) are clipped to the bounding box using Liang-Barsky line clipping.

### Robust Predicates

The `orient2d` and `incircle` predicates use `fractions.Fraction` for exact arithmetic. The float path handles the common case quickly; when the determinant is suspiciously close to zero, the exact fallback prevents misclassification of cocircular/collinear points.

### Lloyd's Relaxation

Iteratively replaces each site with the centroid of its Voronoi cell, converging toward a **centroidal Voronoi tessellation** (CVT) — producing blue-noise-like even point distributions.

## Project Structure

```
delaunay-voronoi/
├── delaunay_voronoi/
│   ├── __init__.py        # Package exports
│   ├── geometry.py        # Point, Triangle, Edge, Circle, predicates
│   ├── delaunay.py        # Bowyer-Watson triangulation
│   ├── voronoi.py         # Voronoi dual + clipping
│   ├── convex_hull.py     # Monotone-chain hull
│   ├── lloyd.py           # Lloyd relaxation + Poisson seeding
│   ├── render.py          # SVG + PPM rendering
│   └── cli.py             # Command-line interface
├── examples/
│   └── generate_diagram.py
├── tests/
│   └── smoke_test.py
└── sample_output/
    └── diagram.svg
```

## License

MIT