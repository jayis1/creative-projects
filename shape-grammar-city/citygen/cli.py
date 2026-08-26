from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .analysis import compute_stats, shortest_path, validate_city
from .config import GenerationConfig, configure_logging, load_config
from .districts import analyze_districts
from .generator import Point, generate_city
from .io import load_city, write_text_output
from .reports import render_report_html
from .render import render_ascii, render_svg

LOGGER = logging.getLogger(__name__)


def add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, help="Load generation settings from JSON or TOML.")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--mode", choices=["grid", "organic", "radial"], default=None)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--landmarks", type=int, default=None)
    parser.add_argument(
        "--zone-weight",
        action="append",
        default=[],
        metavar="NAME=WEIGHT",
        help="Override zone weights, e.g. commercial=0.4",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and inspect procedural city layouts.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
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

    districts = subparsers.add_parser("districts", help="Analyze contiguous districts.")
    add_generation_arguments(districts)
    districts.add_argument("--input", type=Path)
    districts.add_argument("--min-size", type=int, default=6)
    districts.add_argument("--format", choices=["json", "markdown"], default="json")
    districts.add_argument("--output", type=Path)

    report = subparsers.add_parser("report", help="Render a self-contained HTML report.")
    add_generation_arguments(report)
    report.add_argument("--input", type=Path)
    report.add_argument("--title", default=None)
    report.add_argument("--cell-size", type=int, default=None)
    report.add_argument("--output", type=Path, required=True)

    batch = subparsers.add_parser("batch", help="Generate multiple cities and compare them.")
    add_generation_arguments(batch)
    batch.add_argument("--seeds", default=None, help="Comma-separated list of seeds for batch generation.")
    batch.add_argument("--metric", choices=["road_cells", "landmark_count", "largest_component"], default="road_cells")
    batch.add_argument("--output", type=Path)

    return parser


def _parse_zone_weights(items: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"invalid zone weight {item!r}; expected NAME=WEIGHT")
        name, raw_value = item.split("=", 1)
        weights[name.strip()] = float(raw_value)
    return weights


def _load_generation_config(args: argparse.Namespace) -> GenerationConfig:
    config = load_config(args.config) if getattr(args, "config", None) else GenerationConfig()
    overrides: dict[str, Any] = {}
    for key in ("width", "height", "seed", "mode", "iterations", "landmarks", "cell_size", "title"):
        value = getattr(args, key, None)
        if value is not None:
            overrides[key] = value
    if getattr(args, "zone_weight", None):
        overrides["zone_weights"] = {**config.zone_weights, **_parse_zone_weights(args.zone_weight)}
    else:
        overrides["zone_weights"] = dict(config.zone_weights)
    if getattr(args, "seeds", None):
        overrides["seeds"] = [int(part.strip()) for part in str(args.seeds).split(",") if part.strip()]
    else:
        overrides["seeds"] = list(config.seeds)
    merged = GenerationConfig(
        width=overrides.get("width", config.width),
        height=overrides.get("height", config.height),
        seed=overrides.get("seed", config.seed),
        mode=overrides.get("mode", config.mode),
        iterations=overrides.get("iterations", config.iterations),
        landmarks=overrides.get("landmarks", config.landmarks),
        zone_weights=overrides["zone_weights"],
        seeds=overrides["seeds"],
        cell_size=overrides.get("cell_size", config.cell_size),
        title=overrides.get("title", config.title),
    )
    merged.validate()
    return merged


def _build_city(args: argparse.Namespace):
    if getattr(args, "input", None):
        LOGGER.debug("Loading city from %s", args.input)
        return load_city(args.input)
    config = _load_generation_config(args)
    LOGGER.debug("Generating city with config: %s", config)
    return generate_city(
        width=config.width,
        height=config.height,
        seed=config.seed,
        mode=config.mode,
        iterations=config.iterations,
        zone_weights=config.zone_weights or None,
        landmark_count=config.landmarks,
    )


def _district_payload(city, min_size: int) -> list[dict[str, object]]:
    return [district.to_dict() for district in analyze_districts(city, min_size=min_size)]


def _format_district_markdown(items: list[dict[str, object]]) -> str:
    lines = ["| Name | Tile | Cells | Road Access | Waterfront |", "| --- | --- | ---: | ---: | --- |"]
    for item in items:
        lines.append(
            f"| {item['name']} | {item['tile']} | {item['size']} | {item['road_access']} | {'yes' if item['waterfront'] else 'no'} |"
        )
    return "\n".join(lines)


def _require_int(value: object, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"expected integer field {field_name!r}, got {value!r}")
    return value


def _batch_payload(args: argparse.Namespace) -> dict[str, object]:
    config = _load_generation_config(args)
    seeds = config.seeds or ([config.seed] if config.seed is not None else [0, 1, 2])
    runs: list[dict[str, object]] = []
    for seed in seeds:
        city = generate_city(
            width=config.width,
            height=config.height,
            seed=seed,
            mode=config.mode,
            iterations=config.iterations,
            zone_weights=config.zone_weights or None,
            landmark_count=config.landmarks,
        )
        stats = compute_stats(city)
        stats["district_count"] = len(analyze_districts(city))
        runs.append(stats)
    metric = args.metric
    best = max(runs, key=lambda item: _require_int(item[metric], metric))
    return {
        "mode": config.mode,
        "size": [config.width, config.height],
        "metric": metric,
        "runs": runs,
        "best_seed": best["seed"],
        "best_value": best[metric],
        "average_road_cells": round(sum(_require_int(item["road_cells"], "road_cells") for item in runs) / len(runs), 2),
        "average_landmarks": round(sum(_require_int(item["landmark_count"], "landmark_count") for item in runs) / len(runs), 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
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
            write_text_output(payload, args.output)
        elif args.command == "stats":
            city = _build_city(args)
            print(json.dumps(compute_stats(city), indent=2))
        elif args.command == "validate":
            city = _build_city(args)
            issues = validate_city(city)
            print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
        elif args.command == "route":
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
            write_text_output(payload, args.output)
        elif args.command == "districts":
            city = _build_city(args)
            items = _district_payload(city, args.min_size)
            payload = json.dumps(items, indent=2) if args.format == "json" else _format_district_markdown(items)
            write_text_output(payload, args.output)
        elif args.command == "report":
            city = _build_city(args)
            stats = compute_stats(city)
            districts = analyze_districts(city)
            config = _load_generation_config(args)
            payload = render_report_html(
                city,
                stats=stats,
                districts=districts,
                title=args.title or config.title,
                cell_size=config.cell_size,
            )
            write_text_output(payload, args.output)
        else:
            payload = _batch_payload(args)
            write_text_output(json.dumps(payload, indent=2), args.output)
    except ValueError as exc:
        parser.error(str(exc))
    return 0
