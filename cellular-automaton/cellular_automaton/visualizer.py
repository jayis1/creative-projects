"""Visualizers — ASCII, SVG, and PPM/PNG output for CA grids."""

from __future__ import annotations

from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

# Character ramp from sparse to dense for binary grids.
_ON = "#"
_OFF = " "


def render_ascii(grid: np.ndarray, on_char: str = _ON, off_char: str = _OFF) -> str:
    """Render a 2D grid as ASCII art."""
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    lines = []
    for row in grid:
        lines.append("".join(on_char if cell else off_char for cell in row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------

def render_svg(
    grid: np.ndarray,
    cell_size: int = 10,
    on_color: str = "#1a1a1a",
    off_color: str = "#ffffff",
    path: Optional[str] = None,
) -> str:
    """Render a 2D grid as an SVG document.

    If ``path`` is given the SVG is written to that file.  Returns the SVG string.
    """
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    h, w = grid.shape
    svg_w = w * cell_size
    svg_h = h * cell_size
    parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
        f'<rect width="100%" height="100%" fill="{off_color}"/>',
    ]
    for y in range(h):
        for x in range(w):
            if grid[y, x]:
                parts.append(
                    f'<rect x="{x * cell_size}" y="{y * cell_size}" '
                    f'width="{cell_size}" height="{cell_size}" fill="{on_color}"/>'
                )
    parts.append("</svg>")
    svg = "\n".join(parts)
    if path:
        with open(path, "w") as f:
            f.write(svg)
    return svg


# ---------------------------------------------------------------------------
# PPM (P6) rendering — portable pixmap, easily converted to PNG
# ---------------------------------------------------------------------------

def render_ppm(grid: np.ndarray, path: str, cell_size: int = 4) -> None:
    """Write the grid as a binary PPM (P6) image.

    Each cell is rendered as ``cell_size`` x ``cell_size`` pixels.
    """
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    h, w = grid.shape
    img_w = w * cell_size
    img_h = h * cell_size
    header = f"P6\n{img_w} {img_h}\n255\n".encode("ascii")
    # Build pixel array — white background, black for live cells.
    pixels = np.full((img_h, img_w, 3), 255, dtype=np.uint8)
    black = np.array([26, 26, 26], dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if grid[y, x]:
                pixels[
                    y * cell_size : (y + 1) * cell_size,
                    x * cell_size : (x + 1) * cell_size,
                ] = black
    with open(path, "wb") as f:
        f.write(header)
        f.write(pixels.tobytes())


# ---------------------------------------------------------------------------
# PNG via PPM+PIL or pure-Python fallback
# ---------------------------------------------------------------------------

def render_png(grid: np.ndarray, path: str, cell_size: int = 4) -> None:
    """Write the grid as a PNG file. Uses PIL if available, else writes PPM
    to the *same* path (with a PPM header, readable by most image tools)."""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        # PIL not available — write PPM data to the requested path so callers
        # don't need to guess a different filename.  The file is still valid
        # PPM, just with a .png extension.
        render_ppm(grid, path, cell_size)
        return
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    h, w = grid.shape
    img_w = w * cell_size
    img_h = h * cell_size
    pixels = np.full((img_h, img_w, 3), 255, dtype=np.uint8)
    black = np.array([26, 26, 26], dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if grid[y, x]:
                pixels[
                    y * cell_size : (y + 1) * cell_size,
                    x * cell_size : (x + 1) * cell_size,
                ] = black
    Image.fromarray(pixels, "RGB").save(path)


# ---------------------------------------------------------------------------
# ANSI terminal rendering (in-color)
# ---------------------------------------------------------------------------

def render_ansi(grid: np.ndarray) -> str:
    """Render a 2D grid with ANSI colour codes for terminal display."""
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    RESET = "\033[0m"
    ON = "\033[47m  \033[0m"   # white background
    OFF = "\033[40m  \033[0m"  # black background
    lines = []
    for row in grid:
        lines.append("".join(ON if cell else OFF for cell in row))
    return "\n".join(lines) + RESET


# ---------------------------------------------------------------------------
# 1D Spacetime rendering — stack rows over time
# ---------------------------------------------------------------------------


def render_spacetime_ascii(
    spacetime: np.ndarray,
    on_char: str = "#",
    off_char: str = " ",
) -> str:
    """Render a 1D spacetime array (N_timesteps × width) as ASCII.

    Row 0 is the earliest timestep; each subsequent row is one step later.
    """
    if spacetime.ndim == 1:
        spacetime = spacetime.reshape(1, -1)
    lines = []
    for row in spacetime:
        lines.append("".join(on_char if cell else off_char for cell in row))
    return "\n".join(lines)


def render_spacetime_svg(
    spacetime: np.ndarray,
    cell_size: int = 4,
    on_color: str = "#1a1a1a",
    off_color: str = "#ffffff",
    path: Optional[str] = None,
) -> str:
    """Render a 1D spacetime array as an SVG (time flows downward)."""
    if spacetime.ndim == 1:
        spacetime = spacetime.reshape(1, -1)
    n_t, w = spacetime.shape
    svg_w = w * cell_size
    svg_h = n_t * cell_size
    parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
        f'<rect width="100%" height="100%" fill="{off_color}"/>',
    ]
    for t in range(n_t):
        for x in range(w):
            if spacetime[t, x]:
                parts.append(
                    f'<rect x="{x * cell_size}" y="{t * cell_size}" '
                    f'width="{cell_size}" height="{cell_size}" fill="{on_color}"/>'
                )
    parts.append("</svg>")
    svg = "\n".join(parts)
    if path:
        with open(path, "w") as f:
            f.write(svg)
    return svg


def render_spacetime_ppm(spacetime: np.ndarray, path: str, cell_size: int = 2) -> None:
    """Write 1D spacetime as a PPM image."""
    if spacetime.ndim == 1:
        spacetime = spacetime.reshape(1, -1)
    n_t, w = spacetime.shape
    img_w = w * cell_size
    img_h = n_t * cell_size
    header = f"P6\n{img_w} {img_h}\n255\n".encode("ascii")
    pixels = np.full((img_h, img_w, 3), 255, dtype=np.uint8)
    black = np.array([26, 26, 26], dtype=np.uint8)
    for t in range(n_t):
        for x in range(w):
            if spacetime[t, x]:
                pixels[
                    t * cell_size : (t + 1) * cell_size,
                    x * cell_size : (x + 1) * cell_size,
                ] = black
    with open(path, "wb") as f:
        f.write(header)
        f.write(pixels.tobytes())


# ---------------------------------------------------------------------------
# Animation — render a sequence of frames (PPM) for 2D CAs
# ---------------------------------------------------------------------------


def render_animation_frames(
    ca,
    steps: int,
    output_dir: str,
    prefix: str = "frame",
    fmt: str = "ppm",
    cell_size: int = 4,
) -> list:
    """Step the CA ``steps`` times, writing each frame to ``output_dir``.

    Returns a list of file paths.  ``fmt`` may be ``"ppm"`` or ``"png"``.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for i in range(steps + 1):
        fname = f"{prefix}_{i:05d}.{fmt}"
        fpath = os.path.join(output_dir, fname)
        if fmt == "ppm":
            render_ppm(ca.grid, fpath, cell_size=cell_size)
        elif fmt == "png":
            render_png(ca.grid, fpath, cell_size=cell_size)
        else:
            raise ValueError(f"Unsupported animation format: {fmt}")
        paths.append(fpath)
        if i < steps:
            ca.step()
    return paths