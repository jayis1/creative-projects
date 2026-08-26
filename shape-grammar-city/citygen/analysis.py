from __future__ import annotations

from collections import Counter
from typing import Any

from .generator import CityMap, Tile


ASCII_NAMES = {
    Tile.EMPTY: "empty",
    Tile.ROAD: "road",
    Tile.RESIDENTIAL: "residential",
    Tile.COMMERCIAL: "commercial",
    Tile.INDUSTRIAL: "industrial",
    Tile.PARK: "park",
    Tile.WATER: "water",
}


def compute_stats(city: CityMap) -> dict[str, Any]:
    counts = Counter(tile for row in city.grid for tile in row)
    total = city.width * city.height
    road_points = city.road_points()
    degree_histogram = Counter(len(city.road_neighbors(point)) for point in road_points)
    return {
        "width": city.width,
        "height": city.height,
        "seed": city.seed,
        "mode": city.mode,
        "counts": {ASCII_NAMES[tile]: counts.get(tile, 0) for tile in ASCII_NAMES},
        "coverage": {ASCII_NAMES[tile]: round(counts.get(tile, 0) / total, 4) for tile in ASCII_NAMES},
        "road_cells": len(road_points),
        "road_degree_histogram": dict(sorted(degree_histogram.items())),
    }
