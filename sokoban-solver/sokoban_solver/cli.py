"""Command-line interface for the Sokoban solver project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .levels import get_level, list_levels
from .parser import parse_level
from .solver import SokobanSolver


def _read_text(path: str | None, inline_level: str | None, builtin: str | None) -> str:
    selected = sum(1 for value in (path, inline_level, builtin) if value)
    if selected != 1:
        raise ValueError("provide exactly one of --file, --level, or --builtin")
    if path:
        return Path(path).read_text(encoding="utf-8")
    if inline_level:
        return inline_level.replace("\\n", "\n")
    assert builtin is not None
    return get_level(builtin)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve and analyze Sokoban levels")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", help="path to a level file")
    common.add_argument("--level", help="inline level string; use \\n for newlines")
    common.add_argument("--builtin", choices=list_levels(), help="use a built-in sample level")
    common.add_argument("--title", default="untitled", help="level title")

    solve = subparsers.add_parser("solve", parents=[common], help="solve a level")
    solve.add_argument("--max-states", type=int, default=200_000)
    solve.add_argument("--json", action="store_true", help="emit JSON output")
    solve.add_argument("--show-frames", action="store_true", help="print replay frames after solving")

    render = subparsers.add_parser("render", parents=[common], help="render a level")
    render.add_argument("--highlight-solved", action="store_true")

    analyze = subparsers.add_parser("analyze", parents=[common], help="inspect a level")
    analyze.add_argument("--json", action="store_true")

    subparsers.add_parser("list-levels", help="list built-in sample levels")

    benchmark = subparsers.add_parser("benchmark", help="solve multiple built-in levels")
    benchmark.add_argument("--max-states", type=int, default=200_000)
    benchmark.add_argument("--json", action="store_true")
    return parser


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list-levels":
            for name in list_levels():
                print(name)
            return 0
        if args.command == "benchmark":
            rows = []
            failed = False
            for name in list_levels():
                board = parse_level(get_level(name), title=name)
                result = SokobanSolver(board).solve(max_states=args.max_states)
                payload = {"level": name, **_solve_payload(result)}
                rows.append(payload)
                failed = failed or (not result.solved)
            if args.json:
                print(json.dumps(rows, indent=2, sort_keys=True))
            else:
                for row in rows:
                    print(
                        f"{row['level']}: solved={row['solved']} pushes={row['pushes']} "
                        f"steps={row['player_steps']} explored={row['explored_states']}"
                    )
            return 1 if failed else 0

        text = _read_text(args.file, args.level, args.builtin)
        board = parse_level(text, title=args.title if args.title != "untitled" else (args.builtin or args.title))
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
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                for key, value in payload.items():
                    print(f"{key}: {value}")
            return 0

        result = solver.solve(max_states=args.max_states)
        if args.json:
            payload = _solve_payload(result)
            if args.show_frames:
                payload["frames"] = list(solver.replay(result))
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"solved: {result.solved}")
            print(f"reason: {result.reason}")
            print(f"moves: {result.move_sequence or '(none)'}")
            print(f"pushes: {result.push_sequence or '(none)'}")
            print(f"explored_states: {result.stats.explored_states}")
            print(f"deadlocks_pruned: {result.stats.deadlocks_pruned}")
            if args.show_frames:
                print("\n--- replay ---")
                for idx, frame in enumerate(solver.replay(result)):
                    print(f"frame {idx}")
                    print(frame)
        return 0 if result.solved else 1
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"error: {exc}")
        return 2
