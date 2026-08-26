from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import compute_stats
from .generator import CityMap, generate_city
from .render import render_ascii, render_svg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate city layouts with shape-grammar-inspired rules.")
    parser.add_argument("--width", type=int, default=41)
    parser.add_argument("--height", type=int, default=25)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--mode", choices=["grid", "organic"], default="grid")
    parser.add_argument("--iterations", type=int, default=45)
    parser.add_argument("--format", choices=["ascii", "svg", "json", "stats"], default="ascii")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input", type=Path, help="Load an existing city JSON instead of generating a new one.")
    return parser


def _load_city(path: Path) -> CityMap:
    return CityMap.from_dict(json.loads(path.read_text()))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    city = _load_city(args.input) if args.input else generate_city(
        width=args.width,
        height=args.height,
        seed=args.seed,
        mode=args.mode,
        iterations=args.iterations,
    )

    if args.format == "ascii":
        payload = render_ascii(city)
    elif args.format == "svg":
        payload = render_svg(city)
    elif args.format == "json":
        payload = city.to_json()
    else:
        payload = json.dumps(compute_stats(city), indent=2)

    if args.output:
        args.output.write_text(payload)
    else:
        print(payload)
    return 0
