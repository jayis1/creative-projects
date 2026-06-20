# 🌈 raytracer

<p align="center">
  <strong>A from-scratch recursive ray tracer in pure Python — no GPU, no graphics libraries.</strong>
</p>

<p>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-green.svg">
  <img alt="Tests" src="https://img.shields.io/badge/tests-177%20passing-brightgreen.svg">
  <img alt="Version" src="https://img.shields.io/badge/version-2.0.0-orange.svg">
  <img alt="No NumPy" src="https://img.shields.io/badge/NumPy-not%20required-lightgrey.svg">
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Python API](#python-api)
  - [Scene Files (JSON / YAML / TOML)](#scene-files-json--yaml--toml)
  - [Animation](#animation)
  - [Render Statistics](#render-statistics)
- [Architecture](#architecture)
- [Integrator Modes](#integrator-modes)
- [Textures](#textures)
- [Materials](#materials)
- [Primitives](#primitives)
- [Scene Presets](#scene-presets)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Testing](#testing)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [License](#license)

## Overview

**raytracer** is a complete, physically-based path tracer written entirely in
pure Python. Every piece of the rendering pipeline — vector math, ray–primitive
intersection, BVH acceleration, material BSDFs, procedural textures, camera,
integrator, image output — is implemented from first principles. No NumPy,
no OpenGL, no GPU.

The codebase is designed to be **readable** (each module is self-contained),
**educational** (algorithms are named and documented), and **practical**
(it produces real images at reasonable speed for a pure-Python tracer).

```
 ██████╗ █████╗ ██████╗ ███████╗██████╗ ██╔══██╗
██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗██║  ██║
██║     ███████║██████╔╝█████╗  ██████╔╝██████╔╝
██║     ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗██╔═══╝
╚██████╗██║  ██║██║     ███████╗██║  ██║██║
 ╚═════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝
```

## Features

### Geometry
- **Sphere** — analytic ray-sphere via reduced quadratic (half-b formulation)
- **Plane** — infinite ray-plane intersection
- **Triangle** — Möller–Trumbore ray-triangle with barycentric test
- **XYRect / XZRect / YZRect** — axis-aligned rectangles for area lights and walls
- **Box** — axis-aligned box built from 6 rectangles
- **Disk** — flat circular disk with polar UVs
- **Cylinder** — finite Y-axis cylinder with optional caps

### Acceleration
- **BVH** — binary Bounding Volume Hierarchy built with midpoint split on the
  widest axis. Handles rays parallel to slabs without dividing by zero.

### Materials / BSDFs
- **Matte** — Lambertian diffuse with cosine-weighted hemisphere sampling (textured)
- **Metal** — specular reflection with configurable fuzzy roughness (textured)
- **Dielectric** — transparent glass/water with Snell refraction, total internal
  reflection, and Schlick Fresnel approximation
- **Emissive** — diffuse area light sources (textured)
- **Checker** — procedural checkerboard delegating to two child materials
- **Isotropic** — volume scattering / participating media

### Textures
- **SolidColor** — constant color
- **CheckerTexture** — 3-D world-space checkerboard
- **PerlinNoise** — value-noise gradient interpolation
- **NoiseTexture** — Perlin noise mapped to a color range
- **Turbulence** — fractal Brownian motion (sum of abs-noise)
- **Marble** — sinusoidal marble streaks modulated by turbulence
- **ImageTexture** — sample colors from an in-memory image buffer

### Camera
- Pinhole camera with configurable vertical field-of-view
- **Depth-of-field** via aperture disk and focus distance

### Integrator modes (selectable per render via `--mode`)
- `path` — recursive Whitted-style path tracer with bounded depth
- `ao` — ambient occlusion: hemisphere sampling around each hit
- `normal` — debug mode shading each hit by surface normal → RGB
- `depth` — encodes hit distance as grayscale for scale debugging

### Advanced rendering
- **Russian roulette** path termination (`--rr-start-depth`)
- **Next Event Estimation (NEE)** — explicit direct-light sampling
- **Render statistics** — rays, bounces, hits, misses, time, rays/second
- **Anti-aliasing** — jittered supersampling (averaged `samples` rays per pixel)
- **Tone mapping** — configurable gamma correction clamped to 8-bit RGB
- **Backgrounds** — gradient sky, constant color, or any callable `ray → color`

### Output
- Binary PPM (P6), PNG (via Pillow), ASCII-art luminance previews, flat RGB bytes

### Scene management
- **JSON / YAML / TOML scene files** — describe entire scenes in a portable file
- **Scene validation** — `validate` subcommand checks scene files
- **6 built-in presets** — three-balls, Cornell box, random spheres, solar system,
  marble hall, nebula

### Parallel rendering
- Tile-based multi-process rendering via `ProcessPoolExecutor` (`--threads N`)
- All scene objects are picklable so they cross process boundaries cleanly

### Animation
- Camera orbit, linear dolly, and Catmull–Rom spline paths
- `animate` CLI subcommand renders numbered frame sequences

### Developer experience
- **Structured logging** with configurable level and ANSI colors
- **Comprehensive test suite** — 177 tests covering all modules
- **GitHub Actions CI** — runs the full suite on Python 3.10–3.13
- **pip-installable** with `pyproject.toml`
- **Deterministic** — optional RNG seed for reproducible renders

## Installation

```bash
cd raytracer
python3 -m venv .venv
. .venv/bin/activate
pip install -e .           # installs Pillow for PNG output
# Optional: YAML scene file support
pip install -e ".[yaml]"   # adds PyYAML
# For development:
pip install -e ".[dev]"    # adds pytest + PyYAML
```

`numpy` is **not** required — all vector math is pure Python. `Pillow` is only
needed for PNG output; PPM and ASCII work with the standard library alone. YAML
scene files require `PyYAML`; TOML is supported natively on Python 3.11+ (or
`tomli` on older versions).

## Quick Start

```bash
# List available scenes
python -m raytracer.cli scenes

# Render the three-balls scene to PNG
python -m raytracer.cli render --scene three-balls --width 320 --height 180 \
    --samples 16 --max-depth 8 --out three_balls.png

# Cornell box to PPM, using 4 worker processes
python -m raytracer.cli render --scene cornell --width 256 --height 256 \
    --samples 8 --threads 4 --out cornell.ppm

# Quick ASCII preview
python -m raytracer.cli render --scene three-balls --width 80 --height 36 \
    --samples 1 --max-depth 3 --out preview.txt --format ascii

# Render a 60-frame orbit animation
python -m raytracer.cli animate --scene three-balls --orbit \
    --frames 60 --radius 4 --height 1.5 --width 320 --height-px 180 \
    --samples 4 --out-dir frames/

# Render with statistics
python -m raytracer.cli render --scene cornell --width 128 --height 128 \
    --samples 4 --out cornell.png --stats
```

## Usage

### Command Line

```
raytracer [--log-level LEVEL] <command> [options]

Commands:
  render     Render a single image from a preset or scene file
  animate    Render a frame sequence (orbit / dolly / spline)
  scenes     List available preset scenes
  info       Show version and capabilities
  validate   Validate a scene file without rendering
  stats      Render and print render statistics as JSON
```

#### render

```bash
# Render a preset scene
python -m raytracer.cli render --scene three-balls \
    --width 640 --height 360 --samples 16 --max-depth 8 \
    --mode path --gamma 2.0 --seed 42 --out out.png

# Render from a JSON scene file
python -m raytracer.cli render --scene-file my_scene.json \
    --width 640 --height 360 --out out.png

# Render from a YAML scene file
python -m raytracer.cli render --scene-file my_scene.yaml \
    --mode ao --samples 32 --out ao.png

# Render with Russian roulette
python -m raytracer.cli render --scene cornell --max-depth 50 \
    --rr-start-depth 5 --samples 8 --out cornell.png

# Parallel rendering
python -m raytracer.cli render --scene cornell --threads 8 \
    --width 512 --height 512 --samples 16 --out cornell.png
```

#### animate

```bash
# Orbit animation
python -m raytracer.cli animate --scene three-balls --orbit \
    --frames 60 --radius 4 --height 1.5 \
    --width 320 --height-px 180 --samples 4 --out-dir frames/

# Dolly (linear camera move)
python -m raytracer.cli animate --scene cornell --dolly \
    --frames 30 --start 0 2 8 --end 0 2 2 \
    --width 256 --height-px 256 --out-dir dolly/
```

Combine frames with ffmpeg:
```bash
ffmpeg -framerate 24 -i frames/frame_%04d.png -c:v libx264 out.mp4
```

### Python API

```python
from raytracer import (
    Vec3, Camera, Renderer, Sphere, Matte, Metal, Dielectric,
    Checker, Plane, BVHNode, build_three_balls, imageio,
)

# Use a preset scene
scene = build_three_balls(aspect=16/9)
renderer = scene.make_renderer(samples=16, max_depth=8, seed=42)
pixels = renderer.render(scene.camera, 640, 360)
imageio.write_png("out.png", pixels)
print(f"Rendered {renderer.stats.rays} rays in {renderer.stats.elapsed:.2f}s")
```

### Building a custom scene in Python

```python
from raytracer import *

ground = Plane(Vec3(0, -0.5, 0), Vec3(0, 1, 0),
               Checker(Matte(Vec3(0.9, 0.9, 0.9)),
                       Matte(Vec3(0.1, 0.1, 0.1)), scale=2.0))
ball = Sphere(Vec3(0, 0, -2), 0.5, Dielectric(1.5))
world = BVHNode([ground, ball])

cam = Camera(look_from=Vec3(0, 0.5, 3),
             look_at=Vec3(0, 0, -2),
             up=Vec3(0, 1, 0),
             vfov_deg=45, aspect=16/9, aperture=0.05, focus_dist=5)

renderer = Renderer(world, background=sky_gradient,
                    samples=16, max_depth=8, seed=42)
pixels = renderer.render(cam, 640, 360)
imageio.write_png("custom.png", pixels)
```

### Using textures

```python
from raytracer import (
    Vec3, Sphere, Matte, Metal, NoiseTexture, Marble, Turbulence,
    BVHNode, Camera, Renderer, sky_gradient, imageio,
)

# Perlin noise sphere
noise_ball = Sphere(Vec3(0, 0, -2), 0.5,
                    Matte(NoiseTexture(Vec3(0.2, 0.2, 0.4),
                                        Vec3(0.9, 0.3, 0.5),
                                        scale=4.0, seed=42)))

# Marble column
marble_ball = Sphere(Vec3(1, 0, -2), 0.5,
                     Metal(Marble(Vec3(0.9, 0.9, 0.95),
                                  Vec3(0.1, 0.1, 0.15),
                                  scale=3.0, seed=7), fuzz=0.05))

# Turbulent surface
turb_ball = Sphere(Vec3(-1, 0, -2), 0.5,
                   Matte(Turbulence(Vec3(0.6, 0.4, 0.9),
                                   scale=5.0, depth=6, seed=3)))
```

### Scene Files (JSON / YAML / TOML)

Scenes can be described in JSON, YAML, or TOML. The format is auto-detected
from the file extension.

**JSON example:**
```json
{
  "background": "sky",
  "camera": {
    "look_from": [0, 0.8, 3.5],
    "look_at":   [0, 0, -1.5],
    "up":        [0, 1, 0],
    "vfov_deg":  45,
    "aperture":  0.08,
    "focus_dist": 5.0
  },
  "objects": [
    {"type": "plane", "point": [0, -0.5, 0], "normal": [0, 1, 0],
     "material": {"type": "checker", "scale": 1.5,
                   "a": {"type":"matte","albedo":[0.85,0.85,0.85]},
                   "b": {"type":"matte","albedo":[0.15,0.15,0.15]}}},
    {"type": "sphere", "center": [0, 0, -1.5], "radius": 0.5,
     "material": {"type":"dielectric","ior":1.5}}
  ]
}
```

**Textured materials in scene files** — the `albedo` field accepts a texture:
```json
{
  "type": "sphere", "center": [0, 0, -2], "radius": 0.5,
  "material": {"type": "matte",
               "albedo": {"type": "marble", "scale": 3.0, "seed": 7}}
}
```

**YAML example:**
```yaml
background: sky
camera:
  look_from: [0, 0.5, 3]
  look_at: [0, 0, -1]
  vfov_deg: 50
objects:
  - type: sphere
    center: [0, 0, -1]
    radius: 0.5
    material:
      type: dielectric
      ior: 1.5
```

**TOML example:**
```toml
[background]
type = "constant"
color = [0.02, 0.02, 0.03]

[camera]
look_from = [0, 1.5, 3]
look_at = [0, 1.2, -3]
vfov_deg = 50

[[objects]]
type = "sphere"
center = [0, 0, -2]
radius = 0.5

[objects.material]
type = "matte"
albedo = {type = "marble", scale = 3.0}
```

Load with `load_scene_file("scene.json")` or render via
`raytracer.cli render --scene-file scene.json`.

### Animation

```python
from raytracer import build_three_balls
from raytracer.animation import orbit_path, render_animation

scene = build_three_balls(aspect=16/9)
positions = orbit_path(center=Vec3(0, 0, -1), radius=4, height=1.5, frames=60)
paths = render_animation(
    scene=scene, eye_positions=positions,
    out_dir="frames/", width=320, height=180,
    samples=4, max_depth=6, fmt="png",
)
```

### Render Statistics

```python
renderer = scene.make_renderer(samples=16, max_depth=8, seed=42)
pixels = renderer.render(scene.camera, 640, 360)
print(renderer.stats)
# RenderStats(rays=..., bounces=..., hits=..., misses=...,
#             elapsed=...s, 640x360)
print(renderer.stats.as_dict())
# {'rays': ..., 'bounces': ..., 'elapsed_s': ..., 'rays_per_second': ...}
```

CLI: `raytracer render --scene cornell --stats` or `raytracer stats --scene cornell`.

## Architecture

```
Camera ──► Ray ──► BVH ──► Primitive.hit() ──► HitRecord
                                                │
                                                ▼
                              Integrator (path / ao / normal / depth)
                                │             │
                                │             ▼
                                │      NEE (light sampling) + Russian roulette
                                │             │
                                ▼             ▼
                          emit() + attenuation * ray_color(scattered)
                                                │
                                                ▼
                              per-pixel supersample + gamma → 8-bit RGB
```

### Pipeline

1. The `Camera` generates one (jittered) ray per sample per pixel.
2. Each ray traverses the BVH; leaf nodes test a small list of primitives.
3. The nearest hit produces a `HitRecord` carrying the hit point, oriented
   surface normal (flipped against the ray), and a material reference.
4. The selected integrator runs:
   - **path**: the material's `scatter()` either absorbs the ray or produces
     an attenuation color plus a new scattered ray; the integrator recurses
     (`ray_color`) up to `max_depth`, accumulating attenuation multiplicatively
     and adding emissive contributions at each hit. NEE adds direct light
     contributions; Russian roulette terminates long paths unbiasedly.
   - **ao**: hemisphere rays are cast around the hit normal and occlusion is
     counted over a configurable distance.
   - **normal**: the hit normal is mapped into [0, 1] RGB.
   - **depth**: the hit distance is mapped to [0, 1] grayscale.
5. Rays that escape return the background color (gradient sky, etc.).
6. Pixel samples are averaged and gamma-corrected to 8-bit RGB for output.

### Intersection math

- **Sphere** — the classic reduced quadratic `|o + t·d − c|² = r²` solved with
  the half-b formulation for numerical stability.
- **Plane** — single ray–plane `t = (p − o)·n / (d·n)`.
- **Triangle** — Möller–Trumbore with edge-cross product barycentric test.
- **Box** — six axis-aligned rectangle intersections.
- **Cylinder** — quadratic in the XZ plane, clipped to [y0, y1], plus optional
  disk caps.
- **AABB** — the axis-aligned slab method, handling zero-direction components
  (rays parallel to a slab) without dividing by zero.

### Module layout

```
raytracer/
├── raytracer/
│   ├── __init__.py     # public API
│   ├── vec.py          # Vec3 vector math
│   ├── ray.py          # Ray primitive
│   ├── bvh.py          # AABB + BVH + HittableList
│   ├── primitive.py    # Sphere, Plane, Triangle, XY/XZ/YZRect, Box, Disk, Cylinder
│   ├── material.py     # Material/HitRecord, Matte, Metal, Dielectric, Emissive, Checker, Isotropic
│   ├── texture.py      # Texture system: SolidColor, CheckerTexture, PerlinNoise, NoiseTexture, Turbulence, Marble, ImageTexture
│   ├── camera.py       # pinhole camera w/ DoF
│   ├── renderer.py     # integrators (path/ao/normal/depth) + backgrounds + stats + NEE + RR
│   ├── scene.py        # 6 preset scenes
│   ├── serialize.py    # JSON/YAML/TOML scene load/dump + texture/material builders
│   ├── imageio.py      # PPM / PNG / ASCII writers
│   ├── animation.py    # camera paths + frame sequence rendering
│   ├── logging.py      # structured logging
│   └── cli.py          # command-line interface (render/animate/scenes/info/validate/stats)
├── examples/
│   ├── render_all.py   # render every preset + JSON/YAML/TOML scenes
│   ├── sample_scene.json
│   ├── cornell_textured.yaml
│   └── marble_hall.toml
├── tests/
│   ├── test_raytracer.py    # core tests
│   ├── test_enhancements.py # v1.1 features
│   ├── test_bug_hunt.py     # regression tests
│   └── test_v2_enhancements.py # v2.0 features
├── pyproject.toml
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## Integrator Modes

| Mode     | Flag          | Description |
|----------|---------------|-------------|
| `path`   | `--mode path`   | Recursive path tracer with NEE + Russian roulette |
| `ao`     | `--mode ao`     | Ambient occlusion (greyscale, no lighting) |
| `normal` | `--mode normal` | Surface normal → RGB debug visualization |
| `depth`  | `--mode depth`  | Hit distance → grayscale debug visualization |

## Textures

Textures map (u, v, p) → color and can be used wherever a material accepts an
`albedo`:

| Texture         | Description |
|-----------------|-------------|
| `SolidColor`    | Constant color |
| `CheckerTexture`| 3-D world-space checkerboard |
| `PerlinNoise`   | Value-noise gradient interpolation |
| `NoiseTexture`  | Perlin noise → color range |
| `Turbulence`    | Fractal Brownian motion |
| `Marble`        | Sinusoidal marble streaks |
| `ImageTexture`  | Sample from an in-memory image buffer |

## Materials

| Material     | BSDF | Textured | Description |
|--------------|------|----------|-------------|
| `Matte`      | Lambertian | ✅ | Cosine-weighted diffuse |
| `Metal`      | Specular  | ✅ | Reflection with fuzz |
| `Dielectric` | Fresnel   | ❌ | Glass/water refraction (Schlick) |
| `Emissive`   | Emission  | ✅ | Area light source |
| `Checker`    | Proxy     | — | Delegates to two child materials |
| `Isotropic`  | Isotropic | ✅ | Volume scattering |

## Primitives

| Primitive  | Intersection | UVs |
|------------|-------------|-----|
| `Sphere`   | Quadratic   | Spherical |
| `Plane`    | Ray-plane  | Planar projection |
| `Triangle` | Möller–Trumbore | Barycentric |
| `XYRect`   | Z-slab     | Planar |
| `XZRect`   | Y-slab     | Planar |
| `YZRect`   | X-slab     | Planar |
| `Box`      | 6 rects    | Per-face |
| `Disk`     | Ray-plane + radius | Polar |
| `Cylinder` | Quadratic XZ + caps | Cylindrical |

## Scene Presets

| Preset | Description |
|--------|-------------|
| `three-balls` | Glass/metal balls on a checker floor |
| `cornell` | Classic Cornell box with colored walls + NEE |
| `random` | Procedurally generated field of random spheres |
| `solar-system` | Emissive sun + planets (showcases NEE) |
| `marble-hall` | Perlin marble columns + textured floor |
| `nebula` | Noise-textured spheres in a starry void |

## Known Issues (Resolved)

The following bugs were found during the Phase 3 bug hunt and have been fixed,
each with a regression test in `tests/test_bug_hunt.py`:

1. **AABB slab division by zero** — the axis-aligned bounding-box intersection
   divided by `ray.direction.<axis>` unconditionally; rays with a zero
   direction component (e.g. axis-aligned rays) crashed with
   `ZeroDivisionError`. *Fix: detect zero-direction axes and test whether the
   ray origin lies within the slab extents instead of dividing.*
2. **Pixel jitter exceeded the image plane** — anti-aliasing jitter used
   `s + random()` which for the last pixel (`s = 1.0`) sampled at coordinates up
   to ~1.62, far beyond the `[0, 1]` image bounds, causing edge bleed. The
   pixel-coordinate mapping also used edge-aligned `i/(width-1)` rather than
   pixel centres. *Fix: map each pixel to its centre `(i+0.5)/width` and jitter
   within `±half-pixel`, so every sample stays inside its pixel cell.*
3. **`XYRect.hit` division by zero** — the axis-aligned rectangle divided by
   `ray.direction.z` without guarding; a ray parallel to the rectangle plane
   crashed with `ZeroDivisionError`. *Fix: return `None` when
   `ray.direction.z == 0`.*
4. **Unpicklable backgrounds broke multi-process rendering** — `constant_background`
   returned a nested closure and the Cornell scene used a `lambda`, neither of
   which can cross process boundaries, so `--threads N` failed with
   `AttributeError: Can't get local object`. *Fix: introduced a picklable
   `ConstantBackground` class and replaced the lambda with it.*

## Testing

```bash
python -m pytest tests/ -v
```

**177 tests** covering vector math, all primitives, all materials, textures,
BVH, camera, all four integrator modes, JSON/YAML/TOML serialization, parallel
rendering, animation, image I/O, the CLI (all subcommands), and regression
tests for 4 fixed bugs.

| Test file | Tests | Scope |
|-----------|-------|-------|
| `test_raytracer.py` | 44 | Core: Vec3, Ray, primitives, materials, BVH, camera |
| `test_enhancements.py` | 29 | v1.1: serialization, modes, parallel |
| `test_bug_hunt.py` | 18 | Regression tests for fixed bugs |
| `test_v2_enhancements.py` | 86 | v2.0: textures, new primitives, animation, logging |

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, code style, and
guidelines for adding primitives, materials, textures, and scene presets.

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the full version history.

## Roadmap

- [ ] Triangle mesh / OBJ loader
- [ ] Environment maps (HDRI backgrounds)
- [ ] Bump mapping / normal mapping
- [ ] Motion blur
- [ ] Spectral rendering
- [ ] BVH with Surface Area Heuristic (SAH)
- [ ] Denoiser (post-process)
- [ ] GPU acceleration via Numba or ctypes
- [ ] Volumetric primitives (constant-density fog)
- [ ] Thin-lens camera model
- [ ] Multi-threaded rendering (threading, not just multiprocessing)

## License

MIT — see [LICENSE](./LICENSE).