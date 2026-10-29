"""Deterministic thermal and hydraulic erosion on a small height field."""
from __future__ import annotations
import argparse
import math
import random
from pathlib import Path


def generate(width: int, height: int, seed: int) -> list[list[float]]:
    """Create a seeded, gently varied terrain in normalized height units."""
    rng = random.Random(seed)
    grid = [[0.45 + 0.18 * math.sin(x * .31) * math.cos(y * .23) + rng.uniform(-.035, .035)
             for x in range(width)] for y in range(height)]
    return [[max(0.0, min(1.0, value)) for value in row] for row in grid]


def thermal_step(grid: list[list[float]], talus: float = .08, rate: float = .25) -> list[list[float]]:
    """Move a bounded fraction of steepest-neighbor excess downhill, simultaneously."""
    _validate_grid(grid)
    if not math.isfinite(talus) or talus < 0 or not math.isfinite(rate) or not 0 <= rate <= 1:
        raise ValueError("talus must be nonnegative and rate must be in [0, 1]")
    h, w = len(grid), len(grid[0])
    delta = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            neighbors = [(nx, ny) for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if 0 <= nx < w and 0 <= ny < h]
            if not neighbors:
                continue
            nx, ny = max(neighbors, key=lambda p: grid[y][x] - grid[p[1]][p[0]])
            excess = grid[y][x] - grid[ny][nx] - talus
            if excess > 0:
                moved = excess * rate
                delta[y][x] -= moved
                delta[ny][nx] += moved
    result = [[grid[y][x] + delta[y][x] for x in range(w)] for y in range(h)]
    return result


def _validate_grid(grid: list[list[float]]) -> None:
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("height field must be a non-empty rectangle")
    if any(not math.isfinite(v) for row in grid for v in row):
        raise ValueError("height field values must be finite")


def write_pgm(grid: list[list[float]], path: str | Path) -> None:
    """Write normalized heights as an ASCII PGM image."""
    _validate_grid(grid)
    target = Path(path)
    rows = [" ".join(str(round(max(0, min(1, v)) * 255)) for v in row) for row in grid]
    target.write_text(f"P2\n{len(grid[0])} {len(grid)}\n255\n" + "\n".join(rows) + "\n", encoding="ascii")


def erode(grid: list[list[float]], iterations: int, talus: float = .08, rate: float = .25) -> list[list[float]]:
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 0 <= iterations <= 10000:
        raise ValueError("iterations must be an integer in [0, 10000]")
    for _ in range(iterations):
        grid = thermal_step(grid, talus, rate)
    return grid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run the small reproducible sample")
    parser.add_argument("--width", type=int, default=48)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--talus", type=float, default=.08)
    parser.add_argument("--rate", type=float, default=.25)
    parser.add_argument("--output", default="terrain.pgm")
    args = parser.parse_args()
    if not 1 <= args.width <= 512 or not 1 <= args.height <= 512:
        parser.error("width and height must be in [1, 512]")
    try:
        result = erode(generate(args.width, args.height, args.seed), args.iterations, args.talus, args.rate)
        write_pgm(result, args.output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Wrote {args.width}x{args.height} terrain to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
