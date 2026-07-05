# Fractal Explorer

A from-scratch, pure-Python library for rendering escape-time fractals of complex dynamics.

Zero external dependencies — only the Python standard library is used (no NumPy, no Pillow, no PyYAML required for core functionality).

## Fractals

| Fractal | Formula | Notes |
|---|---|---|
| **Mandelbrot** | `z = z^p + c` from `z=0` | `p=2` classic; `p≠2` gives Multibrot |
| **Julia** | `z = z^p + c` from `z=point` | constant `c` set via `--julia-c` |
| **Burning Ship** | `z = (|Re z| + i|Im z|)^2 + c` | the "ship" fractal |
| **Tricorn** (Mandelbar) | `z = conj(z)^2 + c` | non-analytic, fractal "tricorn" |
| **Celtic** | `z = |Re(z^2)| + i·Im(z^2) + c` | Celtic knot-like fractal |
| **Phoenix** | `z_{n+1} = z_n^p + c + p_c·z_{n-1}` | feather-like, two-term recurrence |
| **Magnet** | `m(z) = ((z²+c)/(2z²+c-1))²` | rational map, magnetic-field domains |
| **Newton** | Newton iteration on `z^p − 1` | basin-coloured by root |
| **Custom** | user-supplied `fn(z, c)` | via Python API |

## Coloring Modes

| Mode | Description |
|---|---|
| `smooth` | Normalized iteration count (Hubbard–Douady) — continuous, no banding |
| `flat` | Raw integer iteration count → palette index |
| `de` | **True distance estimator** using derivative tracking (`|z'|·ln|z|/|z|`) for crisp boundary detail |
| `trap` | **Orbit-trap coloring** — colours a point by how close its orbit approaches a configurable trap (point, line, circle, cross) |
| `root` | Newton-basin coloring (color by which root the orbit converges to) |
| `histogram` | **Histogram-equalized** coloring — distributes colours evenly across the full iteration-count distribution |

## Orbit Traps

| Trap | Description |
|---|---|
| `point` | Single complex point (`--trap-point re,im`) |
| `line` | Infinite line through origin at angle (`--trap-angle rad`) |
| `circle` | Circle of given radius (`--trap-radius r`) |
| `cross` | Union of real and imaginary axes |

## Palettes (built-in)

`rainbow`, `fire`, `ice`, `grayscale`, `electric`, `sunset`, `ocean`, `magma`, `earth` — plus custom hex-gradient palettes (`--palette "#000000,#ff0000,#ffff00,#ffffff"` or `--palette '["#ff0000","#00ff00"]'`).

## Features

* **8 fractal families** with configurable parameters (power, Julia constant, Phoenix coefficient, Magnet variant, Newton power).
* **6 coloring modes** including true distance-estimator (derivative tracking), orbit traps, and histogram equalization.
* **4 orbit-trap types** (point, line, circle, cross).
* **9 built-in palettes** + custom hex gradients.
* **Supersampling anti-aliasing** (2×, 3×, 4×) for smooth edges.
* **Multiprocessing parallel rendering** (stdlib `multiprocessing` with spawn) for multi-core speed-up.
* **Arbitrary-precision deep zoom** using `decimal.Decimal` with configurable precision for zooms beyond `1e-15`.
* **Zoom-sequence batch renderer** producing animation-ready frame series with auto-scaling iteration counts and PNG metadata.
* **Julia-explorer**: render a grid of Julia sets for different constants with an HTML index page.
* **Benchmark** subcommand for measuring rendering throughput.
* **Multi-format output**: PNG (pure stdlib zlib, with tEXt metadata), PPM, SVG (vector), ASCII.
* JSON / TOML / YAML config support.
* Argparse CLI with 8 sub-commands.

## Usage

### CLI

