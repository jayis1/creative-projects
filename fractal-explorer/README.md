# 🔮 ASCII Fractal Explorer

**Explore Mandelbrot, Julia, Burning Ship, and Tricorn sets directly in your terminal** — with interactive zoom, pan, palette switching, smooth coloring, bookmarks, and mouse support. Zero external dependencies.

![Fractal](https://img.shields.io/badge/type-visualization-blue) ![Python](https://img.shields.io/badge/python-3.8+-green) ![CLI](https://img.shields.io/badge/interface-curses%20%2B%20CLI-orange) ![Version](https://img.shields.io/badge/version-2.0.0-blue)

## What It Does

ASCII Fractal Explorer renders fractals as colored ASCII art in your terminal. You can zoom into infinite detail, switch between four fractal types, cycle through eight color palettes, jump to curated bookmarks of interesting locations, and export high-resolution renders to text files.

The fractal is computed per-pixel using escape-time iteration with optional smooth coloring (renormalization via log₂(log₂(|z|))) for silky gradient transitions instead of harsh color bands.

## Features

### Fractal Types
- **Mandelbrot set** — The classic z = z² + c
- **Julia set** — z = z² + c with fixed c (8 built-in presets)
- **Burning Ship** — z = (|Re(z)| + i|Im(z)|)² + c (flipped-absolute variant)
- **Tricorn** — z = conj(z)² + c (Mandelbar set)

### Color Palettes (8 total)
Fire, Ocean, Matrix, Electric, Earth, Grayscale, **Neon**, **Sunset**

### Interactive Controls
| Key | Action |
|---|---|
| Arrow keys / WASD | Pan around the fractal |
| `+` / `-` | Zoom in / out |
| `F` | Cycle fractal type (Mandelbrot → Julia → Burning Ship → Tricorn) |
| `P` | Cycle color palette |
| `I` / `Shift+I` | Increase / decrease max iterations |
| `T` | Toggle smooth coloring |
| `J` | Cycle Julia set presets (with names) |
| `B` | Open bookmarks menu — jump to famous coordinates |
| `E` | Export current view to `~/fractal_export.txt` |
| `R` | Reset view to default |
| `H` | Toggle help overlay |
| `Q` / `Esc` | Quit |
| Shift+Arrows | Adjust Julia c parameter |
| Mouse click | Re-center on clicked point |

### Other Features
- **Smooth coloring** — Continuous iteration count for beautiful gradients
- **Auto-scaling iterations** — Max iterations increase automatically as you zoom deeper
- **Flash messages** — Feedback for palette changes, mode switches, and exports
- **Render time display** — Shows ms per frame in the status bar
- **Bookmarks** — 6 curated interesting locations (Seahorse Valley, Elephant Valley, etc.)
- **Mouse support** — Click to re-center the view
- **Export to file** — Save high-resolution renders with ANSI 24-bit color or plain ASCII
- **Non-interactive mode** — Generate fractals from the command line for scripts and pipelines
- **Zero dependencies** — Pure Python 3.8+ standard library only
- **`--version` and `--help` flags**

## Installation

No installation needed — just download and run:

```bash
# Download directly
curl -O https://raw.githubusercontent.com/.../fractal_explorer.py

# Or clone the whole repo
git clone <repo-url>
cd daily-ideas/2026-06-13-fractal-explorer
```

## How to Run

### Interactive mode (requires a terminal)

```bash
python3 fractal_explorer.py
```

### Command-line options

```bash
# Show help
python3 fractal_explorer.py --help

# Show version
python3 fractal_explorer.py --version

# List available Julia presets
python3 fractal_explorer.py --list-presets

# List available color palettes
python3 fractal_explorer.py --list-palettes

# List coordinate bookmarks
python3 fractal_explorer.py --list-bookmarks
```

### Export to file

```bash
# Mandelbrot set, fire palette, 200x80 resolution
python3 fractal_explorer.py --export mandelbrot.txt --width 200 --height 80 --iter 150

# Burning Ship fractal with ocean palette
python3 fractal_explorer.py --fractal burningship --export ship.txt --palette ocean

# Zoom into seahorse valley
python3 fractal_explorer.py --center="-0.745,0.186" --zoom=0.005 --palette neon --export seahorse.txt

# Julia set, plain text (no ANSI colors)
python3 fractal_explorer.py --fractal julia --julia-c="-0.7,0.27015" --plain --width 100 --height 50 --export julia.txt

# Tricorn fractal
python3 fractal_explorer.py --fractal tricorn --export tricorn.txt --iter 200
```

### Print directly to terminal (no curses)

```bash
# Quick render in terminal (no TUI)
python3 fractal_explorer.py --no-curses --plain --width 80 --height 30

# With ANSI colors
python3 fractal_explorer.py --no-curses --width 80 --height 30
```

## Usage Examples

### Deep zoom into the Mandelbrot set
```bash
python3 fractal_explorer.py --center="-0.743643,0.131826" --zoom=0.0001 --iter 500
```

### Electric Julia set
```bash
python3 fractal_explorer.py --fractal julia --julia-c="-0.8,0.156" --palette electric
```

### Burning Ship fractal with neon palette
```bash
python3 fractal_explorer.py --fractal burningship --palette neon
```

### Matrix-style Mandelbrot export
```bash
python3 fractal_explorer.py --palette matrix --plain --export matrix_mandelbrot.txt --width 150 --height 60
```

## How It Works

The renderer computes escape-time iteration for each pixel position in the complex plane. For each point (cx, cy):

1. Start with z = 0 (Mandelbrot/Burning Ship/Tricorn) or z = (cx, cy) (Julia)
2. Iterate the appropriate formula until |z| > 2 or max iterations is reached
3. Map the iteration count to a character + color from the active palette

**Smooth coloring** uses the renormalization formula to get a continuous iteration count:

```
smooth_iter = n + 1 - log₂(log₂(|z|))
```

This eliminates the harsh banding between iteration levels and produces gradients that look like continuous color fields.

The terminal character aspect ratio (≈0.5) is factored in so the fractal doesn't appear stretched.

## Running Tests

```bash
python3 test_fractal_explorer.py
```

27 tests covering: fractal computation, smooth coloring, viewport defaults, text rendering, ANSI output, file export, palette/type registration, CLI flags (--help, --version, --list-presets, --list-palettes, --export), and all four fractal types.

## Project Structure

```
2026-06-13-fractal-explorer/
├── README.md                 ← You are here
├── fractal_explorer.py       ← Main application (single-file)
└── test_fractal_explorer.py  ← Test suite
```

## Requirements

- Python 3.8+
- Terminal with color support (for interactive mode)
- No external packages needed

---

*Part of the [Daily Ideas](https://github.com/…) collection — AI-generated projects, one at a time.*