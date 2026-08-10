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

### Energy Functions (5)
- **Sobel** — gradient magnitude via Sobel operator (default)
- **Prewitt** — gradient magnitude via Prewitt operator
- **Laplacian** — second derivative energy (detects rapid intensity changes)
- **Gradient** — simple central-difference gradient
- **Forward energy** — accounts for energy introduced by seam removal (Avidan et al. 2008)

### Core Operations
- **Seam removal** — reduce width/height by carving lowest-energy seams
- **Seam insertion** — enlarge images by inserting seams (with index adjustment for multi-seam consistency)
- **Object removal** — remove unwanted objects via a boolean mask
- **Mask protection** — protect important regions from being carved

### Visualization & Analysis
- **Energy map visualization** — see the energy distribution (normalized to 0–255)
- **Single seam visualization** — highlight a seam on the image in any color
- **Multiple seam visualization** — draw multiple seams in different colors
- **Seam history recording** — record all removed seams for animation/debugging
- **Quality metrics** — energy preservation ratio, seam cost tracking, statistics

### Performance
- **Vectorized seam removal** — uses NumPy boolean masking instead of Python row-loops
- **Vectorized DP** — row-by-row dynamic programming with NumPy array operations

### I/O & CLI
- **PPM (P6) and PGM (P5) I/O** — no external image libraries required
- **Full CLI** — resize, object removal, energy map export, seam visualization, mask files, statistics
- **Mask file support** — load protection/removal masks from PGM files

## Installation

```bash
pip install numpy
```

## Usage

### As a Library

```python
import numpy as np
from seamcarving import SeamCarver, EnergyType, resize
from seamcarving.core import read_ppm, write_ppm

# Load image (PPM or PGM)
img = read_ppm("input.ppm")

# Reduce width by 30 pixels (with seam recording for animation)
carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
result = carver.carve_vertical(30, record=True)
write_ppm("output.ppm", result)

# Resize to specific dimensions
result = resize(img, target_width=200, target_height=150)

# Use forward energy for better quality
carver = SeamCarver(img, energy_type=EnergyType.FORWARD)
result = carver.carve_vertical(30)

# Protect a region from carving
protect = np.zeros(img.shape[:2], dtype=bool)
protect[50:100, 60:120] = True
carver = SeamCarver(img, protect_mask=protect)
result = carver.carve_vertical(30)

# Remove an object
mask = np.zeros(img.shape[:2], dtype=bool)
mask[50:100, 60:120] = True
carver = SeamCarver(img)
result = carver.remove_object(mask)

# Visualize seams
carver = SeamCarver(img)
seam = carver._find_vertical_seam()
vis = carver.visualize_seam(seam, color=(0, 255, 0))  # green seam
write_ppm("seam.ppm", vis)

# Get statistics
carver = SeamCarver(img)
carver.carve_vertical(30, record=True)
print(carver.get_stats())
```

### Command-Line

```bash
# Reduce width to 100 pixels
python3 -m seamcarving.core input.ppm output.ppm -W 100

# Resize to 200x150 using forward energy
python3 -m seamcarving.core input.ppm output.ppm -W 200 -H 150 -e forward

# Save energy map and seam visualization
python3 -m seamcarving.core input.ppm output.ppm -W 100 \
    --energy-map energy.ppm --seam-vis seam.ppm

# Protect a region (PGM mask: non-zero = protected)
python3 -m seamcarving.core input.ppm output.ppm -W 100 --protect mask.pgm

# Remove an object (PGM mask: non-zero = remove)
python3 -m seamcarving.core input.ppm output.ppm --remove obj_mask.pgm

# Print statistics
python3 -m seamcarving.core input.ppm output.ppm -W 100 --stats

# Use Prewitt energy
python3 -m seamcarving.core input.ppm output.ppm -W 100 -e prewitt
```

### Demo

```bash
cd seam-carving
python3 demo.py
# Generates test images in output/ demonstrating all features
```

## How It Works

### Energy Computation

Each pixel is assigned an "energy" value representing its visual importance.
Low-energy pixels are in smooth/uniform regions; high-energy pixels are at
edges and boundaries. Five energy functions are available:

- **Sobel/Prewitt**: Convolution with directional kernels to approximate gradients
- **Laplacian**: Second-derivative operator that highlights regions of rapid change
- **Gradient**: Simple central-difference approximation
- **Forward energy**: Computes the cost of *new* adjacencies created by seam removal

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

## Quality Metrics

- **Seam cost**: Total energy of each removed seam (tracked in `seam_costs`)
- **Energy preservation ratio**: `1 - (sum of removed seam costs / original total energy)`
- **Statistics**: Via `get_stats()` — image size, seam count, average cost, etc.

## Project Structure

```
seam-carving/
├── seamcarving/
│   ├── __init__.py      # Package exports
│   └── core.py          # Core algorithm, energy functions, CLI
├── demo.py              # Demonstration script
├── tests/
│   └── test_seamcarving.py
├── .gitignore
└── README.md            # This file
```

## License

MIT