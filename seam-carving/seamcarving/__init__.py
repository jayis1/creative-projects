"""
seamcarving — Content-aware image resizing via seam carving.

A pure-Python + NumPy implementation of the classic Avidan & Shamir (2007)
seam carving algorithm for content-aware image resizing.

Modules
-------
- :mod:`seamcarving.carver`  — Core ``SeamCarver`` class and convenience functions
- :mod:`seamcarving.energy`  — Energy functions (Sobel, Prewitt, Laplacian, etc.)
- :mod:`seamcarving.io`      — PPM/PGM/PNG image I/O
- :mod:`seamcarving.config`  — Configuration file support (JSON/YAML/TOML)
- :mod:`seamcarving.cli`     — Command-line interface
- :mod:`seamcarving.exceptions` — Exception hierarchy
"""

from .carver import (
    SeamCarver,
    resize_width,
    resize_height,
    resize,
)
from .energy import EnergyType
from .exceptions import (
    SeamCarvingError,
    InvalidImageError,
    InvalidConfigError,
    InvalidMaskError,
    EnergyComputationError,
    SeamOperationError,
)
from .io import (
    read_ppm,
    write_ppm,
    read_png,
    write_png,
    read_image,
    write_image,
)
from .config import CarverConfig

__version__ = "3.0.0"
__author__ = "Creative Coder Pipeline"

__all__ = [
    "SeamCarver",
    "EnergyType",
    "SeamCarvingError",
    "InvalidImageError",
    "InvalidConfigError",
    "InvalidMaskError",
    "EnergyComputationError",
    "SeamOperationError",
    "resize_width",
    "resize_height",
    "resize",
    "read_ppm",
    "write_ppm",
    "read_png",
    "write_png",
    "read_image",
    "write_image",
    "CarverConfig",
]