"""Rendering helpers for Particle Life snapshots."""

from __future__ import annotations

from math import floor
from typing import Iterable

from .models import Particle, SpeciesStyle


def render_ascii(
    particles: Iterable[Particle],
    styles: list[SpeciesStyle],
    width: float,
    height: float,
    columns: int = 60,
    rows: int = 24,
) -> str:
    """Render particles to an ASCII grid."""

    columns = max(4, columns)
    rows = max(4, rows)
    grid = [["." for _ in range(columns)] for _ in range(rows)]
    symbols = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for particle in particles:
        col = min(columns - 1, max(0, floor((particle.x / width) * columns)))
        row = min(rows - 1, max(0, floor((particle.y / height) * rows)))
        grid[row][col] = symbols[particle.species % len(symbols)]
    legend = " ".join(
        f"{symbols[index % len(symbols)]}={style.name}"
        for index, style in enumerate(styles)
    )
    return "\n".join("".join(line) for line in grid) + "\n" + legend + "\n"


def render_svg(
    particles: Iterable[Particle],
    styles: list[SpeciesStyle],
    width: float,
    height: float,
    radius: float = 2.0,
    background: str = "#0b1020",
) -> str:
    """Render particles to a standalone SVG document."""

    circles: list[str] = []
    for particle in particles:
        style = styles[particle.species]
        circles.append(
            f'<circle cx="{particle.x:.3f}" cy="{particle.y:.3f}" r="{radius:.3f}" fill="{style.color}" />'
        )
    body = "\n  ".join(circles)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.3f} {height:.3f}" '
        f'width="{width:.3f}" height="{height:.3f}">\n'
        f'  <rect width="100%" height="100%" fill="{background}" />\n'
        f'  {body}\n'
        f'</svg>\n'
    )


def render_ppm(
    particles: Iterable[Particle],
    styles: list[SpeciesStyle],
    width: float,
    height: float,
    pixel_width: int = 320,
    pixel_height: int = 240,
    point_radius: int = 2,
    background: tuple[int, int, int] = (11, 16, 32),
) -> str:
    """Render particles to a plain-text PPM image."""

    pixel_width = max(8, pixel_width)
    pixel_height = max(8, pixel_height)
    pixels = [[list(background) for _ in range(pixel_width)] for _ in range(pixel_height)]
    palette = [_hex_to_rgb(style.color) for style in styles]
    for particle in particles:
        cx = min(pixel_width - 1, max(0, round((particle.x / width) * (pixel_width - 1))))
        cy = min(pixel_height - 1, max(0, round((particle.y / height) * (pixel_height - 1))))
        rgb = palette[particle.species]
        for dy in range(-point_radius, point_radius + 1):
            for dx in range(-point_radius, point_radius + 1):
                x = cx + dx
                y = cy + dy
                if 0 <= x < pixel_width and 0 <= y < pixel_height and dx * dx + dy * dy <= point_radius * point_radius:
                    pixels[y][x] = [rgb[0], rgb[1], rgb[2]]
    lines = ["P3", f"{pixel_width} {pixel_height}", "255"]
    for row in pixels:
        lines.append(" ".join(" ".join(map(str, rgb)) for rgb in row))
    return "\n".join(lines) + "\n"


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"expected #RRGGBB color, got {color!r}")
    return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))