```bash
# Render a classic Mandelbrot set
python3 fractal.py render --kind mandelbrot --width 800 --height 600 \
    --max-iter 500 --palette fire --output mandel.png

# Julia set (use = to avoid argparse treating the leading - as an option)
python3 fractal.py julia --julia-c="-0.7,0.27015" --width 800 --output julia.png

# Multibrot (power 5)
python3 fractal.py render --kind mandelbrot --power 5 --width 600 --output multibrot5.png

# Celtic fractal
python3 fractal.py render --kind celtic --center="0,0" --viewport-width 3 --output celtic.png

# Phoenix fractal
python3 fractal.py render --kind phoenix --phoenix-c="-0.5" --output phoenix.png

# Magnet fractal
python3 fractal.py render --kind magnet --magnet-variant 1 --output magnet.png

# Newton's method basins (z^3 - 1)
python3 fractal.py newton --width 600 --max-iter 80 --output newton.png

# Burning Ship
python3 fractal.py render --kind burning_ship --center="-0.5,-0.5" \
    --viewport-width 3.5 --output ship.png

# True distance-estimator coloring (Mandelbrot)
python3 fractal.py render --kind mandelbrot --coloring de --max-iter 500 --output de.png

# Orbit-trap coloring (cross trap)
python3 fractal.py render --kind mandelbrot --coloring trap --trap cross --output trap.png

# Histogram-equalized coloring
python3 fractal.py render --kind mandelbrot --coloring histogram --output hist.png

# Supersampled anti-aliased render
python3 fractal.py render --kind mandelbrot --supersample 3 --width 600 --output smooth.png

# Parallel render (2 worker processes)
python3 fractal.py render --kind mandelbrot --workers 2 --width 800 --output fast.png

# SVG vector output
python3 fractal.py render --kind mandelbrot --format svg --width 100 --output mandel.svg

# ASCII art preview
python3 fractal.py ascii --width 120 --height 40 --output mandel.txt

# Zoom sequence (30 frames, exponential zoom-in, high precision)
python3 fractal.py zoom --center="-0.745,0.105" \
    --start-width 3.0 --end-width 0.0001 --frames 30 \
    --output-dir zoom_frames --hp --prec 80

# Julia-explorer grid (4x4 = 16 Julia sets with HTML index)
python3 fractal.py explore --grid 4 --output-dir julia_grid --palette rainbow

# Palette strip preview
python3 fractal.py palette --name ice --output ice_strip.png

# Benchmark rendering throughput
python3 fractal.py benchmark --width 400 --height 400 --max-iter 300 --trials 3

# List available fractals / palettes / traps
python3 fractal.py info
```

### Python API

```python
from fractal import Viewport, render_fractal, write_png

vp = Viewport(center=-0.5+0j, width=3.0, height=2.0)
pixels, stats = render_fractal(
    kind="mandelbrot",
    viewport=vp,
    width=800, height=600,
    max_iter=512,
    palette_name="fire",
    coloring="smooth",
    supersample=2,      # anti-aliasing
    workers=4,          # parallel
)
write_png("mandel.png", pixels, 800, 600, text_meta={"fractal": "mandelbrot"})
print(stats)
```

True distance-estimator coloring:

```python
pixels, _ = render_fractal("mandelbrot", vp, 800, 600,
                            coloring="de", max_iter=1000)
```

Orbit-trap coloring:

```python
from fractal import CrossTrap
pixels, _ = render_fractal("mandelbrot", vp, 800, 600,
                            coloring="trap", trap=CrossTrap())
```

Histogram-equalized coloring:

```python
from fractal import render_histogram_coloring
pixels, _ = render_histogram_coloring("mandelbrot", vp, 800, 600,
                                       max_iter=512)
```

Deep zoom with arbitrary precision:

```python
from fractal import Viewport, render_mandelbrot_hp, write_png

vp = Viewport(center=-0.745+0.105j, width=1e-12, height=1e-12)
pixels, stats = render_mandelbrot_hp(vp, 400, 300, max_iter=2000, prec=80)
write_png("deep.png", pixels, 400, 300)
```

Julia grid explorer:

```python
from fractal import explore_julia
files = explore_julia(grid_size=4, img_size=(200, 200),
                      output_dir="julia_grid", max_iter=200,
                      palette_name="rainbow", c_radius=1.5)
# writes julia_grid/index.html + 16 PNGs
```

## How It Works

### Escape-time iteration

For each pixel we map screen coordinates to a complex number `c`, then iterate the fractal's map (e.g. `z ← z² + c`) starting from `z = 0` (Mandelbrot) or `z = c` (Julia). If `|z|²` exceeds the bailout radius before `max_iter`, the point escapes; the iteration count at escape determines the color. Points that never escape are colored as the interior.

### Smooth coloring

Integer iteration counts produce visible "bands" of color. We use the **normalized iteration count** formula:

```
ν = n + 1 − log(log|z_n|) / log(p)
```

which gives a continuous value that maps smoothly onto the palette, eliminating banding at the exterior.

### True distance estimator

For the Mandelbrot set, we track the derivative `dz/dc` alongside `z`. The derivative satisfies `dz_{n+1}/dc = p·z^{p-1}·dz_n/dc + 1`. The distance to the boundary is then approximated by:

```
d(c) = |z_n| · ln|z_n| / |dz_n/dc|
```

This gives a sharp, well-defined boundary that is far superior to the iteration-count proxy used by other coloring modes.

### Orbit traps

Instead of coloring by escape time, we track how close the orbit `{z_0, z_1, …}` comes to a geometric "trap" (a point, line, circle, or cross). The minimum distance over the orbit determines the color, producing smooth, artistic images that highlight the trap's geometry.

### Histogram equalization

