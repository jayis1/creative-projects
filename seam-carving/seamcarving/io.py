"""
seamcarving/io.py — Image I/O for PPM (P6), PGM (P5), and PNG formats.

Pure-Python/NumPy implementations with no external image libraries.
PNG support uses the standard library ``zlib`` module for DEFLATE
compression, so the package works with zero external dependencies beyond
NumPy.

Supported formats
------------------
- **PPM P6**  — binary RGB, 3 channels
- **PGM P5**  — binary grayscale, 1 channel
- **PNG**     — 8-bit RGB or grayscale via stdlib zlib
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Union

import numpy as np

from .exceptions import InvalidImageError

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# PPM / PGM
# ---------------------------------------------------------------------------

def read_ppm(path: PathLike) -> np.ndarray:
    """Read a binary PPM (P6) or PGM (P5) file.

    Parameters
    ----------
    path : str or Path
        Path to the file.

    Returns
    -------
    np.ndarray
        ``(H, W, 3)`` ``uint8`` array for PPM, ``(H, W, 1)`` for PGM.

    Raises
    ------
    InvalidImageError
        If the file is not a valid PPM/PGM, is truncated, or has an
        unsupported maxval.
    """
    path = Path(path)
    with open(path, "rb") as f:
        data = f.read()

    if data[:2] == b"P6":
        channels = 3
    elif data[:2] == b"P5":
        channels = 1
    else:
        raise InvalidImageError(
            f"Not a binary PPM (P6) or PGM (P5) file", str(path)
        )

    idx = 2
    vals: list[int] = []
    while len(vals) < 3:
        # Skip whitespace
        while idx < len(data) and data[idx:idx + 1].isspace():
            idx += 1
        # Skip comments
        if idx < len(data) and data[idx:idx + 1] == b"#":
            while idx < len(data) and data[idx:idx + 1] != b"\n":
                idx += 1
            continue
        start = idx
        while idx < len(data) and not data[idx:idx + 1].isspace():
            idx += 1
        try:
            vals.append(int(data[start:idx]))
        except ValueError:
            raise InvalidImageError(
                f"Malformed header in {path}", str(path)
            )
    idx += 1  # single whitespace after maxval
    w, h, maxval = vals
    if maxval != 255:
        raise InvalidImageError(
            f"Unsupported maxval {maxval}, expected 255", str(path)
        )
    expected = h * w * channels
    try:
        pixels = np.frombuffer(data[idx:], dtype=np.uint8, count=expected)
    except ValueError as e:
        raise InvalidImageError(
            f"Truncated file: expected {expected} bytes of pixel data, "
            f"but only {len(data) - idx} available",
            str(path),
        ) from e
    return pixels.reshape(h, w, channels).copy()


def write_ppm(path: PathLike, img: np.ndarray) -> None:
    """Write an ``(H, W, C)`` ``uint8`` array as a binary PPM (P6) or PGM (P5) file.

    ``C=1`` produces PGM; ``C=3`` produces PPM.
    """
    path = Path(path)
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    h, w, c = img.shape
    if c == 1:
        header = f"P5\n{w} {h}\n255\n".encode()
        body = img[:, :, 0].tobytes()
    elif c == 3:
        header = f"P6\n{w} {h}\n255\n".encode()
        body = img.tobytes()
    else:
        raise InvalidImageError(f"Cannot write image with {c} channels to PPM/PGM")
    with open(path, "wb") as f:
        f.write(header)
        f.write(body)


# ---------------------------------------------------------------------------
# PNG (via stdlib zlib — no external dependencies)
# ---------------------------------------------------------------------------

def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk: length + type + data + CRC32."""
    chunk = chunk_type + data
    crc = zlib.crc32(chunk) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)


def write_png(path: PathLike, img: np.ndarray) -> None:
    """Write an ``(H, W, C)`` ``uint8`` array as an 8-bit PNG file.

    Uses stdlib ``zlib`` for DEFLATE compression — no Pillow required.
    Supports RGB (C=3) and grayscale (C=1 or 2D).
    """
    path = Path(path)
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    h, w, c = img.shape

    if c == 1:
        color_type = 0  # grayscale
        bytes_per_pixel = 1
    elif c == 3:
        color_type = 2  # RGB
        bytes_per_pixel = 3
    else:
        raise InvalidImageError(f"PNG supports 1 or 3 channels, got {c}")

    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk: width, height, bit_depth=8, color_type, compression=0,
    # filter=0, interlace=0
    ihdr_data = struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)

    # IDAT chunk: filter type 0 (None) per scanline + zlib compress
    raw = img.reshape(h, w * bytes_per_pixel)
    scanlines = b""
    for row in raw:
        scanlines += b"\x00" + row.tobytes()
    compressed = zlib.compress(scanlines, level=6)

    # IEND chunk
    chunks = (
        _png_chunk(b"IHDR", ihdr_data)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )

    with open(path, "wb") as f:
        f.write(sig)
        f.write(chunks)


