"""Post-processing image filters.

All filters operate on a flat list of RGB tuples and return a new list
of the same length.  They are pure-Python and work on any image size.
"""
from __future__ import annotations

import math
from typing import List, Tuple

from .palettes import _clamp_byte

RGB = Tuple[int, int, int]


def _get(pixels: List[RGB], width: int, height: int, x: int, y: int) -> RGB:
    """Safe pixel access with clamping at edges."""
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    return pixels[y * width + x]


def _convolve(pixels: List[RGB], width: int, height: int,
              kernel: List[float], ksize: int) -> List[RGB]:
    """Apply a convolution kernel (ksize×ksize, odd)."""
    half = ksize // 2
    out: List[RGB] = [(0, 0, 0)] * (width * height)
    for y in range(height):
        for x in range(width):
            r = g = b = 0.0
            ki = 0
            for ky in range(-half, half + 1):
                for kx in range(-half, half + 1):
                    pr, pg, pb = _get(pixels, width, height, x + kx, y + ky)
                    w = kernel[ki]
                    r += pr * w
                    g += pg * w
                    b += pb * w
                    ki += 1
            out[y * width + x] = (_clamp_byte(int(r)), _clamp_byte(int(g)),
                                   _clamp_byte(int(b)))
    return out


def box_blur(pixels: List[RGB], width: int, height: int,
             radius: int = 1) -> List[RGB]:
    """Box blur (average filter) with the given radius."""
    ksize = 2 * radius + 1
    kernel = [1.0 / (ksize * ksize)] * (ksize * ksize)
    return _convolve(pixels, width, height, kernel, ksize)


def gaussian_blur(pixels: List[RGB], width: int, height: int,
                  radius: int = 1) -> List[RGB]:
    """Gaussian blur with the given radius."""
    ksize = 2 * radius + 1
    sigma = radius / 2.0 if radius > 0 else 0.5
    kernel = []
    half = ksize // 2
    for ky in range(-half, half + 1):
        for kx in range(-half, half + 1):
            d2 = kx * kx + ky * ky
            kernel.append(math.exp(-d2 / (2 * sigma * sigma)))
    total = sum(kernel)
    kernel = [k / total for k in kernel]
    return _convolve(pixels, width, height, kernel, ksize)


def edge_detect(pixels: List[RGB], width: int, height: int) -> List[RGB]:
    """Sobel edge detection. Returns a grayscale-ish edge map."""
    # Sobel X and Y kernels
    sx = [-1, 0, 1, -2, 0, 2, -1, 0, 1]
    sy = [-1, -2, -1, 0, 0, 0, 1, 2, 1]
    out: List[RGB] = [(0, 0, 0)] * (width * height)
    for y in range(height):
        for x in range(width):
            gx_r = gx_g = gx_b = 0.0
            gy_r = gy_g = gy_b = 0.0
            ki = 0
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    pr, pg, pb = _get(pixels, width, height, x + kx, y + ky)
                    gx_r += pr * sx[ki]
                    gx_g += pg * sx[ki]
                    gx_b += pb * sx[ki]
                    gy_r += pr * sy[ki]
                    gy_g += pg * sy[ki]
                    gy_b += pb * sy[ki]
                    ki += 1
            mag = int(min(255, math.sqrt(gx_r * gx_r + gy_r * gy_r) +
                          math.sqrt(gx_g * gx_g + gy_g * gy_g) +
                          math.sqrt(gx_b * gx_b + gy_b * gy_b)) / 3)
            out[y * width + x] = (mag, mag, mag)
    return out


def emboss(pixels: List[RGB], width: int, height: int) -> List[RGB]:
    """Emboss filter — gives a 3D raised look."""
    kernel = [-2, -1, 0, -1, 1, 1, 0, 1, 2]
    out: List[RGB] = [(0, 0, 0)] * (width * height)
    for y in range(height):
        for x in range(width):
            r = g = b = 0.0
            ki = 0
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    pr, pg, pb = _get(pixels, width, height, x + kx, y + ky)
                    r += pr * kernel[ki]
                    g += pg * kernel[ki]
                    b += pb * kernel[ki]
                    ki += 1
            val_r = _clamp_byte(int(r + 128))
            val_g = _clamp_byte(int(g + 128))
            val_b = _clamp_byte(int(b + 128))
            out[y * width + x] = (val_r, val_g, val_b)
    return out


def grayscale_filter(pixels: List[RGB], width: int,
                      height: int) -> List[RGB]:
    """Convert to grayscale using luminance weights."""
    out: List[RGB] = []
    for r, g, b in pixels:
        lum = int(0.299 * r + 0.587 * g + 0.114 * b)
        out.append((lum, lum, lum))
    return out


def invert(pixels: List[RGB], width: int, height: int) -> List[RGB]:
    """Invert colours."""
    return [(255 - r, 255 - g, 255 - b) for r, g, b in pixels]


def brightness(pixels: List[RGB], width: int, height: int,
               delta: int = 30) -> List[RGB]:
    """Adjust brightness by ``delta`` (can be negative)."""
    return [(_clamp_byte(r + delta), _clamp_byte(g + delta),
             _clamp_byte(b + delta))
            for r, g, b in pixels]


def contrast(pixels: List[RGB], width: int, height: int,
             factor: float = 1.5) -> List[RGB]:
    """Adjust contrast by ``factor`` (1.0 = no change)."""
    out = []
    for r, g, b in pixels:
        out.append((_clamp_byte(int((r - 128) * factor + 128)),
                     _clamp_byte(int((g - 128) * factor + 128)),
                     _clamp_byte(int((b - 128) * factor + 128))))
    return out


# Dispatch table for the CLI
FILTERS = {
    "blur": lambda px, w, h: box_blur(px, w, h, 1),
    "gaussian": lambda px, w, h: gaussian_blur(px, w, h, 1),
    "edge": edge_detect,
    "emboss": emboss,
    "grayscale": grayscale_filter,
    "invert": invert,
    "brightness": lambda px, w, h: brightness(px, w, h, 30),
    "contrast": lambda px, w, h: contrast(px, w, h, 1.5),
}


def apply_filter(pixels: List[RGB], width: int, height: int,
                 name: str) -> List[RGB]:
    """Apply a named filter to the pixel array."""
    if name not in FILTERS:
        raise ValueError(f"Unknown filter {name!r}; options: {list(FILTERS)}")
    return FILTERS[name](pixels, width, height)