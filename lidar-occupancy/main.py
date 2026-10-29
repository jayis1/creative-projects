#!/usr/bin/env python3
"""Build small occupancy grids from planar range scans."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass
class Grid:
    """A bounded log-odds occupancy grid, indexed as grid[y][x]."""

    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    cells: list[list[float]]

    @classmethod
    def create(cls, width: int, height: int, resolution: float = 1.0,
               origin_x: float = 0.0, origin_y: float = 0.0) -> "Grid":
        if not isinstance(width, int) or not isinstance(height, int) or width < 1 or height < 1:
            raise ValueError("grid dimensions must be positive integers")
        if width * height > 2_000_000:
            raise ValueError("grid exceeds 2,000,000 cells")
        if not math.isfinite(resolution) or resolution <= 0:
            raise ValueError("resolution must be finite and positive")
        if not math.isfinite(origin_x) or not math.isfinite(origin_y):
            raise ValueError("origin must be finite")
        return cls(width, height, resolution, origin_x, origin_y,
                   [[0.0 for _ in range(width)] for _ in range(height)])

    def world_to_cell(self, x: float, y: float) -> tuple[int, int] | None:
        """Map world coordinates to a cell; return None outside the grid."""
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("coordinates must be finite")
        col = math.floor((x - self.origin_x) / self.resolution)
        row = math.floor((y - self.origin_y) / self.resolution)
        return (col, row) if 0 <= col < self.width and 0 <= row < self.height else None

    def trace_ray(self, start: tuple[float, float], end: tuple[float, float],
                  hit: bool = True, free_delta: float = -0.4,
                  occupied_delta: float = 0.85) -> None:
        """Update cells along a ray; the endpoint is occupied only on a hit."""
        if not math.isfinite(free_delta) or not math.isfinite(occupied_delta):
            raise ValueError("updates must be finite")
        first = self.world_to_cell(*start)
        last = self.world_to_cell(*end)
        if first is None:
            raise ValueError("sensor origin is outside the map")
        if last is None:
            # Clip the ray to the grid bounds using parametric slab clipping.
            clipped = self._clip(start, end)
            if clipped is None:
                return
            end = clipped
            last = self.world_to_cell(*end)
            if last is None:
                return
        cells = self._bresenham(first, last)
        endpoint = cells[-1] if cells else None
        for col, row in cells:
            is_hit = hit and (col, row) == endpoint
            self.cells[row][col] = max(-5.0, min(5.0, self.cells[row][col] +
                                                (occupied_delta if is_hit else free_delta)))

    def _clip(self, start: tuple[float, float], end: tuple[float, float]) -> tuple[float, float] | None:
        """Return the last in-bounds point on a segment using slab clipping."""
        x0, y0 = start
        dx, dy = end[0] - x0, end[1] - y0
        t0, t1 = 0.0, 1.0
        bounds = ((self.origin_x, self.origin_x + self.width * self.resolution),
                  (self.origin_y, self.origin_y + self.height * self.resolution))
        for origin, delta, (low, high) in ((x0, dx, bounds[0]), (y0, dy, bounds[1])):
            if delta == 0:
                if origin < low or origin >= high:
                    return None
                continue
            near, far = (low - origin) / delta, (high - origin) / delta
            if near > far:
                near, far = far, near
            t0, t1 = max(t0, near), min(t1, far)
            if t0 > t1:
                return None
        # Nudge inward: the high edge is exclusive.
        t = min(t1, 1.0)
        if t < 1.0:
            t = max(t0, t - 1e-12)
        return x0 + t * dx, y0 + t * dy

    @staticmethod
    def _bresenham(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
        x0, y0 = a
        x1, y1 = b
        dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
        dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
        error = dx + dy
        result = []
        while True:
            result.append((x0, y0))
            if x0 == x1 and y0 == y1:
                return result
            twice = 2 * error
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy

    def integrate_scan(self, origin: tuple[float, float], beams: list[tuple[float, float]],
                       max_range: float, free_delta: float = -0.4,
                       occupied_delta: float = 0.85) -> None:
        """Integrate (angle, measured_range) beams; zero range is a valid hit.

        Measurements beyond max_range are clamped and treated as no-return
        beams. Input count is bounded to prevent accidental unbounded work.
        """
        if not math.isfinite(max_range) or max_range <= 0:
            raise ValueError("max_range must be finite and positive")
        if len(beams) > 100_000:
            raise ValueError("scan exceeds 100,000 beams")
        self.world_to_cell(*origin)  # validate finite coordinates
        for angle, distance in beams:
            if not math.isfinite(angle) or not math.isfinite(distance) or distance < 0:
                raise ValueError("beam angles must be finite and ranges nonnegative")
            hit = distance <= max_range
            traced_distance = min(distance, max_range)
            endpoint = (origin[0] + traced_distance * math.cos(angle),
                        origin[1] + traced_distance * math.sin(angle))
            self.trace_ray(origin, endpoint, hit=hit, free_delta=free_delta,
                           occupied_delta=occupied_delta)

    def summary(self) -> dict[str, int | float]:
        """Return occupancy counts and the observed log-odds range."""
        values = [value for row in self.cells for value in row]
        return {"width": self.width, "height": self.height,
                "resolution": self.resolution,
                "occupied": sum(value > 0 for value in values),
                "free": sum(value < 0 for value in values),
                "unknown": sum(value == 0 for value in values),
                "min_log_odds": min(values), "max_log_odds": max(values)}

    def to_json(self) -> str:
        """Serialize map metadata and cells as deterministic JSON."""
        import json
        return json.dumps({"width": self.width, "height": self.height,
                           "resolution": self.resolution,
                           "origin": [self.origin_x, self.origin_y],
                           "cells": self.cells}, sort_keys=True, separators=(",", ":"))

    def render(self, threshold: float = 0.0) -> str:
        """Render top row first as ASCII: # occupied, . free, _ unknown."""
        if not math.isfinite(threshold):
            raise ValueError("threshold must be finite")
        return "\n".join("".join("#" if v > threshold else "." if v < -threshold else "_"
                                  for v in row) for row in reversed(self.cells))


def demo() -> str:
    grid = Grid.create(15, 9, resolution=1.0, origin_x=-7.0, origin_y=-4.0)
    # Three reproducible synthetic range returns from a sensor at the origin.
    for endpoint in ((5.0, 2.0), (4.0, -2.0), (-3.0, 3.0)):
        grid.trace_ray((0.0, 0.0), endpoint)
    return grid.render()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="render a deterministic synthetic scan")
    args = parser.parse_args()
    if args.demo:
        print(demo())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
