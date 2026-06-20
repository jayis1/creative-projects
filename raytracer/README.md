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
  interactive.
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
- **Integrator** — a recursive Whitted-style path tracer with bounded depth,
  per-pixel supersampled anti-aliasing, and gamma-correct tone mapping.
- **Backgrounds** — gradient sky, constant color, or any callable `ray → color`.
- **Output** — binary PPM (P6), PNG (via Pillow), and ASCII-art luminance
  previews. Plus a flat-bytes RGB buffer for streaming.
- **Scenes** — three built-in presets: *three-balls* (the canonical
  glass/metal balls on a checker floor), *cornell* (a Cornell box with colored
  walls and a ceiling light), and *random* (a procedurally generated field of
  random spheres).
- **CLI** — `render`, `scenes`, and `info` subcommands with progress bar.
- **Deterministic** — optional RNG seed for reproducible renders.

## How it works

```
Camera ──► Ray ──► BVH ──► Primitive.hit() ──► HitRecord
                                                │
                                                ▼
                                Material.scatter() ──► recursive ray_color()
                                                │
                                                ▼
                                  emit() + attenuation * ray_color(scattered)
```

1. The `Camera` generates one (jittered) ray per sample per pixel.
2. Each ray traverses the BVH; leaf nodes test a small list of primitives.
3. The nearest hit produces a `HitRecord` carrying the hit point, oriented
   surface normal (flipped against the ray), and a material reference.
4. The material's `scatter()` either absorbs the ray or produces an
   attenuation color plus a new scattered ray.
5. The integrator recurses (`ray_color`) up to `max_depth`, accumulating
   attenuation multiplicatively and adding emissive contributions at each hit.
6. Rays that escape return the background color (gradient sky, etc.).
7. Pixel samples are averaged and gamma-corrected to 8-bit RGB for output.

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

# Cornell box to PPM
python -m raytracer.cli render --scene cornell --width 256 --height 256 \
    --samples 8 --out cornell.ppm

# Quick ASCII preview
python -m raytracer.cli render --scene three-balls --width 80 --height 36 \
    --samples 1 --max-depth 3 --out preview.txt --format ascii
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

### Building a custom scene

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
│   ├── renderer.py     # recursive integrator + backgrounds
│   ├── scene.py        # preset scenes
│   ├── imageio.py      # PPM / PNG / ASCII writers
│   └── cli.py          # command-line interface
├── tests/
│   └── test_raytracer.py
└── pyproject.toml
```

## Tests

```bash
python -m pytest tests/ -q
```

## License

MIT — see the repository root.