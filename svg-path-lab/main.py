"""Command-line interface for svg-path-lab."""
import argparse
import json
from pathlib import Path

from pathlab import analyze


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SVG path geometry (M/L/H/V/C/S/Q/T/Z).")
    parser.add_argument("path_data", nargs="?", help="SVG path-data string")
    parser.add_argument("--file", type=Path, help="read path data from a UTF-8 text file")
    parser.add_argument("--steps", type=int, default=32, help="curve samples per segment (1..10000)")
    parser.add_argument("--demo", action="store_true", help="analyze a deterministic sample curve")
    args = parser.parse_args()
    if sum((args.path_data is not None, args.file is not None, args.demo)) != 1:
        parser.error("provide exactly one of path_data, --file, or --demo")
    try:
        data = "M 0 0 C 0 10 10 10 10 0 Z" if args.demo else args.file.read_text(encoding="utf-8") if args.file else args.path_data
        print(json.dumps(analyze(data, args.steps), indent=2))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
