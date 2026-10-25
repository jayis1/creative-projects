"""Small, dependency-free parallel-beam tomography and ART reconstruction."""
from __future__ import annotations

import argparse
import math
import random

from io_tools import save_pgm


def main() -> None:
    parser = argparse.ArgumentParser(description="Toy parallel-beam tomography with algebraic reconstruction")
    parser.add_argument("--demo", action="store_true", help="run the deterministic reconstruction demo")
    parser.add_argument("--seed", type=int, default=7, help="noise seed (default: 7)")
    parser.add_argument("--size", type=int, default=12, help="square phantom size, 2..128 (default: 12)")
    parser.add_argument("--output", help="optional path for reconstructed ASCII PGM image")
    args = parser.parse_args()
    if not 2 <= args.size <= 128:
        parser.error("--size must be between 2 and 128")
    result = reconstruct_demo(args.seed, args.size)
    print(demo(args.seed, args.size))
    if args.output:
        save_pgm(result, args.output)
        print(f"Wrote {args.output}")


def phantom(size: int = 16) -> list[list[float]]:
    """Create a deterministic asymmetric phantom with values in [0, 1]."""
    if not 2 <= size <= 128:
        raise ValueError("size must be between 2 and 128")
    out = [[0.0] * size for _ in range(size)]
    for y in range(size):
        for x in range(size):
            nx, ny = (x + .5) / size * 2 - 1, (y + .5) / size * 2 - 1
            if nx * nx / .60 + ny * ny / .82 < 1:
                out[y][x] = .35
            if (nx - .22) ** 2 / .08 + (ny + .10) ** 2 / .22 < 1:
                out[y][x] = 1.0
            if (nx + .38) ** 2 + (ny - .36) ** 2 < .09:
                out[y][x] = .72
    return out


def _ray_weights(size: int, angle: float, offset: float) -> list[tuple[int, int, float]]:
    """Approximate a ray integral by bilinear sampling along its path."""
    c, s = math.cos(angle), math.sin(angle)
    center = (size - 1) / 2
    # Pixel-center coordinates; step is small enough to sample every pixel.
    length = size * math.sqrt(2)
    steps = max(1, math.ceil(length * 2))
    weights: dict[tuple[int, int], float] = {}
    for i in range(steps + 1):
        t = -length / 2 + length * i / steps
        xf, yf = center + offset * c - t * s, center + offset * s + t * c
        x0, y0 = math.floor(xf), math.floor(yf)
        dx, dy = xf - x0, yf - y0
        scale = length / steps
        for x, y, w in ((x0,y0,(1-dx)*(1-dy)), (x0+1,y0,dx*(1-dy)),
                        (x0,y0+1,(1-dx)*dy), (x0+1,y0+1,dx*dy)):
            if 0 <= x < size and 0 <= y < size and w > 0:
                weights[(y, x)] = weights.get((y, x), 0.0) + w * scale
    return [(y, x, w) for (y, x), w in weights.items()]


def project(image: list[list[float]], angles: int = 18, detectors: int | None = None) -> list[list[float]]:
    """Return angle-major line integrals, using parallel rays."""
    size = len(image)
    _validate_image(image)
    if not 1 <= angles <= 180 or not 1 <= (detectors or size * 2) <= 512:
        raise ValueError("angles must be 1..180 and detectors 1..512")
    detectors = detectors or size * 2
    out = []
    for a in range(angles):
        theta = math.pi * a / angles
        row = []
        for d in range(detectors):
            offset = (d - (detectors - 1) / 2) * (size * math.sqrt(2) / detectors)
            row.append(sum(image[y][x] * w for y, x, w in _ray_weights(size, theta, offset)))
        out.append(row)
    return out


def reconstruct(sinogram: list[list[float]], size: int, iterations: int = 8,
                relaxation: float = .18) -> list[list[float]]:
    """Solve the least-squares projection system by sequential ART updates."""
    if not 2 <= size <= 128 or not 1 <= iterations <= 100:
        raise ValueError("size must be 2..128 and iterations 1..100")
    if not math.isfinite(relaxation) or not 0 < relaxation <= 1:
        raise ValueError("relaxation must be finite and in (0, 1]")
    if not sinogram or not sinogram[0] or any(len(r) != len(sinogram[0]) for r in sinogram):
        raise ValueError("sinogram must be a non-empty rectangular matrix")
    if any(not math.isfinite(v) or v < 0 for row in sinogram for v in row):
        raise ValueError("measurements must be finite and non-negative")
    if len(sinogram) > 180 or len(sinogram[0]) > 512:
        raise ValueError("sinogram exceeds supported dimensions")
    image = [[0.0] * size for _ in range(size)]
    rays = []
    for a, row in enumerate(sinogram):
        theta = math.pi * a / len(sinogram)
        for d, measured in enumerate(row):
            offset = (d - (len(row) - 1) / 2) * (size * math.sqrt(2) / len(row))
            weights = _ray_weights(size, theta, offset)
            norm = sum(w*w for _, _, w in weights)
            if norm:
                rays.append((weights, norm, measured))
    for _ in range(iterations):
        for weights, norm, measured in rays:
            residual = measured - sum(image[y][x] * w for y, x, w in weights)
            correction = relaxation * residual / norm
            for y, x, w in weights:
                image[y][x] = max(0.0, image[y][x] + correction * w)
    return image


def _validate_image(image: list[list[float]]) -> None:
    n = len(image)
    if not 1 <= n <= 128 or any(len(row) != n for row in image):
        raise ValueError("image must be a square matrix of size 1..128")
    if any(not math.isfinite(v) or v < 0 for row in image for v in row):
        raise ValueError("image values must be finite and non-negative")


def render(image: list[list[float]]) -> str:
    """Render an image as an ASCII intensity map."""
    _validate_image(image)
    ramp = " .:-=+*#%@"
    peak = max((v for row in image for v in row), default=0.0)
    return "\n".join("".join(ramp[min(9, int(v / peak * 9))] if peak else " " for v in row) for row in image)


def reconstruct_demo(seed: int = 7, size: int = 12) -> list[list[float]]:
    """Create the seeded noisy phantom reconstruction used by CLI export."""
    rng = random.Random(seed)
    scan = project(phantom(size), angles=16, detectors=size * 2)
    noisy = [[max(0.0, v + rng.gauss(0, .025)) for v in row] for row in scan]
    return reconstruct(noisy, size, iterations=10)


def demo(seed: int = 7, size: int = 12) -> str:
    """Produce a reproducible noisy-scan reconstruction report."""
    rng = random.Random(seed)
    original = phantom(size)
    scan = project(original, angles=16, detectors=size * 2)
    noisy = [[max(0.0, v + rng.gauss(0, .025)) for v in row] for row in scan]
    result = reconstruct(noisy, size, iterations=10)
    mae = sum(abs(a-b) for ra, rb in zip(original, result) for a, b in zip(ra, rb)) / (size*size)
    return f"Sinogram Lab | size={size} angles=16 detectors={size*2} seed={seed}\nMAE: {mae:.4f}\n{render(result)}"
