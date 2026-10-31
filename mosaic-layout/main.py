"""CLI for mosaic-layout."""
import argparse
import json
from planner import Part, plan, waste_summary


def main():
    parser = argparse.ArgumentParser(description="Plan a guillotine-cut sheet layout")
    parser.add_argument("width", type=int)
    parser.add_argument("height", type=int)
    parser.add_argument("parts", nargs="+", help="name:width:height[:quantity]")
    parser.add_argument("--no-rotate", action="store_true", help="disallow part rotation")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    args = parser.parse_args()
    parts = []
    try:
        for spec in args.parts:
            fields = spec.split(":")
            if len(fields) not in (3, 4):
                raise ValueError("part must be name:width:height[:quantity]")
            parts.append(Part(fields[0], int(fields[1]), int(fields[2]), int(fields[3]) if len(fields) == 4 else 1))
        placed, free = plan(args.width, args.height, parts, allow_rotation=not args.no_rotate)
    except ValueError as exc:
        parser.error(str(exc))
    stats = waste_summary(args.width, args.height, placed)
    if args.json:
        print(json.dumps({"sheet": {"width": args.width, "height": args.height}, "placements": [item.__dict__ for item in placed], "free_rectangles": free, "summary": stats}, sort_keys=True))
        return
    for item in placed:
        print("{}: x={}, y={}, {}x{}{}".format(item.name, item.x, item.y, item.width, item.height, " rotated" if item.rotated else ""))
    print("Utilization: {:.1%} (waste: {})".format(stats["utilization"], stats["waste"]))


if __name__ == "__main__":
    main()
