"""
seamcarving/core.py — Backward compatibility module.

This module re-exports everything from the new modular sub-packages so
that existing code importing from ``seamcarving.core`` continues to work.

New code should import from the specific sub-modules or from
``seamcarving`` directly.
"""

from __future__ import annotations

import sys

from .carver import (
    SeamCarver,
    resize_width,
    resize_height,
    resize,
    _remove_seam_2d,
    _insert_seam_2d,
)
from .energy import (
    EnergyType,
    compute_energy,
    to_gray as _to_gray,
    sobel_energy as _sobel_energy,
    prewitt_energy as _prewitt_energy,
    laplacian_energy as _laplacian_energy,
    gradient_energy as _gradient_energy,
    forward_energy as _forward_energy,
    hofer_energy as _hofer_energy,
    entropy_energy as _entropy_energy,
)
from .exceptions import (
    SeamCarvingError,
    InvalidImageError,
    InvalidConfigError,
    InvalidMaskError,
    EnergyComputationError,
    SeamOperationError,
)
from .io import read_ppm, write_ppm, read_png, write_png, read_image, write_image
from .cli import main

# Also export the CLI main for backward compatibility
if __name__ == "__main__":
    sys.exit(main())