from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core import TrussModel, TrussSolver, ValidationError


EXAMPLE_MODEL = {
    "nodes": [
        {"id": "A", "x": 0.0, "y": 0.0},
        {"id": "B", "x": 1.0, "y": 0.0},
        {"id": "C", "x": 1.0, "y": 1.0, "load": [0.0, -1000.0]},
    ],
    "elements": [
        {"id": "AB", "start": "A", "end": "B", "E": 210000000000.0, "A": 0.003},
        {"id": "BC", "start": "B", "end": "C", "E": 210000000000.0, "A": 0.003},
        {"id": "AC", "start": "A", "end": "C", "E": 210000000000.0, "A": 0.003},
    ],
    "supports": [
        {"node": "A", "fix": [True, True]},
        {"node": "B", "fix": [False, True]},
    ],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve 2D truss finite element models")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="solve a JSON truss model")
    solve_parser.add_argument("input", type=Path, help="path to JSON model file")
    solve_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    example_parser = subparsers.add_parser("write-example", help="write an example model to disk")
    example_parser.add_argument("output", type=Path, help="destination JSON file")

    return parser


def load_model(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def serialize_result(result) -> dict[str, Any]:
    return {
        "displacements": {node: [dx, dy] for node, (dx, dy) in result.displacements.items()},
        "reactions": {node: [rx, ry] for node, (rx, ry) in result.reactions.items()},
        "elements": [
            {
                "id": item.element_id,
                "length": item.length,
                "strain": item.strain,
                "stress": item.stress,
                "axial_force": item.axial_force,
            }
            for item in result.element_results
        ],
        "max_displacement": result.max_displacement,
    }


def format_text(result) -> str:
    lines = ["Displacements:"]
    for node_id, (dx, dy) in result.displacements.items():
        lines.append(f"  {node_id}: dx={dx:.6e} m, dy={dy:.6e} m")
    lines.append("Reactions:")
    for node_id, (rx, ry) in result.reactions.items():
        lines.append(f"  {node_id}: Rx={rx:.3f} N, Ry={ry:.3f} N")
    lines.append("Element forces:")
    for item in result.element_results:
        lines.append(
            f"  {item.element_id}: axial={item.axial_force:.3f} N, stress={item.stress:.3f} Pa, strain={item.strain:.6e}"
        )
    lines.append(f"Max displacement magnitude: {result.max_displacement:.6e} m")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "write-example":
            args.output.write_text(json.dumps(EXAMPLE_MODEL, indent=2))
            print(f"wrote example model to {args.output}")
            return 0
        if args.command == "solve":
            model = TrussModel.from_dict(load_model(args.input))
            result = TrussSolver(model).solve()
            if args.json:
                print(json.dumps(serialize_result(result), indent=2))
            else:
                print(format_text(result))
            return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 1
