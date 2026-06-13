# LOOM — Terminal Generative Art Weaver

**Version 1.1.1**

LOOM is a terminal-based generative art tool that creates animated geometric tapestry patterns using Unicode block characters. It simulates a textile loom, layering trigonometric wave functions to produce evolving, woven-look patterns directly in your terminal with full 24-bit color support.

## Features

### Weave Patterns (7)
- **plain** — Simple over-under alternation, the most basic weave
- **twill** — Diagonal ridges like denim fabric (default)
- **satin** — Scattered highlights on smooth ground, lustrous feel
- **herringbone** — V-shaped zigzag pattern like classic suiting
- **basket** — Alternating blocks of over/under threads
- **diamond** — Diamond-shaped motifs with time-based subtle rotation
- **hexagonal** — Honeycomb-like structure using axial coordinate mapping

### Color Palettes (9)
- **sunset** — Warm oranges, yellows, and deep reds (default)
- **ocean** — Cool blues, cyans, and teals
- **forest** — Rich greens and earth tones
- **neon** — Electric pink, green, purple, and yellow
- **ember** — Fiery reds and oranges with deep shadows
- **aurora** — Northern lights pastel greens, purples, and teals
- **monochrome** — Grayscale shades from white to near-black
- **thermal** — Deep blue to yellow to white heat-map gradient
- **nightshade** — Rich purples, magentas, and lavender

### Animation & Output
- **Live animation** — Continuously evolving patterns that flow like a loom in motion
- **Snapshot mode** — Output a single frame for piping to files
- **Save-to-file mode** — Export multiple frames as a text file (colored by default, or ASCII with `--ascii`)
- **Info overlay** — Live stats bar showing palette, pattern, seed, dimensions, FPS, and time
- **Configurable speed** — `--speed` multiplier for faster or slower animation
- **Duration limit** — Run for a fixed number of seconds

### Engineering & Quality
- **Reproducible seeds** — Use `--seed` to recreate the exact same pattern
- **ASCII fallback** — `--ascii` for terminals without color support
- **`--version` flag** — Print version and exit
- **`--help` flag** — Full usage examples in the help message
- **`--list-palettes` / `--list-patterns`** — Enumerate all options
- **Graceful signal handling** — Ctrl+C and SIGTERM restore terminal state cleanly
- **Robust terminal size detection** — Falls back gracefully in non-TTY environments
- **Input validation** — Invalid width, height, fps, speed, palette, and pattern values are caught and corrected with warnings
- **BrokenPipeError handling** — Piped output doesn't crash on early close
- **Bounds-safe weave computation** — Out-of-range coordinates no longer cause IndexError

## How It Works

LOOM generates patterns by layering multiple trigonometric functions, similar to how real fabric is woven from interlocking warp and weft threads. Each pixel's value is computed from:

1. **Weave layers** — sine and cosine waves with unique frequencies, phases, and speeds
2. **Warp/weft modulation** — per-column and per-row thread parameters that mimic real fabric structure
3. **Global drift** — a slow-evolving phase offset that makes the entire tapestry shift over time

The resulting value is mapped to both a Unicode character (chosen by the weave pattern algorithm) and a color (interpolated through the selected palette), producing a richly textured, continuously evolving textile visualization.

## Installation

No dependencies beyond Python 3.6+:

```bash
# Just download and run
chmod +x loom.py
```

## How to Run

### Live Animation

```bash
# Default animation (sunset palette, twill pattern)
python3 loom.py

# Neon colors with diamond weave
python3 loom.py --palette neon --pattern diamond

# Reproducible pattern with 5 layers of complexity
python3 loom.py --seed 42 --layers 5

# ASCII-only mode (works in any terminal)
python3 loom.py --ascii

# Ocean palette, herringbone pattern, custom size
python3 loom.py --palette ocean --pattern herringbone --width 100 --height 35

# Run for exactly 30 seconds
python3 loom.py --duration 30

# Show live stats overlay (palette, pattern, FPS, time)
python3 loom.py --info

# Faster animation (4x speed multiplier)
python3 loom.py --speed 4

# Hexagonal weave with thermal palette
python3 loom.py --pattern hexagonal --palette thermal

# Nightshade palette with hexagonal weave and info overlay
python3 loom.py -p nightshade --pattern hexagonal --info
```

