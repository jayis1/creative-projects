from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib
from typing import Any

from .core import SolveResult, TrussModel, TrussSolver, ValidationError, summarize_model


EXAMPLE_MODELS = {
    "triangle": {
        "metadata": {"title": "Cantilever triangle"},
        "materials": [{"id": "steel", "E": 210000000000.0, "density": 7850.0, "yield_strength": 250000000.0}],
        "sections": [{"id": "rod", "A": 0.003}],
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 1.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "material": "steel", "section": "rod"},
            {"id": "BC", "start": "B", "end": "C", "material": "steel", "section": "rod"},
            {"id": "AC", "start": "A", "end": "C", "material": "steel", "section": "rod"},
        ],
        "supports": [
            {"node": "A", "fix": [True, True]},
            {"node": "B", "fix": [False, True]},
        ],
        "load_cases": [
            {"name": "service", "node_loads": [{"node": "C", "load": [0.0, -1000.0]}]},
            {"name": "gravity", "gravity": [0.0, -9.81], "include_self_weight": True},
        ],
    },
    "roof": {
        "metadata": {"title": "Roof truss"},
        "materials": [{"id": "steel", "E": 200000000000.0, "density": 7850.0, "yield_strength": 250000000.0}],
        "sections": [{"id": "chord", "A": 0.004}],
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 2.0, "y": 0.0},
            {"id": "C", "x": 4.0, "y": 0.0},
            {"id": "D", "x": 1.0, "y": 1.0},
            {"id": "E", "x": 3.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "material": "steel", "section": "chord"},
            {"id": "BC", "start": "B", "end": "C", "material": "steel", "section": "chord"},
            {"id": "AD", "start": "A", "end": "D", "material": "steel", "section": "chord"},
            {"id": "DB", "start": "D", "end": "B", "material": "steel", "section": "chord"},
            {"id": "BE", "start": "B", "end": "E", "material": "steel", "section": "chord"},
            {"id": "EC", "start": "E", "end": "C", "material": "steel", "section": "chord"},
            {"id": "DE", "start": "D", "end": "E", "material": "steel", "section": "chord"},
        ],
        "supports": [
            {"node": "A", "fix": [True, True]},
            {"node": "C", "fix": [False, True]},
        ],
        "load_cases": [
            {
                "name": "snow",
                "node_loads": [
                    {"node": "D", "load": [0.0, -6000.0]},
                    {"node": "E", "load": [0.0, -6000.0]}
                ]
            },
            {
                "name": "self-weight",
                "gravity": [0.0, -9.81],
                "include_self_weight": True
            }
        ]
    }
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve 2D truss finite element models")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="solve a JSON or TOML truss model")
    solve_parser.add_argument("input", type=Path, help="path to model file")
    solve_parser.add_argument("--case", dest="case_name", help="named load case to solve")
    solve_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    summary_parser = subparsers.add_parser("summary", help="print aggregate model statistics")
    summary_parser.add_argument("input", type=Path, help="path to model file")
    summary_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    cases_parser = subparsers.add_parser("list-load-cases", help="list available load cases")
    cases_parser.add_argument("input", type=Path, help="path to model file")

    example_parser = subparsers.add_parser("write-example", help="write an example model to disk")
    example_parser.add_argument("output", type=Path, help="destination file")
    example_parser.add_argument("--preset", choices=sorted(EXAMPLE_MODELS), default="triangle")

    return parser


def load_model(path: Path) -> dict[str, Any]:
    raw = path.read_text()
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(raw)
    if suffix == ".toml":
        return tomllib.loads(raw)
    raise ValidationError(f"unsupported input format: {path.suffix or '<none>'}; use .json or .toml")


def dump_model(path: Path, payload: dict[str, Any]) -> None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps(payload, indent=2))
        return
    if suffix == ".toml":
        path.write_text(_to_toml(payload).rstrip() + "\n")
        return
    raise ValidationError(f"unsupported output format: {path.suffix or '<none>'}; use .json or .toml")


def serialize_result(result: SolveResult) -> dict[str, Any]:
    return {
        "case_name": result.case_name,
        "displacements": {node: [dx, dy] for node, (dx, dy) in result.displacements.items()},
        "reactions": {node: [rx, ry] for node, (rx, ry) in result.reactions.items()},
        "elements": [
            {
                "id": item.element_id,
                "length": item.length,
                "strain": item.strain,
                "stress": item.stress,
                "axial_force": item.axial_force,
                "utilization": item.utilization,
                "mass": item.mass,
            }
            for item in result.element_results
        ],
        "max_displacement": result.max_displacement,
        "total_mass": result.total_mass,
        "total_length": result.total_length,
    }


