"""Command-line interface for the Sokoban solver project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .parser import parse_level
from .solver import SokobanSolver


def _read_text(path: str | None, inline_level: str | None) -> str:
    if path and inline_level:
        raise ValueError("use either --file or --level, not both")
    if path:
        return Path(path).read_text(encoding="utf-8")
    if inline_level:
        return inline_level.replace("\\n", "\n")
    raise ValueError("provide --file or --level")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve and analyze Sokoban levels")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", help="path to a level file")
    common.add_argument("--level", help="inline level string; use \\n for newlines")
    common.add_argument("--title", default="untitled", help="level title")

    solve = subparsers.add_parser("solve", parents=[common], help="solve a level")
    solve.add_argument("--max-states", type=int, default=200_000)
    solve.add_argument("--json", action="store_true", help="emit JSON output")

    render = subparsers.add_parser("render", parents=[common], help="render a level")
    render.add_argument("--highlight-solved", action="store_true")

    analyze = subparsers.add_parser("analyze", parents=[common], help="inspect a level")
    analyze.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        text = _read_text(args.file, args.level)
        board = parse_level(text, title=args.title)
        solver = SokobanSolver(board)
        if args.command == "render":
            if args.highlight_solved:
                result = solver.solve(max_states=50_000)
                if result.solved and result.steps:
                    final = result.steps[-1]
                    print(board.render(player=final.player, boxes=final.boxes))
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
            payload = {
                "solved": result.solved,
                "reason": result.reason,
                "move_sequence": result.move_sequence,
                "pushes": result.pushes,
                "player_steps": result.stats.player_steps,
                "explored_states": result.stats.explored_states,
                "generated_states": result.stats.generated_states,
                "deadlocks_pruned": result.stats.deadlocks_pruned,
                "repeated_states": result.stats.repeated_states,
                "frontier_max": result.stats.frontier_max,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"solved: {result.solved}")
            print(f"reason: {result.reason}")
            print(f"moves: {result.move_sequence or '(none)'}")
            print(f"pushes: {result.pushes}")
            print(f"explored_states: {result.stats.explored_states}")
            print(f"deadlocks_pruned: {result.stats.deadlocks_pruned}")
        return 0 if result.solved else 1
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"error: {exc}")
        return 2
