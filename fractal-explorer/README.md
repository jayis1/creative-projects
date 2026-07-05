# 🔺 Fractal Explorer

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 135](https://img.shields.io/badge/tests-135-brightgreen.svg)](#testing)
[![Dependencies: None](https://img.shields.io/badge/dependencies-none-success.svg)](#dependencies)
[![Format: PNG/SVG/TGA](https://img.shields.io/badge/output-PNG%2FSVG%2FTGA-orange.svg)](#output-formats)

> A from-scratch, pure-Python library for rendering escape-time and other
> fractals of complex dynamics — **zero external dependencies** (Python
> stdlib only, no NumPy, no Pillow, no PyYAML required for core features).

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI Reference](#cli-reference)
  - [Python API](#python-api)
  - [Config Files](#config-files)
  - [Presets](#presets)
- [Fractals](#fractals)
- [Coloring Modes](#coloring-modes)
- [Orbit Traps](#orbit-traps)
- [Palettes](#palettes)
- [Post-Processing Filters](#post-processing-filters)
- [Output Formats](#output-formats)
- [Architecture](#architecture)
- [Performance](#performance)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Overview

Fractal Explorer is a comprehensive fractal rendering toolkit written in
pure Python using only the standard library. It supports 10+ fractal
families, 6 coloring modes, 6 orbit-trap types, 11 built-in colour
palettes, 8 post-processing filters, 5 output formats, arbitrary-precision
deep zoom, parallel rendering, and animation — all without a single
external dependency.

The project is structured as a proper Python package with a modular
architecture, a full CLI, preset management, and a 135-test suite.

## Key Features

| Category | Features |
|---|---|
| **Fractals** | Mandelbrot, Multibrot, Julia, Burning Ship, Tricorn, Celtic, Phoenix, Magnet, Newton, Mandelbrot (periodic), Buddhabrot, Anti-Buddhabrot, Lyapunov, IFS (Barnsley Fern, Sierpinski Triangle, Dragon Curve) |
| **Coloring** | Smooth (normalized iteration count), flat, true distance-estimator (derivative tracking), orbit-trap, Newton root-basin, histogram-equalized |
| **Traps** | Point, line, circle, cross, stripe, spiral |
| **Palettes** | rainbow, fire, ice, grayscale, electric, sunset, ocean, magma, earth, neon, forest + custom hex gradients |
| **Filters** | Box blur, Gaussian blur, Sobel edge detect, emboss, grayscale, invert, brightness, contrast |
| **Output** | PNG (with tEXt metadata), PPM, SVG (vector), ASCII art, TGA |
| **Precision** | Double-precision for normal zoom; `decimal.Decimal` for arbitrary-precision deep zoom |
| **Performance** | Multiprocessing parallel rendering, supersampling anti-aliasing, Brent cycle detection for interior points |
| **Tools** | Zoom-sequence batch renderer, Julia-grid explorer, benchmark, animation, preset manager |
| **Config** | JSON / YAML / TOML config files, named presets, CLI with 14 subcommands |

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/fractal-explorer
pip install -e ".[dev]"   # installs with test dependencies
# or just:
pip install -e .           # core only (no test deps)
```

### No installation needed

Since the project has zero dependencies, you can also just run it directly:

```bash
cd fractal-explorer
python3 -m fractal_explorer.cli info
```

### Dependencies

- **Required:** Python 3.9+ (uses only the standard library)
- **Optional:** PyYAML (for YAML config files), tomli (for TOML on Python < 3.11)
- **Test:** pytest

## Quick Start

```bash
# Classic Mandelbrot set
python3 -m fractal_explorer.cli render --kind mandelbrot --width 800 --height 600 \
    --max-iter 500 --palette fire --output mandel.png

# Barnsley Fern (IFS fractal)
python3 -m fractal_explorer.cli ifs --type fern --width 400 --output fern.png

# Buddhabrot (nebula-like escape-dynamics image)
python3 -m fractal_explorer.cli buddhabrot --width 400 --samples 200000 \
    --max-iter 500 --palette magma --output buddha.png

# Lyapunov fractal
python3 -m fractal_explorer.cli lyapunov --width 400 --sequence ABBA \
    --palette ocean --output lyap.png

# List all available options
python3 -m fractal_explorer.cli info
```

## Usage

### CLI Reference

The CLI provides 14 subcommands:

| Command | Description |
|---|---|
| `render` | Render a single fractal image |
| `julia` | Render a Julia set (shortcut) |
| `newton` | Render a Newton basin fractal (shortcut) |
| `ascii` | Render to an ASCII art file |
| `zoom` | Render a zoom sequence (animation frames) |
| `palette` | Render a palette strip preview |
| `explore` | Render a grid of Julia sets with HTML index |
| `benchmark` | Benchmark rendering throughput |
| `info` | List available fractals, palettes, traps, filters, presets |
| `buddhabrot` | Render a Buddhabrot image |
| `lyapunov` | Render a Lyapunov fractal |
| `ifs` | Render an IFS fractal (fern, sierpinski, dragon) |
| `animate` | Render an animation (julia-morph or color-cycle) |
| `preset` | Manage render presets (list, save, load, delete) |
| `filter` | List available post-processing filters |

#### Examples

```bash
# ─── Basic rendering ───────────────────────────────────────────────

# Classic Mandelbrot
python3 -m fractal_explorer.cli render --kind mandelbrot --width 800 \
    --height 600 --max-iter 500 --palette fire --output mandel.png

# Julia set (use = to avoid argparse treating leading - as an option)
python3 -m fractal_explorer.cli julia --julia-c="-0.7,0.27015" \
    --width 800 --output julia.png

# Multibrot (power 5)
python3 -m fractal_explorer.cli render --kind mandelbrot --power 5 \
    --width 600 --output multibrot5.png

# Celtic fractal
python3 -m fractal_explorer.cli render --kind celtic \
    --center="0,0" --viewport-width 3 --output celtic.png

# Phoenix fractal
python3 -m fractal_explorer.cli render --kind phoenix \
    --phoenix-c="-0.5" --output phoenix.png

# Newton's method basins (z^3 - 1)
python3 -m fractal_explorer.cli newton --width 600 --max-iter 80 \
    --output newton.png

# Burning Ship
python3 -m fractal_explorer.cli render --kind burning_ship \
    --center="-0.5,-0.5" --viewport-width 3.5 --output ship.png

# ─── Coloring modes ─────────────────────────────────────────────────

# True distance-estimator coloring (Mandelbrot)
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --coloring de --max-iter 500 --output de.png

# Orbit-trap coloring (cross trap)
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --coloring trap --trap cross --output trap.png

# Orbit-trap with stripe trap
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --coloring trap --trap stripe --output stripe.png

# Histogram-equalized coloring
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --coloring histogram --output hist.png

# ─── Quality & performance ───────────────────────────────────────────

# Supersampled anti-aliased render
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --supersample 3 --width 600 --output smooth.png

# Parallel render (4 worker processes)
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --workers 4 --width 800 --output fast.png

# Periodicity detection (faster interior)
python3 -m fractal_explorer.cli render --kind mandelbrot_periodic \
    --max-iter 1000 --output periodic.png

# ─── Output formats ─────────────────────────────────────────────────

# SVG vector output
python3 -m fractal_explorer.cli render --format svg --width 100 \
    --output mandel.svg

# TGA output
python3 -m fractal_explorer.cli render --format tga --output mandel.tga

# ASCII art preview
python3 -m fractal_explorer.cli ascii --width 120 --height 40 \
    --output mandel.txt

# ─── Post-processing ────────────────────────────────────────────────

# Render + apply edge-detection filter
python3 -m fractal_explorer.cli render --kind mandelbrot \
    --filter edge --output mandel_edges.png

# ─── Advanced fractals ──────────────────────────────────────────────

# Buddhabrot (traces escaping orbits)
python3 -m fractal_explorer.cli buddhabrot --width 500 --samples 500000 \
    --max-iter 1000 --palette magma --output buddha.png

# Anti-Buddhabrot (traces interior orbits)
python3 -m fractal_explorer.cli buddhabrot --anti --width 400 \
    --output anti_buddha.png

# Lyapunov fractal (logistic map chaos/order)
python3 -m fractal_explorer.cli lyapunov --width 400 --sequence ABBA \
    --max-iter 500 --palette magma --output lyap.png

# IFS: Barnsley Fern
python3 -m fractal_explorer.cli ifs --type fern --width 400 \
    --iterations 200000 --palette forest --output fern.png

# IFS: Sierpinski Triangle
python3 -m fractal_explorer.cli ifs --type sierpinski --width 400 \
    --output sierpinski.png

# IFS: Dragon Curve
python3 -m fractal_explorer.cli ifs --type dragon --width 400 \
    --output dragon.png

# ─── Batch & animation ──────────────────────────────────────────────

# Zoom sequence (30 frames, exponential zoom-in, high precision)
python3 -m fractal_explorer.cli zoom --center="-0.745,0.105" \
    --start-width 3.0 --end-width 0.0001 --frames 30 \
    --output-dir zoom_frames --hp --prec 80

# Julia-grid explorer (4x4 = 16 Julia sets with HTML index)
python3 -m fractal_explorer.cli explore --grid 4 \
    --output-dir julia_grid --palette rainbow

# Julia morph animation (interpolate Julia constant)
python3 -m fractal_explorer.cli animate --mode julia-morph \
    --c-start="-0.4,0.6" --c-end="0.285,0.01" --frames 30 \
    --output-dir morph_frames

# Colour-cycling animation
python3 -m fractal_explorer.cli animate --mode color-cycle \
    --kind mandelbrot --frames 24 --output-dir cycle_frames

# ─── Presets ────────────────────────────────────────────────────────

# List available presets
python3 -m fractal_explorer.cli preset list

# Render using a preset
python3 -m fractal_explorer.cli render --preset seahorse-valley \
    --output seahorse.png

# Save a custom preset
python3 -m fractal_explorer.cli preset save --name my-view \
    --params '{"kind":"julia","julia_c":"-0.8,0.156","palette":"neon"}'

# ─── Benchmarking ───────────────────────────────────────────────────

# Benchmark rendering throughput
python3 -m fractal_explorer.cli benchmark --width 400 --height 400 \
    --max-iter 300 --trials 3

# Palette strip preview
python3 -m fractal_explorer.cli palette --name ice --output ice_strip.png

# List all options
python3 -m fractal_explorer.cli info
```

### Python API

```python
from fractal_explorer import (
    Viewport, render_fractal, write_png, write_tga,
    render_buddhabrot, render_lyapunov, render_ifs,
    BARNSLEY_FERN, apply_filter,
)

# ── Basic Mandelbrot ──
vp = Viewport(center=-0.5+0j, width=3.0, height=2.0)
pixels, stats = render_fractal(
    kind="mandelbrot", viewport=vp, width=800, height=600,
    max_iter=512, palette_name="fire", coloring="smooth",
    supersample=2,      # anti-aliasing
    workers=4,          # parallel
)
write_png("mandel.png", pixels, 800, 600,
          text_meta={"fractal": "mandelbrot"})
print(stats)

# ── True distance-estimator coloring ──
pixels, _ = render_fractal("mandelbrot", vp, 800, 600,
                            coloring="de", max_iter=1000)

# ── Orbit-trap coloring ──
from fractal_explorer import CrossTrap, StripeTrap
pixels, _ = render_fractal("mandelbrot", vp, 800, 600,
                            coloring="trap", trap=StripeTrap(count=12))

# ── Histogram-equalized coloring ──
from fractal_explorer import render_histogram_coloring
pixels, _ = render_histogram_coloring("mandelbrot", vp, 800, 600,
                                       max_iter=512)

# ── Deep zoom with arbitrary precision ──
from fractal_explorer import render_mandelbrot_hp
vp = Viewport(center=-0.745+0.105j, width=1e-12, height=1e-12)
pixels, stats = render_mandelbrot_hp(vp, 400, 300, max_iter=2000, prec=80)
write_png("deep.png", pixels, 400, 300)

# ── Buddhabrot ──
pixels, stats = render_buddhabrot(vp, 500, 500, samples=500000,
                                   max_iter=1000, seed=42)

# ── Lyapunov ──
pixels, stats = render_lyapunov(width=500, height=500,
                                sequence="ABBA", max_iter=500)

# ── IFS: Barnsley Fern ──
pixels, stats = render_ifs(BARNSLEY_FERN, width=400, height=400,
                            iterations=200000, palette_name="forest")

# ── Post-processing ──
from fractal_explorer import apply_filter
pixels = apply_filter(pixels, 400, 400, "gaussian")
pixels = apply_filter(pixels, 400, 400, "edge")

# ── Julia grid explorer ──
from fractal_explorer import explore_julia
files = explore_julia(grid_size=4, img_size=(200, 200),
                      output_dir="julia_grid", max_iter=200,
                      palette_name="rainbow", c_radius=1.5)
```

### Config Files

JSON, TOML, and YAML config files are supported via `--config`. Keys mirror
the CLI long options (with `_` instead of `-`).

```json
{
  "kind": "mandelbrot",
  "width": 1024,
  "height": 768,
  "max_iter": 1000,
  "palette": "fire",
  "coloring": "smooth",
  "center": "-0.745,0.105",
  "viewport_width": 0.01,
  "supersample": 2,
  "workers": 4,
  "filter": "gaussian"
}
```

```bash
python3 -m fractal_explorer.cli render --config render.json --output out.png
```

CLI flags always take precedence over config-file values when both are
provided.

### Presets

Built-in named presets for classic fractal viewpoints:

| Preset | Description |
|---|---|
| `mandelbrot-classic` | Standard full Mandelbrot view |
| `seahorse-valley` | Deep zoom into Seahorse Valley |
| `elephant-valley` | Zoom into Elephant Valley |
| `julia-dendrite` | Julia set with dendrite pattern |
| `julia-dragon` | Julia set with dragon pattern |
| `burning-ship` | Classic Burning Ship view |
| `newton-cubic` | Newton basins for z³ − 1 |
| `multibrot-5` | Multibrot with power 5 |
| `tricorn` | Tricorn (Mandelbar) fractal |
| `phoenix` | Phoenix fractal |

```bash
# Use a preset
python3 -m fractal_explorer.cli render --preset seahorse-valley --output out.png

# Save your own
python3 -m fractal_explorer.cli preset save --name my-favorite \
    --params '{"kind":"julia","julia_c":"-0.8,0.156","palette":"neon"}'
```

## Fractals

| Fractal | Formula | Notes |
|---|---|---|
| **Mandelbrot** | `z = z^p + c` from `z=0` | `p=2` classic; `p≠2` gives Multibrot |
| **Mandelbrot (periodic)** | Same + Brent cycle detection | Faster interior rendering |
| **Julia** | `z = z^p + c` from `z=point` | constant `c` set via `--julia-c` |
| **Burning Ship** | `z = (\|Re z\| + i\|Im z\|)^2 + c` | the "ship" fractal |
| **Tricorn** (Mandelbar) | `z = conj(z)^2 + c` | non-analytic, fractal "tricorn" |
| **Celtic** | `z = \|Re(z²)\| + i·Im(z²) + c` | Celtic knot-like fractal |
| **Phoenix** | `z_{n+1} = z_n^p + c + p_c·z_{n-1}` | feather-like, two-term recurrence |
| **Magnet** | `m(z) = ((z²+c)/(2z²+c-1))²` | rational map, magnetic-field domains |
| **Newton** | Newton iteration on `z^p − 1` | basin-coloured by root |
| **Custom** | user-supplied `fn(z, c)` | via Python API |
| **Buddhabrot** | Histogram of escaping orbits | nebula-like escape dynamics |
| **Anti-Buddhabrot** | Histogram of interior orbits | inverse of Buddhabrot |
| **Lyapunov** | Logistic map Lyapunov exponent | chaos/order regions |
| **IFS** | Iterated Function System | Barnsley Fern, Sierpinski, Dragon |

## Coloring Modes

| Mode | Description |
|---|---|
| `smooth` | Normalized iteration count (Hubbard–Douady) — continuous, no banding |
| `flat` | Raw integer iteration count → palette index |
| `de` | **True distance estimator** using derivative tracking (`\|z'\|·ln\|z\|/\|z\|`) |
| `trap` | **Orbit-trap coloring** — colour by closest orbit approach to a trap |
| `root` | Newton-basin coloring (colour by which root the orbit converges to) |
| `histogram` | **Histogram-equalized** coloring — even colour distribution |

## Orbit Traps

| Trap | Description |
|---|---|
| `point` | Single complex point (`--trap-point re,im`) |
| `line` | Infinite line through origin at angle (`--trap-angle rad`) |
| `circle` | Circle of given radius (`--trap-radius r`) |
| `cross` | Union of real and imaginary axes |
| `stripe` | Angular stripes — radiating stripe patterns (`--trap-count N`) |
| `spiral` | Archimedean spiral — spiral trap patterns |

## Palettes

Built-in: `rainbow`, `fire`, `ice`, `grayscale`, `electric`, `sunset`,
`ocean`, `magma`, `earth`, `neon`, `forest`

Custom hex gradients:
```bash
--palette "#000000,#ff0000,#ffff00,#ffffff"
--palette '["#ff0000","#00ff00","#0000ff"]'
```

## Post-Processing Filters

Apply with `--filter <name>` on the `render` command, or via the Python API:

| Filter | Description |
|---|---|
| `blur` | Box blur (radius 1) |
| `gaussian` | Gaussian blur (radius 1) |
| `edge` | Sobel edge detection |
| `emboss` | 3D emboss effect |
| `grayscale` | Luminance grayscale conversion |
| `invert` | Colour inversion |
| `brightness` | +30 brightness shift |
| `contrast` | 1.5× contrast boost |

```python
from fractal_explorer import apply_filter
pixels = apply_filter(pixels, width, height, "edge")
pixels = apply_filter(pixels, width, height, "invert")
```

## Output Formats

| Format | Extension | Description |
|---|---|---|
| **PNG** | `.png` | 8-bit RGB with optional tEXt metadata (pure zlib) |
| **PPM** | `.ppm` | Binary P6 PPM |
| **SVG** | `.svg` | Vector output with run-length encoding (infinitely scalable) |
| **ASCII** | `.txt` | Luminance-mapped ASCII art |
| **TGA** | `.tga` | Uncompressed 24-bit Targa |

## Architecture

```
fractal_explorer/
├── __init__.py       # Public API re-exports + __version__
├── palettes.py       # 11 colour palettes + custom hex gradients
├── iterators.py      # 10 fractal iteration functions + FRACTALS registry
├── periodicity.py    # Brent cycle detection for interior points
├── traps.py          # 6 orbit-trap classes (point/line/circle/cross/stripe/spiral)
├── viewport.py       # Complex-plane viewport with zoom, fit_aspect, pixel_to_complex
├── coloring.py       # Per-pixel colour computation (smooth/flat/de/trap/root)
├── render.py         # Rendering engine (single + multiprocessing parallel)
├── hp.py             # Arbitrary-precision Decimal rendering for deep zoom
├── io_writers.py     # PNG/PPM/SVG/ASCII/TGA output (all stdlib)
├── zoom.py           # Zoom-sequence batch renderer
├── julia.py          # Julia-grid explorer with HTML index
├── benchmark.py      # Throughput benchmarking
├── config.py         # JSON/YAML/TOML config loading + CLI merge
├── buddhabrot.py     # Buddhabrot / Anti-Buddhabrot rendering
├── lyapunov.py       # Lyapunov fractal (logistic map chaos/order)
├── ifs.py            # Iterated Function System fractals (fern/sierpinski/dragon)
├── filters.py        # 8 post-processing image filters
├── animation.py      # Julia-morph and colour-cycling animation
├── presets.py        # 10 built-in presets + PresetManager
├── cli.py            # Argparse CLI with 14 subcommands
└── fractal.py        # Backward-compat shim (imports from package)
```

### How It Works

#### Escape-time iteration

For each pixel we map screen coordinates to a complex number `c`, then
iterate the fractal's map (e.g. `z ← z² + c`) starting from `z = 0`
(Mandelbrot) or `z = c` (Julia). If `|z|²` exceeds the bailout radius before
`max_iter`, the point escapes; the iteration count at escape determines the
colour. Points that never escape are coloured as the interior.

#### Periodicity detection

For interior points (which never escape), Brent's cycle detection algorithm
identifies repeating orbits early, allowing the iterator to return
`max_iter` before doing all the iterations. This dramatically speeds up
rendering of the interior, especially at high iteration counts.

#### Smooth coloring

Integer iteration counts produce visible "bands" of colour. We use the
**normalized iteration count** formula:

```
ν = n + 1 − log(log|z_n|) / log(p)
```

which gives a continuous value that maps smoothly onto the palette,
eliminating banding at the exterior.

#### True distance estimator

For the Mandelbrot set, we track the derivative `dz/dc` alongside `z`. The
derivative satisfies `dz_{n+1}/dc = p·z^{p-1}·dz_n/dc + 1`. The distance to
the boundary is then approximated by:

```
d(c) = |z_n| · ln|z_n| / |dz_n/dc|
```

This gives a sharp, well-defined boundary that is far superior to the
iteration-count proxy used by other coloring modes.

#### Orbit traps

Instead of coloring by escape time, we track how close the orbit
`{z_0, z_1, …}` comes to a geometric "trap" (a point, line, circle, cross,
stripe, or spiral). The minimum distance over the orbit determines the
colour, producing smooth, artistic images that highlight the trap's geometry.

#### Histogram equalization

Most pixels in a Mandelbrot render escape in just a few iterations, so a
naive palette mapping wastes most of the colour range. Histogram-equalized
coloring first computes the iteration count for every pixel, builds a
cumulative distribution, and maps each count so that equal colour ranges
cover equal numbers of pixels — spreading detail evenly across the palette.

#### Buddhabrot

The Buddhabrot traces the *orbits* of escaping points and accumulates a
histogram of how often each pixel is visited. Points that escape quickly
contribute little; points that take many iterations to escape travel far
and contribute the most. The result is a haunting, nebula-like image.

#### High-precision rendering

When the viewport width drops below roughly `1e-13`, double-precision floats
no longer have enough mantissa bits to distinguish adjacent pixels. The
`render_mandelbrot_hp` function switches to `decimal.Decimal` arithmetic
with a configurable precision (`prec` decimal digits), so deep zooms remain
crisp. A `localcontext()` ensures the precision change doesn't leak
globally.

#### Parallel rendering

For large images, the `workers` parameter distributes rows across
`multiprocessing.Pool` worker processes (spawn context). A module-level
worker function (`_render_row_worker`) is used so it can be pickled. Each
worker rebuilds its iterator function and renders its assigned rows
independently.

## Performance

| Configuration | ~Pixels/sec (single core) |
|---|---|
| Mandelbrot, smooth, 256 iter | ~500K |
| Mandelbrot, DE, 512 iter | ~200K |
| Burning Ship, smooth, 256 iter | ~400K |
| Newton, root, 60 iter | ~1M |

Use `--workers N` for N-core parallel speedup (near-linear scaling).
Use `--kind mandelbrot_periodic` for faster interior rendering at high
iteration counts. Use `--supersample 2` for anti-aliased output (costs 4×).

Run `python3 -m fractal_explorer.cli benchmark` to measure on your machine.

## Testing

```bash
cd fractal-explorer

# Full suite (135 tests)
python3 -m pytest tests/ -v

# Or with unittest
python3 -m pytest tests/test_fractal.py -v       # original 77 tests
python3 -m pytest tests/test_bugs.py -v          # 9 regression tests
python3 -m pytest tests/test_new_features.py -v  # 58 new-feature tests
```

The test suite has **135 tests** across three files:

- `tests/test_fractal.py` — 68 tests covering palettes, coloring, fractals,
  rendering, orbit traps, deep zoom, I/O, zoom sequences, Julia explorer,
  benchmark, and CLI parsing.
- `tests/test_bugs.py` — 9 regression tests for bugs found and fixed.
- `tests/test_new_features.py` — 58 tests covering new palettes, new traps,
  Buddhabrot, Lyapunov, IFS, filters, TGA output, periodicity detection,
  presets, animation, viewport improvements, CLI new commands, and package
  structure.

## Known Issues (Resolved)

The following bugs were found during the original bug hunt and fixed. Each
has a regression test in `tests/test_bugs.py`.

1. **Trap coloring used the wrong orbit formula for non-Mandelbrot fractals.**
   The orbit-trap coloring re-ran the iteration with a hardcoded
   `z = z*z + c` step, ignoring the fractal kind. **Fix:** the re-run now
   uses the correct per-kind iteration formula. *(test_bug01)*

2. **`_merge_config` silently overrode CLI flags with config-file values.**
   **Fix:** `_merge_config` now accepts an `explicit` set of dest names that
   are never overridden. *(test_bug07)*

3. **`render_mandelbrot_hp` modified the global `decimal` context.**
   **Fix:** use `decimal.localcontext()` so the precision change is scoped
   to the render call only. *(test_bug08)*

4. **`render_fractal` mutated the caller's `Viewport` object.**
   **Fix:** create a local `Viewport` copy via `fit_aspect()` instead of
   mutating the argument. *(test_bug12)*

5. **`render_histogram_coloring` mutated the caller's `Viewport` object.**
   Same aspect-ratio mutation bug. **Fix:** make a local copy. *(test_bug15)*

6. **`_parse_complex` and `_parse_rgb` raised unhelpful errors on malformed
   input.** **Fix:** validate the comma-count first and raise clear
   `ValueError` messages. *(test_bug09)*

## Roadmap

- [ ] Animated GIF output (stdlib-only encoder)
- [ ] 3D heightmap rendering (fractal → terrain)
- [ ] Fractal flame renderer (variation-based IFS)
- [ ] WebAssembly build for browser rendering
- [ ] GPU acceleration via ctypes/OpenCL fallback
- [ ] Interactive viewer mode (terminal-based navigation)
- [ ] More IFS fractals (Heighway dragon, Levy C-curve, Koch snowflake)
- [ ] Domain coloring for arbitrary complex functions
- [ ] Quaternion Julia sets (3D)
- [ ] Perlin-noise palette perturbation

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
architecture guide, and how to add new fractals, palettes, and filters.

## Changelog

### v1.1.0 — Comprehensive Improvement

**Architecture:**
- Split monolithic 1751-line `fractal.py` into 19 focused modules
- Created proper `fractal_explorer` Python package
- Added `pyproject.toml` for pip installation
- Added backward-compatibility shim (`fractal.py` still works)
- Added type hints throughout
- Added `__version__` and `__author__` metadata

**New Fractals:**
- Buddhabrot (escape-orbit histogram)
- Anti-Buddhabrot (interior-orbit histogram)
- Lyapunov fractal (logistic map chaos/order)
- IFS fractals: Barnsley Fern, Sierpinski Triangle, Dragon Curve
- Mandelbrot with Brent periodicity detection

**New Features:**
- TGA output format
- 8 post-processing filters (blur, Gaussian, edge, emboss, grayscale,
  invert, brightness, contrast)
- 2 new orbit traps (stripe, spiral)
- 2 new palettes (neon, forest)
- Julia-morph animation
- Colour-cycling animation
- 10 built-in render presets + PresetManager
- Viewport improvements: `copy()`, `fit_aspect()`, `pixel_to_complex()`
- CLI expanded from 8 to 14 subcommands
- `--filter` flag for post-processing on render
- `--preset` flag for named preset rendering
- `--format tga` support
- GitHub Actions CI workflow

**Testing:**
- Expanded from 77 to 135 tests (58 new tests for new features)

### v1.0.0 — Initial Release

8 fractal families, 6 coloring modes, 4 orbit traps, 9 palettes,
supersampling, multiprocessing, arbitrary-precision deep zoom, zoom
sequences, Julia explorer, benchmark, PNG/PPM/SVG/ASCII output, JSON/YAML/
TOML config, 77 tests.

## License

MIT — see [LICENSE](LICENSE).