"""Command-line interface for the Sokoban solver project."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .config import RuntimeConfig, load_config
from .io import LevelEntry, load_level_text, parse_level_pack
from .levels import get_level, list_levels
from .parser import parse_level
from .solver import SokobanSolver, solve_level_pack

LOGGER = logging.getLogger("sokoban_solver")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="[%(levelname)s] %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve and analyze Sokoban levels")
    parser.add_argument("--config", help="load CLI defaults from a JSON or TOML config file")
    parser.add_argument("--log-level", default=None, help="logging level (DEBUG, INFO, WARNING, ERROR)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", help="path to a level file")
    common.add_argument("--level", help="inline level string; use \\n for newlines")
    common.add_argument("--builtin", choices=list_levels(), help="use a built-in sample level")
    common.add_argument("--title", default="untitled", help="level title")

    solve = subparsers.add_parser("solve", parents=[common], help="solve a level")
    solve.add_argument("--max-states", type=int, default=None)
    solve.add_argument("--json", action="store_true", help="emit JSON output")
    solve.add_argument("--show-frames", action="store_true", help="print replay frames after solving")
    solve.add_argument("--output", help="write solution payload to a JSON file")

    render = subparsers.add_parser("render", parents=[common], help="render a level")
    render.add_argument("--highlight-solved", action="store_true")

    analyze = subparsers.add_parser("analyze", parents=[common], help="inspect a level")
    analyze.add_argument("--json", action="store_true")
    analyze.add_argument("--show-overlay", action="store_true", help="print an annotated explain overlay")

    explain = subparsers.add_parser("explain", parents=[common], help="render annotated deadlock and reachability info")
    explain.add_argument("--json", action="store_true")

    subparsers.add_parser("list-levels", help="list built-in sample levels")

    benchmark = subparsers.add_parser("benchmark", help="solve multiple built-in levels")
    benchmark.add_argument("--max-states", type=int, default=None)
    benchmark.add_argument("--json", action="store_true")

    solve_pack = subparsers.add_parser("solve-pack", help="solve every level in a text level pack")
    solve_pack.add_argument("--file", required=True, help="path to a multi-level pack file")
    solve_pack.add_argument("--max-states", type=int, default=None)
    solve_pack.add_argument("--json", action="store_true")

    subparsers.add_parser("version", help="print version and exit")
    return parser


def _resolve_runtime(args: argparse.Namespace) -> RuntimeConfig:
    config_data = load_config(args.config)
    config = RuntimeConfig.from_mapping(config_data)
    if args.log_level:
        config = RuntimeConfig(
            max_states=config.max_states,
            json_output=config.json_output,
            show_frames=config.show_frames,
            log_level=args.log_level.upper(),
        )
    return config


def _effective_max_states(value: int | None, config: RuntimeConfig) -> int:
    max_states = config.max_states if value is None else value
    if max_states <= 0:
        raise ValueError("max_states must be positive")
    return max_states


def _parse_single_level(args: argparse.Namespace):
    text = load_level_text(args.file, args.level, args.builtin)
    title = args.title if args.title != "untitled" else (args.builtin or args.title)
    return parse_level(text, title=title)


def _solve_payload(result):
    return {
        "solved": result.solved,
        "reason": result.reason,
        "move_sequence": result.move_sequence,
        "push_sequence": result.push_sequence,
        "pushes": result.pushes,
        "player_steps": result.stats.player_steps,
        "explored_states": result.stats.explored_states,
        "generated_states": result.stats.generated_states,
        "deadlocks_pruned": result.stats.deadlocks_pruned,
        "repeated_states": result.stats.repeated_states,
        "frontier_max": result.stats.frontier_max,
        "solved_depth": result.stats.solved_depth,
    }


def _print_payload(payload: object, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        for row in payload:
            print(
                f"{row['level']}: solved={row['solved']} pushes={row['pushes']} "
                f"steps={row['player_steps']} explored={row['explored_states']}"
            )
        return
    assert isinstance(payload, dict)
    for key, value in payload.items():
        print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        runtime = _resolve_runtime(args)
        configure_logging(runtime.log_level)
        LOGGER.debug("parsed arguments: %s", args)

        if args.command == "version":
            print("sokoban-solver 0.3.0")
            return 0
        if args.command == "list-levels":
            for name in list_levels():
                print(name)
            return 0
        if args.command == "benchmark":
            max_states = _effective_max_states(args.max_states, runtime)
            rows = []
            failed = False
            for name in list_levels():
                board = parse_level(get_level(name), title=name)
                result = SokobanSolver(board).solve(max_states=max_states)
                payload = {"level": name, **_solve_payload(result)}
                rows.append(payload)
                failed = failed or (not result.solved)
            _print_payload(rows, as_json=args.json or runtime.json_output)
            return 1 if failed else 0
        if args.command == "solve-pack":
            max_states = _effective_max_states(args.max_states, runtime)
            pack_entries = parse_level_pack(Path(args.file).read_text(encoding="utf-8"))
            rows = solve_level_pack(pack_entries, max_states=max_states)
            _print_payload(rows, as_json=args.json or runtime.json_output)
            return 0 if all(row["solved"] for row in rows) else 1

        board = _parse_single_level(args)
        solver = SokobanSolver(board)

        if args.command == "render":
            if args.highlight_solved:
                result = solver.solve(max_states=50_000)
                if result.solved and result.steps:
                    final = result.steps[-1]
                    print(board.render(player=final.player_after, boxes=final.boxes))
                    return 0
            print(board.render())
            return 0
        if args.command == "analyze":
            payload = solver.analyze()
            _print_payload(payload, as_json=args.json or runtime.json_output)
            if args.show_overlay:
                print("\n--- overlay ---")
                print(solver.explain()["overlay"])
            return 0
        if args.command == "explain":
            payload = solver.explain()
            _print_payload(payload, as_json=args.json or runtime.json_output)
            return 0

        max_states = _effective_max_states(args.max_states, runtime)
        result = solver.solve(max_states=max_states)
        payload = _solve_payload(result)
        show_frames = args.show_frames or runtime.show_frames
        if show_frames:
            payload["frames"] = list(solver.replay(result))
        if args.output:
            Path(args.output).write_text(json.dumps(solver.export_solution(result, include_frames=show_frames), indent=2, sort_keys=True), encoding="utf-8")
            LOGGER.info("wrote solution JSON to %s", args.output)
        if args.json or runtime.json_output:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"solved: {result.solved}")
            print(f"reason: {result.reason}")
            print(f"moves: {result.move_sequence or '(none)'}")
            print(f"pushes: {result.push_sequence or '(none)'}")
            print(f"explored_states: {result.stats.explored_states}")
            print(f"deadlocks_pruned: {result.stats.deadlocks_pruned}")
            if show_frames:
                print("\n--- replay ---")
                for idx, frame in enumerate(solver.replay(result)):
                    print(f"frame {idx}")
                    print(frame)
        return 0 if result.solved else 1
    except Exception as exc:  # pragma: no cover - CLI guardrail
        LOGGER.error("%s", exc)
        print(f"error: {exc}")
        return 2
