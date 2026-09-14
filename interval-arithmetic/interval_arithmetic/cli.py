"""Command-line interval calculator."""
from __future__ import annotations
import argparse
import json
from .core import Interval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate conservative interval arithmetic")
    parser.add_argument("operation", choices=("add", "sub", "mul", "div"))
    parser.add_argument("left", type=float)
    parser.add_argument("right", type=float)
    parser.add_argument("--width", type=float, default=0.0, help="half-width applied to both inputs")
    args = parser.parse_args(argv)
    if args.width < 0:
        parser.error("--width must be non-negative")
    left = Interval(args.left - args.width, args.left + args.width)
    right = Interval(args.right - args.width, args.right + args.width)
    try:
        result_interval = {"add": left + right, "sub": left - right,
                           "mul": left * right, "div": left / right}[args.operation]
    except ZeroDivisionError as exc:
        parser.error(str(exc))
    result = {"lower": result_interval.lower, "upper": result_interval.upper}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
