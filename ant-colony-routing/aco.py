#!/usr/bin/env python3
"""Ant-colony optimization for bounded, symmetric traveling-salesperson instances."""
from __future__ import annotations
import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

@dataclass(frozen=True)
class Result:
    route: tuple[int, ...]
    distance: float
    history: tuple[float, ...]

def route_length(route: tuple[int, ...], distances: list[list[float]]) -> float:
    if not route:
        return 0.0
    return sum(distances[a][b] for a, b in zip(route, route[1:] + route[:1]))

def validate(points: list[tuple[float, float]]) -> None:
    if not 2 <= len(points) <= 200:
        raise ValueError("point count must be between 2 and 200")
    if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError("each point must contain two finite coordinates")

def improve_two_opt(route: tuple[int, ...], distances: list[list[float]]) -> tuple[int, ...]:
    """Apply improving 2-opt reversals until no strictly shorter tour remains."""
    best = route
    changed = True
    while changed:
        changed = False
        for i in range(len(best) - 1):
            for j in range(i + 2, len(best)):
                if i == 0 and j == len(best) - 1:
                    continue  # reversing the complete cycle changes no edges
                candidate = best[:i+1] + tuple(reversed(best[i+1:j+1])) + best[j+1:]
                if route_length(candidate, distances) + 1e-12 < route_length(best, distances):
                    best, changed = candidate, True
                    break
            if changed:
                break
    return best

def solve(points: list[tuple[float, float]], *, ants: int = 24, iterations: int = 100,
          alpha: float = 1.0, beta: float = 3.0, evaporation: float = 0.35,
          seed: int = 0, two_opt: bool = True) -> Result:
    """Find a good closed tour; deterministic for a fixed seed and parameters."""
    validate(points)
    if ants < 1 or ants > 500 or iterations < 1 or iterations > 5000:
        raise ValueError("ants must be 1..500 and iterations 1..5000")
    if not all(math.isfinite(x) for x in (alpha, beta, evaporation)) or alpha < 0 or beta < 0 or not 0 < evaporation <= 1:
        raise ValueError("alpha/beta must be finite and nonnegative; evaporation must be in (0, 1]")
    n = len(points)
    d = [[math.hypot(points[i][0]-points[j][0], points[i][1]-points[j][1]) for j in range(n)] for i in range(n)]
    tau = [[1.0 for _ in range(n)] for _ in range(n)]
    rng = random.Random(seed)
    best: tuple[int, ...] | None = None
    best_len = math.inf
    history = []
    for _ in range(iterations):
        batch = []
        for _ant in range(ants):
            start = rng.randrange(n)
            route, remaining = [start], set(range(n)) - {start}
            while remaining:
                here = route[-1]
                weights = [(j, tau[here][j] ** alpha * (1.0 / d[here][j] if d[here][j] else 1.0) ** beta) for j in sorted(remaining)]
                total = sum(w for _, w in weights)
                if not math.isfinite(total) or total <= 0:
                    nxt = min(remaining)
                else:
                    target, acc, nxt = rng.random() * total, 0.0, weights[-1][0]
                    for j, weight in weights:
                        acc += weight
                        if acc >= target:
                            nxt = j
                            break
                route.append(nxt)
                remaining.remove(nxt)
            r = tuple(route)
            if two_opt:
                r = improve_two_opt(r, d)
            length = route_length(r, d)
            batch.append((r, length))
            if length < best_len:
                best, best_len = r, length
        for i in range(n):
            for j in range(n):
                tau[i][j] *= 1.0 - evaporation
        for route, length in batch:
            deposit = 1.0 / max(length, 1e-12)
            for a, b in zip(route, route[1:] + route[:1]):
                tau[a][b] += deposit
                tau[b][a] += deposit
        history.append(best_len)
    assert best is not None
    return Result(best, best_len, tuple(history))

def load_points(path: Path) -> list[tuple[float, float]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON points: {exc}") from exc
    if not isinstance(raw, list) or any(not isinstance(p, list) or len(p) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in p) for p in raw):
        raise ValueError("input must be a JSON array of [x, y] coordinate pairs")
    try:
        points = [(float(p[0]), float(p[1])) for p in raw]
    except (OverflowError, ValueError) as exc:
        raise ValueError("coordinates must be finite numbers within floating-point range") from exc
    validate(points)
    return points

def load_config(path: Path) -> dict[str, object]:
    """Load solver defaults from a JSON object, rejecting unknown settings."""
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON config: {exc}") from exc
    allowed = {"ants", "iterations", "seed", "alpha", "beta", "evaporation", "two_opt"}
    if not isinstance(config, dict) or set(config) - allowed:
        unknown = set(config) - allowed if isinstance(config, dict) else set()
        detail = f"; unknown keys: {', '.join(sorted(unknown))}" if unknown else ""
        raise ValueError(f"config must be a JSON object containing only {', '.join(sorted(allowed))}{detail}")
    return config

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("points", nargs="?", type=Path, help="JSON file containing [[x,y], ...]")
    parser.add_argument("--config", type=Path, help="JSON settings file (explicit CLI options override it)")
    parser.add_argument("--ants", type=int)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--alpha", type=float)
    parser.add_argument("--beta", type=float)
    parser.add_argument("--evaporation", type=float)
    parser.add_argument("--no-two-opt", action="store_true", help="disable 2-opt local search")
    args = parser.parse_args()
    config = load_config(args.config) if args.config else {}
    for key in ("ants", "iterations", "seed", "alpha", "beta", "evaporation"):
        value = getattr(args, key)
        if value is not None:
            config[key] = value
    if args.no_two_opt:
        config["two_opt"] = False
    points = load_points(args.points) if args.points else [(0.,0.),(4.,0.),(5.,3.),(2.,5.),(-1.,3.)]
    try:
        result = solve(points, **cast(Any, config))
    except TypeError as exc:
        raise ValueError(f"invalid solver configuration: {exc}") from exc
    print(json.dumps({"route": list(result.route), "distance": result.distance, "history": list(result.history)}, indent=2))
    return 0
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        raise SystemExit(f"error: {exc}")
