"""Dependency-free sparse signal recovery with iterative hard thresholding."""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from typing import Sequence

Vector = list[float]
Matrix = list[Vector]


@dataclass(frozen=True)
class RecoveryResult:
    estimate: Vector
    residuals: tuple[float, ...]
    iterations: int
    converged: bool


def _finite(values: Sequence[float], label: str) -> None:
    if any(not math.isfinite(x) for x in values):
        raise ValueError(f"{label} values must be finite")


def gaussian_matrix(rows: int, cols: int, seed: int = 0) -> Matrix:
    """Create an M-by-N iid Gaussian matrix normalized by sqrt(M)."""
    if rows <= 0 or cols <= 0:
        raise ValueError("matrix dimensions must be positive")
    rng = random.Random(seed)
    scale = 1.0 / math.sqrt(rows)
    return [[rng.gauss(0.0, 1.0) * scale for _ in range(cols)] for _ in range(rows)]


def matvec(matrix: Matrix, vector: Sequence[float]) -> Vector:
    if not matrix or len(matrix[0]) != len(vector):
        raise ValueError("matrix and vector dimensions do not match")
    width = len(vector)
    if any(len(row) != width for row in matrix):
        raise ValueError("matrix must be rectangular")
    _finite(vector, "vector")
    for row in matrix:
        _finite(row, "matrix")
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def sparse_signal(size: int, sparsity: int, seed: int = 1) -> Vector:
    """Return a seeded signal with exactly sparsity nonzero entries."""
    if size <= 0 or not 0 <= sparsity <= size:
        raise ValueError("require size > 0 and 0 <= sparsity <= size")
    rng = random.Random(seed)
    result = [0.0] * size
    for idx in rng.sample(range(size), sparsity):
        result[idx] = rng.uniform(-1.0, 1.0)
    return result


def _norm_squared(matrix: Matrix) -> float:
    """Power iteration estimate of the largest eigenvalue of A^T A."""
    n = len(matrix[0])
    v = [1.0 / math.sqrt(n)] * n
    for _ in range(80):
        av = [sum(a * x for a, x in zip(row, v)) for row in matrix]
        nxt = [sum(matrix[i][j] * av[i] for i in range(len(matrix))) for j in range(n)]
        norm = math.sqrt(sum(x * x for x in nxt))
        if norm == 0:
            return 0.0
        v = [x / norm for x in nxt]
    av = [sum(a * x for a, x in zip(row, v)) for row in matrix]
    return sum(x * x for x in av)


def recover(matrix: Matrix, measurements: Sequence[float], sparsity: int,
            max_iterations: int = 500, tolerance: float = 1e-8) -> RecoveryResult:
    """Recover a K-sparse vector from y=A x using iterative hard thresholding."""
    if not matrix or not matrix[0]:
        raise ValueError("matrix must be non-empty")
    rows, cols = len(matrix), len(matrix[0])
    if any(len(row) != cols for row in matrix):
        raise ValueError("matrix must be rectangular")
    if len(measurements) != rows:
        raise ValueError("measurement count must match matrix rows")
    if not 1 <= sparsity <= cols:
        raise ValueError("sparsity must be between 1 and signal dimension")
    if not isinstance(max_iterations, int) or max_iterations < 1:
        raise ValueError("max_iterations must be a positive integer")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    _finite(measurements, "measurements")
    for row in matrix:
        _finite(row, "matrix")
    lipschitz = _norm_squared(matrix)
    if lipschitz <= 0 or not math.isfinite(lipschitz):
        raise ValueError("matrix must have positive finite energy")
    step = 1.0 / lipschitz
    x = [0.0] * cols
    residuals: list[float] = []
    converged = False
    for _ in range(max_iterations):
        residual = [measurements[i] - sum(a * b for a, b in zip(matrix[i], x)) for i in range(rows)]
        error = math.sqrt(sum(r * r for r in residual))
        residuals.append(error)
        if error <= tolerance:
            converged = True
            break
        gradient = [sum(matrix[i][j] * residual[i] for i in range(rows)) for j in range(cols)]
        candidate = [x[j] + step * gradient[j] for j in range(cols)]
        keep = set(sorted(range(cols), key=lambda j: abs(candidate[j]), reverse=True)[:sparsity])
        updated = [candidate[j] if j in keep else 0.0 for j in range(cols)]
        if math.sqrt(sum((updated[j] - x[j]) ** 2 for j in range(cols))) <= tolerance:
            x = updated
            break
        x = updated
    else:
        residual = [measurements[i] - sum(a * b for a, b in zip(matrix[i], x)) for i in range(rows)]
        residuals.append(math.sqrt(sum(r * r for r in residual)))
    return RecoveryResult(x, tuple(residuals), len(residuals), converged)


def demo() -> dict[str, object]:
    original = sparse_signal(32, 4, seed=17)
    matrix = gaussian_matrix(20, 32, seed=23)
    measured = matvec(matrix, original)
    result = recover(matrix, measured, 4)
    error = math.sqrt(sum((a - b) ** 2 for a, b in zip(original, result.estimate)))
    return {"dimension": len(original), "measurements": len(measured), "sparsity": 4,
            "iterations": result.iterations, "residual": result.residuals[-1],
            "reconstruction_error": error, "estimate": result.estimate}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run seeded recovery example")
    parser.add_argument("--json", help="JSON file containing matrix, measurements, sparsity")
    args = parser.parse_args()
    if args.json:
        with open(args.json, encoding="utf-8") as stream:
            data = json.load(stream)
        result = recover(data["matrix"], data["measurements"], data["sparsity"])
        print(json.dumps({"estimate": result.estimate, "residuals": result.residuals,
                          "iterations": result.iterations, "converged": result.converged}))
    elif args.demo:
        print(json.dumps(demo(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
