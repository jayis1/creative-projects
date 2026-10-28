"""Plan deterministic, travel-aware running stitches over a binary raster mask."""
from __future__ import annotations
import argparse
import math
from pathlib import Path


def plan(mask: list[str], spacing: int = 2, max_stitches: int = 10000) -> list[tuple[float, float]]:
    """Scan horizontal rows and emit contiguous ink-run endpoints as stitch points."""
    if not mask or not mask[0]:
        raise ValueError("mask must be a non-empty rectangle")
    width = len(mask[0])
    if any(len(row) != width or set(row) - {".", "#"} for row in mask):
        raise ValueError("mask must be rectangular and contain only '.' and '#'")
    if isinstance(spacing, bool) or not isinstance(spacing, int) or spacing < 1:
        raise ValueError("spacing must be a positive integer")
    if max_stitches < 1:
        raise ValueError("max_stitches must be positive")
    points: list[tuple[float, float]] = []
    for y in range(0, len(mask), spacing):
        runs: list[tuple[int, int]] = []
        x = 0
        while x < width:
            if mask[y][x] == "#":
                start = x
                while x + 1 < width and mask[y][x + 1] == "#":
                    x += 1
                runs.append((start, x))
            x += 1
        if y // spacing % 2:
            runs.reverse()
        for start, end in runs:
            pair = [(float(start), float(y)), (float(end), float(y))]
            if y // spacing % 2:
                pair.reverse()
            if len(points) + len(pair) > max_stitches:
                raise ValueError("stitch limit exceeded")
            points.extend(pair)
    return points


def svg(points: list[tuple[float, float]], width: int, height: int, stitch_length: float = 0.0) -> str:
    """Render stitch path as a self-contained SVG; optional maximum-length subdivision."""
    if width < 1 or height < 1:
        raise ValueError("dimensions must be positive")
    if not math.isfinite(stitch_length) or stitch_length < 0:
        raise ValueError("stitch_length must be finite and nonnegative")
    expanded: list[tuple[float, float]] = []
    for p in points:
        if not all(math.isfinite(v) for v in p):
            raise ValueError("coordinates must be finite")
        if expanded:
            a = expanded[-1]
            distance = math.dist(a, p)
            count = max(1, math.ceil(distance / stitch_length)) if stitch_length else 1
            expanded.extend((a[0] + (p[0]-a[0])*i/count, a[1] + (p[1]-a[1])*i/count) for i in range(1, count+1))
        else:
            expanded.append(p)
    d = " ".join(("M" if i == 0 else "L") + f"{x:g},{y:g}" for i, (x, y) in enumerate(expanded))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><path d="{d}" fill="none" stroke="#c23b55" stroke-width="0.7" stroke-linecap="round"/></svg>\n'


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan running stitches from a text raster mask")
    parser.add_argument("mask", type=Path, help="ASCII mask file (# ink, . blank)")
    parser.add_argument("-o", "--output", type=Path, default=Path("stitches.svg"))
    parser.add_argument("--spacing", type=int, default=2)
    args = parser.parse_args()
    rows = args.mask.read_text(encoding="utf-8").splitlines()
    points = plan(rows, args.spacing)
    args.output.write_text(svg(points, len(rows[0]), len(rows)), encoding="utf-8")
    print(f"Wrote {len(points)} stitch points to {args.output}")

if __name__ == "__main__":
    main()
