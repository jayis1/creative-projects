"""Output writers: PNG, PPM, SVG, ASCII, and TGA.

All writers use only the Python standard library.
"""
from __future__ import annotations

import struct
import zlib
from typing import List, Optional, Tuple

from .palettes import _clamp_byte

RGB = Tuple[int, int, int]


def write_ppm(path: str, pixels, width: int, height: int):
    """Write a binary P6 PPM file."""
    with open(path, "wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode())
        buf = bytearray()
        for r, g, b in pixels:
            buf += bytes((_clamp_byte(r), _clamp_byte(g), _clamp_byte(b)))
        f.write(buf)


def write_png(path: str, pixels, width: int, height: int,
              text_meta: Optional[dict] = None):
    """Write an 8-bit RGB PNG file using only the standard library.

    Builds IHDR, optional tEXt metadata chunks, IDAT (zlib-compressed
    scanlines with per-row filter byte 0), and IEND with correct CRC-32.
    """

    def _chunk(tag, data):
        chunk = tag + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = bytearray()
    for row in range(height):
        raw.append(0)  # filter type 0 (None)
        base = row * width
        for col in range(width):
            r, g, b = pixels[base + col]
            raw += bytes((_clamp_byte(r), _clamp_byte(g), _clamp_byte(b)))
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig)
        f.write(_chunk(b"IHDR", ihdr))
        if text_meta:
            for key, val in text_meta.items():
                text = f"{key}\0{val}".encode("latin-1", "replace")
                f.write(_chunk(b"tEXt", text))
        f.write(_chunk(b"IDAT", idat))
        f.write(_chunk(b"IEND", b""))


def write_svg(path: str, pixels, width: int, height: int):
    """Write an SVG file with one ``<rect>`` per pixel (run-length encoded)."""
    parts = [f'<?xml version="1.0" encoding="UTF-8"?>',
             f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" shape-rendering="crispEdges">']
    for row in range(height):
        base = row * width
        col = 0
        while col < width:
            r, g, b = pixels[base + col]
            run = 1
            while (col + run < width and
                   pixels[base + col + run] == (r, g, b)):
                run += 1
            parts.append(f'<rect x="{col}" y="{row}" width="{run}" '
                         f'height="1" fill="rgb({r},{g},{b})"/>')
            col += run
    parts.append('</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def write_ascii(path: str, pixels, width: int, height: int,
                chars: str = " .:-=+*#%@"):
    """Write an ASCII-art representation of the image (luminance-mapped)."""
    if not chars:
        chars = " .:-=+*#%@"
    lines = []
    n_chars = len(chars)
    for row in range(height):
        line = []
        base = row * width
        for col in range(width):
            r, g, b = pixels[base + col]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            idx = min(n_chars - 1, int(lum * n_chars))
            line.append(chars[idx])
        lines.append("".join(line))
    with open(path, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")


def write_tga(path: str, pixels, width: int, height: int):
    """Write an uncompressed 24-bit TGA (Targa) file.

    TGA is simpler than PNG (no CRC, no compression) and is useful for
    tools that expect raw pixel data. The image is written bottom-to-top
    by default (TGA's natural orientation).
    """
    header = bytearray(18)
    header[2] = 2  # uncompressed true-color
    struct.pack_into("<H", header, 12, width)
    struct.pack_into("<H", header, 14, height)
    header[16] = 24  # bits per pixel
    header[17] = 0x20  # top-origin bit set (top-to-bottom)
    buf = bytearray(header)
    for r, g, b in pixels:
        # TGA stores BGR
        buf += bytes((_clamp_byte(b), _clamp_byte(g), _clamp_byte(r)))
    with open(path, "wb") as f:
        f.write(buf)