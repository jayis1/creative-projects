# Changelog

All notable changes to **raytracer** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] — 2026-06-20

### Added — Major new features
- **Texture system** (`raytracer/texture.py`): `Texture` base class, `SolidColor`,
  `CheckerTexture`, `PerlinNoise`, `NoiseTexture`, `Turbulence`, `Marble`,
  `ImageTexture`. All materials now accept textures in addition to flat colors.
- **New primitives**: `Box` (axis-aligned box from 6 rects), `Disk` (flat
  circular disk), `Cylinder` (finite Y-axis cylinder with optional caps),
  `XZRect`, `YZRect`.
- **New material**: `Isotropic` (volume scattering / participating media).
- **New integrator mode**: `depth` — encodes hit distance as grayscale for
  debugging scene scale and camera placement.
- **Russian roulette** path termination (`--rr-start-depth`) for unbiased
  early termination of long paths.
- **Next Event Estimation (NEE)**: explicit direct-light sampling when a scene
  defines emissive lights, reducing noise in directly-lit scenes.
- **Render statistics**: `RenderStats` tracks rays, bounces, hits, misses,
  elapsed time, and rays/second. Accessible via `renderer.stats` and the
  `--stats` flag / `stats` CLI subcommand.
- **Animation module** (`raytracer/animation.py`): `orbit_path`,
  `linear_path`, `spline_path` (Catmull–Rom), and `render_animation` driver.
- **Logging module** (`raytracer/logging.py`): pre-configured
  `"raytracer"` logger with ANSI color formatter and `--log-level` CLI flag.
- **New scene presets**: `solar-system` (emissive sun + planets),
  `marble-hall` (Perlin marble columns), `nebula` (noise-textured spheres).
- **YAML and TOML scene file support**: `load_scene_file` auto-detects
  JSON / YAML / TOML from the file extension.
- **Textured materials in scene files**: `albedo` fields accept either a Vec3
  or a full texture mapping (`{"type": "noise", ...}`).
- **CLI `animate` subcommand**: render camera orbit / dolly / spline
  frame sequences.
- **CLI `stats` subcommand**: render and print JSON render statistics.
- **CLI `--rr-start-depth` flag** for Russian roulette.
- **CLI `--stats` flag** on `render` to print stats after rendering.
- **CONTRIBUTING.md**, **LICENSE**, **CHANGELOG.md**.

### Changed
- `Matte`, `Metal`, `Emissive` now accept `Texture` objects in addition to
  `Vec3` colors (backward compatible — Vec3 is auto-wrapped in `SolidColor`).
- `Scene` now carries an optional `lights` list for NEE; `make_renderer`
  forwards it to the `Renderer`.
- `MODES` now includes `"depth"`.
- `Renderer.__init__` accepts `rr_start_depth` and `lights` parameters.
- `pyproject.toml` declares optional dependencies (`yaml`, `dev`) and metadata
  (license, authors, keywords).
- Version bumped to 2.0.0.

### Fixed
- `ImageTexture` pixel mapping now uses `int(u * width)` with clamping instead
  of `int(u * (width - 1))`, fixing subpixel errors on small images.

## [1.1.0] — 2026-06-20

### Added
- Three integrator modes: `path`, `ao`, `normal`.
- JSON scene serialization (`serialize.py`).
- Multi-threaded tile-based rendering via `ProcessPoolExecutor`.
- `validate` CLI subcommand.
- `--mode`, `--threads`, `--scene-file`, `--ao-distance`, `--gamma` CLI flags.
- Example script and sample JSON scene.
- 23 new tests (72 total).

### Fixed
- AABB slab division by zero on parallel rays.
- Pixel jitter exceeding the image plane (edge bleed).
- `XYRect.hit` division by zero on parallel rays.
- Unpicklable backgrounds breaking multi-process rendering.

## [1.0.0] — 2026-06-20

### Added
- From-scratch recursive ray tracer: `Vec3`, `Ray`, `Camera`, `Renderer`.
- Primitives: `Sphere`, `Plane`, `Triangle` (Möller–Trumbore), `XYRect`.
- BVH acceleration (midpoint split, zero-dir-safe slabs).
- Materials: `Matte`, `Metal`, `Dielectric` (Schlick), `Emissive`, `Checker`.
- Pinhole camera with depth-of-field.
- Jittered supersampled anti-aliasing.
- Gradient sky background.
- PPM / PNG / ASCII output.
- Three scene presets: `three-balls`, `cornell`, `random`.
- argparse CLI: `render`, `scenes`, `info`.
- 49 tests.