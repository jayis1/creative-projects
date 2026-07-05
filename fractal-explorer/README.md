# Fractal Explorer

A from-scratch, pure-Python library for rendering escape-time fractals of complex dynamics.

Zero external dependencies — only the Python standard library is used (no NumPy, no Pillow).

## Fractals

| Fractal | Formula | Notes |
|---|---|---|
| **Mandelbrot** | `z = z^p + c` from `z=0` | `p=2` classic; `p≠2` gives Multibrot |
| **Julia** | `z = z^p + c` from `z=point` | constant `c` set via `--julia-c` |
| **Burning Ship** | `z = (|Re z| + i|Im z|)^2 + c` | the "ship" fractal |
| **Tricorn** (Mandelbar) | `z = conj(z)^2 + c` | non-analytic, fractal "tricorn" |
| **Newton** | Newton iteration on `z^p − 1` | basin-coloured by root |
| **Custom** | user-supplied `fn(z, c)` | via Python API |

## Coloring Modes

| Mode | Description |
|---|---|
| `smooth` | Normalized iteration count (Hubbard–Douady) — continuous, no banding |
| `flat` | Raw integer iteration count → palette index |
| `de` | Distance-estimator proxy for crisp boundary detail |
| `root` | Newton-basin coloring (color by which root the orbit converges to) |

## Palettes (built-in)

`rainbow`, `fire`, `ice`, `grayscale`, `electric` — plus custom hex-gradient palettes
(`--palette "#000000,#ff0000,#ffff00,#ffffff"`).

## Arbitrary-Precision Deep Zoom

For extreme zoom levels where IEEE-754 double precision loses digits, the
`mandelbrot_decimal` / `render_mandelbrot_hp` functions use Python's
`decimal.Decimal` with configurable precision. Use `zoom --hp --prec 80` for
zoom depths beyond `1e-15`.

## Usage

### CLI

```bash
# Render a classic Mandelbrot set
python3 fractal.py render --kind mandelbrot --width 800 --height 600 \
    --max-iter 500 --palette fire --output mandel.png

# Julia set
python3 fractal.py julia --julia-c="-0.7,0.27015" --width 800 --output julia.png

# Newton's method basins (z^3 - 1)
python3 fractal.py newton --width 600 --max-iter 80 --output newton.png

# Burning Ship
python3 fractal.py render --kind burning_ship --center="-0.5,-0.5" \
    --viewport-width 3.5 --output ship.png

# ASCII art preview
python3 fractal.py ascii --width 120 --height 40 --output mandel.txt

# Zoom sequence (30 frames, exponential zoom-in)
python3 fractal.py zoom --center="-0.745,0.105" \
    --start-width 3.0 --end-width 0.0001 --frames 30 \
    --output-dir zoom_frames --hp --prec 80

# Palette strip preview
python3 fractal.py palette --name ice --output ice_strip.png

# List available fractals / palettes
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
)
write_png("mandel.png", pixels, 800, 600)
print(stats)
```

Deep zoom with arbitrary precision:

```python
from fractal import Viewport, render_mandelbrot_hp, write_png

vp = Viewport(center=-0.745+0.105j, width=1e-12, height=1e-12)
pixels, stats = render_mandelbrot_hp(vp, 400, 300, max_iter=2000, prec=80)
write_png("deep.png", pixels, 400, 300)
```

## How It Works

### Escape-time iteration

For each pixel we map screen coordinates to a complex number `c`, then iterate
the fractal's map (e.g. `z ← z² + c`) starting from `z = 0` (Mandelbrot) or
`z = c` (Julia). If `|z|²` exceeds the bailout radius before `max_iter`, the
point escapes; the iteration count at escape determines the color. Points that
never escape are colored as the interior.

### Smooth coloring

Integer iteration counts produce visible "bands" of color. We use the
**normalized iteration count** formula:

```
ν = n + 1 − log(log|z_n|) / log(p)
```

which gives a continuous value that maps smoothly onto the palette, eliminating
banding at the exterior.

### High-precision rendering

When the viewport width drops below roughly `1e-13`, double-precision floats
no longer have enough mantissa bits to distinguish adjacent pixels. The
`render_mandelbrot_hp` function switches to `decimal.Decimal` arithmetic with a
configurable precision (`prec` decimal digits), so deep zooms remain crisp.

### PNG output

PNG files are written using only `zlib` and `struct` from the standard library —
the IHDR, IDAT (zlib-compressed scanlines with per-row filter byte 0), and IEND
chunks are assembled by hand with correct CRC-32 checksums.

## Config Files

JSON, TOML, and YAML config files are supported via `--config`. Keys mirror
the CLI long options (with `_` instead of `-`).

```json
{
  "kind": "mandelbrot",
  "width": 1024,
  "height": 768,
  "max_iter": 1000,
  "palette": "fire",
  "center": "-0.745,0.105",
  "viewport_width": 0.01
}
```

## Project Layout

```
fractal-explorer/
├── fractal.py          # Main library + CLI (single file)
├── README.md           # This file
├── examples/
│   └── gallery.py      # Script rendering several example fractals
└── tests/
    └── test_fractal.py # Test suite
```

## License

MIT.