Most pixels in a Mandelbrot render escape in just a few iterations, so a naive palette mapping wastes most of the color range. Histogram-equalized coloring first computes the iteration count for every pixel, builds a cumulative distribution, and maps each count so that equal color ranges cover equal numbers of pixels — spreading detail evenly across the palette.

### High-precision rendering

When the viewport width drops below roughly `1e-13`, double-precision floats no longer have enough mantissa bits to distinguish adjacent pixels. The `render_mandelbrot_hp` function switches to `decimal.Decimal` arithmetic with a configurable precision (`prec` decimal digits), so deep zooms remain crisp.

### Parallel rendering

For large images, the `workers` parameter distributes rows across `multiprocessing.Pool` worker processes (spawn context). A module-level worker function (`_render_row_worker`) is used so it can be pickled. Each worker rebuilds its iterator function and renders its assigned rows independently.

### Supersampling

Each output pixel is the average of an `N×N` grid of sub-samples (`supersample=N`). This smooths jagged edges at the cost of `N²`-times more computation per pixel.

### PNG output

PNG files are written using only `zlib` and `struct` from the standard library — the IHDR, optional tEXt metadata, IDAT (zlib-compressed scanlines with per-row filter byte 0), and IEND chunks are assembled by hand with correct CRC-32 checksums.

### SVG output

SVG files use one `<rect>` per pixel with run-length encoding of identical consecutive pixels in each row to keep file sizes manageable. The result is infinitely-scalable vector output (practical for images up to a few hundred pixels per side).

## Config Files

JSON, TOML, and YAML config files are supported via `--config`. Keys mirror the CLI long options (with `_` instead of `-`).

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
  "workers": 4
}
```

## Project Layout

```
fractal-explorer/
├── fractal.py          # Main library + CLI (single file)
├── README.md           # This file
├── examples/
│   └── gallery.py      # Script rendering 8 example fractals
└── tests/
    └── test_fractal.py # 68-test suite
```

## Testing

```bash
cd fractal-explorer
python3 -m unittest tests.test_fractal -v
# or
python3 -m pytest tests/
```

The test suite has 77 tests across two files:
- `tests/test_fractal.py` — 68 tests covering palettes, coloring, fractals,
  rendering, orbit traps, deep zoom, I/O, zoom sequences, Julia explorer,
  benchmark, and CLI parsing.
- `tests/test_bugs.py` — 9 regression tests for the bugs found and fixed
  during the Phase 3 bug hunt (see below).

## Known Issues (Resolved)

The following bugs were found during the bug hunt and fixed. Each has a
regression test in `tests/test_bugs.py`.

1. **Trap coloring used the wrong orbit formula for non-Mandelbrot fractals.**
   The orbit-trap coloring re-ran the iteration with a hardcoded
   `z = z*z + c` step, ignoring the fractal kind (Burning Ship, Tricorn,
   Celtic, Phoenix, Magnet, Newton) and the `power` parameter. This produced
   flat single-colour images for any fractal other than power-2
   Mandelbrot/Julia. **Fix:** the re-run now uses the correct per-kind
   iteration formula (Burning Ship takes `abs()` of components, Phoenix uses
   the two-term recurrence, Tricorn uses `conj(z)²`, etc.). *(test_bug01)*

2. **`_merge_config` silently overrode CLI flags with config-file values.**
   The docstring claimed config values would not override user-passed CLI
   flags, but the implementation did override them unconditionally. **Fix:**
   `_merge_config` now accepts an `explicit` set of dest names that are
   never overridden; `main()` detects which flags the user explicitly
   passed (by scanning `sys.argv` for option strings, recursing into
   subparsers) and passes that set through. *(test_bug07)*

3. **`render_mandelbrot_hp` modified the global `decimal` context.**
   Setting `getcontext().prec = prec` is a process-wide side effect that
   would corrupt any other `Decimal` user in the same process. **Fix:**
   use `decimal.localcontext()` so the precision change is scoped to the
   render call only. *(test_bug08)*

4. **`render_fractal` mutated the caller's `Viewport` object.**
   The aspect-ratio adjustment wrote `viewport.height = ...` in place, so
   calling `render_fractal` modified the caller's viewport — a surprising
   and bug-prone side effect. **Fix:** create a local `Viewport` copy
   instead of mutating the argument. *(test_bug12)*

5. **`render_histogram_coloring` mutated the caller's `Viewport` object.**
   Same aspect-ratio mutation bug as `render_fractal`. **Fix:** make a local
   copy. *(test_bug15)*

6. **`_parse_complex` and `_parse_rgb` raised unhelpful errors on malformed
   input.** `_parse_complex("1,2,3")` raised `ValueError: too many values to
   unpack`; `_parse_rgb("1,2,3,4")` crashed inside the list comprehension
   before the length check. **Fix:** validate the comma-count first and
   raise clear `ValueError` messages. *(test_bug09)*

## License

MIT.