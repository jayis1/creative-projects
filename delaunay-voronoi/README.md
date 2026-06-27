# delaunay-voronoi

A pure-Python computational geometry toolkit implementing Delaunay triangulation, Voronoi diagrams, convex hulls, Lloyd's relaxation, Ruppert's mesh refinement, spatial queries, polygon utilities, and SVG/PPM/animated-SVG rendering — with robust exact-arithmetic geometric predicates.

**No external dependencies.** Uses only the Python standard library (`math`, `fractions`, `dataclasses`, `random`, `json`, `argparse`).

## Features

### Core Algorithms
- **Bowyer-Watson Delaunay triangulation** — incremental insertion with robust in-circle tests
- **Voronoi diagrams** — dual graph construction with Liang-Barsky boundary edge clipping
- **Convex hull** — Andrew's monotone-chain algorithm (O(n log n))
- **Lloyd's relaxation** — centroidal Voronoi tessellation for even point distributions
- **Ruppert's Delaunay refinement** — quality meshing with minimum-angle guarantee and max-area constraint
- **Ear-clip polygon triangulation** — triangulate simple polygons

### Spatial Queries
- **Nearest-neighbour** lookup via walking traversal
- **k-nearest neighbours** by graph distance (BFS on triangulation)
- **Point location** — visibility-walk to find the containing triangle

### Polygon Utilities
- **Area** (shoelace formula), **centroid** (area-weighted)
- **Point-in-polygon** (ray casting)
- **Sutherland-Hodgman clipping** (polygon ∩ convex polygon)
- **Ear clipping triangulation**

### Robust Predicates
- `orient2d` and `incircle` use `fractions.Fraction` for exact arithmetic. The float path handles the common case; an exact fallback prevents misclassification of cocircular/collinear points.

### Rendering
- **SVG** — vector output with layered Delaunay/Voronoi/hull/points
- **Animated SVG** — CSS-keyframe cross-fade between Lloyd relaxation frames
- **PPM** — flat-shaded Voronoi raster (nearest-site colouring)

### Serialization
- **JSON** save/load of triangulations and Voronoi diagrams

## Installation

```bash
cd delaunay-voronoi
python3 -m venv .venv
source .venv/bin/activate
pip install -e .   # optional, installs the `delaunay-voronoi` CLI command
```

Or just import in place without installation.

## Usage

### Command-line (7 subcommands)

```bash
# Generate a Delaunay/Voronoi SVG diagram
python3 -m delaunay_voronoi.cli diagram -n 50 --lloyd 5 -o diagram.svg

# Animated SVG of Lloyd relaxation
python3 -m delaunay_voronoi.cli animate -n 30 --lloyd 10 --frame-ms 500 -o anim.svg

# Ruppert's quality mesh refinement
python3 -m delaunay_voronoi.cli refine -n 20 --min-angle 30 --max-area 500 -o mesh.svg

# Flat-shaded Voronoi PPM raster
python3 -m delaunay_voronoi.cli ppm -n 15 -w 200 --height 150 -o voronoi.ppm

# Print triangulation statistics (min angle, hull, etc.)
python3 -m delaunay_voronoi.cli info -n 30

# Save triangulation as JSON
python3 -m delaunay_voronoi.cli json -n 20 -o mesh.json

# Find nearest site to a query point
python3 -m delaunay_voronoi.cli nearest -n 25 --x 200 --y 150
```

### Python API

```python
from delaunay_voronoi import (
    DelaunayTriangulation, VoronoiDiagram, convex_hull,
    lloyd_relaxation, ruppert_refine,
    nearest_neighbor, k_nearest_neighbors, locate_point,
    polygon_area, polygon_centroid, point_in_polygon,
    sutherland_hodgman_clip, ear_clip_triangulate,
    render_svg, render_ppm, render_lloyd_animation,
    save_json, triangulation_to_dict,
)
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed

# Generate random sites and relax for even spacing
box = (Point(0, 0), Point(800, 600))
pts = generate_poisson_seed(50, box, seed=42)
pts = lloyd_relaxation(pts, iterations=10, clip_box=box, seed=42)

# Build Delaunay and Voronoi
dt = DelaunayTriangulation.from_points(pts)
vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
hull = convex_hull(pts)

# Spatial queries
nn = nearest_neighbor(dt, Point(400, 300))
tri = locate_point(dt, Point(400, 300))

# Quality mesh refinement
refined = ruppert_refine(pts, min_angle_deg=30.0, max_area=200.0)

# Render to SVG
svg = render_svg(width=800, height=600,
    delaunay_edges=dt.edges(), voronoi_edges=vd.edges,
    points=pts, hull=hull)
open("diagram.svg", "w").write(svg)

# Save triangulation as JSON
save_json(triangulation_to_dict(dt), "mesh.json")
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

### Ruppert's Refinement

Repeatedly finds the triangle with the smallest minimum angle (or largest area) and inserts its circumcenter as a new site, improving mesh quality until all triangles meet the angle bound or a stall/limit is reached. Includes stall detection to prevent infinite loops on unconstrained input.

### Robust Predicates

The `orient2d` and `incircle` predicates use `fractions.Fraction` for exact arithmetic. The float path handles the common case quickly; when the determinant is suspiciously close to zero (relative to coordinate magnitude), the exact fallback prevents misclassification.

### Lloyd's Relaxation

Iteratively replaces each site with the centroid of its Voronoi cell, converging toward a **centroidal Voronoi tessellation** (CVT) — producing blue-noise-like even point distributions.

## Project Structure

```
delaunay-voronoi/
├── delaunay_voronoi/
│   ├── __init__.py        # Package exports
│   ├── geometry.py        # Point, Triangle, Edge, Circle, predicates
│   ├── delaunay.py        # Bowyer-Watson triangulation
│   ├── voronoi.py         # Voronoi dual + Liang-Barsky clipping
│   ├── convex_hull.py     # Monotone-chain hull
│   ├── lloyd.py           # Lloyd relaxation + Poisson seeding
│   ├── refine.py          # Ruppert's Delaunay refinement
│   ├── spatial.py         # Nearest-neighbor, k-NN, point location
│   ├── polygon.py         # Area, centroid, point-in-poly, clipping, ear-clip
│   ├── render.py          # SVG + PPM rendering
│   ├── animate.py         # Animated SVG (Lloyd relaxation)
│   ├── serialize.py       # JSON save/load
│   └── cli.py             # Command-line interface (7 subcommands)
├── examples/
│   └── generate_diagram.py
├── tests/
│   └── smoke_test.py
└── pyproject.toml
```

## License

MIT