#!/usr/bin/env python3
"""Deterministic multi-car elevator dispatch simulation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Request:
    time: int
    origin: int
    destination: int


@dataclass
class Car:
    floor: int = 0
    available: int = 0
    distance: int = 0


@dataclass(frozen=True)
class Result:
    request: Request
    car: int
    pickup_time: int
    arrival_time: int
    wait: int
    ride: int


def validate_requests(requests: Iterable[Request], floors: int) -> list[Request]:
    if floors < 2:
        raise ValueError("floors must be at least 2")
    items = list(requests)
    for index, item in enumerate(items):
        if item.time < 0:
            raise ValueError(f"request {index}: time must be nonnegative")
        if not 0 <= item.origin < floors or not 0 <= item.destination < floors:
            raise ValueError(f"request {index}: floor outside 0..{floors - 1}")
        if item.origin == item.destination:
            raise ValueError(f"request {index}: origin and destination must differ")
    return sorted(items, key=lambda r: r.time)


def simulate(requests: Iterable[Request], floors: int = 10, cars: int = 2) -> list[Result]:
    """Assign each request to the car minimizing estimated pickup time.

    Cars are modeled as returning to their starting floor after each trip; this
    deliberately bounded model makes dispatch choices reproducible and clear.
    """
    if cars < 1 or cars > 64:
        raise ValueError("cars must be between 1 and 64")
    work = validate_requests(requests, floors)
    fleet = [Car() for _ in range(cars)]
    results: list[Result] = []
    for req in work:
        # Choose earliest pickup; ties go to the lowest car index.
        candidates = [(max(req.time, car.available) + abs(car.floor - req.origin), i)
                      for i, car in enumerate(fleet)]
        pickup, index = min(candidates)
        car = fleet[index]
        travel = abs(req.origin - req.destination)
        finish = pickup + travel
        car.distance += abs(car.floor - req.origin) + travel
        car.floor = req.destination
        car.available = finish
        results.append(Result(req, index, pickup, finish, pickup - req.time, travel))
    return results


def parse_input(path: Path) -> tuple[int, int, list[Request]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read request file: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("requests"), list):
        raise ValueError("input must be an object containing a requests array")
    floors, cars = data.get("floors", 10), data.get("cars", 2)
    if type(floors) is not int or type(cars) is not int:
        raise ValueError("floors and cars must be integers")
    requests = []
    for i, row in enumerate(data["requests"]):
        if not isinstance(row, dict) or any(type(row.get(k)) is not int for k in ("time", "origin", "destination")):
            raise ValueError(f"request {i} must contain integer time, origin, destination")
        requests.append(Request(row["time"], row["origin"], row["destination"]))
    validate_requests(requests, floors)
    return floors, cars, requests


def summarize(results: Iterable[Result], cars: int) -> dict[str, object]:
    """Return fleet-level service metrics without changing assignment results."""
    rows = list(results)
    waits = [row.wait for row in rows]
    return {
        "request_count": len(rows),
        "total_wait": sum(waits),
        "average_wait": (sum(waits) / len(waits)) if waits else 0.0,
        "maximum_wait": max(waits, default=0),
        "car_requests": [sum(row.car == i for row in rows) for i in range(cars)],
    }


def demo() -> list[Result]:
    return simulate([Request(0, 0, 5), Request(1, 2, 8), Request(4, 9, 1), Request(6, 3, 7)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON request file")
    parser.add_argument("--demo", action="store_true", help="run a built-in scenario")
    parser.add_argument("--floors", type=int, default=10, help="number of floors for demo")
    parser.add_argument("--cars", type=int, default=2, help="elevator count for demo")
    parser.add_argument("--summary", action="store_true", help="print aggregate service metrics instead of per-request rows")
    args = parser.parse_args(argv)
    try:
        floors = args.floors
        car_count = args.cars
        if args.demo:
            rows = simulate([Request(0, 0, 5), Request(1, 2, 8), Request(4, 9, 1), Request(6, 3, 7)], floors, car_count)
        elif args.input:
            floors, car_count, requests = parse_input(args.input)
            rows = simulate(requests, floors, car_count)
        else:
            parser.error("provide an input file or --demo")
        output = summarize(rows, car_count) if args.summary else [asdict(row) for row in rows]
        print(json.dumps(output, indent=2))
        return 0
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
