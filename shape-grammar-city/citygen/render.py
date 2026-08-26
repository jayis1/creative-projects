from __future__ import annotations

from .generator import CityMap, Tile


ASCII_TILES = {
    Tile.EMPTY: " ",
    Tile.ROAD: "#",
    Tile.RESIDENTIAL: "r",
    Tile.COMMERCIAL: "c",
    Tile.INDUSTRIAL: "i",
    Tile.PARK: ".",
    Tile.WATER: "~",
}

SVG_COLORS = {
    Tile.EMPTY: "#f8f6f0",
    Tile.ROAD: "#2d3142",
    Tile.RESIDENTIAL: "#d9ed92",
    Tile.COMMERCIAL: "#76c893",
    Tile.INDUSTRIAL: "#f8961e",
    Tile.PARK: "#52b788",
    Tile.WATER: "#4ea8de",
}


def render_ascii(city: CityMap) -> str:
    return "\n".join("".join(ASCII_TILES[tile] for tile in row) for row in city.grid)


def render_svg(city: CityMap, cell_size: int = 18) -> str:
    width = city.width * cell_size
    height = city.height * cell_size
    rects: list[str] = []
    for y, row in enumerate(city.grid):
        for x, tile in enumerate(row):
            rects.append(
                f'<rect x="{x * cell_size}" y="{y * cell_size}" width="{cell_size}" height="{cell_size}" fill="{SVG_COLORS[tile]}" />'
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#f8f6f0" />'
        + "".join(rects)
        + "</svg>"
    )
