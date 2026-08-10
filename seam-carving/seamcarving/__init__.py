#!/usr/bin/env python3
"""
seamcarving/__init__.py — Content-aware image resizing via seam carving.

A pure-Python + NumPy implementation of the classic Avidan & Shamir (2007)
seam carving algorithm for content-aware image resizing.
"""

from .core import (
    SeamCarver,
    EnergyType,
    SeamCarvingError,
    InvalidImageError,
    resize_width,
    resize_height,
    resize,
    read_ppm,
    write_ppm,
)

__version__ = "2.0.0"
__all__ = [
    "SeamCarver",
    "EnergyType",
    "SeamCarvingError",
    "InvalidImageError",
    "resize_width",
    "resize_height",
    "resize",
    "read_ppm",
    "write_ppm",
]