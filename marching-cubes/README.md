# marching-cubes

A from-scratch isosurface extraction toolkit implementing three classic meshing algorithms that convert an implicit function `f(x, y, z) = isolevel` into a triangle mesh. Pure Python, standard library only — no NumPy required.

## Algorithms

### Marching Cubes (`MarchingCubes`)
The classic Lorensen–Cline algorithm. Each grid cell is classified by which of its 8 corners are inside the surface (field < isolevel), producing a 0–255 case index. A precomputed triangle table (loaded from a verified JSON file generated from the scikit-image Lorensen–Cline lookup table) determines which edges the surface crosses and how to triangulate. Edge-crossing vertices are **shared** across neighbouring cells via a global edge cache, producing watertight, manifold meshes.

### Marching Tetrahedra (`MarchingTetrahedra`)
Each cube is decomposed into 5 tetrahedra. A tetrahedron has only 16 sign cases and **no face ambiguity** (triangular faces can't be ambiguous), so the resulting mesh is always topologically consistent within the tetrahedralization. The trade-off is ~5× the per-cell work and more triangles. Note: the 5-tetrahedra decomposition introduces diagonal edges that may not be shared between neighbouring cubes, so the mesh may have seams along certain cell boundaries.

### Dual Contouring (`DualContouring`)
Places a single vertex per cell that the surface crosses, positioned by minimising the Quadratic Error Function (QEF) — the sum of squared distances to the surface's tangent planes at each edge crossing. This produces **much lower-poly-count** meshes than Marching Cubes while preserving sharp features (cube edges, octahedron tips). Vertices are connected by quads (split into triangles) around each crossed grid edge.

## Features

- **3 meshing algorithms** with a unified API
- **12+ built-in implicit surfaces**: sphere, torus, octahedron, Steiner surface, genus-2, gyroid, heart, superquadric, hyperboloid, noisy variants, plus Boolean operations (union/intersection/difference via R-functions)
- **VolumeSampler**: mesh arbitrary 3-D scalar field data via trilinear interpolation
- **7 export formats**: OBJ, OFF, PLY (ASCII + binary), STL (ASCII + binary), glTF 2.0
- **Mesh diagnostics**: watertightness check, Euler characteristic, genus estimation, surface area, bounding box, degenerate face detection, edge length statistics
- **Mesh simplification**: edge-collapse simplifier to reduce triangle count while preserving topology
- **ASCII preview**: render a mesh as ASCII art for quick visualisation without any graphics dependencies
- **CLI tool**: `mcengine` command-line interface with render, info, list-samplers, and compare subcommands
- **Vertex normals**: area-weighted per-vertex normals computed from face geometry
- **Analytic gradients**: samplers provide analytic gradients for Dual Contouring; numerical fallback via central differences
- **Watertight meshes**: Marching Cubes produces manifold, watertight meshes via edge-vertex sharing
- Pure Python, zero dependencies (standard library only)

## Installation

```bash
cd marching-cubes
pip install -e .
```

Or just use the package directly by adding the directory to your `PYTHONPATH`.

## Usage

### CLI

```bash
# Render a sphere to OBJ
mcengine render --algorithm mc --sampler sphere --resolution 32 --output sphere.obj

# Render a torus to binary STL with ASCII preview
mcengine render -s torus --res 48 -o torus.stl --preview

# Compare all three algorithms
mcengine compare -s sphere --res 32

# List available samplers
mcengine list-samplers

# Get info from an OBJ file
mcengine info -i sphere.obj
```

### Python API

```python
from mcengine import (
    MarchingCubes, MarchingTetrahedra, DualContouring,
    SphereSampler, TorusSampler, GyroidSampler,
    analyze_mesh, write_obj, write_stl_binary,
    render_ascii_preview, simplify_mesh, VolumeSampler,
)

# Marching Cubes on a sphere
mc = MarchingCubes(
    SphereSampler(radius=1.0),
    bounds=((-1.5, -1.5, -1.5), (1.5, 1.5, 1.5)),
    resolution=(32, 32, 32),
    isolevel=0.0,
)
mesh = mc.run()
print(f"V={mesh.num_vertices}, F={mesh.num_faces}")

# Diagnostics
d = analyze_mesh(mesh)
print(d.summary())
# Vertices: 1158, Faces: 2312, Euler characteristic: 2, Watertight: True, Genus: 0

# ASCII preview
print(render_ascii_preview(mesh, width=50, height=20))

# Simplify
simple = simplify_mesh(mesh, target_faces=500)
print(f"Simplified: {simple.num_faces} faces")

# Export
write_obj(mesh, "sphere.obj")
write_stl_binary(mesh, "sphere.stl")

# Dual Contouring preserves sharp features
dc = DualContouring(
    OctahedronSampler(1.0),
    bounds=((-1.5, -1.5, -1.5), (1.5, 1.5, 1.5)),
    resolution=(16, 16, 16),
)
mesh = dc.run()  # far fewer triangles than MC

# Boolean operations
from mcengine import BooleanOpsSampler, SphereSampler
s1 = SphereSampler(1.0, center=(0, 0, 0))
s2 = SphereSampler(0.8, center=(0.7, 0, 0))
union = BooleanOpsSampler(s1, s2, op="union")
mc = MarchingCubes(union, resolution=(48, 48, 48))
mesh = mc.run()

# Mesh arbitrary volumetric data
import math
data = [[[math.sqrt((i-4)**2 + (j-4)**2 + (k-4)**2) - 3.0
          for k in range(9)] for j in range(9)] for i in range(9)]
vs = VolumeSampler(data, bounds=((0,0,0), (8,8,8)))
mc = MarchingCubes(vs, bounds=((0,0,0), (8,8,8)), resolution=(32, 32, 32))
mesh = mc.run()
```

### Using a custom implicit function

```python
def my_surface(x, y, z):
    return x**2 + y**2 - z**2 - 1.0  # hyperboloid

mc = MarchingCubes(my_surface, resolution=(32, 32, 32))
mesh = mc.run()
```

## Architecture

```
mcengine/
├── __init__.py              # Public API
├── tables.py               # Cube topology, edge table, triangle table (JSON-loaded)
├── mc_triangle_table.json  # Verified 256-entry MC triangle table
├── mesh.py                 # Mesh dataclass, lerp, normal computation
├── vec3.py                 # 3D vector math (cross, dot, normalize)
├── samplers.py             # 12 implicit surface functions
├── volume_sampler.py       # Trilinear-interpolated volume data sampler
├── marching_cubes.py       # MC algorithm with vertex sharing
├── marching_tetrahedra.py  # MT algorithm with 5-tetrahedra decomposition
├── dual_contouring.py      # DC algorithm with QEF minimisation
├── export.py               # OBJ/OFF/PLY/STL/glTF writers
├── diagnostics.py          # Mesh analysis (Euler char, watertight, area, genus)
├── simplify.py             # Edge-collapse mesh simplification
├── ascii_preview.py        # ASCII art mesh renderer
└── cli.py                  # Command-line interface (argparse)
```

## Examples

```bash
python3 examples/render_sphere.py        # Sphere with ASCII preview
python3 examples/compare_algorithms.py   # Compare MC/MT/DC on a torus
python3 examples/gyroid_surface.py       # Gyroid minimal surface → STL
```

## Verified Results

| Surface | Algorithm | Vertices | Faces | Watertight | χ | Genus |
|---------|-----------|----------|-------|------------|---|-------|
| Sphere (r=1) | MC 24³ | 1158 | 2312 | ✓ | 2 | 0 |
| Sphere (r=1) | DC 16³ | 536 | 1068 | — | — | — |
| Torus (R=1, r=0.35) | MC 32³ | 2904 | 5808 | ✓ | 0 | 1 |
| Gyroid | MC 32³ | 5103 | 9660 | — | — | — |
| Volume data sphere | MC 16³ | 384 | 764 | ✓ | 2 | 0 |
| Sphere (simplified) | MC 32³→500 | 502 | 1000 | — | — | — |

## License

MIT