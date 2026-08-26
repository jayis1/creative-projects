from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import compute_stats, shortest_path, validate_city
from .generator import CityMap, Point, generate_city
from .render import render_ascii, render_svg


def add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--width", type=int, default=41)
    parser.add_argument("--height", type=int, default=25)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--mode", choices=["grid", "organic", "radial"], default="grid")
    parser.add_argument("--iterations", type=int, default=45)
    parser.add_argument("--landmarks", type=int, default=4)
    parser.add_argument(
        "--zone-weight",
        action="append",
        default=[],
        metavar="NAME=WEIGHT",
        help="Override zone weights, e.g. commercial=0.4",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and inspect procedural city layouts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a city and render it.")
    add_generation_arguments(generate)
    generate.add_argument("--format", choices=["ascii", "svg", "json", "stats"], default="ascii")
    generate.add_argument("--output", type=Path)

    stats = subparsers.add_parser("stats", help="Compute stats for a generated or saved city.")
    add_generation_arguments(stats)
    stats.add_argument("--input", type=Path)

    validate = subparsers.add_parser("validate", help="Validate a generated or saved city.")
    add_generation_arguments(validate)
    validate.add_argument("--input", type=Path)

    route = subparsers.add_parser("route", help="Find a shortest route through the road network.")
    add_generation_arguments(route)
    route.add_argument("--input", type=Path)
    route.add_argument("--start", required=True, help="Start point as x,y")
    route.add_argument("--goal", required=True, help="Goal point as x,y")
    route.add_argument("--format", choices=["ascii", "json", "svg"], default="ascii")
    route.add_argument("--output", type=Path)

    return parser


def _parse_zone_weights(items: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"invalid zone weight {item!r}; expected NAME=WEIGHT")
        name, raw_value = item.split("=", 1)
        weights[name.strip()] = float(raw_value)
    return weights


def _load_city(path: Path) -> CityMap:
    return CityMap.from_dict(json.loads(path.read_text()))


def _build_city(args: argparse.Namespace) -> CityMap:
    if getattr(args, "input", None):
        return _load_city(args.input)
    zone_weights = _parse_zone_weights(args.zone_weight)
    return generate_city(
        width=args.width,
        height=args.height,
        seed=args.seed,
        mode=args.mode,
        iterations=args.iterations,
        zone_weights=zone_weights or None,
        landmark_count=args.landmarks,
    )


def _write_or_print(payload: str, output: Path | None) -> None:
    if output:
        output.write_text(payload)
    else:
        print(payload)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            city = _build_city(args)
            if args.format == "ascii":
                payload = render_ascii(city)
            elif args.format == "svg":
                payload = render_svg(city)
            elif args.format == "json":
                payload = city.to_json()
            else:
                payload = json.dumps(compute_stats(city), indent=2)
            _write_or_print(payload, args.output)
        elif args.command == "stats":
            city = _build_city(args)
            print(json.dumps(compute_stats(city), indent=2))
        elif args.command == "validate":
            city = _build_city(args)
            issues = validate_city(city)
            print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
        else:
            city = _build_city(args)
            start = Point.parse(args.start)
            goal = Point.parse(args.goal)
            path = shortest_path(city, start, goal)
            if args.format == "ascii":
                payload = render_ascii(city, path=path)
            elif args.format == "svg":
                payload = render_svg(city, path=path)
            else:
                payload = json.dumps({"path": [[point.x, point.y] for point in path], "steps": len(path) - 1}, indent=2)
            _write_or_print(payload, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    return 0
