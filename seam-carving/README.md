# Seam Carving — Content-Aware Image Resizing

A pure-Python + NumPy implementation of the classic **seam carving** algorithm
for content-aware image resizing, as described in:

> Avidan, D., & Shamir, A. (2007). *Seam carving for content-aware image resizing.*
> ACM Transactions on Graphics (TOG), 26(3), 10.

## What is Seam Carving?

Seam carving resizes images by repeatedly removing or inserting low-energy
"seams" — connected paths of pixels that traverse the image from top-to-bottom
(vertical seams) or left-to-right (horizontal seams). Unlike naive cropping or
scaling, seam carving preserves the most visually important content (high-energy
regions like edges and objects) while discarding unimportant background.

## Features

- **Three energy functions:**
  - **Sobel** — gradient magnitude via Sobel operator (default)
  - **Gradient** — simple central-difference gradient
  - **Forward energy** — accounts for energy introduced by seam removal (Avidan et al. 2008)
- **Seam removal** — reduce width/height by carving lowest-energy seams
- **Seam insertion** — enlarge images by inserting seams (with index adjustment for multi-seam consistency)
- **Object removal** — remove unwanted objects via a boolean mask
- **Mask protection** — protect important regions from being carved
- **Energy map visualization** — see the energy distribution
- **Seam visualization** — highlight seams on the image
- **PPM I/O** — no external image libraries required (uses P6 PPM format)
- **CLI interface** — command-line tool for batch processing

## Installation

```bash
# No install needed — just ensure numpy is available
pip install numpy
```

## Usage

### As a Library

```python
import numpy as np
from seamcarving import SeamCarver, EnergyType, resize
from seamcarving.core import read_ppm, write_ppm

# Load image
img = read_ppm("input.ppm")

# Reduce width by 30 pixels
carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
result = carver.carve_vertical(30)
write_ppm("output.ppm", result)

# Resize to specific dimensions
result = resize(img, target_width=200, target_height=150)

# Remove an object
mask = np.zeros(img.shape[:2], dtype=bool)
mask[50:100, 60:120] = True  # mark object for removal
carver = SeamCarver(img)
result = carver.remove_object(mask)

# Use forward energy for better results
carver = SeamCarver(img, energy_type=EnergyType.FORWARD)
result = carver.carve_vertical(30)
```

### Command-Line

```bash
# Reduce width to 100 pixels
python3 -m seamcarving.core input.ppm output.ppm -W 100

# Resize to 200x150 using forward energy
python3 -m seamcarving.core input.ppm output.ppm -W 200 -H 150 -e forward

# Also save energy map
python3 -m seamcarving.core input.ppm output.ppm -W 100 --energy-map energy.ppm
```

### Demo

```bash
cd seam-carving
python3 demo.py
# Generates test images in output/
```

## How It Works

### Energy Computation

Each pixel is assigned an "energy" value representing its visual importance.
Low-energy pixels are in smooth/uniform regions; high-energy pixels are at
edges and boundaries.

### Dynamic Programming

For vertical seams, a cumulative minimum energy table `M` is computed:

```
M[i, j] = energy[i, j] + min(M[i-1, j-1], M[i-1, j], M[i-1, j+1])
```

The seam is then backtraced from the minimum value in the last row.

### Seam Insertion

To enlarge an image, the optimal `k` seams are first identified on a temporary
copy (removing them one by one to find the next best), then inserted into the
original image with index adjustment to account for already-inserted seams.

### Forward Energy

The forward energy improvement accounts for the *new* adjacency cost created
when a seam is removed — pixels that were not previously neighbors become
adjacent, potentially creating a visible artifact. Forward energy minimizes
this introduced cost rather than just the existing gradient.

## Project Structure

```
seam-carving/
├── seamcarving/
│   ├── __init__.py      # Package exports
│   └── core.py          # Core algorithm, energy functions, CLI
├── demo.py              # Demonstration script
├── README.md            # This file
└── tests/
    └── test_seamcarving.py
```

## License

MIT