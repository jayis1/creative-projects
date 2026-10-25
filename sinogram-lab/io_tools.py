"""Portable PGM export helpers for reconstructed grayscale images."""
from __future__ import annotations

from pathlib import Path


def save_pgm(image: list[list[float]], destination: str | Path) -> None:
    """Write a validated square float image as an ASCII PGM (P2) file."""
    if not image or len(image) > 128 or any(len(row) != len(image) for row in image):
        raise ValueError("image must be a non-empty square matrix of size at most 128")
    if any(not isinstance(value, (int, float)) or not 0 <= value < float("inf")
           for row in image for value in row):
        raise ValueError("pixels must be finite non-negative numbers")
    peak = max((float(value) for row in image for value in row), default=0.0)
    scale = peak or 1.0
    lines = ["P2", "# Sinogram Lab reconstruction", f"{len(image)} {len(image)}", "255"]
    lines.extend(" ".join(str(round(float(value) / scale * 255)) for value in row) for row in image)
    Path(destination).write_text("\n".join(lines) + "\n", encoding="ascii")