Press `Ctrl+C` to stop the animation (terminal state is restored cleanly).

### Single Snapshot

```bash
# Print one frame (useful for piping to files)
python3 loom.py --snapshot --ascii > art.txt

# Snapshot with colors (view in terminal)
python3 loom.py --snapshot
```

### Save Frames to File

```bash
# Save 10 colored frames to a text file (default is now colored)
python3 loom.py --save output.txt --save-frames 10

# Save 10 ASCII-only frames
python3 loom.py --save output.txt --save-frames 10 --ascii

# Save 30 frames with ANSI color codes (explicit)
python3 loom.py --save animation.txt --save-frames 30 --save-colored

# Save ASCII frames with custom interval
python3 loom.py --save frames.txt --save-frames 5 --ascii
```

### Listing Options

```bash
# Show all available palettes with color previews
python3 loom.py --list-palettes

# Show all available weave patterns
python3 loom.py --list-patterns
```

## Usage Examples

| Command | Effect |
|---|---|
| `python3 loom.py` | Default animated tapestry |
| `python3 loom.py -p aurora --pattern diamond` | Aurora-colored diamond weave |
| `python3 loom.py -p ember --pattern herringbone -l 4` | Ember herringbone, 4 layers |
| `python3 loom.py --seed 1337 --snapshot --ascii` | Reproducible single-frame ASCII art |
| `python3 loom.py --ascii --fps 10 --width 80` | 80-wide ASCII animation at 10fps |
| `python3 loom.py --pattern satin -p neon` | Neon satin weave pattern |
| `python3 loom.py --pattern hexagonal -p thermal --info` | Thermal hexagonal with stats |
| `python3 loom.py --speed 5 --fps 30` | Fast 30fps animation |
| `python3 loom.py --save art.txt --save-frames 20` | Save 20 colored frames to file |
| `python3 loom.py --save art.txt --save-frames 20 --ascii` | Save 20 ASCII frames to file |
| `python3 loom.py --version` | Print version (1.1.1) |

## What It Does

LOOM transforms your terminal into a generative art canvas that mimics real textile weaving. Each frame, it computes a complex interference pattern from layered mathematical waves, then maps those values to Unicode block characters arranged in traditional weave structures (twill diagonals, herringbone Vs, satin floats, hexagonal honeycombs, etc.) and smoothly interpolated colors from the chosen palette.

The result is a mesmerizing, continuously evolving tapestry that looks like fabric being woven in real time — but is entirely mathematical, created from the interference of sine waves and the structure of weave algorithms.

## Changelog

### v1.1.1
- **Fixed IndexError** in `compute_weave_value` when x/y exceeded width/height bounds — now uses safe modulo indexing
- **Fixed invalid palette/pattern name mismatch** — unknown names now default to 'sunset'/'twill' with a warning, keeping `palette_name` and actual palette in sync
- **Fixed `--save` default output** — now defaults to colored (ANSI) output instead of ASCII, matching the animation default; `--ascii` flag is properly respected
- **Added validation for `--speed` and `--fps`** — zero and negative values are now rejected with a warning and corrected (speed defaults to 1.0, fps to 15)
- **Added 11 new tests** covering all bug fixes (out-of-bounds coords, invalid names, fps/speed validation, save mode behavior)

### v1.1.0
- **New pattern: hexagonal** — honeycomb-like weave structure
- **New palettes: thermal, nightshade** — heat-map and purple/violet schemes
- **New `--info` flag** — live overlay showing palette, pattern, seed, dimensions, FPS, and time
- **New `--speed` flag** — control animation speed multiplier (default 2.0)
- **New `--version` flag** — print version and exit
- **New `--list-palettes` and `--list-patterns`** — enumerate available options
- **New `--save-colored` flag** — save frames with ANSI color codes
- **Improved signal handling** — graceful shutdown on Ctrl+C and SIGTERM, terminal state always restored
- **Improved terminal detection** — falls back gracefully in non-TTY environments
- **Improved input validation** — tiny width/height values are clamped with warnings
- **Added BrokenPipeError handling** — piped output no longer crashes
- **Added comprehensive docstrings** to all public methods and functions
- **Added `clamp()` utility** — replaces inline min/max for cleaner code
- **Added full test suite** (51 tests covering all modules, patterns, palettes, and edge cases)