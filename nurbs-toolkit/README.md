# NURBS Toolkit

A pure-Python NURBS (Non-Uniform Rational B-Splines) & B-spline CAGD
(Computer-Aided Geometric Design) toolkit. No external dependencies —
only the Python standard library.

## Features

- **B-spline basis functions** via the Cox–de Boor recursion with
  derivative computation (Algorithm A2.3 from *The NURBS Book*).
- **B-spline curves** with evaluation, derivatives, tangents, normals.
- **NURBS curves** with rational weights, evaluation and analytic
  derivatives via the homogeneous quotient rule.
- **Tensor-product NURBS surfaces** with evaluation, partial
  derivatives, surface normals.
- **Bezier curves** with de Casteljau evaluation, degree elevation,
  subdivision, and conversion to B-spline form.
- **Geometric operations**: knot insertion (Boehm's algorithm), knot
  removal, degree elevation, Bezier decomposition.
- **Knot vector utilities**: clamped/unclamped uniform generation,
  validation (length, monotonicity, multiplicity).
- **Curve fitting**: least-squares B-spline approximation with
  chord-length parameterization and averaged interior knots.
- **Point projection**: Newton-based projection of a point onto a
  B-spline curve (coarse sampling + refinement).
- **Arc-length computation** via composite Simpson's rule and
  arc-length parameterization tables.
- **Shape presets**: exact NURBS circle, sphere octant patch, torus,
  cylinder, cone.
- **SVG rendering**: 2-D curve rendering with control polygon overlay
  and 3-D surface wireframe (isometric projection).
- **JSON serialization**: full round-trip for curves and surfaces.
- **Tessellation & export**: curve sampling, surface meshing, OBJ and
  PLY ASCII export.
- **Custom exception hierarchy**: `NURBSError`, `InvalidKnotVector`,
  `InvalidControlPoint`, `InvalidWeight`, `SingularMatrix`.
- **CLI** with subcommands for evaluation, tessellation, surface
  export, knot insertion, degree elevation, and Bezier decomposition.

## Installation

```bash
cd nurbs-toolkit
pip install -e .
```

## Usage

### Python API

```python
from nurbs import (
    BSplineCurve, NURBSCurve, NURBSSurface, BezierCurve,
    generate_clamped_uniform_knot_vector,
    knot_insert, degree_elevate, tessellate_surface, export_obj,
    fit_bspline_curve, project_point, arc_length,
    make_circle, make_torus, make_cylinder,
    curve_to_svg, curve_to_json, curve_from_json,
)

# Cubic Bezier curve as a clamped B-spline
cps = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
knots = generate_clamped_uniform_knot_vector(3, 3)
curve = BSplineCurve(3, knots, cps)
print(curve.evaluate(0.5))  # [2.0, 1.5, 0.0]

# NURBS quarter-circle (weight = 1/sqrt(2) at midpoint)
ncps = [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
weights = [1.0, 0.70710678, 1.0]
nknots = [0, 0, 0, 1, 1, 1]
nurbs = NURBSCurve(2, nknots, ncps, weights)
print(nurbs.evaluate(0.5))  # ~[0.707, 0.707, 0.0]

# Exact full circle (4 segments)
circle = make_circle(1.0, (0, 0), segments=4)
import math
p = circle.evaluate(1.5)
print(math.hypot(p[0], p[1]))  # 1.0 (exact radius)

# Fit a curve to data points
import math
data = [[i, math.sin(i * 0.3), 0] for i in range(10)]
fitted = fit_bspline_curve(data, degree=3, num_control_points=6)

# Project a point onto a curve
u, closest = project_point(fitted, [1.5, 0.5, 0])

# Arc length
length = arc_length(fitted)

# Bilinear surface patch
scps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
surf = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], scps)
verts, faces = tessellate_surface(surf, 20, 20)
print(export_obj(verts, faces))

# Torus surface
torus = make_torus(R=2.0, r=0.5, u_segments=4, v_segments=4)

# SVG rendering
svg = curve_to_svg(curve, samples=50)
with open("curve.svg", "w") as f:
    f.write(svg)

# Serialization
json_str = curve_to_json(curve)
restored = curve_from_json(json_str)
```

### CLI

```bash
# Evaluate a curve
nurbs eval-curve --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5

# Tessellate a curve
nurbs tess-curve --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --samples 50

# Export a surface to OBJ (from JSON spec)
nurbs surface-obj --spec surface.json --samples-u 50 --samples-v 50 -o out.obj

# Knot insertion
nurbs knot-insert --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5 --times 1

# Degree elevation
nurbs degree-elevate --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0" --times 1

# Decompose into Bezier segments
nurbs decompose --degree 3 --knots 0,0,0,0,1,1,1,1 \
    --points "0,0,0;1,2,0;3,2,0;4,0,0"

# Bezier curve evaluation
nurbs bezier --points "0,0,0;1,2,0;3,2,0;4,0,0" --t 0.5

nurbs version
```

## How It Works

### Cox–de Boor Recursion

The B-spline basis functions of degree *p* are defined recursively:

```
N_{i,0}(u) = 1  if U[i] <= u < U[i+1],  else 0
N_{i,p}(u) = (u - U[i]) / (U[i+p] - U[i]) * N_{i,p-1}(u)
           + (U[i+p+1] - u) / (U[i+p+1] - U[i+1]) * N_{i+1,p-1}(u)
```

The implementation uses the efficient triangular computation from
*The NURBS Book* (Piegl & Tiller, 1997), Algorithm A2.2.

### NURBS Curves

A NURBS curve is the projective image of a B-spline in homogeneous
coordinates:

```
C(u) = sum_i N_{i,p}(u) w_i P_i  /  sum_i N_{i,p}(u) w_i
```

Derivatives are computed analytically using the quotient rule on the
homogeneous coordinate derivatives (NURBS Book Eq. 4.14–4.15).

### Exact Circles

A NURBS circle is constructed from arc segments.  For each arc of
angle θ, the middle control point is placed at the intersection of the
tangent lines at the arc endpoints (at distance R/cos(θ/2) from the
center along the bisector) with weight cos(θ/2).  This produces an
*exact* circle, not an approximation.

### Knot Insertion (Boehm's Algorithm)

Inserting a knot *u* into a B-spline curve refines the representation
without changing the curve geometry.  New control points are computed
as affine combinations of adjacent originals.

### Degree Elevation

Degree elevation increases the polynomial degree while preserving the
curve.  The implementation decomposes the curve into Bezier segments,
elevates each segment, then reassembles.

### Curve Fitting

Given data points Q_k, we solve the least-squares problem
``min sum |C(u_k) - Q_k|^2`` by forming the normal equations
``N^T N P = N^T Q`` and solving via Gaussian elimination with partial
pivoting.  Interior knots are positioned by averaging the
chord-length parameters (NURBS Book Eq. 9.68).

## Project Structure

```
nurbs-toolkit/
├── nurbs/
│   ├── __init__.py        # Package exports
│   ├── exceptions.py      # Custom exception hierarchy
│   ├── knot_vector.py     # Knot vector generation & validation
│   ├── bspline.py         # Basis functions, BSplineBasis, BSplineCurve
│   ├── nurbs_curve.py     # NURBSCurve (rational B-splines)
│   ├── nurbs_surface.py   # NURBSSurface (tensor-product)
│   ├── bezier.py          # BezierCurve, bezier_to_bspline
│   ├── operations.py      # Knot insert/remove, degree elevate, decompose
│   ├── fitting.py         # Least-squares curve fitting
│   ├── projection.py      # Point projection, arc length
│   ├── presets.py         # Circle, sphere, torus, cylinder, cone
│   ├── svg_render.py      # SVG curve & wireframe rendering
│   ├── serialization.py   # JSON serialization
│   ├── export.py          # Tessellation, OBJ/PLY export
│   └── cli.py             # argparse CLI
├── examples/
│   ├── fit_curve.py
│   ├── circle.py
│   └── torus_obj.py
├── pyproject.toml
└── README.md
```

## License

MIT