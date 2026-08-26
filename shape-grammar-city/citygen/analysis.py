from __future__ import annotations

from collections import Counter, deque
from typing import Any

from .generator import CityMap, Point, Tile


ASCII_NAMES = {
    Tile.EMPTY: "empty",
    Tile.ROAD: "road",
    Tile.RESIDENTIAL: "residential",
    Tile.COMMERCIAL: "commercial",
    Tile.INDUSTRIAL: "industrial",
    Tile.PARK: "park",
    Tile.WATER: "water",
    Tile.CIVIC: "civic",
}


def connected_road_components(city: CityMap) -> list[list[Point]]:
    seen: set[Point] = set()
    components: list[list[Point]] = []
    for start in city.road_points():
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        component: list[Point] = []
        while queue:
            point = queue.popleft()
            component.append(point)
            for neighbor in city.road_neighbors(point):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return components


def shortest_path(city: CityMap, start: Point, goal: Point) -> list[Point]:
    city.require_bounds(start)
    city.require_bounds(goal)
    if city.get_tile(start) != Tile.ROAD or city.get_tile(goal) != Tile.ROAD:
        raise ValueError("start and goal must both be road cells")
    if start == goal:
        return [start]
    queue = deque([start])
    parent: dict[Point, Point | None] = {start: None}
    while queue:
        point = queue.popleft()
        for neighbor in city.road_neighbors(point):
            if neighbor in parent:
                continue
            parent[neighbor] = point
            if neighbor == goal:
                path = [goal]
                cursor = point
                while cursor is not None:
                    path.append(cursor)
                    cursor = parent[cursor]
                path.reverse()
                return path
            queue.append(neighbor)
    raise ValueError("no road path exists between start and goal")


def validate_city(city: CityMap) -> list[str]:
    issues: list[str] = []
    roads = city.road_points()
    if not roads:
        issues.append("city contains no roads")
    for point in roads:
        if len(city.road_neighbors(point)) == 0:
            issues.append(f"isolated road at {point.x},{point.y}")
            break
    components = connected_road_components(city)
    if len(components) > 1:
        issues.append(f"road network is disconnected ({len(components)} components)")
    empties = city.tile_points(Tile.EMPTY)
    if empties:
        issues.append(f"city still contains {len(empties)} empty cells")
    if city.metadata.get("landmarks") and len(city.metadata["landmarks"]) == 0:
        issues.append("landmark metadata exists but is empty")
    return issues


def compute_stats(city: CityMap) -> dict[str, Any]:
    counts = Counter(tile for row in city.grid for tile in row)
    total = city.width * city.height
    road_points = city.road_points()
    degree_histogram = Counter(len(city.road_neighbors(point)) for point in road_points)
    components = connected_road_components(city)
    issues = validate_city(city)
    return {
        "width": city.width,
        "height": city.height,
        "seed": city.seed,
        "mode": city.mode,
        "counts": {ASCII_NAMES[tile]: counts.get(tile, 0) for tile in ASCII_NAMES},
        "coverage": {ASCII_NAMES[tile]: round(counts.get(tile, 0) / total, 4) for tile in ASCII_NAMES},
        "road_cells": len(road_points),
        "road_degree_histogram": dict(sorted(degree_histogram.items())),
        "road_components": len(components),
        "largest_component": max((len(component) for component in components), default=0),
        "landmark_count": len(city.metadata.get("landmarks", [])),
        "issues": issues,
    }
