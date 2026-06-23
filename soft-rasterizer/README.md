# soft-rasterizer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 159](https://img.shields.io/badge/tests-159%20passing-brightgreen.svg)](#tests)
[![Pure Python](https://img.shields.io/badge/pure-Python-no%20deps-success.svg)](#technical-details)

A from-scratch software 3D rasterizer in pure Python — no OpenGL, no NumPy, no
external graphics libraries. Implements the complete fixed-function rendering
pipeline from vertex transformation to per-pixel shading, with 10 shading
models, texture mapping, JSON scene configuration, post-processing effects,
turntable animation, and multi-format image output.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [JSON Scene Configuration](#json-scene-configuration)
  - [Loading OBJ Files](#loading-obj-files)
  - [Animation](#animation)
  - [Post-Processing](#post-processing)
- [How It Works](#how-it-works)
  - [Rendering Pipeline](#rendering-pipeline)
  - [Shading Models](#shading-models)
  - [Coordinate System](#coordinate-system)
- [Architecture](#architecture)
- [Examples](#examples)
- [Tests](#tests)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

### Core Rendering Pipeline
- **Complete rendering pipeline**: vertex shader → near-plane clipping → perspective divide → viewport transform → scanline rasterization → z-buffer test → fragment shader
- **Z-buffer (depth buffer)**: per-pixel depth testing for correct visibility
- **Perspective-correct interpolation**: all vertex attributes (normals, UVs, colours) interpolated with proper `1/w` weighting
- **Near-plane clipping**: Sutherland-Hodgman polygon clipping against the near plane
- **Backface culling**: screen-space winding-order test (correctly accounts for Y-axis flip)
- **Frustum culling**: broad-phase bounding-sphere test against the view frustum
- **Fragment discard**: shaders can discard fragments (e.g., wireframe interior) via a `DISCARD` sentinel — the renderer skips framebuffer writes for discarded fragments

### Shading Models (10)
| Shader | Lighting | Description |
|--------|----------|-------------|
| **Flat** | Per-face | One colour per triangle (lighting at face centroid) |
| **Gouraud** | Per-vertex | Lighting computed at vertices, colour interpolated |
| **Phong** | Per-pixel | Interpolated normals, per-fragment lighting with specular |
| **Toon (Cel)** | Quantised | Cartoon-like discrete bands with silhouette outlines |
| **Wireframe** | None | Edge-only rendering with fragment discard |
| **Normal** | None | Visualise normals as RGB (debugging) |
| **Depth** | None | Greyscale depth visualisation |
| **Fog** | Wrapper | Exponential distance-based fog around any shader |
| **Crosshatch** | NPR | Pen-and-ink illustration look with hatching patterns |
| **Matcap** | Texture | Material capture — normal-mapped sphere texture lookup |

### Textures & Materials
- **Nearest-neighbour and bilinear sampling** with clamp-to-edge wrapping
- **Mipmapping**: `MipTexture` with pre-computed mipmap chain and LOD-based level selection
- **Procedural checkerboard texture** with configurable colours
- **Phong illumination model**: ambient + diffuse (Lambertian) + specular (Phong) with multiple point/directional lights, distance attenuation

### Geometry
- **7 primitive mesh generators**: cube, sphere, plane, cylinder, torus, tetrahedron, octahedron
- **OBJ file loading**: Wavefront OBJ parser with `v`/`vt`/`vn`/`f` support and fan triangulation
- **OBJ export**: Save meshes back to OBJ format
- **Mesh operations**: translate, scale, merge, compute normals, bounds

### Scene Management
- **Scene graph**: objects with position/rotation/scale transforms, cameras, lights
- **JSON scene configuration**: define complete scenes in JSON files (cameras, lights, objects, shaders, materials, textures, fog)
- **Gradient backgrounds**: vertical gradient between two colours
- **Scene template generator**: `soft-rasterizer template` writes a starter JSON config

### Output
- **PPM (P6 binary)**: portable pixmap format
- **BMP (24-bit BGR)**: widely supported by browsers and image viewers
- **ASCII preview**: render to terminal as ASCII art for quick debugging
- **Auto-format detection**: `renderer.save("output.bmp")` picks format from extension

### Post-Processing
- **Grayscale**: luminance conversion (Rec. 601 weights)
- **Edge detection**: Sobel operator with configurable threshold
- **Vignette**: configurable radial darkening at edges

### Animation
- **Turntable animation**: multi-frame rendering with camera orbit and/or object rotation
- **Multiple output formats**: PPM or BMP frames
- **State restoration**: camera and object transforms are restored after rendering

### Developer Experience
- **Logging**: configurable logging via Python `logging` module
- **Type hints**: throughout the codebase
- **Input validation**: all public APIs validate inputs and raise descriptive errors
- **159-test suite**: comprehensive pytest tests covering math, rendering, shaders, config, animation
- **Installable**: `pip install -e .` with entry point `soft-rasterizer`
- **CLI tool**: `soft-rasterizer render`, `animate`, `list`, `template` subcommands

---

## Installation

```bash
cd soft-rasterizer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the `soft-rasterizer` command-line tool and the `soft_rasterizer` Python package.

**Requirements**: Python 3.10+ (uses `match` syntax, `|` type unions). No external dependencies for the core package; `pytest` only for running tests.

---

## Quick Start

### Render a cube in one command

```bash
soft-rasterizer render -o cube.ppm -p cube -s phong
```

### Render with the Python API

```python
from soft_rasterizer import Renderer, Scene, Camera, Light, Object3D, Vec3, PhongShader
from soft_rasterizer.primitives import make_cube

scene = Scene()
scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3), intensity=0.8))
camera = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=60)
scene.add(Object3D(make_cube(2.0), shader=PhongShader()))

renderer = Renderer(320, 240)
renderer.render(scene, camera)
renderer.save("cube.ppm")
```

---

## Usage

### Python API

#### Basic Rendering

```python
from soft_rasterizer import (
    Renderer, Scene, Camera, Light, Object3D,
    Vec3, PhongShader, PhongMaterial, CheckerTexture,
)
from soft_rasterizer.primitives import make_cube

# Create a scene with lights
scene = Scene()
scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.8))
scene.lights.append(Light.point(Vec3(5, 5, 5), Vec3(0.4, 0.4, 0.6), 0.5))

# Gradient background
scene.background = Vec3(0.02, 0.02, 0.05)
scene.background_top = Vec3(0.08, 0.08, 0.15)

# Camera
camera = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=60)

# Create a textured cube
cube = make_cube(size=2.0)
cube.texture = CheckerTexture(squares=4)
material = PhongMaterial(
    diffuse=Vec3(0.9, 0.7, 0.5),
    specular=Vec3(0.9, 0.9, 0.9),
    shininess=64,
    ambient=Vec3(0.2, 0.2, 0.2),
)
obj = Object3D(cube, shader=PhongShader(material=material),
               rotation=Vec3(0.3, 0.8, 0))
scene.add(obj)

# Render and save
renderer = Renderer(640, 480)
renderer.render(scene, camera)
renderer.save_ppm("output.ppm")
# or: renderer.save_bmp("output.bmp")
# or: renderer.save("output.bmp")  # auto-detects format
```

#### Multiple Objects with Different Shaders

```python
from soft_rasterizer import (
    ToonShader, NormalShader, FogShader,
)
from soft_rasterizer.primitives import make_sphere, make_torus

# Phong cube (left)
scene.add(Object3D(
    make_cube(1.5),
    shader=PhongShader(material=PhongMaterial(diffuse=Vec3(0.8, 0.7, 0.5))),
    position=Vec3(-2, 0, 0),
))

# Toon sphere (center)
scene.add(Object3D(
    make_sphere(1.0, segments=20, rings=14),
    shader=ToonShader(material=PhongMaterial(diffuse=Vec3(0.9, 0.5, 0.3)),
                      bands=4),
    position=Vec3(0, 0, 0),
))

# Normal-viz torus (right) with fog
scene.add(Object3D(
    make_torus(0.7, 0.25),
    shader=FogShader(NormalShader(), density=0.05),
    position=Vec3(2, 0, 0),
))
```

#### Accessing Render Statistics

```python
renderer = Renderer(640, 480)
renderer.render(scene, camera)

stats = renderer.stats
print(f"Triangles: {stats['triangles_rasterized']} rasterized")
print(f"Fragments: {stats['fragments_processed']} shaded, "
      f"{stats['fragments_discarded']} discarded")
print(f"Culling: {stats['objects_frustum_culled']} objects, "
      f"{stats['triangles_culled']} triangles")
```

### CLI

```bash
# Render a Phong-shaded sphere
soft-rasterizer render -o sphere.bmp -p sphere -s phong --width 640 --height 480

# Render a textured cube from a specific angle
soft-rasterizer render -o cube.ppm -p cube -s phong --texture checker \
    --angle 0.8 --distance 5 --cam-height 2 --rotation 0.5

# Render a toon-shaded sphere with 4 colour bands
soft-rasterizer render -o toon.ppm -p sphere -s toon --bands 4

# Render with fog effect
soft-rasterizer render -o fog.ppm -p torus -s phong --fog --fog-density 0.08

# Render a crosshatch sphere (pen-and-ink style)
soft-rasterizer render -o hatch.bmp -p sphere -s crosshatch

# Render an OBJ file
soft-rasterizer render -o model.ppm --obj model.obj -s gouraud

# Normal visualization (debugging)
soft-rasterizer render -o normals.ppm -p torus -s normal

# Render with gradient background
soft-rasterizer render -o cube.bmp -p cube -s phong \
    --bg-gradient 0.1 0.1 0.3 0.02 0.02 0.05

# Render with post-processing
soft-rasterizer render -o stylized.bmp -p sphere -s phong \
    --edge --edge-threshold 0.15 --vignette --vignette-strength 0.6

# Render with statistics
soft-rasterizer render -o cube.ppm -p cube -s phong --stats

# ASCII preview (quick debugging without opening an image viewer)
soft-rasterizer render -o /dev/null -p cube -s phong --ascii

# Render from a JSON scene config
soft-rasterizer render --scene examples/multi_object_scene.json -o scene.bmp

# List available primitives and shaders
soft-rasterizer list

# Generate a template JSON scene file
soft-rasterizer template -o my_scene.json
```

### JSON Scene Configuration

Define complete scenes declaratively in JSON:

```json
{
  "camera": {
    "position": [0, 3, 6],
    "target": [0, 0, 0],
    "fov": 50
  },
  "lights": [
    {"type": "directional", "direction": [-0.3, -1, -0.5],
     "color": [1, 0.95, 0.8], "intensity": 0.9},
    {"type": "point", "position": [-3, 2, 3],
     "color": [0.3, 0.5, 1.0], "intensity": 0.6}
  ],
  "background": [0.02, 0.02, 0.05],
  "background_top": [0.1, 0.08, 0.2],
  "objects": [
    {
      "primitive": "sphere",
      "size": 1.2,
      "segments": 24,
      "rings": 16,
      "shader": {
        "name": "toon",
        "bands": 4,
        "material": {"diffuse": [0.8, 0.4, 0.3]}
      },
      "position": [-1.5, 0, 0]
    },
    {
      "primitive": "torus",
      "size": 0.8,
      "minor_radius": 0.25,
      "shader": {
        "name": "phong",
        "material": {
          "diffuse": [0.3, 0.6, 0.9],
          "shininess": 128
        }
      },
      "position": [1.5, 0, 0]
    }
  ]
}
```

Load and render:

```python
from soft_rasterizer import Renderer, SceneConfig

scene, camera = SceneConfig.load("my_scene.json")
renderer = Renderer(400, 300)
renderer.render(scene, camera)
renderer.save("output.bmp")
```

Or via CLI:

```bash
soft-rasterizer render --scene my_scene.json -o output.bmp
```

### Loading OBJ Files

```python
from soft_rasterizer import OBJLoader, Object3D, PhongShader

mesh = OBJLoader.load("model.obj")
mesh.compute_smooth_normals()  # if normals aren't in the file
obj = Object3D(mesh, shader=PhongShader())
scene.add(obj)
```

Export a mesh to OBJ:

```python
OBJLoader.save(mesh, "output.obj")
```

### Animation

Render a turntable animation (36 frames, one full rotation):

```python
from soft_rasterizer import Renderer, Scene, Camera, AnimationBuilder

renderer = Renderer(240, 180)
builder = AnimationBuilder(renderer, scene, camera)

files = builder.render_turntable(
    output_dir="frames/",
    frames=36,
    fmt="bmp",
    prefix="frame",
)
```

Or via CLI:

```bash
soft-rasterizer animate -o frames/ -p torus -s phong -n 36 --format bmp
```

Assemble into a GIF (requires ImageMagick):

```bash
convert -delay 10 -loop 0 frames/frame_*.bmp animation.gif
```

### Post-Processing

```python
from soft_rasterizer import Renderer, post_edge_detect, post_vignette, post_grayscale

renderer = Renderer(400, 300)
renderer.render(scene, camera)

# Apply effects (in-place on the framebuffer)
post_edge_detect(renderer.framebuffer, threshold=0.15)
post_vignette(renderer.framebuffer, strength=0.6)
# post_grayscale(renderer.framebuffer)  # optional

renderer.save("stylized.bmp")
```

### Available Primitives

| Primitive | Parameters | Description |
|-----------|-----------|-------------|
| `cube` | `size` | Unit cube with per-face normals |
| `sphere` | `radius`, `segments`, `rings` | UV sphere |
| `plane` | `size`, `divisions` | Flat plane on Y=0 |
| `cylinder` | `radius`, `height`, `segments` | Cylinder along Y axis with caps |
| `torus` | `major_radius`, `minor_radius`, `major_segments`, `minor_segments` | Torus (donut) |
| `tetrahedron` | `size` | Regular tetrahedron |
| `octahedron` | `size` | Regular octahedron |

---

## How It Works

### Rendering Pipeline

```
Vertices → Vertex Shader → Clip Space → Near-Plane Clipping → Perspective Divide (÷w)
         → NDC → Viewport Transform → Screen Space → Rasterization (scanline fill)
         → Z-Buffer Test → Fragment Shader → Framebuffer
```

1. **Vertex Shader**: Each vertex is transformed from model space → world space (model matrix) → view space (view matrix) → clip space (projection matrix). Normals are transformed by the inverse-transpose of the model matrix.

2. **Near-Plane Clipping**: Triangles straddling the near plane are clipped using the Sutherland-Hodgman algorithm. The clip condition is `w + z ≥ 0` (i.e., the vertex is in front of the near plane). Clipped polygons are fan-triangulated.

3. **Perspective Divide**: Clip-space coordinates `(x, y, z, w)` are divided by `w` to produce Normalized Device Coordinates (NDC) in `[-1, 1]³`.

4. **Viewport Transform**: NDC coordinates are mapped to screen pixels: `x_screen = (ndc.x + 1) × width/2`, `y_screen = (1 - ndc.y) × height/2` (Y is flipped).

5. **Rasterization**: For each triangle, a bounding box is computed and each pixel within it is tested using edge functions. Pixels inside all three edges are shaded.

6. **Perspective-Correct Interpolation**: Vertex attributes are interpolated using `1/w` weighting:
   ```
   attr = (Σ bᵢ × attrᵢ / wᵢ) / (Σ bᵢ / wᵢ)
   ```
   This prevents warping of textures and normals under perspective projection.

7. **Z-Buffer Test**: Each fragment's NDC z-value is compared against the z-buffer. Closer fragments (lower z) overwrite farther ones.

8. **Fragment Shader**: Per-pixel lighting (Phong) or interpolated colour (Gouraud) is computed and written to the framebuffer. Shaders can return `DISCARD` to skip writing (used by WireframeShader).

### Shading Models

| Shader | Lighting | Per-Vertex | Per-Pixel | Normals | Special |
|--------|----------|------------|-----------|---------|---------|
| Flat | At face centroid | ✗ | Same for all fragments | Face normal | — |
| Gouraud | At each vertex | ✓ | Colour interpolated | Vertex normals | — |
| Phong | At each pixel | ✗ | ✓ | Interpolated normals | Specular highlights |
| Toon | Quantised per pixel | ✗ | ✓ | Interpolated normals | Silhouette outlines, discrete bands |
| Wireframe | None | ✗ | ✓ | — | Edge-only, discards interior |
| Fog | Wraps inner shader | — | ✓ | — | Exponential distance fog |
| Normal | None | ✗ | ✓ | Mapped to RGB | Debugging |
| Depth | None | ✗ | ✓ | — | Greyscale depth |
| Crosshatch | Per-pixel | ✗ | ✓ | Interpolated normals | Hatching patterns (NPR) |
| Matcap | Normal lookup | ✗ | ✓ | Mapped to UV | Pre-baked material sphere |

### Coordinate System

- Right-handed (OpenGL convention)
- Camera looks down -Z
- NDC: x∈[-1,1] right, y∈[-1,1] up, z∈[-1,1] (near=-1, far=+1)
- Screen: x∈[0,width] right, y∈[0,height] down (Y flipped)

---

## Architecture

```
soft-rasterizer/
├── soft_rasterizer/
│   ├── __init__.py       # Package exports, version
│   ├── math3d.py         # Vec2, Vec3, Vec4, Mat4, barycentric
│   ├── texture.py        # Texture, CheckerTexture, MipTexture (nearest + bilinear)
│   ├── mesh.py           # Vertex, Triangle, Mesh, OBJLoader
│   ├── rasterizer.py     # Renderer, Framebuffer, clipping, z-buffer, post-processing
│   ├── shaders.py        # 10 shaders: Flat, Gouraud, Phong, Toon, Wireframe, Normal, Depth, Fog, Crosshatch, Matcap
│   ├── scene.py          # Scene, Camera, Light, Object3D (with gradient background)
│   ├── primitives.py     # 7 mesh generators: cube, sphere, plane, cylinder, torus, tetrahedron, octahedron
│   ├── config.py         # SceneConfig — JSON scene loading/saving
│   ├── animation.py      # AnimationBuilder — turntable animation
│   └── cli.py            # Command-line interface (render, animate, list, template)
├── tests/
│   ├── test_math3d.py       # 40+ tests: vectors, matrices, barycentric
│   ├── test_texture.py      # 16 tests: sampling, mipmapping, checkerboard
│   ├── test_mesh.py         # 20+ tests: mesh ops, OBJ load/save, fan triangulation
│   ├── test_rasterizer.py   # 40+ tests: rendering, shaders, clipping, post-processing
│   └── test_scene_config.py # 30+ tests: config, animation, primitives, scene
├── examples/
│   ├── basic_render.py      # Simple Phong cube
│   ├── multi_shader.py      # Multiple objects with different shaders
│   ├── post_processing.py   # Edge detection + vignette
│   ├── animation.py         # Turntable animation
│   ├── json_scene.py        # JSON config file rendering
│   ├── phong_cube.json      # JSON scene: textured Phong cube
│   ├── multi_object_scene.json  # JSON scene: toon sphere + Phong torus
│   └── crosshatch_sphere.json   # JSON scene: crosshatch NPR sphere
├── pyproject.toml        # Build config, dependencies, pytest config
├── CONTRIBUTING.md       # Contribution guidelines
├── LICENSE               # MIT license
└── README.md             # This file
```

### Module Dependencies

```
cli.py ────┬── config.py ────┬── scene.py ──── math3d.py
           │                  ├── shaders.py ──┤
           │                  ├── primitives.py─┤
           │                  └── mesh.py ──────┤
           ├── animation.py ─── rasterizer.py ──┤
           └── rasterizer.py ─── texture.py ────┘
```

---

## Examples

The `examples/` directory contains ready-to-run demos:

| Example | Description | Run |
|---------|-------------|-----|
| `basic_render.py` | Simple textured Phong cube | `python3 examples/basic_render.py` |
| `multi_shader.py` | 3 objects with different shaders | `python3 examples/multi_shader.py` |
| `post_processing.py` | Edge detection + vignette | `python3 examples/post_processing.py` |
| `animation.py` | 36-frame turntable animation | `python3 examples/animation.py` |
| `json_scene.py` | Load and render a JSON scene | `python3 examples/json_scene.py` |
| `phong_cube.json` | JSON scene config | `soft-rasterizer render --scene examples/phong_cube.json -o out.bmp` |
| `multi_object_scene.json` | Multi-object JSON scene | `soft-rasterizer render --scene examples/multi_object_scene.json -o out.bmp` |
| `crosshatch_sphere.json` | NPR crosshatch scene | `soft-rasterizer render --scene examples/crosshatch_sphere.json -o out.bmp` |

---

## Tests

```bash
# Run all 159 tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=soft_rasterizer --cov-report=term-missing

# Specific test file
pytest tests/test_rasterizer.py -v
```

The test suite covers:
- **Math primitives** (40+ tests): vector operations, matrix transforms, inverse, perspective, barycentric coordinates
- **Texture sampling** (16 tests): nearest, bilinear, mipmapping, checkerboard, edge cases
- **Mesh operations** (20+ tests): construction, normals, bounds, OBJ load/save, fan triangulation
- **Rendering pipeline** (40+ tests): rasterization, z-buffer, clipping, culling, all shaders, post-processing, BMP/PPM output
- **Scene config & animation** (30+ tests): JSON loading, all shader types via config, animation, gradient backgrounds, error handling

---

## Known Issues (Resolved)

### Bug 1: Barycentric Coordinate Formula Error (FIXED)
**Issue**: The `barycentric()` function in `math3d.py` used an incorrect formula that produced wrong weights for vertices B and C. The original formula mixed vertex-relative terms incorrectly.

**Fix**: Rewrote using the standard signed-area (cross-product) approach:
```python
denom = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
u = Area(PBC) / Area(ABC)  # weight for A
v = Area(APC) / Area(ABC)  # weight for B
w = 1 - u - v              # weight for C
```

**Test**: `test_math3d.py::TestBarycentric::test_vertex_a/b/c` verify that each vertex maps to its correct barycentric weight.

### Bug 2: WireframeShader Discard Not Working (FIXED)
**Issue**: `WireframeShader` returned `Vec3(-1, -1, -1)` as a "discard" sentinel, but the renderer's `clamp(0, 1)` turned it into `Vec3(0, 0, 0)` (black), filling triangle interiors instead of showing only edges.

**Fix**: Added a proper `DISCARD` sentinel object. The renderer checks for `DISCARD` *before* clamping and skips the framebuffer write. `FogShader` also passes through `DISCARD` from its inner shader.

**Test**: `test_rasterizer.py::TestShaders::test_wireframe_shader_discard` verifies interior fragments return `DISCARD`; `test_render_discard_count` verifies the renderer counts discarded fragments.

### Bug 3: Ambient Light Tinted by First Light's Color (FIXED)
**Issue**: `_compute_lighting()` computed the ambient term as `material.ambient.component_mul(lights[0].color)`, which incorrectly tinted all ambient light with the first light's hue. A scene with a red light would have red ambient everywhere, even on unlit surfaces.

**Fix**: Changed to use `material.ambient` directly (neutral white base), which is the correct Phong model behaviour.

**Test**: `test_rasterizer.py::TestShaders::test_ambient_neutral` verifies that ambient is not tinted by the first light's colour.

### Bug 4: PPM Output Truncation (FIXED)
**Issue**: PPM output used `int(c.x * 255)` (truncation) instead of `round()`, causing slight darkening of bright pixels. For example, `0.999 * 255 = 254.745` → `int()` gives 254, but `round()` gives 255.

**Fix**: Changed to `round(c.x * 255)` in `Framebuffer.to_ppm()`. Also applied the same fix to the new `to_bmp()` method.

**Test**: `test_rasterizer.py::TestFramebuffer::test_to_ppm_rounding` verifies that `0.999` maps to 255, not 254.

### Bug 5: Frustum Culling NDC Radius Calculation (FIXED)
**Issue**: The frustum cull NDC radius calculation used `mvp[0]` (the first matrix element) as a scale factor, which incorrectly mixed the projection scale into the radius calculation.

**Fix**: Replaced with a simpler `radius * inv_w` approximation, which is conservative (slightly overestimates the radius, which is safe for culling — false positives keep visible objects).

### Bug 6: OBJLoader Redundant Triangle Rebuilding (FIXED)
**Issue**: The OBJ loader had a two-pass approach that first created `Triangle(idx, -1, -1)` placeholder objects and then rebuilt them in a second loop, adding unnecessary complexity and memory overhead.

**Fix**: Rewrote as a single pass that directly builds `Triangle` objects with correct vertex indices during fan triangulation, eliminating the placeholder and rebuild step entirely.

### Bug 7: pyproject.toml Invalid Build Backend (FIXED)
**Issue**: `pyproject.toml` specified `setuptools.backends._legacy:_Backend` as the build backend, which doesn't exist in any setuptools version, causing `pip install` to fail.

**Fix**: Changed to the standard `setuptools.build_meta` backend.

---

## Roadmap

- [ ] **PNG output** — pure-Python PNG encoder for maximum compatibility
- [ ] **Shadow mapping** — basic shadow map generation and sampling
- [ ] **Per-pixel mipmapping** — screen-space derivative-based LOD selection
- [ ] **Normal mapping** — tangent-space normal maps for surface detail
- [ ] **Environment mapping** — cubemap reflections
- [ ] **Anti-aliasing** — MSAA or SSAA supersampling
- [ ] **Triangle strip / fan optimization** — reduce vertex transform overhead
- [ ] **Spatial acceleration** — BVH or octree for multi-object scenes
- [ ] **GIF output** — direct animated GIF creation from turntable frames
- [ ] **WebGL viewer** — interactive preview in a browser canvas
- [ ] **Scene scripting** — keyframe animation with interpolation

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding shaders, primitives, and features, running tests, and submitting pull requests.

---

## Changelog

### v2.0.0 — Comprehensive Improvement
- **Fixed 7 bugs**: barycentric formula, wireframe discard, ambient tint, PPM rounding, frustum culling, OBJ loader redundancy, pyproject build backend
- **New shaders**: CrosshatchShader (NPR pen-and-ink), MatcapShader (material capture)
- **New output format**: BMP (24-bit, browser-compatible)
- **JSON scene configuration**: `SceneConfig` class + `soft-rasterizer template` command
- **Turntable animation**: `AnimationBuilder` class + `soft-rasterizer animate` command
- **Post-processing**: grayscale, Sobel edge detection, vignette
- **Gradient backgrounds**: vertical gradient between two colours
- **Fragment discard support**: `DISCARD` sentinel for wireframe and future shaders
- **Logging**: configurable logging throughout the pipeline
- **159-test pytest suite**: comprehensive coverage of math, rendering, shaders, config, animation
- **Examples directory**: 5 Python scripts + 3 JSON scene files
- **CLI improvements**: `--scene`, `--bg-gradient`, `--bg-color`, `--grayscale`, `--edge`, `--vignette`, `animate` subcommand, `template` subcommand
- **CONTRIBUTING.md** and **LICENSE** added
- **pyproject.toml**: dev dependencies, pytest config, proper classifiers

### v1.0.0 — Initial Release
- Complete rendering pipeline with z-buffer
- 8 shaders: Flat, Gouraud, Phong, Toon, Wireframe, Normal, Depth, Fog
- Texture mapping with mipmapping
- 7 primitive mesh generators
- OBJ loading
- PPM output, ASCII preview
- CLI tool
- Backface culling, frustum culling
- Render statistics

---

## License

MIT — see [LICENSE](LICENSE).