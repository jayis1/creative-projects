#!/usr/bin/env python3
"""Newton basin renderer for a user-specified complex polynomial."""
from __future__ import annotations
import argparse
import cmath
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Result:
    basin: int
    iterations: int


def evaluate(coefficients: tuple[complex, ...], z: complex) -> tuple[complex, complex]:
    """Evaluate polynomial and its derivative together using Horner's rule."""
    value = coefficients[0]
    deriv = 0j
    for coefficient in coefficients[1:]:
        deriv = deriv * z + value
        value = value * z + coefficient
    return value, deriv


def classify(z: complex, coefficients: tuple[complex, ...], roots: tuple[complex, ...], *,
             max_iterations: int = 80, tolerance: float = 1e-8, damping: float = 1.0,
             escape_radius: float = 1e6) -> Result:
    """Iterate Newton's method and return the nearest converged root's index, or -1."""
    if len(coefficients) < 2 or not roots:
        raise ValueError("polynomial and at least one root candidate are required")
    if max_iterations < 1 or tolerance <= 0 or not 0 < damping <= 1 or escape_radius <= 0:
        raise ValueError("invalid iteration, tolerance, damping, or escape limit")
    for iteration in range(max_iterations + 1):
        value, derivative = evaluate(coefficients, z)
        if abs(value) <= tolerance:
            distances = [abs(z - root) for root in roots]
            nearest = min(range(len(roots)), key=distances.__getitem__)
            return Result(nearest if distances[nearest] <= tolerance * 10 else -1, iteration)
        if iteration == max_iterations or abs(z) > escape_radius or abs(derivative) <= 1e-15:
            return Result(-1, iteration)
        z -= damping * value / derivative
    return Result(-1, max_iterations)


def render(width: int, height: int, bounds: tuple[float, float, float, float],
           coefficients: tuple[complex, ...], roots: tuple[complex, ...], *,
           max_iterations: int = 80, tolerance: float = 1e-8, damping: float = 1.0) -> list[list[Result]]:
    """Sample an inclusive rectangular complex-plane viewport."""
    if width < 1 or height < 1:
        raise ValueError("image dimensions must be positive")
    xmin, xmax, ymin, ymax = bounds
    if not all(map(lambda x: isinstance(x, (int, float)), bounds)) or xmin >= xmax or ymin >= ymax:
        raise ValueError("bounds must be finite increasing numeric intervals")
    rows = []
    for row in range(height):
        y = ymax - (ymax - ymin) * row / max(1, height - 1)
        rows.append([classify(complex(xmin + (xmax - xmin) * col / max(1, width - 1), y),
                              coefficients, roots, max_iterations=max_iterations,
                              tolerance=tolerance, damping=damping)
                     for col in range(width)])
    return rows


def ascii_art(rows: list[list[Result]], symbols: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.") -> str:
    """Map basins to symbols and unresolved samples to the final symbol."""
    if not symbols:
        raise ValueError("symbols cannot be empty")
    return "\n".join("".join(symbols[cell.basin % (len(symbols)-1)] if cell.basin >= 0
                           and len(symbols) > 1 else symbols[-1] for cell in row) for row in rows)


def ppm_bytes(rows: list[list[Result]]) -> bytes:
    """Produce a small deterministic P6 image with one fixed color per basin."""
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("rows must form a non-empty rectangle")
    palette = ((239, 83, 80), (66, 165, 245), (102, 187, 106), (255, 202, 40),
               (171, 71, 188), (38, 198, 218))
    data = bytearray()
    for row in rows:
        for cell in row:
            rgb = palette[cell.basin % len(palette)] if cell.basin >= 0 else (0, 0, 0)
            data.extend(rgb)
    return f"P6\n{len(rows[0])} {len(rows)}\n255\n".encode("ascii") + data


def demo() -> None:
    coefficients = (1, 0, 0, -1)
    roots = (1 + 0j, cmath.exp(2j * cmath.pi / 3), cmath.exp(4j * cmath.pi / 3))
    rows = render(72, 32, (-1.6, 1.6, -1.2, 1.2), coefficients, roots)
    print(ascii_art(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="render the cubic z^3-1 example")
    parser.add_argument("--width", type=int, default=72)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--format", choices=("ascii", "ppm"), default="ascii")
    parser.add_argument("--output", type=Path, help="write PPM image to this path")
    args = parser.parse_args()
    if args.demo:
        demo(); return
    coeffs = (1, 0, 0, -1)
    roots = (1 + 0j, cmath.exp(2j * cmath.pi / 3), cmath.exp(4j * cmath.pi / 3))
    rows = render(args.width, args.height, (-1.6, 1.6, -1.2, 1.2), coeffs, roots)
    if args.format == "ppm":
        if args.output is None:
            parser.error("--output is required for PPM format")
        args.output.write_bytes(ppm_bytes(rows))
    else:
        print(ascii_art(rows))

if __name__ == "__main__":
    main()
