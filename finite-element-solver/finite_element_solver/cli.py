from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
import tomllib
from typing import Any, cast

from .examples import EXAMPLE_MODELS
from .io import dump_model, load_model
from .model import TrussModel, ValidationError
from .reporting import build_envelope, format_summary, format_text, serialize_result, summarize_model
from .solver import TrussSolver

LOGGER = logging.getLogger("finite_element_solver")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve 2D truss finite element models")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--log-file", type=Path, help="optional log destination")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="solve a truss model")
    solve_parser.add_argument("input", type=Path, help="path to model file")
    solve_group = solve_parser.add_mutually_exclusive_group()
    solve_group.add_argument("--case", dest="case_name", help="named load case to solve")
    solve_group.add_argument("--combination", help="named load combination to solve")
    solve_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    summary_parser = subparsers.add_parser("summary", help="print aggregate model statistics")
    summary_parser.add_argument("input", type=Path, help="path to model file")
    summary_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    cases_parser = subparsers.add_parser("list-load-cases", help="list available load cases")
    cases_parser.add_argument("input", type=Path, help="path to model file")

    combinations_parser = subparsers.add_parser("list-load-combinations", help="list available load combinations")
    combinations_parser.add_argument("input", type=Path, help="path to model file")

    envelope_parser = subparsers.add_parser("envelope", help="compute case and combination envelopes")
    envelope_parser.add_argument("input", type=Path, help="path to model file")
    envelope_parser.add_argument("--cases", nargs="*", default=None, help="specific load cases to include")
    envelope_parser.add_argument(
        "--combinations",
        nargs="*",
        default=None,
        help="specific load combinations to include; defaults to all combinations",
    )
    envelope_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    validate_parser = subparsers.add_parser("validate", help="validate a model without solving it")
    validate_parser.add_argument("input", type=Path, help="path to model file")

    example_parser = subparsers.add_parser("write-example", help="write an example model to disk")
    example_parser.add_argument("output", type=Path, help="destination file")
    example_parser.add_argument("--preset", choices=sorted(EXAMPLE_MODELS), default="triangle")

    return parser


def configure_logging(level_name: str, log_file: Path | None) -> None:
    handlers: list[logging.Handler] = []
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    else:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(
        level=getattr(logging, level_name),
        format="%(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level, args.log_file)
    try:
        if args.command == "write-example":
            payload = EXAMPLE_MODELS[args.preset]
            dump_model(args.output, payload)
            LOGGER.info("Wrote example '%s' to %s", args.preset, args.output)
            print(f"wrote {args.preset} example model to {args.output}")
            return 0

        LOGGER.info("Loading model from %s", args.input)
        model = TrussModel.from_dict(load_model(args.input))
        solver = TrussSolver(model)

        if args.command == "summary":
            summary = summarize_model(model)
            print(json.dumps(summary, indent=2) if args.json else format_summary(summary))
            return 0
        if args.command == "list-load-cases":
            names = [case.name for case in model.load_cases] or ["default"]
            print("\n".join(names))
            return 0
        if args.command == "list-load-combinations":
            names = [combo.name for combo in model.load_combinations]
            print("\n".join(names) if names else "none")
            return 0
        if args.command == "validate":
            print(f"model valid: {args.input}")
            return 0
        if args.command == "envelope":
            results = []
            selected_cases = args.cases or [case.name for case in model.load_cases] or [None]
            for case_name in selected_cases:
                results.append(solver.solve(case_name))
            selected_combos = args.combinations
            if selected_combos is None:
                selected_combos = [combo.name for combo in model.load_combinations]
            for combo_name in selected_combos:
                results.append(solver.solve_combination(combo_name))
            envelope = build_envelope(results)
            print(json.dumps(envelope, indent=2) if args.json else _format_envelope(envelope))
            return 0
        if args.command == "solve":
            if args.combination:
                result = solver.solve_combination(args.combination)
            else:
                result = solver.solve(args.case_name)
            print(json.dumps(serialize_result(result), indent=2) if args.json else format_text(result))
            return 0
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError, ValidationError) as exc:
        LOGGER.error("Command failed: %s", exc)
        parser.exit(1, f"error: {exc}\n")
    return 1


def _format_envelope(envelope: dict[str, object]) -> str:
    global_max = cast(dict[str, Any], envelope["global_max_displacement"])
    node_payloads = cast(dict[str, dict[str, Any]], envelope["nodes"])
    element_payloads = cast(dict[str, dict[str, Any]], envelope["elements"])
    lines = [
        f"Results included: {envelope['result_count']}",
        (
            "Global max displacement: "
            f"{global_max['node']} = {global_max['magnitude']:.6e} m from {global_max['source']}"
            if global_max["node"] is not None
            else "Global max displacement: none"
        ),
        "Node envelope:",
    ]
    for node_id, payload in node_payloads.items():
        lines.append(f"  {node_id}: {payload['max_displacement']:.6e} m from {payload['source']}")
    lines.append("Element envelope:")
    for element_id, payload in element_payloads.items():
        util = cast(dict[str, Any], payload["max_utilization"])
        axial = cast(dict[str, Any], payload["max_abs_axial_force"])
        stress = cast(dict[str, Any], payload["max_abs_stress"])
        util_text = "n/a" if util["value"] is None else f"{util['value']:.3%} from {util['source']}"
        lines.append(
            "  "
            f"{element_id}: |axial|={axial['value']:.3f} N from {axial['source']}, "
            f"|stress|={stress['value']:.3f} Pa from {stress['source']}, "
            f"utilization={util_text}"
        )
    return "\n".join(lines)
