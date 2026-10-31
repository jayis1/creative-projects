"""CLI for mosaic-layout."""
import argparse
from planner import Part, plan, waste_summary


def main():
    parser = argparse.ArgumentParser(description="Plan a guillotine-cut sheet layout")
    parser.add_argument("width", type=int)
    parser.add_argument("height", type=int)
    parser.add_argument("parts", nargs="+", help="name:width:height[:quantity]")
    args = parser.parse_args()
    parts = []
    try:
        for spec in args.parts:
            fields = spec.split(":")
            if len(fields) not in (3, 4):
                raise ValueError("part must be name:width:height[:quantity]")
            parts.append(Part(fields[0], int(fields[1]), int(fields[2]), int(fields[3]) if len(fields) == 4 else 1))
        placed, _ = plan(args.width, args.height, parts)
    except ValueError as exc:
        parser.error(str(exc))
    for item in placed:
        print("{}: x={}, y={}, {}x{}{}".format(item.name, item.x, item.y, item.width, item.height, " rotated" if item.rotated else ""))
    stats = waste_summary(args.width, args.height, placed)
    print("Utilization: {:.1%} (waste: {})".format(stats["utilization"], stats["waste"]))


if __name__ == "__main__":
    main()
