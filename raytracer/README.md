# raytracer

A **from-scratch recursive ray tracer** written in pure Python — no external
graphics libraries, no GPU, no framework. Every piece of the rendering
pipeline (vector math, ray–primitive intersection, BVH acceleration, material
BSDFs, camera, integrator, image output) is implemented from first
principles.

## Features

- **Geometry** — spheres, infinite planes, triangles (Möller–Trumbore), and
  axis-aligned rectangles for area lights.
- **Acceleration** — a binary **Bounding Volume Hierarchy** (BVH) built with a
  midpoint split on the widest axis, so scenes with hundreds of primitives stay
  interactive. Handles rays parallel to slabs without dividing by zero.
- **Materials / BSDFs**
  - `Matte` — Lambertian diffuse with cosine-weighted hemisphere sampling.
  - `Metal` — specular reflection with configurable fuzzy roughness.
  - `Dielectric` — transparent glass/water with Snell refraction, total
    internal reflection, and the Schlick Fresnel approximation.
  - `Emissive` — diffuse area light sources.
  - `Checker` — a procedural checkerboard that delegates to two child materials
    based on world position.
- **Camera** — pinhole camera with configurable vertical field-of-view, plus
  **depth-of-field** via an aperture disk and focus distance.
- **Integrator modes** (selectable per render via `mode=`)
  - `path` — recursive Whitted-style path tracer with bounded depth.
  - `ao` — ambient occlusion: hemisphere sampling around each hit, shading grey
    by visibility. Fast, no-light preview.
  - `normal` — debug mode shading each hit by its surface normal mapped to RGB.
- **Anti-aliasing** — jittered supersampling (averaged `samples` rays per pixel).
- **Tone mapping** — configurable gamma correction clamped to 8-bit RGB.
- **Backgrounds** — gradient sky, constant color (picklable), or any callable
  `ray → color`.
- **Output** — binary PPM (P6), PNG (via Pillow), ASCII-art luminance previews,
  and a flat-bytes RGB buffer for streaming.
- **Scene JSON serialization** — describe entire scenes (camera, background,
  objects, materials) in a portable JSON file and render them with
  `--scene-file`. Includes a `validate` subcommand.
- **Multi-threaded rendering** — tile-based parallel rendering across a process
  pool (`--threads N`); scenes/backgrounds are picklable so they cross process
  boundaries cleanly.
- **Scenes** — three built-in presets: *three-balls* (the canonical
  glass/metal balls on a checker floor), *cornell* (a Cornell box with colored
  walls and a ceiling light), and *random* (a procedurally generated field of
  random spheres).
- **CLI** — `render`, `scenes`, `info`, and `validate` subcommands with a
  progress bar and rich flags (`--mode`, `--threads`, `--scene-file`,
  `--ao-distance`, `--gamma`).
- **Deterministic** — optional RNG seed for reproducible renders.
- **CI** — GitHub Actions workflow runs the full test suite.

## How it works

```
Camera ──► Ray ──► BVH ──► Primitive.hit() ──► HitRecord
                                                │
                                                ▼
                              Integrator (path / ao / normal)
                                                │
                                                ▼
                                  emit() + attenuation * ray_color(scattered)
                                                │
                                                ▼
                              per-pixel supersample + gamma → 8-bit RGB
```

1. The `Camera` generates one (jittered) ray per sample per pixel.
2. Each ray traverses the BVH; leaf nodes test a small list of primitives.
3. The nearest hit produces a `HitRecord` carrying the hit point, oriented
   surface normal (flipped against the ray), and a material reference.
4. The selected integrator runs:
   - **path**: the material's `scatter()` either absorbs the ray or produces
     an attenuation color plus a new scattered ray; the integrator recurses
     (`ray_color`) up to `max_depth`, accumulating attenuation multiplicatively
     and adding emissive contributions at each hit.
   - **ao**: hemisphere rays are cast around the hit normal and occlusion is
     counted over a configurable distance.
   - **normal**: the hit normal is mapped into [0, 1] RGB.
