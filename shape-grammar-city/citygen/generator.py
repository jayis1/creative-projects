from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class Tile(str, Enum):
    EMPTY = "empty"
    ROAD = "road"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    PARK = "park"
    WATER = "water"
    CIVIC = "civic"


@dataclass(frozen=True, order=True)
class Point:
    x: int
    y: int

    @classmethod
    def parse(cls, payload: str) -> "Point":
        """Parse a point from 'x,y'."""
        parts = [part.strip() for part in payload.split(",")]
        if len(parts) != 2:
            raise ValueError(f"invalid point {payload!r}; expected 'x,y'")
        try:
            return cls(int(parts[0]), int(parts[1]))
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"invalid point {payload!r}; coordinates must be integers") from exc


@dataclass
class CityMap:
    width: int
    height: int
    grid: list[list[Tile]] = field(init=False)
    seed: int | None = None
    mode: str = "grid"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width < 9 or self.height < 9:
            raise ValueError("width and height must both be at least 9")
        self.grid = [[Tile.EMPTY for _ in range(self.width)] for _ in range(self.height)]

    def in_bounds(self, point: Point) -> bool:
        return 0 <= point.x < self.width and 0 <= point.y < self.height

    def require_bounds(self, point: Point) -> None:
        if not self.in_bounds(point):
            raise ValueError(f"point {point} is outside the city bounds {self.width}x{self.height}")

    def set_tile(self, point: Point, tile: Tile) -> None:
        if self.in_bounds(point):
            self.grid[point.y][point.x] = tile

    def get_tile(self, point: Point) -> Tile:
        self.require_bounds(point)
        return self.grid[point.y][point.x]

    def neighbors4(self, point: Point) -> list[Point]:
        candidates = [
            Point(point.x + 1, point.y),
            Point(point.x - 1, point.y),
            Point(point.x, point.y + 1),
            Point(point.x, point.y - 1),
        ]
        return [candidate for candidate in candidates if self.in_bounds(candidate)]

    def road_neighbors(self, point: Point) -> list[Point]:
        return [neighbor for neighbor in self.neighbors4(point) if self.get_tile(neighbor) == Tile.ROAD]

    def tile_points(self, tile: Tile) -> list[Point]:
        points: list[Point] = []
        for y, row in enumerate(self.grid):
            for x, value in enumerate(row):
                if value == tile:
                    points.append(Point(x, y))
        return points

    def road_points(self) -> list[Point]:
        return self.tile_points(Tile.ROAD)

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "mode": self.mode,
            "metadata": self.metadata,
            "grid": [[tile.value for tile in row] for row in self.grid],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CityMap":
        city = cls(
            payload["width"],
            payload["height"],
            seed=payload.get("seed"),
            mode=payload.get("mode", "grid"),
        )
        rows = payload["grid"]
        if len(rows) != city.height:
            raise ValueError("grid height does not match declared city height")
        if any(len(row) != city.width for row in rows):
            raise ValueError("grid width does not match declared city width")
        city.metadata = payload.get("metadata", {})
        city.grid = [[Tile(tile) for tile in row] for row in rows]
        return city


DIRECTIONS = [Point(1, 0), Point(-1, 0), Point(0, 1), Point(0, -1)]
VALID_MODES = {"grid", "organic", "radial"}
DEFAULT_ZONE_WEIGHTS = {
    Tile.RESIDENTIAL: 0.48,
    Tile.COMMERCIAL: 0.2,
    Tile.INDUSTRIAL: 0.14,
    Tile.PARK: 0.12,
    Tile.WATER: 0.03,
    Tile.CIVIC: 0.03,
}


def _normalise_zone_weights(zone_weights: dict[str, float] | None) -> dict[Tile, float]:
    if zone_weights is None:
        return dict(DEFAULT_ZONE_WEIGHTS)
    parsed: dict[Tile, float] = {}
    for name, value in zone_weights.items():
        tile = Tile(name)
        if tile in {Tile.EMPTY, Tile.ROAD}:
            raise ValueError(f"zone weight {name!r} is not a land-use tile")
        if not math.isfinite(value):
            raise ValueError(f"zone weight {name!r} must be finite")
        if value < 0:
            raise ValueError(f"zone weight {name!r} cannot be negative")
        parsed[tile] = float(value)
    merged = dict(DEFAULT_ZONE_WEIGHTS)
    merged.update(parsed)
    total = sum(merged.values())
    if total <= 0:
        raise ValueError("zone weights must sum to a positive value")
    return {tile: value / total for tile, value in merged.items()}


