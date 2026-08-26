from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .generator import CityMap, Point, Tile


@dataclass(frozen=True, slots=True)
class District:
    name: str
    tile: str
    size: int
    centroid: tuple[float, float]
    road_access: int
    waterfront: bool
    bounds: tuple[int, int, int, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "tile": self.tile,
            "size": self.size,
            "centroid": [round(self.centroid[0], 2), round(self.centroid[1], 2)],
            "road_access": self.road_access,
            "waterfront": self.waterfront,
            "bounds": list(self.bounds),
        }


DISTRICT_TITLES = {
    Tile.RESIDENTIAL: "Residential",
    Tile.COMMERCIAL: "Commercial",
    Tile.INDUSTRIAL: "Industrial",
    Tile.PARK: "Park",
    Tile.CIVIC: "Civic",
}


def _compass_label(city: CityMap, centroid_x: float, centroid_y: float) -> str:
    horizontal = "West" if centroid_x < city.width / 3 else "East" if centroid_x > city.width * 2 / 3 else "Central"
    vertical = "North" if centroid_y < city.height / 3 else "South" if centroid_y > city.height * 2 / 3 else "Mid"
    if horizontal == "Central" and vertical == "Mid":
        return "Core"
    if horizontal == "Central":
        return vertical
    if vertical == "Mid":
        return horizontal
    return f"{vertical} {horizontal}"


def analyze_districts(city: CityMap, min_size: int = 6) -> list[District]:
    """Group contiguous zoned cells into named districts."""

    if min_size < 1:
        raise ValueError("min_size must be at least 1")
    seen: set[Point] = set()
    districts: list[District] = []
    blocked = {Tile.ROAD, Tile.WATER, Tile.EMPTY}
    for y in range(city.height):
        for x in range(city.width):
            start = Point(x, y)
            tile = city.get_tile(start)
            if tile in blocked or start in seen:
                continue
            queue = deque([start])
            seen.add(start)
            cells: list[Point] = []
            while queue:
                point = queue.popleft()
                cells.append(point)
                for neighbor in city.neighbors4(point):
                    if neighbor in seen or city.get_tile(neighbor) != tile:
                        continue
                    seen.add(neighbor)
                    queue.append(neighbor)
            if len(cells) < min_size:
                continue
            centroid_x = sum(point.x for point in cells) / len(cells)
            centroid_y = sum(point.y for point in cells) / len(cells)
            road_access = sum(
                1
                for point in cells
                for neighbor in city.neighbors4(point)
                if city.get_tile(neighbor) == Tile.ROAD
            )
            waterfront = any(
                city.get_tile(neighbor) == Tile.WATER
                for point in cells
                for neighbor in city.neighbors4(point)
            )
            name = f"{DISTRICT_TITLES.get(tile, tile.value.title())} {_compass_label(city, centroid_x, centroid_y)}"
            districts.append(
                District(
                    name=name,
                    tile=tile.value,
                    size=len(cells),
                    centroid=(centroid_x, centroid_y),
                    road_access=road_access,
                    waterfront=waterfront,
                    bounds=(
                        min(point.x for point in cells),
                        min(point.y for point in cells),
                        max(point.x for point in cells),
                        max(point.y for point in cells),
                    ),
                )
            )
    districts.sort(key=lambda district: (-district.size, district.name))
    return districts
