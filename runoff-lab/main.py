#!/usr/bin/env python3
"""A bounded, deterministic rainfall-runoff and flow-accumulation model."""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

OFFSETS = ((-1, 0), (0, 1), (1, 0), (0, -1))


def make_terrain(width: int, height: int, seed: int) -> list[list[float]]:
    """Create a seeded basin-like elevation field with a central ridge."""
    rng = random.Random(seed)
    return [[
        1.0 - 0.55 * (abs(x - (width - 1) / 2) / max(1, width / 2)
                      + abs(y - (height - 1) / 2) / max(1, height / 2))
        + rng.random() * 0.025
        for x in range(width)] for y in range(height)]


def _validate_grid(grid: list[list[float]]) -> tuple[int, int]:
    if not isinstance(grid, list) or not grid or not all(isinstance(row, list) for row in grid):
        raise ValueError("grid must be a non-empty rectangular list of rows")
    width = len(grid[0])
    if width == 0 or any(len(row) != width for row in grid):
        raise ValueError("grid must be rectangular and non-empty")
    if len(grid) > 512 or width > 512 or width * len(grid) > 262144:
        raise ValueError("grid exceeds the 512x512 cell limit")
    for row in grid:
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("elevations must be finite numbers (not booleans)")
    return width, len(grid)


def route_flow(grid: list[list[float]]) -> tuple[list[list[int | None]], list[list[float]]]:
    """Assign each cell to its steepest lower cardinal neighbor (D8 facets not used).

    Cells with no lower neighbor are sinks. Destinations strictly decrease in
    elevation, so the resulting single-receiver graph cannot contain cycles.
    """
    width, height = _validate_grid(grid)
    downstream: list[list[int | None]] = [[None] * width for _ in range(height)]
    order = sorted(((grid[y][x], y, x) for y in range(height) for x in range(width)), reverse=True)
    for _, y, x in order:
        best_drop = 0.0
        best: int | None = None
        for dy, dx in OFFSETS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width:
                drop = grid[y][x] - grid[ny][nx]
                if drop > best_drop:
                    best_drop = drop
                    best = ny * width + nx
        downstream[y][x] = best
    accumulation = [[1.0] * width for _ in range(height)]
    for _, y, x in order:
        dest = downstream[y][x]
        if dest is not None:
            dy, dx = divmod(dest, width)
            accumulation[dy][dx] += accumulation[y][x]
    return downstream, accumulation


def render_ascii(grid: list[list[float]], accumulation: list[list[float]]) -> str:
    """Render elevation with flow intensity overlaid as ASCII glyphs."""
    _validate_grid(grid)
    if len(accumulation) != len(grid) or any(len(a) != len(grid[0]) for a in accumulation):
        raise ValueError("accumulation dimensions must match grid")
    symbols = " .:-=+*#%@"
    values = [v for row in accumulation for v in row]
    cap = max(values)
    return "\n".join("".join(symbols[min(len(symbols)-1, int((math.log1p(v) / math.log1p(cap)) * (len(symbols)-1)))] for v in row) for row in accumulation)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=24)
    parser.add_argument("--height", type=int, default=14)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--rain", type=float, default=1.0, help="rainfall contribution per cell")
    parser.add_argument("--output", type=Path, help="write JSON flow report (does not overwrite)")
    parser.add_argument("--demo", action="store_true", help="print a small flow-accumulation map")
    args = parser.parse_args(argv)
    if not (1 <= args.width <= 512 and 1 <= args.height <= 512 and args.width * args.height <= 262144):
        parser.error("dimensions must be 1..512 and at most 262144 cells")
    if not math.isfinite(args.rain) or args.rain <= 0:
        parser.error("--rain must be finite and greater than zero")
    grid = make_terrain(args.width, args.height, args.seed)
    downstream, counts = route_flow(grid)
    weighted = [[v * args.rain for v in row] for row in counts]
    if args.demo or not args.output:
        print(render_ascii(grid, weighted))
    if args.output:
        payload = {"width": args.width, "height": args.height, "seed": args.seed,
                   "rain_per_cell": args.rain, "accumulation": weighted,
                   "downstream": downstream}
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2)
                stream.write("\n")
        except FileExistsError:
            parser.error(f"refusing to overwrite existing file: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
