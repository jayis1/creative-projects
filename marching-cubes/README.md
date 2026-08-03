# mcengine — Isosurface Extraction Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 175](https://img.shields.io/badge/tests-175%20passed-brightgreen.svg)](tests/)
[![Pure Python](https://img.shields.io/badge/pure-Python-no%20deps-success.svg)](#)

A from-scratch isosurface extraction toolkit implementing three classic meshing
algorithms that convert an implicit function `f(x, y, z) = isolevel` into a
triangle mesh. **Pure Python, standard library only — no NumPy required.**

---

## Table of Contents

- [Algorithms](#algorithms)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Configuration Files](#configuration-files)
- [Examples](#examples)
- [Verified Results](#verified-results)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

---

## Algorithms

### Marching Cubes (`MarchingCubes`)
The classic Lorensen–Cline algorithm. Each grid cell is classified by which of
its 8 corners are inside the surface (field < isolevel), producing a 0–255 case
index. A precomputed triangle table (loaded from a verified JSON file generated
from the scikit-image Lorensen–Cline lookup table) determines which edges the
surface crosses and how to triangulate. Edge-crossing vertices are **shared**
across neighbouring cells via a global edge cache, producing watertight,
manifold meshes.

### Marching Tetrahedra (`MarchingTetrahedra`)
Each cube is decomposed into 5 tetrahedra. A tetrahedron has only 16 sign cases
and **no face ambiguity** (triangular faces can't be ambiguous), so the
resulting mesh is always topologically consistent within the tetrahedralization.
The trade-off is ~5× the per-cell work and more triangles.

### Dual Contouring (`DualContouring`)
Places a single vertex per cell that the surface crosses, positioned by
minimising the Quadratic Error Function (QEF) — the sum of squared distances to
the surface's tangent planes at each edge crossing. This produces **much
lower-poly-count** meshes than Marching Cubes while preserving sharp features
(cube edges, octahedron tips). Vertices are connected by quads (split into
triangles) around each crossed grid edge.

## Features

### Core Meshing
- **3 meshing algorithms** with a unified API
- **12+ built-in implicit surfaces**: sphere, torus, octahedron, Steiner
  surface, genus-2, gyroid, heart, superquadric, hyperboloid, noisy variants,
  plus Boolean operations (union/intersection/difference via R-functions)
- **VolumeSampler**: mesh arbitrary 3-D scalar field data via trilinear
  interpolation
- **Watertight meshes**: Marching Cubes produces manifold, watertight meshes
  via edge-vertex sharing
- **Vertex normals**: area-weighted per-vertex normals computed from face
  geometry
- **Analytic gradients**: samplers provide analytic gradients for Dual
  Contouring; numerical fallback via central differences

### Mesh Processing
- **Transforms**: translate, scale, rotate (X/Y/Z), mirror, center,
  normalize-size, merge-meshes
- **Loop subdivision**: refine meshes with the classic Loop scheme (4× faces
  per iteration, preserves topology)
- **Edge-collapse simplification**: reduce triangle count while preserving
  topology
- **ASCII preview**: render a mesh as ASCII art for quick visualisation without
  any graphics dependencies

### File I/O
- **7 export formats**: OBJ, OFF, PLY (ASCII + binary), STL (ASCII + binary),
  glTF 2.0
- **5 import formats**: OBJ, OFF, PLY (ASCII), STL (ASCII + binary)
- **Auto-detect**: `read_mesh()` auto-detects format from file extension

### Tools & Workflow
- **CLI tool**: 10+ subcommands (`render`, `info`, `compare`, `convert`,
  `transform`, `subdivide`, `simplify`, `batch`, `preset`, `list-samplers`,
  `list-presets`)
- **Batch rendering**: execute multiple jobs from a JSON/TOML config file
- **6 built-in presets**: quick-start configurations for common surfaces
- **Configuration files**: JSON or TOML support for declarative rendering
- **Logging**: configurable logging with console and file handlers
- **Mesh diagnostics**: watertightness check, Euler characteristic, genus
  estimation, surface area, bounding box, degenerate face detection, edge
  length statistics

## Installation

```bash
cd marching-cubes
pip install -e .
```

Or just use the package directly by adding the directory to your `PYTHONPATH`.

### From source (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/marching-cubes
pip install -e ".[dev]"  # installs pytest for running tests
```

### Requirements

- Python ≥ 3.10
- No external dependencies (standard library only)
- Optional: `pytest` for running tests, `tomli` for TOML config on Python < 3.11

## Quick Start

### CLI

```bash
# Render a sphere to OBJ
mcengine render --algorithm mc --sampler sphere --resolution 32 --output sphere.obj

# Render a torus to binary STL with ASCII preview
mcengine render -s torus --res 48 -o torus.stl --preview

# Use a preset
mcengine preset gyroid -o gyroid.stl

# Compare all three algorithms
mcengine compare -s sphere --res 32

# Convert OBJ to STL
mcengine convert -i sphere.obj -o sphere.stl

# Transform a mesh
mcengine transform -i sphere.obj -o rotated.obj --rotate-z 1.57 --scale 2

# Subdivide a mesh
mcengine subdivide -i sphere.obj -o smooth.obj --iterations 2

# Batch render from config
mcengine batch -c examples/batch_config.json

# List available samplers and presets
mcengine list-samplers
mcengine list-presets
```

### Python API

```python
from mcengine import (
    MarchingCubes, MarchingTetrahedra, DualContouring,
    SphereSampler, TorusSampler, GyroidSampler, OctahedronSampler,
    analyze_mesh, write_obj, write_stl_binary,
    render_ascii_preview, simplify_mesh, VolumeSampler,
    translate, scale, rotate_z, mirror, merge_meshes, normalize_size,
    loop_subdivide, subdivide_n,
    read_obj, read_mesh,
    render_job, render_preset, get_preset,
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
# Vertices: 2142, Faces: 4280, Euler characteristic: 2, Watertight: True, Genus: 0

# ASCII preview
print(render_ascii_preview(mesh, width=50, height=20))

# Transform: translate, scale, rotate
moved = translate(mesh, 2, 0, 0)
big = scale(mesh, 2, 2, 2)
rotated = rotate_z(mesh, 1.5708)

# Subdivide for smoother mesh
smooth = subdivide_n(mesh, 2)  # 16x faces, same topology

# Simplify
simple = simplify_mesh(mesh, target_faces=500)

# Merge multiple meshes
combined = merge_meshes([mesh, mirror(mesh, "x")])

# Export
write_obj(mesh, "sphere.obj")
write_stl_binary(mesh, "sphere.stl")

# Read mesh back
loaded = read_obj("sphere.obj")
print(f"Loaded: V={loaded.num_vertices}, F={loaded.num_faces}")

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

### Batch rendering from config

```python
from mcengine import render_config

results = render_config("examples/batch_config.json")
for r in results:
    d = r["diagnostics"]
    print(f"{r['name']}: V={d.num_vertices} F={d.num_faces} ({r['elapsed']:.2f}s)")
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `render` | Extract isosurface and export mesh |
| `info` | Print mesh diagnostics from a file |
| `compare` | Compare all 3 algorithms on the same surface |
| `convert` | Convert mesh between file formats |
| `transform` | Apply geometric transformations to a mesh |
| `subdivide` | Subdivide a mesh using Loop subdivision |
| `simplify` | Simplify a mesh using edge-collapse |
| `batch` | Run multiple jobs from a config file |
| `preset` | Render using a built-in preset |
| `list-samplers` | List available implicit surfaces |
| `list-presets` | List available render presets |

Run `mcengine <command> --help` for command-specific options.

## Architecture

```
mcengine/
├── __init__.py              # Public API (60+ exports)
├── cli.py                   # Command-line interface (argparse, 10+ subcommands)
├── mesh.py                  # Mesh dataclass, lerp, normal computation
├── vec3.py                  # 3D vector math (Vec3, cross, dot, normalize)
├── tables.py                # Cube topology, edge table, MC/MT triangle tables
├── mc_triangle_table.json   # Verified 256-entry MC triangle table
├── samplers.py              # 12 implicit surface functions + Boolean ops
├── volume_sampler.py        # Trilinear-interpolated volume data sampler
├── marching_cubes.py        # MC algorithm (vertex sharing, asymptotic decider)
├── marching_tetrahedra.py   # MT algorithm (5-tetrahedra decomposition)
├── dual_contouring.py       # DC algorithm (QEF minimisation, sharp features)
├── export.py                # OBJ/OFF/PLY/STL/glTF writers
├── mesh_io.py               # OBJ/OFF/PLY/STL readers (auto-detect format)
├── diagnostics.py           # Mesh analysis (Euler char, watertight, area, genus)
├── simplify.py              # Edge-collapse mesh simplification
├── subdivision.py           # Loop subdivision (4× faces per iteration)
├── transforms.py            # Geometric transforms (translate, scale, rotate, mirror)
├── ascii_preview.py         # ASCII art mesh renderer
├── config.py                # JSON/TOML config + 6 built-in presets
├── batch.py                 # Batch rendering engine
└── logging_util.py          # Logging utilities

tests/
├── conftest.py              # Shared fixtures and helpers
├── test_mesh.py             # Mesh data structures and lerp tests
├── test_vec3.py             # Vector math tests
├── test_marching_cubes.py   # MC algorithm + table consistency tests
├── test_algorithms.py       # MT and DC algorithm tests
├── test_samplers.py         # All implicit surface tests
├── test_export.py           # Export/import round-trip tests
├── test_diagnostics.py      # Mesh diagnostics tests
├── test_postprocessing.py   # Transform, subdivide, simplify, preview tests
├── test_volume_and_config.py # VolumeSampler, config, batch tests
└── test_cli.py              # CLI integration tests

examples/
├── render_sphere.py         # Basic sphere rendering
├── compare_algorithms.py    # Compare MC/MT/DC on a torus
├── gyroid_surface.py        # Gyroid minimal surface
├── transforms_demo.py       # Mesh transformation showcase
├── subdivision_demo.py      # Loop subdivision showcase
├── mesh_io_demo.py          # File I/O round-trip demo
├── batch_render.py          # Batch rendering from config
└── batch_config.json        # Example batch config (5 jobs)
```

## Configuration Files

The toolkit supports JSON and TOML configuration files for batch rendering.
Each file contains a list of "jobs", each specifying:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | `"unnamed"` | Job name for logging |
| `algorithm` | string | `"mc"` | Meshing algorithm: `mc`, `mt`, or `dc` |
| `sampler` | string | `"sphere"` | Implicit surface name |
| `sampler_params` | object | `{}` | Parameters for the sampler constructor |
| `resolution` | int | `32` | Grid resolution per axis |
| `bounds` | list | `[-1.5, 1.5]` | Bounds: `[lo, hi]` or `[x0,y0,z0,x1,y1,z1]` |
| `isolevel` | float | `0.0` | Isovalue |
| `output` | string | `null` | Output file path |
| `format` | string | auto | Output format (auto-detect from extension) |
| `preview` | bool | `false` | Print ASCII preview |
| `simplify_target` | int | `0` | Simplify to target face count |
| `subdivide` | int | `0` | Loop subdivision iterations |
| `transform` | object | `{}` | Transformations to apply |

Example:

```json
{
  "jobs": [
    {
      "name": "my-sphere",
      "algorithm": "mc",
      "sampler": "sphere",
      "sampler_params": {"radius": 1.5},
      "resolution": 48,
      "bounds": [-2, 2],
      "output": "sphere.obj",
      "preview": true
    }
  ]
}
```

## Examples

```bash
python3 examples/render_sphere.py        # Sphere with ASCII preview
python3 examples/compare_algorithms.py   # Compare MC/MT/DC on a torus
python3 examples/gyroid_surface.py       # Gyroid minimal surface → STL
python3 examples/transforms_demo.py      # Transform showcase
python3 examples/subdivision_demo.py     # Loop subdivision showcase
python3 examples/mesh_io_demo.py         # File I/O round-trip
python3 examples/batch_render.py         # Batch render from config
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
| Sphere (subdivided 2x) | MC 8³ | 1986 | 3968 | ✓ | 2 | 0 |

### ASCII Preview Demo

Sphere (MC 24³):
```
              :..-.-..=::+::=..-.-..:
        :..+::#::+:*::#::+::#::*:+::#::+..:
     .+:*-:*::+::#:+::*-:#:=+::+:#:-+::*:-*-+.
   +-:#:#::#::*::*:*::+-:%:=*::*:*::#::#-:#:@:=+
:--+*:+*-+:=+::*=:+:*::#::+::#::*:+:=*::+=:+=*+:#+--
```

## Known Issues (Resolved)

1. **Binary STL header was 81 bytes instead of 80** — off-by-one in padding
   count. Fixed: changed `b"\x00" * 61` to `b"\x00" * 60` (20-byte string + 60
   zeros = 80 bytes).

2. **Marching Tetrahedra case 15 (all inside) produced spurious triangles** —
   the MT triangle table had non-`-1` entries for the "all corners inside"
   case, causing geometry to be generated when no surface crossing exists.
   Fixed: set case 15 to all `-1` (no surface, matching case 0).

3. **VolumeSampler boundary interpolation error** — clamping to `nx - 1.001`
   caused incorrect values at grid boundaries. Fixed: clamp to `nx - 1.0` and
   handle boundary access by clamping `i0` to `nx - 2`.

4. **Marching Cubes face winding reversed** — face normals pointed inward
   instead of outward due to a winding convention mismatch with the
   skimage-derived triangle table. Fixed: reversed winding to produce outward
   normals.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style
guidelines, and instructions for adding new samplers and export formats.

## Roadmap

- [ ] Transvoxel Marching Cubes for terrain (LOD-aware meshing)
- [ ] Quadric Error Metric (QEM) simplification (higher quality than edge-collapse)
- [ ] Manifold Dual Contouring (guaranteed manifold output)
- [ ] Neural implicit surface support (meshing SDF networks)
- [ ] WebAssembly build for browser-based rendering
- [ ] GUI viewer (tkinter or browser-based)
- [ ] Adaptive resolution (octree-based meshing)
- [ ] UV unwrapping and texture mapping
- [ ] More export formats: FBX, Collada, 3MF
- [ ] Multithreaded field evaluation for high-resolution grids

## Changelog

### v2.0.0 — Comprehensive Improvement

**New Modules**
- `transforms.py` — Mesh transformations: translate, scale, rotate (X/Y/Z),
  mirror, center, normalize-size, merge-meshes
- `subdivision.py` — Loop subdivision scheme for mesh refinement
- `mesh_io.py` — Mesh file readers: OBJ, OFF, PLY (ASCII), STL (ASCII + binary)
  with auto-detect format detection
- `config.py` — JSON/TOML configuration file support with 6 built-in presets
- `batch.py` — Batch rendering engine for multi-job execution
- `logging_util.py` — Configurable logging with console and file handlers

**Enhanced CLI**
- 6 new subcommands: `convert`, `transform`, `subdivide`, `simplify`, `batch`,
  `preset`
- `list-presets` command for viewing built-in presets
- Improved error handling with try/except and descriptive messages
- `--verbose` flag for debug logging
- `--simplify` and `--subdivide` flags on `render` command

**Bug Fixes**
- Fixed binary STL header off-by-one (81→80 bytes)
- Fixed Marching Tetrahedra case 15 (all-inside) producing spurious geometry
- Fixed VolumeSampler boundary interpolation
- Fixed Marching Cubes face winding (inward→outward normals)

**Testing & CI**
- 175 comprehensive tests across 10 test files
- GitHub Actions CI workflow (Python 3.10/3.11/3.12)
- Syntax checking and example verification in CI

**Documentation**
- Comprehensive README with badges, TOC, architecture, roadmap, changelog
- CONTRIBUTING.md with development guidelines
- LICENSE (MIT)
- 7 example scripts + batch config file

### v1.0.0 — Initial Release

- 3 meshing algorithms (MC, MT, DC)
- 12 implicit surface samplers
- 7 export formats
- ASCII preview renderer
- Edge-collapse simplification
- CLI tool with 4 subcommands

## License

MIT