def format_text(result: SolveResult) -> str:
    lines = [f"Load case: {result.case_name}", "Displacements:"]
    for node_id, (dx, dy) in result.displacements.items():
        lines.append(f"  {node_id}: dx={dx:.6e} m, dy={dy:.6e} m")
    lines.append("Reactions:")
    for node_id, (rx, ry) in result.reactions.items():
        lines.append(f"  {node_id}: Rx={rx:.3f} N, Ry={ry:.3f} N")
    lines.append("Element forces:")
    for item in result.element_results:
        util = "n/a" if item.utilization is None else f"{item.utilization:.3%}"
        lines.append(
            "  "
            f"{item.element_id}: axial={item.axial_force:.3f} N, stress={item.stress:.3f} Pa, "
            f"strain={item.strain:.6e}, utilization={util}, mass={item.mass:.3f} kg"
        )
    lines.append(f"Total length: {result.total_length:.3f} m")
    lines.append(f"Total mass: {result.total_mass:.3f} kg")
    lines.append(f"Max displacement magnitude: {result.max_displacement:.6e} m")
    return "\n".join(lines)


def format_summary(summary: dict[str, Any]) -> str:
    bbox = summary["bounding_box"]
    return "\n".join(
        [
            f"Title: {summary['title']}",
            f"Nodes: {summary['node_count']}",
            f"Elements: {summary['element_count']}",
            f"Supports: {summary['support_count']}",
            f"Load cases: {summary['load_case_count']}",
            f"Total length: {summary['total_length']:.3f} m",
            f"Total mass: {summary['total_mass']:.3f} kg",
            f"Bounding box: x=[{bbox['min_x']:.3f}, {bbox['max_x']:.3f}], y=[{bbox['min_y']:.3f}, {bbox['max_y']:.3f}]",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "write-example":
            payload = EXAMPLE_MODELS[args.preset]
            dump_model(args.output, payload)
            print(f"wrote {args.preset} example model to {args.output}")
            return 0

        model = TrussModel.from_dict(load_model(args.input))

        if args.command == "summary":
            summary = summarize_model(model)
            print(json.dumps(summary, indent=2) if args.json else format_summary(summary))
            return 0
        if args.command == "list-load-cases":
            names = [case.name for case in model.load_cases] or ["default"]
            print("\n".join(names))
            return 0
        if args.command == "solve":
            result = TrussSolver(model).solve(args.case_name)
            print(json.dumps(serialize_result(result), indent=2) if args.json else format_text(result))
            return 0
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError, ValidationError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 1


def _to_toml(value: Any, prefix: str = "") -> str:
    lines: list[str] = []
    scalars = {k: v for k, v in value.items() if not isinstance(v, (dict, list))}
    tables = {k: v for k, v in value.items() if isinstance(v, dict)}
    arrays = {k: v for k, v in value.items() if isinstance(v, list)}

    for key, item in scalars.items():
        lines.append(f"{key} = {_toml_scalar(item)}")

    for key, item in arrays.items():
        if not item:
            lines.append(f"{key} = []")
            continue
        if all(not isinstance(entry, (dict, list)) for entry in item):
            rendered = ", ".join(_toml_scalar(entry) for entry in item)
            lines.append(f"{key} = [{rendered}]")
            continue
        if all(isinstance(entry, dict) for entry in item):
            for entry in item:
                table_name = f"{prefix}{key}" if prefix else key
                lines.append(f"[[{table_name}]]")
                nested = _to_toml(entry, prefix=f"{table_name}.")
                if nested:
                    lines.append(nested.rstrip())
            continue
        raise ValidationError(f"cannot serialize mixed array for key: {key}")

    for key, item in tables.items():
        table_name = f"{prefix}{key}" if prefix else key
        lines.append(f"[{table_name}]")
        nested = _to_toml(item, prefix=f"{table_name}.")
        if nested:
            lines.append(nested.rstrip())

    return "\n".join(line for line in lines if line is not None) + ("\n" if lines else "")


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return repr(value)
    raise ValidationError(f"cannot serialize value to TOML: {value!r}")
