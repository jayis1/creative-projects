# NURBS Toolkit

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Version](https://img.shields.io/badge/version-3.0.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Tests](https://img.shields.io/badge/tests-105%20passing-brightgreen)
![Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-orange)

> A pure-Python NURBS (Non-Uniform Rational B-Splines) & B-spline CAGD
> (Computer-Aided Geometric Design) toolkit — no external dependencies,
> just the Python standard library.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Configuration](#configuration)
  - [Logging](#logging)
- [Architecture](#architecture)
- [Features](#features)
- [Examples](#examples)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The NURBS Toolkit is a comprehensive, self-contained Python library for
working with NURBS curves and surfaces — the mathematical foundation of
modern CAD/CAM/CAE software. It implements the algorithms from *The NURBS
Book* (Piegl & Tiller, 1997) in pure Python with no external runtime
dependencies.

### What can it do?

- **Design curves and surfaces** — B-splines, NURBS, Bezier curves,
  tensor-product surfaces
- **Analyze geometry** — curvature, torsion, arc length, inflection points,
  point projection
- **Manipulate curves** — knot insertion/removal, degree elevation, offset
  curves, splitting, reversal, concatenation, Bezier decomposition
- **Fit to data** — least-squares curve and surface fitting
- **Create presets** — exact NURBS circles, spheres, tori, cylinders, cones
- **Export meshes** — OBJ, PLY, STL (ASCII & binary)
- **Render** — SVG output for curves and surface wireframes
- **Serialize** — full JSON round-trip for all geometry types
- **Configure** — JSON/TOML/YAML config files

---

## Installation

```bash
cd nurbs-toolkit
pip install -e .
```

With development dependencies (pytest, pytest-cov):

```bash
pip install -e ".[dev]"
```

Optional YAML config support:

```bash
pip install -e ".[yaml]"
```

---

## Quick Start

```python
from nurbs import (
    BSplineCurve, NURBSCurve, make_circle,
    curvature, arc_length, curve_to_svg,
)

# Create an exact NURBS circle
circle = make_circle(1.0, (0, 0), segments=4)

# Analyze it
print(f"Curvature at u=0.5: {curvature(circle, 0.5):.6f}")  # 1.0
print(f"Circumference: {arc_length(circle):.6f}")            # ~6.2832

# Render to SVG
svg = curve_to_svg(circle, samples=200)
```

---

## Usage

### Python API

#### B-spline Curves

```python
from nurbs import BSplineCurve, generate_clamped_uniform_knot_vector

# Cubic B-spline (Bezier with n=p=3)
cps = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
knots = generate_clamped_uniform_knot_vector(3, 3)
curve = BSplineCurve(3, knots, cps)

# Evaluate
print(curve.evaluate(0.5))  # [2.0, 1.5, 0.0]

# Derivatives
print(curve.derivative(0.5, 1))  # first derivative
print(curve.derivative(0.5, 2))  # second derivative

# Tangent and normal
print(curve.tangent(0.5))
print(curve.normal(0.5))
```

#### NURBS Curves (Rational B-splines)

```python
from nurbs import NURBSCurve

# Quarter circle with weights
ncps = [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
weights = [1.0, 1.0 / 2**0.5, 1.0]
nknots = [0, 0, 0, 1, 1, 1]
nurbs = NURBSCurve(2, nknots, ncps, weights)

# Exact circle evaluation
p = nurbs.evaluate(0.5)
print(f"Point: {p}")  # ~[0.707, 0.707, 0.0]
print(f"Radius: {(p[0]**2 + p[1]**2)**0.5:.6f}")  # 1.000000
```

#### NURBS Surfaces

```python
from nurbs import NURBSSurface, tessellate_surface, export_obj

# Bilinear patch
scps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
surf = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], scps)
print(surf.evaluate(0.5, 0.5))  # [0.5, 0.5, 0.0]

# Tessellate and export
verts, faces = tessellate_surface(surf, 20, 20)
print(export_obj(verts, faces))
```

#### Curvature Analysis

```python
from nurbs import curvature, torsion, find_inflections, max_curvature, curvature_plot_data

# Curvature at a point
k = curvature(curve, 0.5)

# Torsion (3-D only)
tau = torsion(curve, 0.5)

# Find inflection points
infl = find_inflections(curve, samples=500)

# Maximum curvature
u_max, k_max = max_curvature(curve)

# Plot data
us, kappas = curvature_plot_data(curve, samples=200)
```

#### Offset Curves

```python
from nurbs import offset_curve

# Offset a 2-D curve by 0.5 units
offset_pts = offset_curve(curve, distance=0.5, samples=100)
```

#### Curve Splitting & Reversal

```python
from nurbs import split_curve, reverse_curve, concatenate_curves

# Split at a parameter
left, right = split_curve(curve, 0.5)

# Reverse direction
rev = reverse_curve(curve)

# Concatenate two curves
merged = concatenate_curves(curve1, curve2)
```

#### Curve Intersection

```python
from nurbs import intersect_curves

# Find intersection points between two curves
results = intersect_curves(curve1, curve2, samples=200)
for u, v, point in results:
    print(f"u={u}, v={v}, point={point}")
```

#### Surface Fitting

```python
from nurbs import fit_bspline_surface

# Fit a surface to a grid of data points
surf = fit_bspline_surface(
    points_grid,
    degree_u=3, degree_v=3,
    num_ctrl_u=6, num_ctrl_v=6,
)
```

#### Shape Presets

```python
from nurbs import (
    make_circle, make_torus, make_cylinder, make_cone, make_sphere_patch,
)

circle = make_circle(2.0, (0, 0), segments=4)
torus = make_torus(R=3.0, r=1.0, u_segments=4, v_segments=4)
cylinder = make_cylinder(1.0, 2.0, segments=4)
cone = make_cone(1.0, 2.0, segments=4)
sphere = make_sphere_patch(1.0)
```

#### STL Export

```python
from nurbs import make_torus, tessellate_surface
from nurbs.stl_export import export_stl_ascii, export_stl_binary

torus = make_torus(3.0, 1.0)
verts, faces = tessellate_surface(torus, 40, 40)

# ASCII STL
stl_text = export_stl_ascii(verts, faces)

# Binary STL
stl_bytes = export_stl_binary(verts, faces)
```

#### JSON Serialization

```python
from nurbs import curve_to_json, curve_from_json, surface_to_json, surface_from_json

# Serialize
json_str = curve_to_json(curve)

# Deserialize
restored = curve_from_json(json_str)
```

#### SVG Rendering

```python
from nurbs import curve_to_svg, surface_to_svg_wireframe

# 2-D curve → SVG
svg = curve_to_svg(curve, samples=100, width=600, height=400)

# 3-D surface → wireframe SVG
svg = surface_to_svg_wireframe(torus, 20, 20)
```

### CLI

The toolkit provides a comprehensive CLI with 30+ subcommands:

```bash
# Evaluation
nurbs eval-curve --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5
nurbs eval-derivative --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5 --order 1

# Curvature analysis
nurbs curvature --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0" --u 0.5
nurbs curvature-plot --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0" -o curvature.json
nurbs inflections --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0"
nurbs max-curvature --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0"

# Offset curves
nurbs offset --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0" --distance 0.5

# Split & reverse
nurbs split --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5
nurbs reverse --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0"

# Intersection
nurbs intersect --degree 1 --knots 0,0,1,1 --points "0,0;1,1" \
    --degree2 1 --knots2 0,0,1,1 --points2 "0,1;1,0"

# Fitting
nurbs fit-curve --data "0,0,0;1,1,0;2,0.5,0;3,1,0;4,0,0" --degree 3 --num-cp 4

# Projection
nurbs project --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --point "1.5,0.5,0"

# Arc length
nurbs arc-length --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0" --samples 1000

# Presets
nurbs preset-circle --radius 2 --segments 4
nurbs preset-torus --R 3 --r 1 --u-segs 4 --v-segs 4
nurbs preset-cylinder --radius 1 --height 2 --segments 4
nurbs preset-cone --radius 1 --height 2 --segments 4
nurbs preset-sphere --radius 1

# Surface export
nurbs surface-obj --spec surface.json --samples-u 50 --samples-v 50 -o out.obj
nurbs surface-stl --spec surface.json --samples-u 50 --samples-v 50 -o out.stl --binary

# Rendering
nurbs render-svg --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0;1,2;3,2;4,0" --samples 200 -o curve.svg

# Serialization
nurbs serialize --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0"
nurbs deserialize --file curve.json --u 0.5

# Knot operations
nurbs knot-insert --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5 --times 1
nurbs degree-elevate --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --times 1
nurbs decompose --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0"

# Bezier
nurbs bezier --points "0,0,0;1,2,0;3,2,0;4,0,0" --t 0.5

# Config
nurbs config --save-config nurbs.json
nurbs version
```

### Configuration

The toolkit supports configuration files in JSON, TOML, and YAML formats:

```python
from nurbs import NURBSConfig

# Create custom config
cfg = NURBSConfig()
cfg.tessellation.curve_samples = 500
cfg.tessellation.surface_samples_u = 100
cfg.tessellation.surface_samples_v = 100
cfg.export.format = "stl_binary"
cfg.export.precision = 8
cfg.fitting.degree = 5
cfg.fitting.num_control_points = 10
cfg.logging.level = "DEBUG"

# Save
cfg.save("nurbs_config.json")

# Load
cfg = NURBSConfig.from_file("nurbs_config.json")
```

Example JSON config:

```json
{
  "tessellation": {
    "curve_samples": 500,
    "surface_samples_u": 100,
    "surface_samples_v": 100
  },
  "export": {
    "format": "stl_binary",
    "precision": 8,
    "flip_faces": false
  },
  "fitting": {
    "degree": 5,
    "num_control_points": 10,
    "method": "least_squares"
  },
  "logging": {
    "level": "DEBUG",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "file": null
  }
}
```

### Logging

```python
from nurbs import get_logger

log = get_logger("my_app", level="DEBUG", log_file="nurbs.log")
log.info("Processing curve...")
log.debug(f"Degree: {curve.degree}")
log.warning("High curvature detected")
```

JSON log format is also available:

```python
log = get_logger("my_app", level="INFO", use_json=True)
```

---

## Architecture

```
nurbs-toolkit/
├── nurbs/
│   ├── __init__.py          # Package exports (all public API)
│   ├── exceptions.py        # Custom exception hierarchy
│   ├── knot_vector.py       # Knot vector generation & validation
│   ├── bspline.py           # Basis functions, BSplineBasis, BSplineCurve
│   ├── nurbs_curve.py       # NURBSCurve (rational B-splines)
│   ├── nurbs_surface.py     # NURBSSurface (tensor-product)
│   ├── bezier.py            # BezierCurve, bezier_to_bspline
│   ├── operations.py        # Knot insert/remove, degree elevate, decompose
│   ├── fitting.py           # Least-squares curve fitting
│   ├── surface_fitting.py   # Least-squares surface fitting
│   ├── projection.py        # Point projection, arc length
│   ├── curvature.py         # Curvature, torsion, inflections, comb
│   ├── offset.py            # Offset, reverse, split, concatenate
│   ├── trimming.py          # Curve intersection, trimming loops
│   ├── presets.py           # Circle, sphere, torus, cylinder, cone
│   ├── export.py            # Tessellation, OBJ/PLY export
│   ├── stl_export.py        # STL export (ASCII & binary)
│   ├── svg_render.py        # SVG curve & wireframe rendering
│   ├── serialization.py     # JSON serialization
│   ├── config.py            # Configuration management (JSON/TOML/YAML)
│   ├── logging_utils.py     # Structured logging with JSON support
│   └── cli.py               # Enhanced argparse CLI (30+ subcommands)
├── tests/
│   ├── test_nurbs.py        # Original 73 tests
│   └── test_new_features.py # 32 new feature tests
├── examples/
│   ├── circle.py            # NURBS circle verification
│   ├── fit_curve.py         # Curve fitting + SVG rendering
│   ├── torus_obj.py         # Torus → OBJ export
│   ├── curvature_analysis.py # Curvature analysis demo
│   ├── offset_split_reverse.py # Offset, split, reverse, concatenate
│   ├── intersection_trimming.py # Curve intersection & trimming
│   ├── surface_fit_stl.py   # Surface fitting + STL export
│   └── config_and_logging.py # Configuration & logging demo
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI (Python 3.10-3.13)
├── pyproject.toml           # Package metadata, pip-installable
├── CONTRIBUTING.md          # Contribution guidelines
├── LICENSE                  # MIT license
└── README.md                # This file
```

### Module Dependencies

```
knot_vector.py ← bspline.py ← nurbs_curve.py ← nurbs_surface.py
                                    ↓
              bezier.py    operations.py   fitting.py   surface_fitting.py
                  ↓             ↓               ↓               ↓
              export.py   stl_export.py   projection.py   curvature.py
                  ↓             ↓               ↓               ↓
            svg_render.py  serialization.py   offset.py    trimming.py
                  ↓             ↓               ↓               ↓
                     config.py  logging_utils.py  cli.py  __init__.py
```

---

## Features

### Core Geometry
| Feature | Description |
|---------|-------------|
| B-spline basis | Cox–de Boor recursion with derivatives (Algorithm A2.3) |
| BSplineCurve | Evaluation, derivatives, tangents, normals |
| NURBSCurve | Rational weights, analytic derivatives via quotient rule |
| NURBSSurface | Tensor-product with normals, partial derivatives |
| BezierCurve | De Casteljau evaluation, elevation, subdivision |

### Geometric Operations
| Feature | Description |
|---------|-------------|
| Knot insertion | Boehm's algorithm — refine without changing geometry |
| Knot removal | Remove redundant knots within tolerance |
| Degree elevation | Increase polynomial degree, preserve curve |
| Bezier decomposition | Split B-spline into Bezier segments |
| Offset curves | Parallel curves at fixed distance (2-D & 3-D) |
| Split / reverse / concatenate | Curve manipulation operations |

### Analysis
| Feature | Description |
|---------|-------------|
| Curvature | Geometric curvature κ (2-D & 3-D) |
| Torsion | Torsion τ for 3-D curves |
| Inflection detection | Sign-change based inflection point finding |
| Curvature comb | Osculating-plane normal teeth for visualization |
| Max curvature | Find maximum curvature parameter |
| Arc length | Composite Simpson's rule |
| Point projection | Newton-based projection with coarse sampling |

### Fitting & Intersection
| Feature | Description |
|---------|-------------|
| Curve fitting | Least-squares with chord-length parameterization |
| Surface fitting | Tensor-product least-squares surface fitting |
| Curve intersection | Bounding-box + Newton refinement |
| Trimming loops | 2-D parameter-space trimming with winding number |

### Export & Rendering
| Feature | Description |
|---------|-------------|
| OBJ export | Wavefront OBJ mesh format |
| PLY export | ASCII PLY mesh format |
| STL export | ASCII and binary STL |
| SVG rendering | 2-D curves with control polygon, 3-D wireframes |
| JSON serialization | Full round-trip for curves and surfaces |

### Infrastructure
| Feature | Description |
|---------|-------------|
| Configuration | JSON / TOML / YAML config files |
| Logging | Structured logging with JSON formatter |
| CLI | 30+ subcommands with argparse |
| Exception hierarchy | NURBSError, InvalidKnotVector, InvalidControlPoint, ... |
| CI | GitHub Actions (Python 3.10–3.13) |

---

## Examples

### ASCII Demo: Circle Curvature

```
=== Curvature Analysis of a Unit Circle ===
Expected curvature: 1.0 (κ = 1/R)

  u=0.0: point=(1.0000, 0.0000), κ=1.000000
  u=0.5: point=(0.7071, 0.7071), κ=1.000000
  u=1.0: point=(0.0000, 1.0000), κ=1.000000
  u=1.5: point=(-0.7071, 0.7071), κ=1.000000

Max curvature: κ=1.000000 at u=3.1311
Inflection points: 0 found
```

### ASCII Demo: Curve Splitting

```
=== Split at u=0.5 ===
  Left:  degree=3, range=(0.0, 0.5), cps=4
  Right: degree=3, range=(0.5, 1.0), cps=4
  Junction: left_end=[2.0, 2.25, 0.0], right_start=[2.0, 2.25, 0.0]
```

Run the examples:

```bash
python3 examples/circle.py
python3 examples/curvature_analysis.py
python3 examples/offset_split_reverse.py
python3 examples/intersection_trimming.py
python3 examples/surface_fit_stl.py
python3 examples/config_and_logging.py
python3 examples/fit_curve.py
python3 examples/torus_obj.py
```

---

## Changelog

### v3.0.0 — Comprehensive Improvement (2026-08-17)

**New modules:**
- `curvature.py` — curvature κ, torsion τ, inflection detection, curvature
  comb, max curvature, curvature plot data
- `offset.py` — offset curves (2-D & 3-D), curve reversal, splitting,
  concatenation
- `trimming.py` — curve–curve intersection (Newton refinement),
  TrimmingLoop with winding-number inside test
- `surface_fitting.py` — least-squares tensor-product B-spline surface
  fitting
- `stl_export.py` — ASCII and binary STL mesh export
- `config.py` — NURBSConfig dataclass with JSON/TOML/YAML support
- `logging_utils.py` — structured logging with JSON formatter

**Enhanced CLI:**
- Expanded from 8 to 30+ subcommands
- New: `curvature`, `curvature-plot`, `inflections`, `max-curvature`,
  `offset`, `split`, `reverse`, `intersect`, `fit-curve`, `project`,
  `arc-length`, `preset-circle/torus/cylinder/cone/sphere`,
  `render-svg`, `render-surface-svg`, `serialize`, `deserialize`,
  `config`, `eval-derivative`, `surface-stl`
- Error handling with structured logging

**Improved package:**
- `pyproject.toml` updated: v3.0.0, keywords, classifiers, optional deps
- `__init__.py` expanded to export all new APIs
- 32 new tests (105 total, all passing)
- 5 new example scripts (8 total)
- GitHub Actions CI (Python 3.10–3.13)
- LICENSE (MIT)
- CONTRIBUTING.md

### v2.0.0 — Enhanced (bug hunt + enhancements)
- Curve fitting, point projection, arc length, shape presets
- SVG rendering, JSON serialization, custom exceptions
- 73 tests, 3 bugs fixed

### v1.0.0 — Initial release
- B-spline basis, curves, NURBS curves & surfaces, Bezier curves
- Knot operations, tessellation, OBJ/PLY export, CLI

---

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and
have been fixed:

1. **`basis_functions_derivatives` crash on order > degree**
   (`nurbs/bspline.py`): Requesting a derivative of order higher than
   the spline degree caused an `IndexError` because the internal
   `ders` array was sized to `min(n_derivatives, p) + 1` rows but the
   computation loop iterated up to `n_derivatives`.  **Fix**: Allocate
   `n_derivatives + 1` rows (higher orders remain zero since
   derivatives of order > p are identically zero for B-splines), and
   cap the computation loop at `du = min(n_derivatives, p)`.
   *Test: `test_derivative_zero_at_endpoint_bezier`*

2. **`decompose_bezier_segments` infinite re-processing of knots**
   (`nurbs/operations.py`): After inserting a knot to raise its
   multiplicity to `p` (for Bezier decomposition), the loop index
   advancement (`i = j`) didn't skip past the newly-inserted
   occurrences.  On the next iteration the same knot value was
   encountered again, causing additional insertions that pushed
   multiplicity beyond `p + 1` and triggered a validation error.
   **Fix**: After each insertion, advance `i` past *all* occurrences
   of the processed knot value in the updated knot vector.  Also skip
   knots that already have full multiplicity `p + 1` (end knots).
   *Test: `test_decompose_multi_segment`*

3. **`make_sphere_patch` produced non-spherical geometry**
   (`nurbs/presets.py`): The sphere octant control net used incorrect
   revolution control point coordinates.  The middle revolution
   control point was placed at `(w, w)` (the point on the circle)
   instead of `(1, 1)` (the tangent-line intersection).  This caused
   the surface to deviate from a true sphere — interior points had
   radii as low as 0.76 instead of 1.0.  **Fix**: Use the correct
   tangent-intersection control points `(1, 0), (1, 1), (0, 1)` with
   weights `(1, 1/√2, 1)` for the revolution direction.  All evaluated
   points now lie exactly on the sphere (radius = 1.0 within machine
   precision).
   *Test: `test_sphere_patch`*

---

## Roadmap

- **NURBS volume** (trivariate) support
- **Gaussian quadrature** for higher-accuracy arc length & area
- **Surface–surface intersection** (SSI)
- **Boolean operations** on NURBS surfaces (union, difference, intersection)
- **IGES/STEP file format** import/export
- **Adaptive tessellation** with curvature-based refinement
- **Multi-threaded** surface tessellation
- **NumPy acceleration** (optional backend for large meshes)
- **WebGL viewer** for interactive 3-D visualization

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and architecture guidelines.

---

## License

MIT