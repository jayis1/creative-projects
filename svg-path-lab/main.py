"""Command-line interface for svg-path-lab."""
import argparse
import json
from pathlib import Path

from pathlab import analyze, analyze_svg


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SVG path geometry (M/L/H/V/C/S/Q/T/Z).")
    parser.add_argument("path_data", nargs="?", help="SVG path-data string")
    parser.add_argument("--file", type=Path, help="read path data from a UTF-8 text file")
    parser.add_argument("--svg", type=Path, help="inspect all path elements in an SVG/XML file")
    parser.add_argument("--steps", type=int, default=32, help="curve samples per segment (1..10000)")
    parser.add_argument("--demo", action="store_true", help="analyze a deterministic sample curve")
    args = parser.parse_args()
    if sum((args.path_data is not None, args.file is not None, args.svg is not None, args.demo)) != 1:
        parser.error("provide exactly one of path_data, --file, --svg, or --demo")
    try:
        if args.demo:
            result = analyze("M 0 0 C 0 10 10 10 10 0 Z", args.steps)
        elif args.svg:
            if args.svg.stat().st_size > 5_000_000:
                raise ValueError("SVG input exceeds 5 MB limit")
            result = analyze_svg(args.svg.read_text(encoding="utf-8"), args.steps)
        else:
            data = args.file.read_text(encoding="utf-8") if args.file else args.path_data
            result = analyze(data, args.steps)
        print(json.dumps(result, indent=2))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