def _carve_segment(city: CityMap, start: Point, direction: Point, length: int) -> Point:
    current = start
    city.set_tile(current, Tile.ROAD)
    for _ in range(length):
        nxt = Point(current.x + direction.x, current.y + direction.y)
        if not city.in_bounds(nxt):
            break
        city.set_tile(nxt, Tile.ROAD)
        current = nxt
    return current


def _grow_grid(city: CityMap, rng: random.Random, iterations: int) -> None:
    center = Point(city.width // 2, city.height // 2)
    frontier = [center]
    city.set_tile(center, Tile.ROAD)
    for _ in range(iterations):
        anchor = rng.choice(frontier)
        direction = rng.choice(DIRECTIONS)
        length = rng.randint(2, max(2, min(city.width, city.height) // 5))
        endpoint = _carve_segment(city, anchor, direction, length)
        if endpoint not in frontier:
            frontier.append(endpoint)
        if len(frontier) > max(4, iterations // 2):
            frontier.pop(0)


def _grow_organic(city: CityMap, rng: random.Random, iterations: int) -> None:
    walkers = [Point(city.width // 2, city.height // 2)]
    city.set_tile(walkers[0], Tile.ROAD)
    for _ in range(iterations * 2):
        walker = rng.choice(walkers)
        direction = rng.choice(DIRECTIONS)
        nxt = Point(walker.x + direction.x, walker.y + direction.y)
        if city.in_bounds(nxt):
            city.set_tile(nxt, Tile.ROAD)
            walkers.append(nxt)
            if rng.random() < 0.25:
                walkers.append(nxt)
        if len(walkers) > iterations:
            del walkers[: len(walkers) - iterations]


def _grow_radial(city: CityMap, rng: random.Random, iterations: int) -> None:
    center = Point(city.width // 2, city.height // 2)
    city.set_tile(center, Tile.ROAD)
    spoke_length = max(3, min(city.width, city.height) // 2 - 2)
    for direction in DIRECTIONS:
        _carve_segment(city, center, direction, spoke_length)
    for ring_radius in range(3, max(4, min(city.width, city.height) // 2), 4):
        ring_points = [
            Point(center.x - ring_radius, center.y),
            Point(center.x + ring_radius, center.y),
            Point(center.x, center.y - ring_radius),
            Point(center.x, center.y + ring_radius),
        ]
        valid_points = [point for point in ring_points if city.in_bounds(point)]
        for point in valid_points:
            city.set_tile(point, Tile.ROAD)
        for left, right in zip(valid_points, valid_points[1:] + valid_points[:1]):
            current = left
            while current.x != right.x:
                step = 1 if right.x > current.x else -1
                current = Point(current.x + step, current.y)
                if city.in_bounds(current):
                    city.set_tile(current, Tile.ROAD)
            while current.y != right.y:
                step = 1 if right.y > current.y else -1
                current = Point(current.x, current.y + step)
                if city.in_bounds(current):
                    city.set_tile(current, Tile.ROAD)
    _grow_grid(city, rng, iterations // 2)


def _weighted_choice(rng: random.Random, weights: dict[Tile, float]) -> Tile:
    threshold = rng.random()
    cumulative = 0.0
    last_tile = Tile.RESIDENTIAL
    for tile, weight in weights.items():
        cumulative += weight
        last_tile = tile
        if threshold <= cumulative:
            return tile
    return last_tile


def _adjusted_weights(
    base_weights: dict[Tile, float],
    *,
    distance: int,
    road_adjacent: int,
    edge_bias: int,
    water_bias: int,
) -> dict[Tile, float]:
    weights = dict(base_weights)
    if distance < 5:
        weights[Tile.COMMERCIAL] += 0.18
        weights[Tile.CIVIC] += 0.06
        weights[Tile.INDUSTRIAL] *= 0.4
    if edge_bias <= 1:
        weights[Tile.INDUSTRIAL] += 0.18
    if road_adjacent == 0:
        weights[Tile.PARK] += 0.15
    elif road_adjacent >= 2:
        weights[Tile.COMMERCIAL] += 0.12
    if water_bias <= 1:
        weights[Tile.PARK] += 0.08
        weights[Tile.RESIDENTIAL] += 0.06
    total = sum(weights.values())
    return {tile: value / total for tile, value in weights.items()}


def _place_water_corridor(city: CityMap, rng: random.Random) -> None:
    vertical = rng.random() < 0.5
    if vertical:
        x = rng.randint(max(1, city.width // 5), min(city.width - 2, city.width * 4 // 5))
        for y in range(city.height):
            if city.get_tile(Point(x, y)) != Tile.ROAD:
                city.set_tile(Point(x, y), Tile.WATER)
            if rng.random() < 0.35 and x + 1 < city.width and city.get_tile(Point(x + 1, y)) != Tile.ROAD:
                city.set_tile(Point(x + 1, y), Tile.WATER)
    else:
        y = rng.randint(max(1, city.height // 5), min(city.height - 2, city.height * 4 // 5))
        for x in range(city.width):
            if city.get_tile(Point(x, y)) != Tile.ROAD:
                city.set_tile(Point(x, y), Tile.WATER)
            if rng.random() < 0.35 and y + 1 < city.height and city.get_tile(Point(x, y + 1)) != Tile.ROAD:
                city.set_tile(Point(x, y + 1), Tile.WATER)


def _paint_zones(city: CityMap, rng: random.Random, zone_weights: dict[Tile, float]) -> None:
    center = Point(city.width // 2, city.height // 2)
    water_points = set(city.tile_points(Tile.WATER))
    for y in range(city.height):
        for x in range(city.width):
            point = Point(x, y)
            if city.get_tile(point) != Tile.EMPTY:
                continue
            distance = abs(center.x - x) + abs(center.y - y)
            road_adjacent = sum(1 for neighbor in city.neighbors4(point) if city.get_tile(neighbor) == Tile.ROAD)
            edge_bias = min(x, y, city.width - 1 - x, city.height - 1 - y)
            water_bias = min((abs(point.x - wp.x) + abs(point.y - wp.y) for wp in water_points), default=max(city.width, city.height))
            weights = _adjusted_weights(
                zone_weights,
                distance=distance,
                road_adjacent=road_adjacent,
                edge_bias=edge_bias,
                water_bias=water_bias,
            )
            city.set_tile(point, _weighted_choice(rng, weights))


def _place_landmarks(city: CityMap, rng: random.Random, landmark_count: int) -> list[Point]:
    if landmark_count < 0:
        raise ValueError("landmark_count cannot be negative")
    candidates = [
        point for point in city.road_points() if len(city.road_neighbors(point)) >= 3
    ]
    rng.shuffle(candidates)
    landmarks: list[Point] = []
    for point in candidates:
        nearby = [n for n in city.neighbors4(point) if city.get_tile(n) in {Tile.RESIDENTIAL, Tile.COMMERCIAL, Tile.PARK}]
        if not nearby:
            continue
        target = nearby[0]
        city.set_tile(target, Tile.CIVIC)
        landmarks.append(target)
        if len(landmarks) >= landmark_count:
            break
    return landmarks


def _ensure_fill(city: CityMap, fallback: Tile = Tile.RESIDENTIAL) -> None:
    for y in range(city.height):
        for x in range(city.width):
            point = Point(x, y)
            if city.get_tile(point) == Tile.EMPTY:
                city.set_tile(point, fallback)


def generate_city(
    width: int = 41,
    height: int = 25,
    *,
    seed: int | None = None,
    mode: str = "grid",
    iterations: int = 45,
    zone_weights: dict[str, float] | None = None,
    landmark_count: int = 4,
) -> CityMap:
    """Generate a procedural city map.

    Parameters are intentionally conservative so the generator stays deterministic,
    fast, and easy to test while still producing varied street patterns.
    """
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")

    rng = random.Random(seed)
    city = CityMap(width, height, seed=seed, mode=mode)
    if mode == "grid":
        _grow_grid(city, rng, iterations)
    elif mode == "organic":
        _grow_organic(city, rng, iterations)
    else:
        _grow_radial(city, rng, iterations)
    _place_water_corridor(city, rng)
    normalised_weights = _normalise_zone_weights(zone_weights)
    _paint_zones(city, rng, normalised_weights)
    landmarks = _place_landmarks(city, rng, landmark_count)
    _ensure_fill(city)
    city.metadata = {
        "iterations": iterations,
        "road_cells": len(city.road_points()),
        "landmarks": [[point.x, point.y] for point in landmarks],
        "zone_weights": {tile.value: round(weight, 4) for tile, weight in normalised_weights.items()},
    }
    return city
