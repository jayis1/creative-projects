# Seam Carving — Content-Aware Image Resizing v3.0

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)
![Tests: 129](https://img.shields.io/badge/tests-129%20passing-brightgreen)
![NumPy](https://img.shields.io/badge/NumPy-powered-orange)

A pure-Python + NumPy implementation of the classic **seam carving** algorithm
for content-aware image resizing, as described in:

> Avidan, D., & Shamir, A. (2007). *Seam carving for content-aware image resizing.*
> ACM Transactions on Graphics (TOG), 26(3), 10.

---

## Table of Contents

- [What is Seam Carving?](#what-is-seam-carving)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [As a Library](#as-a-library)
  - [Command-Line Interface](#command-line-interface)
  - [Configuration Files](#configuration-files)
  - [Batch Processing](#batch-processing)
  - [Animation Export](#animation-export)
- [Architecture](#architecture)
- [Energy Functions](#energy-functions)
- [How It Works](#how-it-works)
- [Quality Metrics](#quality-metrics)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is Seam Carving?

Seam carving resizes images by repeatedly removing or inserting low-energy
"seams" — connected paths of pixels that traverse the image from top-to-bottom
(vertical seams) or left-to-right (horizontal seams). Unlike naive cropping or
scaling, seam carving preserves the most visually important content (high-energy
regions like edges and objects) while discarding unimportant background.

```
Original          Carve 20 seams       Insert 20 seams
┌───────────┐     ┌─────────┐         ┌─────────────┐
│ ░░███░░░░░ │     │░░███░░░░│         │ ░░░░███░░░░░│
│ ░░███░░░░░ │ ──► │░░███░░░░│  ──►    │ ░░░░███░░░░░│
│ ░░███░░░░░ │     │░░███░░░░│         │ ░░░░███░░░░░│
└───────────┘     └─────────┘         └─────────────┘
  120×80            100×80               140×80
```

---

## Features

### Energy Functions (7)
- **Sobel** — gradient magnitude via Sobel operator (default)
- **Prewitt** — gradient magnitude via Prewitt operator
- **Laplacian** — second derivative energy (detects rapid intensity changes)
- **Gradient** — simple central-difference gradient
- **Forward energy** — accounts for energy introduced by seam removal (Avidan et al. 2008)
- **Hölder** — Hölder exponent energy (texture-based roughness estimation)
- **Entropy** — local Shannon entropy energy (window-based information content)

### Core Operations
- **Seam removal** — reduce width/height by carving lowest-energy seams
- **Seam insertion** — enlarge images by inserting seams (with index adjustment)
- **Object removal** — remove unwanted objects via a boolean mask
- **Mask protection** — protect important regions from being carved
- **Animation frame export** — export each carving step as a PNG/PPM frame

### Image I/O (no external dependencies)
- **PPM (P6)** and **PGM (P5)** — binary read/write
- **PNG** — 8-bit RGB and grayscale via stdlib `zlib` (no Pillow required!)
- **Auto-detection** — format determined by file extension or magic bytes

### Infrastructure
- **Configuration files** — JSON, YAML, and TOML support
- **Structured logging** — text or JSON format, file output
- **Batch processing** — process entire directories of images
- **CLI** — full argparse CLI with subcommands and backward compatibility
- **Exception hierarchy** — `SeamCarvingError` base with specific subtypes
- **Type hints** — full PEP 484 type annotations
- **pyproject.toml** — pip-installable with `seamcarving` console script
- **GitHub Actions CI** — automated testing on Python 3.10–3.13

### Performance
- **Vectorized seam removal** — NumPy boolean masking instead of Python loops
- **Vectorized DP** — row-by-row dynamic programming with NumPy operations
- **Energy function registry** — O(1) dispatch via dictionary lookup

---

## Installation

### From the repository

```bash
cd seam-carving
pip install -e ".[dev]"
```

### Minimal (NumPy only)

```bash
pip install numpy
```

### With YAML config support

```bash
pip install numpy pyyaml
```

### Development

```bash
pip install -e ".[dev]"  # installs numpy, pyyaml, pytest
```

---

## Quick Start

```python
import numpy as np
from seamcarving import SeamCarver, EnergyType
from seamcarving.io import read_image, write_image

# Load an image (PPM, PGM, or PNG — auto-detected)
img = read_image("photo.png")

# Reduce width by 30 pixels
carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
result = carver.carve_vertical(30)
write_image("resized.png", result)

# Or use the convenience function
from seamcarving import resize
result = resize(img, target_width=200, target_height=150)
```

---

## Usage

### As a Library

```python
import numpy as np
from seamcarving import (
    SeamCarver, EnergyType, resize, resize_width, resize_height,
    read_image, write_image, CarverConfig,
)

# Load image (auto-detects PPM/PGM/PNG)
img = read_image("input.png")

# --- Basic resizing ---
# Reduce width by 30 pixels (with seam recording for animation)
carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
result = carver.carve_vertical(30, record=True)
write_image("output.png", result)

# Resize to specific dimensions
result = resize(img, target_width=200, target_height=150)

# --- Energy function selection ---
# Use forward energy for better quality
carver = SeamCarver(img, energy_type=EnergyType.FORWARD)
result = carver.carve_vertical(30)

# Try all 7 energy functions
for etype in EnergyType:
    c = SeamCarver(img, energy_type=etype)
    result = c.carve_vertical(20)
    print(f"{etype.value}: {c.get_stats()}")

# --- Region protection ---
# Protect a region from being carved
protect = np.zeros(img.shape[:2], dtype=bool)
protect[50:100, 60:120] = True
carver = SeamCarver(img, protect_mask=protect)
result = carver.carve_vertical(30)
# The protected region is preserved!

# --- Object removal ---
mask = np.zeros(img.shape[:2], dtype=bool)
mask[50:100, 60:120] = True  # mark the object to remove
carver = SeamCarver(img)
result = carver.remove_object(mask)

# --- Animation frame export ---
carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
carver.carve_vertical(30, animation_dir="frames/", animation_format="png")
# Each frame saved as frames/frame_00000.png, frame_00001.png, ...

# --- Seam visualization ---
carver = SeamCarver(img)
seam = carver._find_vertical_seam()
vis = carver.visualize_seam(seam, color=(0, 255, 0))  # green seam
write_image("seam.png", vis)

# --- Quality metrics ---
carver = SeamCarver(img)
carver.carve_vertical(30, record=True)
stats = carver.get_stats()
print(f"Energy preserved: {stats['energy_preservation_ratio']:.4f}")
print(f"Avg seam cost: {stats['avg_seam_cost']:.2f}")
print(f"Min/Max cost: {stats['min_seam_cost']:.2f} / {stats['max_seam_cost']:.2f}")

# --- Config files ---
config = CarverConfig(energy_type="forward", target_width=200, log_level="DEBUG")
config.save("my_config.json")  # Save to JSON/YAML/TOML
loaded = CarverConfig.load("my_config.json")  # Load back
```

### Command-Line Interface

```bash
# Resize to 100px wide
python3 -m seamcarving input.png output.png -W 100

# Resize to 200x150 using forward energy
python3 -m seamcarving input.ppm output.ppm -W 200 -H 150 -e forward

# Save energy map and seam visualization
python3 -m seamcarving input.png output.png -W 100 \
    --energy-map energy.png --seam-vis seam.png

# Protect a region (PGM mask: non-zero = protected)
python3 -m seamcarving input.ppm output.ppm -W 100 --protect mask.pgm

# Remove an object (PGM mask: non-zero = remove)
python3 -m seamcarving input.ppm output.ppm --remove obj_mask.pgm

# Export animation frames
python3 -m seamcarving input.png output.png -W 50 --animate frames/

# Print statistics
python3 -m seamcarving input.ppm output.ppm -W 100 --stats

# Use Prewitt energy
python3 -m seamcarving input.ppm output.ppm -W 100 -e prewitt

# Use JSON logging with file output
python3 -m seamcarving input.png output.png -W 100 \
    --json-logs --log-file carving.log --log-level DEBUG
```

#### Subcommands

```bash
# Batch process a directory
python3 -m seamcarving batch input_dir/ output_dir/ -W 100 --format png

# Save a config template
python3 -m seamcarving save-config config.json

# Print current configuration
python3 -m seamcarving config-info
python3 -m seamcarving config-info --config my_config.yaml
```

#### Backward Compatibility

The old CLI still works:
```bash
python3 -m seamcarving.core input.ppm output.ppm -W 100
```

### Configuration Files

Create a config file (JSON, YAML, or TOML) to specify all parameters:

**JSON (`config.json`):**
```json
{
  "energy_type": "forward",
  "target_width": 200,
  "target_height": 150,
  "output_format": "png",
  "log_level": "INFO",
  "record_seams": true,
  "max_iterations": 500
}
```

**YAML (`config.yaml`):**
```yaml
energy_type: forward
target_width: 200
target_height: 150
output_format: png
log_level: INFO
record_seams: true
max_iterations: 500
```

**TOML (`config.toml`):**
```toml
energy_type = "forward"
target_width = 200
target_height = 150
output_format = "png"
log_level = "INFO"
record_seams = true
max_iterations = 500
```

Use with CLI:
```bash
python3 -m seamcarving input.png output.png --config config.json
```

Or programmatically:
```python
from seamcarving import CarverConfig
config = CarverConfig.load("config.yaml")
print(config.to_json())
```

### Batch Processing

Process all images in a directory:

```bash
python3 -m seamcarving batch input_dir/ output_dir/ -W 100 --format png
```

```python
from seamcarving.cli import process_batch
from seamcarving import EnergyType

results = process_batch(
    "input_dir/", "output_dir/",
    target_width=100,
    energy_type=EnergyType.FORWARD,
    output_format="png",
)
print(f"Processed {len(results)} images")
```

### Animation Export

Export each carving step as a PNG frame for creating time-lapse animations:

```bash
python3 -m seamcarving input.png output.png -W 50 --animate frames/
```

```python
carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
carver.carve_vertical(
    50,
    record=True,
    animation_dir="frames/",
    animation_format="png",
)
# Frame files: frames/frame_00000.png, frame_00001.png, ...
# Combine into GIF: ffmpeg -framerate 10 -i frames/frame_%05d.png output.gif
```

---

## Architecture

```
seam-carving/
├── seamcarving/
│   ├── __init__.py       # Public API exports
│   ├── __main__.py       # `python -m seamcarving` entry point
│   ├── carver.py         # SeamCarver class, seam operations, resize helpers
│   ├── energy.py         # 7 energy functions + EnergyType enum
│   ├── io.py             # PPM/PGM/PNG image I/O (PNG via stdlib zlib)
│   ├── cli.py            # argparse CLI with subcommands
│   ├── config.py         # CarverConfig dataclass, JSON/YAML/TOML loading
│   ├── exceptions.py     # Exception hierarchy
│   ├── logging.py        # Structured logging with JSON support
│   └── core.py           # Backward-compatibility shim (re-exports)
├── tests/
│   ├── test_seamcarving.py  # 79 original tests (I/O, energy, seams, bugs)
│   └── test_new_features.py # 50 new tests (PNG, config, logging, batch, etc.)
├── examples/
│   ├── 01_basic_resize.py
│   ├── 02_energy_comparison.py
│   ├── 03_object_removal.py
│   ├── 04_animation_export.py
│   └── 05_config_file.py
├── config/
│   ├── default.json      # JSON config template
│   └── default.yaml      # YAML config template
├── demo.py               # Full demonstration script
├── pyproject.toml        # Package metadata + pip install
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md             # This file
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `carver.py` | `SeamCarver` class — the core algorithm (seam finding, removal, insertion, object removal, visualization, stats) |
| `energy.py` | Energy function implementations and the `EnergyType` enum |
| `io.py` | Image I/O for PPM, PGM, and PNG formats (PNG uses stdlib `zlib`) |
| `cli.py` | Command-line interface with subcommands (resize, batch, save-config, config-info) |
| `config.py` | `CarverConfig` dataclass with JSON/YAML/TOML load/save |
| `exceptions.py` | Exception hierarchy (`SeamCarvingError` → specific subtypes) |
| `logging.py` | Logger configuration with JSON formatting support |
| `core.py` | Backward-compatibility shim that re-exports from new modules |

---

## Energy Functions

| Function | Description | Best For |
|----------|-------------|----------|
| **Sobel** (default) | Gradient magnitude via Sobel operator | General purpose, edges |
| **Prewitt** | Gradient magnitude via Prewitt operator | Similar to Sobel, slightly smoother |
| **Laplacian** | Second derivative — detects rapid intensity changes | Sharp edges, textures |
| **Gradient** | Simple central-difference gradient | Fast computation, simple images |
| **Forward** | Accounts for new adjacency cost after seam removal | Best quality results (Avidan et al. 2008) |
| **Hölder** | Hölder exponent — local roughness estimation | Textured regions |
| **Entropy** | Local Shannon entropy in a sliding window | Information-dense regions |

---

## How It Works

### Energy Computation

Each pixel is assigned an "energy" value representing its visual importance.
Low-energy pixels are in smooth/uniform regions; high-energy pixels are at
edges and boundaries. Seven energy functions are available.

### Dynamic Programming

For vertical seams, a cumulative minimum energy table `M` is computed:

```
M[i, j] = energy[i, j] + min(M[i-1, j-1], M[i-1, j], M[i-1, j+1])
```

The seam is then backtraced from the minimum value in the last row. This is
done with vectorized NumPy operations for each row.

### Seam Insertion

To enlarge an image, the optimal `k` seams are first identified on a temporary
copy (removing them one by one to find the next best), then inserted into the
original image with index adjustment to account for already-inserted seams.

### Forward Energy

The forward energy improvement accounts for the *new* adjacency cost created
when a seam is removed — pixels that were not previously neighbors become
adjacent, potentially creating a visible artifact. Forward energy minimizes
this introduced cost rather than just the existing gradient.

### Vectorized Seam Removal

Seam removal uses a boolean mask: `mask[arange(h), seam] = False`, then
`image[mask].reshape(h, w-1, c)`. This avoids slow Python row-by-row loops
and leverages NumPy's optimized C backend.

### PNG Support

PNG is implemented using the standard library `zlib` module for DEFLATE
compression. All 5 PNG filter types (None, Sub, Up, Average, Paeth) are
supported for reading, and filter type 0 (None) is used for writing. This
means **no external image library** (Pillow, imageio, etc.) is required.

---

## Quality Metrics

- **Seam cost**: Total energy of each removed seam (tracked in `seam_costs`)
- **Energy preservation ratio**: `1 - (sum of removed seam costs / original total energy)`
- **Statistics**: Via `get_stats()` — image size, seam count, avg/min/max cost, preservation ratio, energy type

```python
stats = carver.get_stats()
# {
#   "image_size": (80, 100),
#   "num_seams_carved": 20,
#   "num_seams_recorded": 20,
#   "avg_seam_cost": 0.0,
#   "total_seam_cost": 0.0,
#   "min_seam_cost": 0.0,
#   "max_seam_cost": 0.0,
#   "energy_preservation_ratio": 1.0,
#   "energy_type": "sobel"
# }
```

---

## Examples

Run the demo script:
```bash
cd seam-carving
python3 demo.py
# Generates test images in output/ demonstrating all features
```

Run individual examples:
```bash
python3 examples/01_basic_resize.py       # Basic width reduction
python3 examples/02_energy_comparison.py  # Compare all 7 energy functions
python3 examples/03_object_removal.py     # Remove an object + restore dimensions
python3 examples/04_animation_export.py   # Export animation frames
python3 examples/05_config_file.py        # Config file creation and loading
```

---

## Known Issues (Resolved)

The following bugs were identified during the bug hunt phase and have been fixed:

1. **Floating-point precision in grayscale conversion** — The original `_to_gray` used
   floating-point weights (0.299, 0.587, 0.114) which caused tiny precision errors
   (~1e-14) for uniform images, making the Sobel energy non-zero when it should be
   exactly zero. **Fix**: Rewrote `_to_gray` using integer arithmetic
   (`(R*299 + G*587 + B*114) / 1000`) to eliminate floating-point artifacts.

2. **Stale energy map after horizontal seam finding** — `_find_horizontal_seam`
   transposes the image, calls `_find_vertical_seam` (which sets `self.energy` on
   the transposed image), then transposes back — but left `self.energy` with the
   transposed dimensions `(w, h)` instead of `(h, w)`. This caused dimension
   mismatches in subsequent operations. **Fix**: Clear `self.energy = None` after
   transposing back, and recompute energy in `_remove_horizontal_seam` when needed.

3. **`remove_object` didn't track seam costs** — The `remove_object` method called
   `_remove_vertical_seam` and `_remove_horizontal_seam` but discarded the returned
   cost values, so `seam_costs` remained empty after object removal. **Fix**: Append
   the returned cost to `self.seam_costs` in the removal loop.

4. **Dead code in `_find_vertical_seam`** — A `cost` variable was computed but never
   returned or used. **Fix**: Removed the dead code.

5. **Missing validation in `resize_width` and `resize_height`** — These functions
   didn't validate that `target_width`/`target_height` was positive. **Fix**: Added
   explicit `ValueError` for non-positive target dimensions.

6. **Unclear error for truncated PPM/PGM files** — `read_ppm` passed a raw
   `ValueError` from `np.frombuffer` when the file had fewer pixels than expected.
   **Fix**: Wrapped the call in `try/except ValueError` and raise `InvalidImageError`
   with a descriptive message showing expected vs. available bytes.

7. **Seam insertion index bug** — `insert_vertical` used `seams_to_insert.index(seam)`
   to find the current seam's position, which fails on numpy arrays. **Fix**: Replaced
   with `enumerate()` for index tracking.

---

## Changelog

### v3.0 (Comprehensive Improvement)

**New Features:**
- 2 new energy functions: Hölder exponent and local entropy (total: 7)
- PNG image I/O via stdlib `zlib` (no external image libraries)
- Configuration file support (JSON, YAML, TOML)
- Structured logging with JSON formatting and file output
- Animation frame export (PNG/PPM per carving step)
- Batch directory processing
- `CarverConfig` dataclass with validation and serialization
- Enhanced statistics (min/max seam cost)
- Full exception hierarchy (6 exception types)
- CLI subcommands (resize, batch, save-config, config-info)
- `pyproject.toml` for pip installation with console script
- GitHub Actions CI (Python 3.10–3.13)
- 5 example scripts
- CONTRIBUTING.md and LICENSE

**Architecture:**
- Modularized monolithic `core.py` into 8 focused modules:
  `carver.py`, `energy.py`, `io.py`, `cli.py`, `config.py`,
  `exceptions.py`, `logging.py`, `__main__.py`
- `core.py` preserved as backward-compatibility shim
- Full type hints (PEP 484) throughout

**Tests:**
- 50 new tests (total: 129) covering PNG I/O, config, logging, animation,
  batch processing, new energy functions, exception hierarchy, backward
  compatibility

### v2.0 (Enhancement)

- Added Prewitt, Laplacian energy functions
- Vectorized seam removal
- PGM support, mask file CLI
- Quality metrics, seam history recording
- Multi-seam visualization
- Exception hierarchy
- Comprehensive input validation
- 75 tests, 7 bugs fixed

### v1.0 (Initial)

- Core seam carving implementation
- 3 energy functions (Sobel, gradient, forward)
- Seam removal/insertion, object removal
- PPM I/O, CLI
- Quality metrics

---

## Roadmap

- [ ] GPU acceleration via CuPy
- [ ] Real-time interactive resizing (GUI)
- [ ] Multi-image panorama seam carving
- [ ] Video seam carving (temporal coherence)
- [ ] Optimal seam ordering for 2D retargeting
- [ ] Automatic energy function selection via ML
- [ ] WebAssembly build for browser use
- [ ] JPEG codec support (using jpeg-codec project)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
architecture overview, and PR checklist.

---

## License

MIT — see [LICENSE](LICENSE).