5. Rays that escape return the background color (gradient sky, etc.).
6. Pixel samples are averaged and gamma-corrected to 8-bit RGB for output.

### Intersection math

- **Sphere** — the classic reduced quadratic `|o + t·d − c|² = r²` solved with
  the half-b formulation for numerical stability.
- **Plane** — single ray–plane `t = (p − o)·n / (d·n)`.
- **Triangle** — Möller–Trumbore with edge-cross product barycentric test.
- **AABB** — the axis-aligned slab method, handling zero-direction components
  (rays parallel to a slab) without dividing by zero.

## Installation

```bash
cd raytracer
python3 -m venv .venv
. .venv/bin/activate
pip install -e .      # installs Pillow for PNG output
```

`numpy` is *not* required — all vector math is pure Python. `Pillow` is only
needed for PNG output; PPM and ASCII work with the standard library alone.

## Usage

### From the command line

```bash
# List available scenes
python -m raytracer.cli scenes

# Render the three-balls scene to PNG (default 320×180, 4 spp)
python -m raytracer.cli render --scene three-balls --width 640 --height 360 \
    --samples 16 --max-depth 8 --out three_balls.png

# Cornell box to PPM, using 4 worker processes
python -m raytracer.cli render --scene cornell --width 256 --height 256 \
    --samples 8 --threads 4 --out cornell.ppm

# Normal-shading debug preview
python -m raytracer.cli render --scene three-balls --mode normal \
    --width 128 --height 72 --out normals.png

# Ambient-occlusion pass of a JSON scene
python -m raytracer.cli render --scene-file examples/sample_scene.json \
    --mode ao --samples 32 --width 200 --height 200 --threads 4 --out ao.png

# Quick ASCII preview
python -m raytracer.cli render --scene three-balls --width 80 --height 36 \
    --samples 1 --max-depth 3 --out preview.txt --format ascii

# Validate a JSON scene file
python -m raytracer.cli validate examples/sample_scene.json
```

### From Python

```python
from raytracer import (
    Vec3, Camera, Renderer, Sphere, Matte, Metal, Dielectric,
    Checker, Plane, BVHNode, build_three_balls, imageio,
)

scene = build_three_balls(aspect=16/9)
renderer = scene.make_renderer(samples=16, max_depth=8, seed=42)
pixels = renderer.render(scene.camera, 640, 360)
imageio.write_png("out.png", pixels)
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

### Describing a scene in JSON

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
     "material": {"type": "dielectric", "ior": 1.5}}
  ]
}
```

Load with `load_scene_file("scene.json")` or render via
`raytracer.cli render --scene-file scene.json`.

## Project layout

```
raytracer/
├── raytracer/
│   ├── __init__.py     # public API
│   ├── vec.py          # Vec3 vector math
│   ├── ray.py          # Ray primitive
│   ├── bvh.py          # AABB + BVH + HittableList
│   ├── primitive.py    # Sphere, Plane, Triangle, XYRect
│   ├── material.py     # Material/HitRecord, Matte, Metal, Dielectric, Emissive, Checker
│   ├── camera.py       # pinhole camera w/ DoF
│   ├── renderer.py     # integrators (path/ao/normal) + backgrounds
│   ├── scene.py        # preset scenes
│   ├── serialize.py    # JSON scene load/dump
│   ├── imageio.py      # PPM / PNG / ASCII writers
│   └── cli.py          # command-line interface
├── examples/
│   ├── render_all.py   # render every preset + JSON scene
│   └── sample_scene.json
├── tests/
│   ├── test_raytracer.py
│   └── test_enhancements.py
└── pyproject.toml
```

## Tests

```bash
python -m pytest tests/ -q
```

72 tests covering vector math, intersections, materials, BVH, camera, all
three integrator modes, JSON serialization, parallel rendering, image I/O, and
the CLI.

## License

MIT — see the repository root.