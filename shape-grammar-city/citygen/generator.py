from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Tile(str, Enum):
    EMPTY = "empty"
    ROAD = "road"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    PARK = "park"
    WATER = "water"


@dataclass(frozen=True, order=True)
class Point:
    x: int
    y: int


@dataclass
class CityMap:
    width: int
    height: int
    grid: list[list[Tile]] = field(init=False)
    seed: int | None = None
    mode: str = "grid"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.grid = [[Tile.EMPTY for _ in range(self.width)] for _ in range(self.height)]

    def in_bounds(self, point: Point) -> bool:
        return 0 <= point.x < self.width and 0 <= point.y < self.height

    def set_tile(self, point: Point, tile: Tile) -> None:
        if self.in_bounds(point):
            self.grid[point.y][point.x] = tile

    def get_tile(self, point: Point) -> Tile:
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

    def road_points(self) -> list[Point]:
        points: list[Point] = []
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile == Tile.ROAD:
                    points.append(Point(x, y))
        return points

    def fill_zone(self, points: list[Point], tile: Tile) -> None:
        for point in points:
            if self.get_tile(point) == Tile.EMPTY:
                self.set_tile(point, tile)

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
        city = cls(payload["width"], payload["height"], seed=payload.get("seed"), mode=payload.get("mode", "grid"))
        city.metadata = payload.get("metadata", {})
        city.grid = [[Tile(tile) for tile in row] for row in payload["grid"]]
        return city


DIRECTIONS = [Point(1, 0), Point(-1, 0), Point(0, 1), Point(0, -1)]


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


def _paint_zones(city: CityMap, rng: random.Random) -> None:
    center = Point(city.width // 2, city.height // 2)
    for y in range(city.height):
        for x in range(city.width):
            point = Point(x, y)
            if city.get_tile(point) != Tile.EMPTY:
                continue
            distance = abs(center.x - x) + abs(center.y - y)
            road_adjacent = sum(1 for neighbor in city.neighbors4(point) if city.get_tile(neighbor) == Tile.ROAD)
            edge_bias = min(x, y, city.width - 1 - x, city.height - 1 - y)
            roll = rng.random()
            if distance > (city.width + city.height) // 3 and roll < 0.16:
                city.set_tile(point, Tile.WATER)
            elif road_adjacent == 0 and roll < 0.18:
                city.set_tile(point, Tile.PARK)
            elif edge_bias < 2 and roll < 0.28:
                city.set_tile(point, Tile.INDUSTRIAL)
            elif distance < min(city.width, city.height) // 5:
                city.set_tile(point, Tile.COMMERCIAL)
            else:
                city.set_tile(point, Tile.RESIDENTIAL)


def generate_city(width: int = 41, height: int = 25, *, seed: int | None = None, mode: str = "grid", iterations: int = 45) -> CityMap:
    if width < 9 or height < 9:
        raise ValueError("width and height must both be at least 9")
    if mode not in {"grid", "organic"}:
        raise ValueError("mode must be 'grid' or 'organic'")

    rng = random.Random(seed)
    city = CityMap(width, height, seed=seed, mode=mode)
    if mode == "grid":
        _grow_grid(city, rng, iterations)
    else:
        _grow_organic(city, rng, iterations)
    _paint_zones(city, rng)
    city.metadata = {"iterations": iterations, "road_cells": len(city.road_points())}
    return city
