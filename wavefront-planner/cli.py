"""Command-line interface for weighted-grid route planning."""
import argparse
import json
from pathlib import Path
import sys

from planner import Grid, find_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", help="JSON file with grid, start, and goal")
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"grid", "start", "goal"}:
            raise ValueError("scenario must contain exactly grid, start, and goal")
        grid = Grid.from_rows(data["grid"])
        route = find_path(grid, tuple(data["start"]), tuple(data["goal"]))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = {"reachable": route is not None}
    if route is not None:
        result.update(path=route.points, cost=route.cost, expanded=route.expanded)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