def read_png(path: PathLike) -> np.ndarray:
    """Read an 8-bit PNG file (grayscale or RGB).

    Returns ``(H, W, C)`` ``uint8`` array.
    Supports filter types 0–4 (None, Sub, Up, Average, Paeth).
    """
    path = Path(path)
    with open(path, "rb") as f:
        data = f.read()

    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise InvalidImageError("Not a valid PNG file", str(path))

    idx = 8
    width = height = bit_depth = color_type = 0
    idat_data = b""

    while idx < len(data):
        chunk_len = struct.unpack(">I", data[idx:idx + 4])[0]
        chunk_type = data[idx + 4:idx + 8]
        chunk_data = data[idx + 8:idx + 8 + chunk_len]
        idx += 12 + chunk_len  # skip data + CRC

        if chunk_type == b"IHDR":
            (width, height, bit_depth, color_type,
             _comp, _filt, _interlace) = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat_data += chunk_data
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8:
        raise InvalidImageError(
            f"Only 8-bit PNG supported, got bit depth {bit_depth}", str(path)
        )

    # Determine channels
    if color_type == 0:
        channels = 1
    elif color_type == 2:
        channels = 3
    elif color_type == 6:
        channels = 4  # RGBA — drop alpha
    else:
        raise InvalidImageError(
            f"Unsupported PNG color type {color_type}", str(path)
        )

    # Decompress
    raw = zlib.decompress(idat_data)
    bytes_per_pixel = channels if color_type != 6 else 4
    stride = width * bytes_per_pixel

    # Unfilter scanlines
    prev_row = bytearray(stride)
    result = np.zeros((height, width, channels), dtype=np.uint8)
    pos = 0

    for y in range(height):
        filter_type = raw[pos]
        pos += 1
        scanline = bytearray(raw[pos:pos + stride])
        pos += stride

        if filter_type == 0:  # None
            pass
        elif filter_type == 1:  # Sub
            for i in range(bytes_per_pixel, stride):
                scanline[i] = (scanline[i] + scanline[i - bytes_per_pixel]) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                scanline[i] = (scanline[i] + prev_row[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = scanline[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                scanline[i] = (scanline[i] + (left + prev_row[i]) // 2) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                left = scanline[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up = prev_row[i]
                up_left = (
                    prev_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                )
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                if pa <= pb and pa <= pc:
                    pred = left
                elif pb <= pc:
                    pred = up
                else:
                    pred = up_left
                scanline[i] = (scanline[i] + pred) & 0xFF
        else:
            raise InvalidImageError(
                f"Unknown PNG filter type {filter_type}", str(path)
            )

        prev_row = scanline

        if color_type == 6:  # RGBA → drop alpha
            row_arr = np.frombuffer(bytes(scanline), dtype=np.uint8)
            result[y] = row_arr.reshape(width, 4)[:, :3]
        else:
            row_arr = np.frombuffer(bytes(scanline), dtype=np.uint8)
            result[y] = row_arr.reshape(width, channels)

    return result


# ---------------------------------------------------------------------------
# Unified read/write dispatch
# ---------------------------------------------------------------------------

def read_image(path: PathLike) -> np.ndarray:
    """Read an image, auto-detecting format from the file extension.

    Supported: ``.ppm`` (P6), ``.pgm`` (P5), ``.png``.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".ppm", ".pgm"):
        return read_ppm(path)
    elif suffix == ".png":
        return read_png(path)
    else:
        # Try by magic bytes
        with open(path, "rb") as f:
            magic = f.read(8)
        if magic[:2] in (b"P5", b"P6"):
            return read_ppm(path)
        elif magic[:8] == b"\x89PNG\r\n\x1a\n":
            return read_png(path)
        raise InvalidImageError(
            f"Unsupported image format: {suffix or 'unknown'}", str(path)
        )


def write_image(path: PathLike, img: np.ndarray) -> None:
    """Write an image, selecting format from the file extension.

    Supported: ``.ppm``, ``.pgm``, ``.png``.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".ppm", ".pgm"):
        write_ppm(path, img)
    elif suffix == ".png":
        write_png(path, img)
    else:
        # Default to PPM
        write_ppm(path, img)