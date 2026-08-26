from __future__ import annotations

from .generator import CityMap, Point, Tile


ASCII_TILES = {
    Tile.EMPTY: " ",
    Tile.ROAD: "#",
    Tile.RESIDENTIAL: "r",
    Tile.COMMERCIAL: "c",
    Tile.INDUSTRIAL: "i",
    Tile.PARK: ".",
    Tile.WATER: "~",
    Tile.CIVIC: "@",
}

SVG_COLORS = {
    Tile.EMPTY: "#f8f6f0",
    Tile.ROAD: "#2d3142",
    Tile.RESIDENTIAL: "#d9ed92",
    Tile.COMMERCIAL: "#76c893",
    Tile.INDUSTRIAL: "#f8961e",
    Tile.PARK: "#52b788",
    Tile.WATER: "#4ea8de",
    Tile.CIVIC: "#b5179e",
}


def render_ascii(city: CityMap, path: list[Point] | None = None) -> str:
    highlights = set(path or [])
    rows: list[str] = []
    for y, row in enumerate(city.grid):
        chars: list[str] = []
        for x, tile in enumerate(row):
            point = Point(x, y)
            if point in highlights and tile == Tile.ROAD:
                chars.append("*")
            else:
                chars.append(ASCII_TILES[tile])
        rows.append("".join(chars))
    return "\n".join(rows)


def render_svg(city: CityMap, cell_size: int = 18, path: list[Point] | None = None) -> str:
    width = city.width * cell_size
    height = city.height * cell_size
    rects: list[str] = []
    highlights = {point for point in (path or [])}
    for y, row in enumerate(city.grid):
        for x, tile in enumerate(row):
            fill = SVG_COLORS[tile]
            stroke = "#f8f6f0" if tile == Tile.ROAD else "#ffffff33"
            rects.append(
                f'<rect x="{x * cell_size}" y="{y * cell_size}" width="{cell_size}" height="{cell_size}" fill="{fill}" stroke="{stroke}" stroke-width="1" />'
            )
            point = Point(x, y)
            if point in highlights:
                inset = max(2, cell_size // 4)
                rects.append(
                    f'<rect x="{x * cell_size + inset}" y="{y * cell_size + inset}" width="{cell_size - 2 * inset}" height="{cell_size - 2 * inset}" fill="#ef476f" opacity="0.85" />'
                )
    legend_entries = [
        ("Road", SVG_COLORS[Tile.ROAD]),
        ("Residential", SVG_COLORS[Tile.RESIDENTIAL]),
        ("Commercial", SVG_COLORS[Tile.COMMERCIAL]),
        ("Industrial", SVG_COLORS[Tile.INDUSTRIAL]),
        ("Park", SVG_COLORS[Tile.PARK]),
        ("Water", SVG_COLORS[Tile.WATER]),
        ("Civic", SVG_COLORS[Tile.CIVIC]),
    ]
    legend = []
    for index, (label, color) in enumerate(legend_entries):
        y = 12 + index * 18
        legend.append(f'<rect x="12" y="{y}" width="12" height="12" fill="{color}" />')
        legend.append(f'<text x="30" y="{y + 10}" font-size="12" font-family="monospace">{label}</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#f8f6f0" />'
        + "".join(rects)
        + "".join(legend)
        + "</svg>"
    )
